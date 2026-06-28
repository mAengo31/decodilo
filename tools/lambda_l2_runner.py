#!/usr/bin/env python3
"""Run the Lambda L2 remote split learner/syncer experiment.

This is intentionally a local operator script, not a production scheduler. It performs
real Lambda launch/terminate mutations when executed.
"""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import tarfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from decodilo.lambda_cloud.l2_remote_runtime_evidence_package import (
    build_lambda_l2_remote_runtime_evidence_package_from_dir,
    write_lambda_l2_remote_runtime_evidence_package,
)

API_BASE = "https://cloud.lambdalabs.com/api/v1"
REMOTE_SRC = "/home/ubuntu/diloco_l2_src"
REMOTE_RUN = "/home/ubuntu/lambda_l2_run"
DEFAULT_PORT = 28080
_BACKGROUND_PROCS: list[subprocess.Popen[bytes]] = []


@dataclass(frozen=True)
class Instance:
    role: str
    instance_id: str
    ip: str
    region: str
    instance_type: str


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    parser.add_argument(
        "--ssh-private-key",
        type=Path,
        default=Path.home() / ".ssh" / "diloco_lambda",
    )
    parser.add_argument("--ssh-key-name", default=None)
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--instance-type", default="gpu_1x_a10")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--run-id", default=f"lambda-l2-{int(time.time())}")
    parser.add_argument(
        "--evidence-root",
        type=Path,
        default=Path("docs/evidence/lambda_l2_remote_adamw_nesterov"),
    )
    parser.add_argument("--skip-launch", action="store_true", help="Only print planned commands")
    args = parser.parse_args()

    api_key, env_ssh_key = _load_env(args.env_file)
    ssh_key_name = args.ssh_key_name or env_ssh_key
    if not ssh_key_name:
        raise SystemExit("missing Lambda SSH key name")
    bundle = _make_source_bundle(Path.cwd(), args.run_id)
    evidence_dir = args.evidence_root / args.run_id
    if args.skip_launch:
        _print_planned_commands(args, ssh_key_name=ssh_key_name, evidence_dir=evidence_dir)
        return 0

    owned: list[Instance] = []
    try:
        _assert_no_live_instances(api_key)
        roles = ["syncer", "learner-0", "learner-1"]
        for role in roles:
            instance_id = _launch_instance(api_key, args.region, args.instance_type, ssh_key_name)
            owned.append(Instance(role, instance_id, "", args.region, args.instance_type))
            print(
                json.dumps({"event": "launched", "role": role, "instance_id": instance_id}),
                flush=True,
            )
        owned = _wait_for_ips(api_key, owned)
        for inst in owned:
            _wait_for_ssh(inst.ip, args.ssh_private_key)
            _install_source(inst.ip, args.ssh_private_key, bundle)
        syncer = _by_role(owned, "syncer")
        _start_syncer(syncer, args)
        _wait_remote_file(syncer.ip, args.ssh_private_key, f"{REMOTE_RUN}/syncer_ready.json")
        _start_ssh_tunnels(owned, syncer, args)
        _wait_learner_tunnels(owned, args)
        _run_learners(owned, "127.0.0.1", args)
        _shutdown_syncer(syncer, args)
        evidence_dir.mkdir(parents=True, exist_ok=True)
        _collect_evidence(owned, args, evidence_dir)
        _write_layout(owned, args, evidence_dir)
    except Exception as exc:  # noqa: BLE001 - collect partial remote evidence before teardown
        if owned:
            evidence_dir.mkdir(parents=True, exist_ok=True)
            (evidence_dir / "failure.json").write_text(
                json.dumps({"error": str(exc)}, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            try:
                _collect_evidence(owned, args, evidence_dir)
                _write_layout(owned, args, evidence_dir)
            except Exception as collect_exc:  # noqa: BLE001
                (evidence_dir / "failure_collect_error.json").write_text(
                    json.dumps({"error": str(collect_exc)}, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
        raise
    finally:
        _terminate_all(api_key, [inst.instance_id for inst in owned])
        _cleanup_background_procs()
        final_count = _wait_until_owned_absent(api_key, [inst.instance_id for inst in owned])
        if owned:
            evidence_dir.mkdir(parents=True, exist_ok=True)
            _write_termination(owned, final_count, evidence_dir)
    if owned:
        package = build_lambda_l2_remote_runtime_evidence_package_from_dir(evidence_dir)
        write_lambda_l2_remote_runtime_evidence_package(
            evidence_dir / "lambda_l2_evidence_package.json",
            package,
        )
        print(package.to_json(), end="")
        return 0 if package.lambda_l2_remote_runtime_passed else 2
    return 1


def _load_env(path: Path) -> tuple[str, str | None]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values["LAMBDA_API_KEY"], values.get("LAMBDA_SSH_KEY")


def _api(api_key: str, method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = Request(
        API_BASE + path,
        method=method,
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "decodilo-lambda-l2-runner/0.1",
        },
    )
    try:
        with urlopen(req, timeout=30) as response:  # noqa: S310 - fixed Lambda API endpoint
            body = response.read()
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Lambda API {method} {path} failed: {exc.code} {body}") from exc
    return json.loads(body.decode("utf-8")) if body else {}


def _assert_no_live_instances(api_key: str) -> None:
    instances = _list_instances(api_key)
    if instances:
        ids = [str(item.get("id")) for item in instances]
        raise RuntimeError(f"refusing L2 launch while live instances exist: {ids}")


def _list_instances(api_key: str) -> list[dict[str, Any]]:
    payload = _api(api_key, "GET", "/instances")
    data = payload.get("data", []) if isinstance(payload, dict) else []
    return list(data)


def _launch_instance(api_key: str, region: str, instance_type: str, ssh_key_name: str) -> str:
    payload = {
        "region_name": region,
        "instance_type_name": instance_type,
        "ssh_key_names": [ssh_key_name],
        "quantity": 1,
    }
    response = _api(api_key, "POST", "/instance-operations/launch", payload)
    data = response.get("data", {}) if isinstance(response, dict) else {}
    instances = data.get("instance_ids") or data.get("instances") or []
    if instances and isinstance(instances[0], dict):
        return str(instances[0].get("id"))
    if instances:
        return str(instances[0])
    launched = data.get("launched_instances") or []
    if launched:
        return str(launched[0].get("id"))
    raise RuntimeError(f"could not parse launch response shape: {response}")


def _wait_for_ips(api_key: str, owned: list[Instance]) -> list[Instance]:
    ids = {inst.instance_id: inst for inst in owned}
    deadline = time.time() + 360
    while time.time() < deadline:
        live = _list_instances(api_key)
        by_id = {str(item.get("id")): item for item in live}
        resolved: list[Instance] = []
        for instance_id, inst in ids.items():
            item = by_id.get(instance_id)
            ip = _extract_ip(item or {})
            if not ip:
                break
            resolved.append(Instance(inst.role, instance_id, ip, inst.region, inst.instance_type))
        else:
            return resolved
        time.sleep(5)
    raise TimeoutError("timed out waiting for instance IPs")


def _extract_ip(item: dict[str, Any]) -> str | None:
    return (
        item.get("ip")
        or item.get("ip_address")
        or item.get("public_ip")
        or item.get("hostname")
        or item.get("jupyter_token") and item.get("ip")
    )


def _ssh_base(ip: str, key: Path) -> list[str]:
    return [
        "ssh",
        "-i",
        str(key),
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        "UserKnownHostsFile=/dev/null",
        "-o",
        "ConnectTimeout=10",
        f"ubuntu@{ip}",
    ]


def _ssh(
    ip: str,
    key: Path,
    remote: str,
    *,
    timeout: int = 120,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [*_ssh_base(ip, key), remote],
        text=True,
        capture_output=True,
        timeout=timeout,
        check=True,
    )


def _wait_for_ssh(ip: str, key: Path) -> None:
    deadline = time.time() + 240
    last = ""
    while time.time() < deadline:
        try:
            _ssh(ip, key, "echo ok", timeout=15)
            return
        except Exception as exc:  # noqa: BLE001
            last = str(exc)
            time.sleep(5)
    raise TimeoutError(f"SSH not ready for {ip}: {last}")


def _make_source_bundle(root: Path, run_id: str) -> Path:
    bundle = Path("/tmp") / f"diloco-l2-src-{run_id}.tar.gz"
    with tarfile.open(bundle, "w:gz") as tar:
        for name in ["src", "pyproject.toml", "README.md"]:
            tar.add(root / name, arcname=name)
    return bundle


def _install_source(ip: str, key: Path, bundle: Path) -> None:
    _ssh(ip, key, f"rm -rf {REMOTE_SRC} {REMOTE_RUN} && mkdir -p {REMOTE_SRC} {REMOTE_RUN}")
    subprocess.run(
        [
            "scp",
            "-i",
            str(key),
            "-o",
            "StrictHostKeyChecking=no",
            "-o",
            "UserKnownHostsFile=/dev/null",
            str(bundle),
            f"ubuntu@{ip}:/home/ubuntu/diloco_l2_src.tar.gz",
        ],
        check=True,
    )
    _ssh(
        ip,
        key,
        (
            f"tar -xzf /home/ubuntu/diloco_l2_src.tar.gz -C {REMOTE_SRC} "
            "&& python3 -m pip install --user 'pydantic>=2,<3' "
            f"&& cd {REMOTE_SRC} && PYTHONPATH=src python3 -c "
            + shlex.quote("import decodilo, numpy, pydantic; print('deps-ok')")
        ),
        timeout=240,
    )


def _start_syncer(syncer: Instance, args: argparse.Namespace) -> None:
    cmd = _syncer_command(args)
    remote = (
        f"mkdir -p {REMOTE_RUN} && cd {REMOTE_SRC} && "
        f"{cmd} > {REMOTE_RUN}/syncer.stdout 2> {REMOTE_RUN}/syncer.stderr"
    )
    proc = subprocess.Popen(
        [*_ssh_base(syncer.ip, args.ssh_private_key), remote],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    _BACKGROUND_PROCS.append(proc)


def _syncer_command(args: argparse.Namespace) -> str:
    return shlex.join(
        [
            "env",
            "PYTHONPATH=src",
            "python3",
            "-m",
            "decodilo.cli",
            "syncer",
            "serve",
            "--host",
            "0.0.0.0",
            "--port",
            str(args.port),
            "--ready-file",
            f"{REMOTE_RUN}/syncer_ready.json",
            "--workdir",
            REMOTE_RUN,
            "--run-id",
            args.run_id,
            "--learners",
            "2",
            "--steps",
            "30",
            "--vector-dim",
            "8",
            "--fragments",
            "1",
            "--local-steps-per-sync",
            "1",
            "--min-quorum",
            "2",
            "--seed",
            "123",
            "--learner-lr",
            "0.05",
            "--outer-lr",
            "0.5",
            "--outer-optimizer",
            "nesterov",
            "--outer-momentum",
            "0.9",
            "--heartbeat-timeout-seconds",
            "10",
            "--heartbeat-check-interval-seconds",
            "0.1",
            "--update-long-poll-timeout-seconds",
            "0.05",
            "--syncer-checkpoint-interval-rounds",
            "1",
        ]
    )


def _learner_command(args: argparse.Namespace, learner_id: str, syncer_ip: str) -> str:
    return shlex.join(
        [
            "env",
            "PYTHONPATH=src",
            "python3",
            "-m",
            "decodilo.cli",
            "learner",
            "run",
            "--learner-id",
            learner_id,
            "--run-id",
            args.run_id,
            "--host",
            syncer_ip,
            "--port",
            str(args.port),
            "--workdir",
            REMOTE_RUN,
            "--steps",
            "30",
            "--local-steps-per-sync",
            "1",
            "--heartbeat-interval-seconds",
            "0.05",
            "--step-delay-seconds",
            "0.005",
            "--learner-lr",
            "0.05",
            "--trainer-type",
            "tiny_adamw",
            "--trainer-config-json",
            json.dumps({"optimizer": "adamw"}),
            "--seed",
            "123",
        ]
    )



def _start_ssh_tunnels(owned: list[Instance], syncer: Instance, args: argparse.Namespace) -> None:
    local_port = args.port + 10_000
    syncer_tunnel = subprocess.Popen(
        [
            *_ssh_base(syncer.ip, args.ssh_private_key),
            "-N",
            "-L",
            f"127.0.0.1:{local_port}:127.0.0.1:{args.port}",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    _BACKGROUND_PROCS.append(syncer_tunnel)
    time.sleep(1)
    for learner_id in ["learner-0", "learner-1"]:
        inst = _by_role(owned, learner_id)
        learner_tunnel = subprocess.Popen(
            [
                *_ssh_base(inst.ip, args.ssh_private_key),
                "-N",
                "-R",
                f"127.0.0.1:{args.port}:127.0.0.1:{local_port}",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        _BACKGROUND_PROCS.append(learner_tunnel)
    time.sleep(1)


def _wait_learner_tunnels(owned: list[Instance], args: argparse.Namespace) -> None:
    for learner_id in ["learner-0", "learner-1"]:
        inst = _by_role(owned, learner_id)
        deadline = time.time() + 60
        while time.time() < deadline:
            try:
                _ssh(
                    inst.ip,
                    args.ssh_private_key,
                    (
                        "python3 - <<'PY'\n"
                        "import socket\n"
                        f"s=socket.create_connection(('127.0.0.1',{args.port}),5)\n"
                        "s.close()\n"
                        "PY\n"
                    ),
                    timeout=10,
                )
                break
            except Exception:  # noqa: BLE001
                time.sleep(1)
        else:
            raise TimeoutError(f"tunnel not ready for {learner_id}")

def _run_learners(owned: list[Instance], syncer_ip: str, args: argparse.Namespace) -> None:
    procs = []
    for learner_id in ["learner-0", "learner-1"]:
        inst = _by_role(owned, learner_id)
        cmd = _learner_command(args, learner_id, syncer_ip)
        remote = (
            f"cd {REMOTE_SRC} && {cmd} > {REMOTE_RUN}/{learner_id}.stdout "
            f"2> {REMOTE_RUN}/{learner_id}.stderr"
        )
        procs.append(
            (
                learner_id,
                subprocess.Popen([*_ssh_base(inst.ip, args.ssh_private_key), remote]),
            )
        )
    failures = []
    for learner_id, proc in procs:
        code = proc.wait(timeout=240)
        if code != 0:
            failures.append((learner_id, code))
    if failures:
        raise RuntimeError(f"learner failures: {failures}")


def _shutdown_syncer(syncer: Instance, args: argparse.Namespace) -> None:
    script = f"""
import asyncio, json
from decodilo.transport.tcp_client import JsonlTcpClient
from decodilo.transport.envelope import MessageType, make_envelope
async def main():
    async with JsonlTcpClient(host='127.0.0.1', port={args.port}, timeout_seconds=5) as client:
        envelope = make_envelope(
            run_id={args.run_id!r},
            sender_id='l2-supervisor',
            recipient_id='syncer',
            message_type=MessageType.SYNCER_SHUTDOWN,
            payload={{'reason': 'lambda_l2_complete'}},
        )
        response = await client.request(envelope)
        print(json.dumps(response.payload, sort_keys=True))
asyncio.run(main())
"""
    remote = (
        f"cd {REMOTE_SRC} && PYTHONPATH=src python3 - <<'PY' > {REMOTE_RUN}/syncer_summary.json\n"
        + script
        + "PY\n"
    )
    _ssh(syncer.ip, args.ssh_private_key, remote, timeout=60)
    _wait_for_background_procs(timeout=15)


def _wait_remote_file(ip: str, key: Path, path: str) -> None:
    deadline = time.time() + 120
    while time.time() < deadline:
        try:
            _ssh(ip, key, f"test -s {path}", timeout=10)
            return
        except Exception:  # noqa: BLE001
            time.sleep(1)
    diag = ""
    try:
        result = _ssh(
            ip,
            key,
            (
                f"ls -la {REMOTE_RUN}; "
                f"echo ---stdout---; cat {REMOTE_RUN}/syncer.stdout 2>/dev/null; "
                f"echo ---stderr---; cat {REMOTE_RUN}/syncer.stderr 2>/dev/null; "
                f"echo ---ps---; ps -ef | grep decodilo | grep -v grep || true"
            ),
            timeout=20,
        )
        diag = result.stdout[-4000:]
    except Exception as exc:  # noqa: BLE001
        diag = f"diagnostic failed: {exc}"
    raise TimeoutError(f"remote file not ready: {path}; diagnostic={diag}")


def _collect_evidence(owned: list[Instance], args: argparse.Namespace, evidence_dir: Path) -> None:
    for inst in owned:
        role_dir = evidence_dir / inst.role
        role_dir.mkdir(parents=True, exist_ok=True)
        patterns = [
            "events.jsonl",
            "syncer_checkpoint.json",
            "syncer_summary.json",
            "syncer.stdout",
            "syncer.stderr",
            f"{inst.role}.checkpoint.json",
            f"{inst.role}.log",
            f"{inst.role}.stdout",
            f"{inst.role}.stderr",
        ]
        for pattern in patterns:
            remote = f"{REMOTE_RUN}/{pattern}"
            subprocess.run(
                [
                    "scp",
                    "-i",
                    str(args.ssh_private_key),
                    "-o",
                    "StrictHostKeyChecking=no",
                    "-o",
                    "UserKnownHostsFile=/dev/null",
                    f"ubuntu@{inst.ip}:{remote}",
                    str(role_dir / pattern),
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )


def _write_layout(owned: list[Instance], args: argparse.Namespace, evidence_dir: Path) -> None:
    roles = {
        inst.role: {
            "instance_id": inst.instance_id,
            "ip": inst.ip,
            "region": inst.region,
            "instance_type": inst.instance_type,
        }
        for inst in owned
    }
    (evidence_dir / "layout.json").write_text(
        json.dumps(
            {
                "run_id": args.run_id,
                "roles": roles,
                "syncer_port": args.port,
                "remote_instance_count": len(owned),
                "network_path": "ssh_reverse_tunnel_via_operator",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _write_termination(owned: list[Instance], final_count: int, evidence_dir: Path) -> None:
    (evidence_dir / "termination_safety.json").write_text(
        json.dumps(
            {
                "owned_instance_ids": [inst.instance_id for inst in owned],
                "observed_final_live_instance_count": final_count,
                "billing_safety_status": (
                    "BILLING_SAFETY_OK" if final_count == 0 else "LIVE_INSTANCES_REMAIN"
                ),
                "contains_credentials": False,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )



def _wait_for_background_procs(*, timeout: int) -> None:
    deadline = time.time() + timeout
    for proc in list(_BACKGROUND_PROCS):
        remaining = max(0.1, deadline - time.time())
        try:
            proc.wait(timeout=remaining)
        except subprocess.TimeoutExpired:
            continue


def _cleanup_background_procs() -> None:
    for proc in list(_BACKGROUND_PROCS):
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
    _BACKGROUND_PROCS.clear()

def _terminate_all(api_key: str, instance_ids: list[str]) -> None:
    for instance_id in instance_ids:
        try:
            _api(api_key, "POST", "/instance-operations/terminate", {"instance_ids": [instance_id]})
            print(
                json.dumps({"event": "terminate_requested", "instance_id": instance_id}),
                flush=True,
            )
        except Exception as exc:  # noqa: BLE001
            print(
                json.dumps(
                    {
                        "event": "terminate_failed",
                        "instance_id": instance_id,
                        "error": str(exc),
                    }
                ),
                flush=True,
            )


def _wait_until_owned_absent(api_key: str, instance_ids: list[str]) -> int:
    owned = set(instance_ids)
    deadline = time.time() + 240
    live: list[dict[str, Any]] = []
    while time.time() < deadline:
        live = _list_instances(api_key)
        live_owned = [item for item in live if str(item.get("id")) in owned]
        if not live_owned:
            return len(live)
        time.sleep(5)
    return len(live)


def _by_role(owned: list[Instance], role: str) -> Instance:
    for inst in owned:
        if inst.role == role:
            return inst
    raise KeyError(role)


def _print_planned_commands(
    args: argparse.Namespace,
    *,
    ssh_key_name: str,
    evidence_dir: Path,
) -> None:
    print(json.dumps({"ssh_key_configured": bool(ssh_key_name), "evidence_dir": str(evidence_dir)}))
    print(_syncer_command(args))
    print(_learner_command(args, "learner-0", "<syncer-ip>"))
    print(_learner_command(args, "learner-1", "<syncer-ip>"))


if __name__ == "__main__":
    raise SystemExit(main())
