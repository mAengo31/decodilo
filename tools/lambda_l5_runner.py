#!/usr/bin/env python3
"""Run the Lambda L5 restart/recovery direct-TCP learner/syncer experiment.

This is intentionally a local operator script, not a production scheduler. It performs
real Lambda launch/terminate mutations when executed.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import tarfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from decodilo.lambda_cloud.l5_restart_recovery_direct_tcp_evidence_package import (
    build_lambda_l5_restart_recovery_direct_tcp_evidence_package_from_dir,
    write_lambda_l5_restart_recovery_direct_tcp_evidence_package,
)
from decodilo.operation.pathway_scheduler import (
    PathwayResourcePolicy,
    PathwayScheduler,
    PathwaySchedulerError,
    PathwayTask,
)

API_BASE = "https://cloud.lambdalabs.com/api/v1"
REMOTE_SRC = "/home/ubuntu/diloco_l5_src"
REMOTE_RUN = "/home/ubuntu/lambda_l5_run"
DEFAULT_PORT = 28080
_BACKGROUND_PROCS: list[subprocess.Popen[bytes]] = []


@dataclass(frozen=True)
class Instance:
    role: str
    instance_id: str
    ip: str
    region: str
    instance_type: str


def _learner_roles(args: argparse.Namespace) -> list[str]:
    return [f"learner-{index}" for index in range(int(args.learners))]


def _all_roles(args: argparse.Namespace) -> list[str]:
    return ["syncer", *_learner_roles(args)]


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
    parser.add_argument("--run-id", default=f"lambda-l5-{int(time.time())}")
    parser.add_argument(
        "--evidence-root",
        type=Path,
        default=Path("docs/evidence/lambda_l5_restart_recovery_direct_tcp_adamw_nesterov"),
    )
    parser.add_argument("--restart-after-round", type=int, default=20)
    parser.add_argument(
        "--experiment-mode",
        choices=["restart_recovery", "scale_only_no_restart"],
        default="restart_recovery",
        help=(
            "restart_recovery performs the planned syncer restart; "
            "scale_only_no_restart proves model/artifact scale without a mid-run restart"
        ),
    )
    parser.add_argument(
        "--no-restart",
        action="store_true",
        help="Alias for --experiment-mode scale_only_no_restart",
    )
    parser.add_argument("--trainer-type", default="tiny_adamw")
    parser.add_argument("--trainer-config-json", default=json.dumps({"optimizer": "adamw"}))
    parser.add_argument("--vector-dim", type=int, default=8)
    parser.add_argument("--learners", type=int, default=2)
    parser.add_argument("--steps", type=int, default=200)
    parser.add_argument("--min-quorum", type=int, default=2)
    parser.add_argument("--local-steps-per-sync", type=int, default=1)
    parser.add_argument("--fragments", type=int, default=1)
    parser.add_argument("--payload-storage-mode", default="inline")
    parser.add_argument("--checkpoint-storage-mode", default="inline")
    parser.add_argument("--merge-mode", default="in_memory")
    parser.add_argument("--global-update-storage-mode", default="inline")
    parser.add_argument("--inline-payload-max-bytes", type=int, default=1_000_000)
    parser.add_argument("--chunk-size-mb", type=int, default=1)
    parser.add_argument("--tensor-artifact-codec", default="binary_v1")
    parser.add_argument("--fragment-artifact-codec", default="binary_v1")
    parser.add_argument("--checkpoint-artifact-codec", default="binary_v1")
    parser.add_argument("--artifact-transfer-mode", default="bundle")
    parser.add_argument("--artifact-storage-backend", default="auto")
    parser.add_argument("--s3-endpoint-url", default=None)
    parser.add_argument("--s3-bucket", default=None)
    parser.add_argument("--s3-prefix", default="decodilo-artifacts")
    parser.add_argument("--s3-region", default=None)
    parser.add_argument("--s3-access-key-ref", default=None)
    parser.add_argument("--s3-secret-key-ref", default=None)
    parser.add_argument("--s3-session-token-ref", default=None)
    parser.add_argument(
        "--launch-delay-seconds",
        type=float,
        default=0.0,
        help="Optional pacing delay between sequential Lambda launch requests",
    )
    parser.add_argument(
        "--learner-reconnect-timeout-seconds",
        type=float,
        default=15.0,
        help="Learner reconnect window after syncer restart/recovery",
    )
    parser.add_argument(
        "--learner-run-timeout-seconds",
        type=float,
        default=300.0,
        help="Maximum wall-clock time to wait for learner SSH commands",
    )
    parser.add_argument(
        "--learner-pause-timeout-seconds",
        type=float,
        default=120.0,
        help="Maximum wall-clock time to wait for all learners to acknowledge pause",
    )
    parser.add_argument(
        "--syncer-stop-timeout-seconds",
        type=float,
        default=90.0,
        help="Maximum wall-clock time to wait for syncer process stop during restart",
    )
    parser.add_argument(
        "--restart-shutdown-request-timeout-seconds",
        type=float,
        default=20.0,
        help="Single shutdown RPC timeout for Pathway-managed restart",
    )
    parser.add_argument("--skip-launch", action="store_true", help="Only print planned commands")
    args = parser.parse_args()
    if args.no_restart or args.restart_after_round <= 0:
        args.experiment_mode = "scale_only_no_restart"

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
    firewall_original_rules: list[dict[str, Any]] | None = None
    firewall_changed = False
    try:
        _assert_no_live_instances(api_key)
        firewall_original_rules = _get_firewall_rules(api_key)
        evidence_dir.mkdir(parents=True, exist_ok=True)
        owned = _launch_owned_instances(api_key, args, ssh_key_name)
        owned = _wait_for_ips(api_key, owned)
        for inst in owned:
            _wait_for_ssh(inst.ip, args.ssh_private_key)
            _install_source(inst.ip, args.ssh_private_key, bundle, args)
        syncer = _by_role(owned, "syncer")
        _apply_temporary_firewall_rules(
            api_key,
            firewall_original_rules,
            args.port,
            learner_ips=[_by_role(owned, role).ip for role in _learner_roles(args)],
            evidence_dir=evidence_dir,
        )
        firewall_changed = True
        _start_syncer(syncer, args)
        _wait_remote_file(syncer.ip, args.ssh_private_key, f"{REMOTE_RUN}/syncer_ready.json")
        _wait_direct_tcp(owned, syncer.ip, args, evidence_dir)
        _run_learners_for_experiment_mode(owned, syncer, args, evidence_dir)
        _shutdown_syncer_after_experiment(syncer, args, evidence_dir)
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
        if firewall_original_rules is not None:
            _restore_firewall_rules(
                api_key,
                firewall_original_rules,
                evidence_dir=evidence_dir,
                attempted=firewall_changed,
            )
        _terminate_all(api_key, [inst.instance_id for inst in owned])
        _cleanup_background_procs()
        final_count = _wait_until_owned_absent(api_key, [inst.instance_id for inst in owned])
        if owned:
            evidence_dir.mkdir(parents=True, exist_ok=True)
            _write_termination(owned, final_count, evidence_dir)
    if owned:
        _install_local_s3_runtime_env_for_package(args)
        package = build_lambda_l5_restart_recovery_direct_tcp_evidence_package_from_dir(
            evidence_dir
        )
        write_lambda_l5_restart_recovery_direct_tcp_evidence_package(
            evidence_dir / "lambda_l5_evidence_package.json",
            package,
        )
        print(package.to_json(), end="")
        passed = (
            package.lambda_l5_restart_recovery_direct_tcp_passed
            or package.lambda_l5_scale_only_direct_tcp_passed
        )
        return 0 if passed else 2
    return 1



def _launch_owned_instances(
    api_key: str,
    args: argparse.Namespace,
    ssh_key_name: str,
) -> list[Instance]:
    owned: list[Instance] = []
    for index, role in enumerate(_all_roles(args)):
        if index > 0 and float(args.launch_delay_seconds) > 0:
            time.sleep(float(args.launch_delay_seconds))
        instance_id = _launch_instance(api_key, args.region, args.instance_type, ssh_key_name)
        owned.append(Instance(role, instance_id, "", args.region, args.instance_type))
        print(
            json.dumps({"event": "launched", "role": role, "instance_id": instance_id}),
            flush=True,
        )
    return owned

def _load_env_values(path: Path) -> dict[str, str]:
    values: dict[str, str] = dict(os.environ)
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("\"").strip("'")
    return values


def _load_env(path: Path) -> tuple[str, str | None]:
    values = _load_env_values(path)
    return values["LAMBDA_API_KEY"], values.get("LAMBDA_SSH_KEY")


def _api(api_key: str, method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    last_error: Exception | None = None
    for attempt in range(1, 6):
        req = Request(
            API_BASE + path,
            method=method,
            data=data,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "decodilo-lambda-l5-runner/0.1",
            },
        )
        try:
            with urlopen(req, timeout=30) as response:  # noqa: S310 - fixed Lambda API endpoint
                body = response.read()
            return json.loads(body.decode("utf-8")) if body else {}
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            last_error = RuntimeError(f"Lambda API {method} {path} failed: {exc.code} {body}")
            if exc.code != 429 and exc.code < 500:
                raise last_error from exc
            if exc.code == 429:
                retry_after = _retry_after_seconds(exc, body)
                time.sleep(retry_after if retry_after is not None else min(30 * attempt, 120))
                continue
        except (TimeoutError, URLError) as exc:
            last_error = exc
        time.sleep(min(2 * attempt, 10))
    raise RuntimeError(f"Lambda API {method} {path} failed after retries: {last_error}")



def _retry_after_seconds(exc: HTTPError, body: str) -> float | None:
    header = exc.headers.get("Retry-After") if exc.headers is not None else None
    for value in (header, _retry_after_from_body(body)):
        if value is None:
            continue
        try:
            seconds = float(value)
        except (TypeError, ValueError):
            continue
        if seconds >= 0:
            return min(seconds, 300.0)
    return None


def _retry_after_from_body(body: str) -> Any | None:
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return None
    if isinstance(payload, dict):
        return payload.get("retry_after")
    return None

def _assert_no_live_instances(api_key: str) -> None:
    instances = _list_instances(api_key)
    if instances:
        ids = [str(item.get("id")) for item in instances]
        raise RuntimeError(f"refusing L5 launch while live instances exist: {ids}")


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
    deadline = time.time() + 480
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
    bundle = Path("/tmp") / f"diloco-l5-src-{run_id}.tar.gz"
    with tarfile.open(bundle, "w:gz") as tar:
        for name in ["src", "pyproject.toml", "README.md"]:
            tar.add(root / name, arcname=name)
    return bundle



def _retry_operation(label: str, operation, *, attempts: int = 3, delay_seconds: float = 10.0):
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return operation()
        except (
            subprocess.CalledProcessError,
            subprocess.TimeoutExpired,
            TimeoutError,
            URLError,
        ) as exc:
            last_error = exc
            if attempt == attempts:
                break
            print(
                json.dumps({"event": "retry", "label": label, "attempt": attempt}),
                flush=True,
            )
            time.sleep(delay_seconds * attempt)
    raise RuntimeError(f"{label} failed after {attempts} attempts: {last_error}") from last_error




def _remote_dependency_install_command(args: argparse.Namespace) -> str:
    packages = ["'pydantic>=2,<3'"]
    if getattr(args, "artifact_storage_backend", "auto") == "s3_compatible":
        packages.append("boto3")
    return "python3 -m pip install --user " + " ".join(packages)


def _install_s3_runtime_env(ip: str, key: Path, args: argparse.Namespace) -> None:
    if getattr(args, "artifact_storage_backend", "auto") != "s3_compatible":
        return
    values = _s3_runtime_env_values(args)
    local_env = Path("/tmp") / f"decodilo-l5-s3-env-{args.run_id}.sh"
    local_env.write_text(
        "\n".join(f"export {name}={shlex.quote(value)}" for name, value in values.items())
        + "\n",
        encoding="utf-8",
    )
    try:
        _retry_operation(
            "upload_s3_runtime_env",
            lambda: subprocess.run(
                [
                    "scp",
                    "-i",
                    str(key),
                    "-o",
                    "StrictHostKeyChecking=no",
                    "-o",
                    "UserKnownHostsFile=/dev/null",
                    str(local_env),
                    f"ubuntu@{ip}:{REMOTE_RUN}/s3_runtime_env.sh",
                ],
                check=True,
            ),
        )
        _ssh(ip, key, f"chmod 600 {REMOTE_RUN}/s3_runtime_env.sh")
    finally:
        local_env.unlink(missing_ok=True)


def _s3_runtime_env_values(args: argparse.Namespace) -> dict[str, str]:
    env_values = _load_env_values(args.env_file)
    required_refs = [args.s3_access_key_ref, args.s3_secret_key_ref]
    if args.s3_session_token_ref:
        required_refs.append(args.s3_session_token_ref)
    values: dict[str, str] = {}
    for ref in required_refs:
        if not ref or not env_values.get(ref):
            raise RuntimeError(f"missing local S3 env ref {ref!r}")
        values[str(ref)] = env_values[str(ref)]
    return values


def _install_local_s3_runtime_env_for_package(args: argparse.Namespace) -> None:
    if getattr(args, "artifact_storage_backend", "auto") != "s3_compatible":
        return
    os.environ.update(_s3_runtime_env_values(args))


def _remote_env_prefix(args: argparse.Namespace) -> str:
    if getattr(args, "artifact_storage_backend", "auto") != "s3_compatible":
        return ""
    return f"set -a && . {REMOTE_RUN}/s3_runtime_env.sh && set +a && "

def _install_source(ip: str, key: Path, bundle: Path, args: argparse.Namespace) -> None:
    _retry_operation(
        "prepare_remote_source_dir",
        lambda: _ssh(
            ip,
            key,
            f"rm -rf {REMOTE_SRC} {REMOTE_RUN} && mkdir -p {REMOTE_SRC} {REMOTE_RUN}",
        ),
    )
    _retry_operation(
        "upload_source_bundle",
        lambda: subprocess.run(
            [
                "scp",
                "-i",
                str(key),
                "-o",
                "StrictHostKeyChecking=no",
                "-o",
                "UserKnownHostsFile=/dev/null",
                str(bundle),
                f"ubuntu@{ip}:/home/ubuntu/diloco_l5_src.tar.gz",
            ],
            check=True,
        ),
    )
    _retry_operation(
        "install_remote_source",
        lambda: _ssh(
            ip,
            key,
            (
                f"tar -xzf /home/ubuntu/diloco_l5_src.tar.gz -C {REMOTE_SRC} "
                f"&& {_remote_dependency_install_command(args)} "
                f"&& cd {REMOTE_SRC} && PYTHONPATH=src python3 -c "
                + shlex.quote("import decodilo, numpy, pydantic; print('deps-ok')")
            ),
            timeout=240,
        ),
    )
    _install_s3_runtime_env(ip, key, args)


def _start_syncer(syncer: Instance, args: argparse.Namespace, *, recover: bool = False) -> None:
    cmd = _syncer_command(args, recover=recover)
    suffix = "recover" if recover else "initial"
    remote = (
        f"mkdir -p {REMOTE_RUN} && rm -f {REMOTE_RUN}/syncer_ready.json && "
        f"cd {REMOTE_SRC} && "
        f"{_remote_env_prefix(args)}{cmd} > {REMOTE_RUN}/syncer.{suffix}.stdout "
        f"2> {REMOTE_RUN}/syncer.{suffix}.stderr"
    )
    proc = subprocess.Popen(
        [*_ssh_base(syncer.ip, args.ssh_private_key), remote],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    _BACKGROUND_PROCS.append(proc)


def _runtime_mode_args(args: argparse.Namespace, *, include_syncer_only: bool) -> list[str]:
    values = [
        "--payload-storage-mode",
        str(getattr(args, "payload_storage_mode", "inline")),
        "--global-update-storage-mode",
        str(getattr(args, "global_update_storage_mode", "inline")),
        "--inline-payload-max-bytes",
        str(getattr(args, "inline_payload_max_bytes", 1_000_000)),
        "--chunk-size-bytes",
        str(int(getattr(args, "chunk_size_mb", 1)) * 1024 * 1024),
    ]
    if include_syncer_only:
        values.extend(
            [
                "--checkpoint-storage-mode",
                str(getattr(args, "checkpoint_storage_mode", "inline")),
                "--merge-mode",
                str(getattr(args, "merge_mode", "in_memory")),
                "--checkpoint-artifact-codec",
                str(getattr(args, "checkpoint_artifact_codec", "binary_v1")),
            ]
        )
    values.extend(
        [
            "--tensor-artifact-codec",
            str(getattr(args, "tensor_artifact_codec", "binary_v1")),
            "--fragment-artifact-codec",
            str(getattr(args, "fragment_artifact_codec", "binary_v1")),
            "--artifact-transfer-mode",
            str(getattr(args, "artifact_transfer_mode", "bundle")),
            "--artifact-storage-backend",
            str(getattr(args, "artifact_storage_backend", "auto")),
        ]
    )
    return values



def _s3_runtime_args(args: argparse.Namespace) -> list[str]:
    if getattr(args, "artifact_storage_backend", "auto") != "s3_compatible":
        return []
    values = [
        "--s3-endpoint-url",
        str(args.s3_endpoint_url or ""),
        "--s3-bucket",
        str(args.s3_bucket or ""),
        "--s3-prefix",
        str(args.s3_prefix),
        "--s3-access-key-ref",
        str(args.s3_access_key_ref or ""),
        "--s3-secret-key-ref",
        str(args.s3_secret_key_ref or ""),
    ]
    if args.s3_region:
        values.extend(["--s3-region", str(args.s3_region)])
    if args.s3_session_token_ref:
        values.extend(["--s3-session-token-ref", str(args.s3_session_token_ref)])
    return values


def _syncer_command(args: argparse.Namespace, *, recover: bool = False) -> str:
    command = [
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
        str(args.learners),
        "--steps",
        str(args.steps),
        "--vector-dim",
        str(args.vector_dim),
        "--fragments",
        str(args.fragments),
        "--local-steps-per-sync",
        str(args.local_steps_per_sync),
        "--min-quorum",
        str(args.min_quorum),
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
        "60",
        "--heartbeat-check-interval-seconds",
        "0.1",
        "--update-long-poll-timeout-seconds",
        "0.05",
        "--syncer-checkpoint-interval-rounds",
        "1",
        *_runtime_mode_args(args, include_syncer_only=True),
        *_s3_runtime_args(args),
    ]
    if recover:
        command.append("--recover-from-checkpoint")
    return shlex.join(command)

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
            str(args.steps),
            "--local-steps-per-sync",
            str(args.local_steps_per_sync),
            "--heartbeat-interval-seconds",
            "0.05",
            "--step-delay-seconds",
            "0.05",
            "--learner-lr",
            "0.05",
            "--trainer-type",
            args.trainer_type,
            "--trainer-config-json",
            args.trainer_config_json,
            "--seed",
            "123",
            "--reconnect-timeout-seconds",
            str(getattr(args, "learner_reconnect_timeout_seconds", 15.0)),
            *_runtime_mode_args(args, include_syncer_only=False),
            *_s3_runtime_args(args),
        ]
    )




def _get_firewall_rules(api_key: str) -> list[dict[str, Any]]:
    payload = _api(api_key, "GET", "/firewall-rules")
    data = payload.get("data", []) if isinstance(payload, dict) else []
    return [_sanitize_firewall_rule(item) for item in data]


def _put_firewall_rules(api_key: str, rules: list[dict[str, Any]]) -> Any:
    return _api(api_key, "PUT", "/firewall-rules", {"data": rules})


def _sanitize_firewall_rule(rule: dict[str, Any]) -> dict[str, Any]:
    allowed = {"protocol", "port_range", "source_network", "description"}
    return {key: value for key, value in rule.items() if key in allowed}


def _temporary_firewall_rules(
    original_rules: list[dict[str, Any]],
    *,
    port: int,
    learner_ips: list[str],
) -> list[dict[str, Any]]:
    rules = [_sanitize_firewall_rule(rule) for rule in original_rules]
    existing = {json.dumps(rule, sort_keys=True) for rule in rules}
    for index, ip in enumerate(learner_ips):
        rule = {
            "protocol": "tcp",
            "port_range": [port, port],
            "source_network": f"{ip}/32",
            "description": f"Temporary Decodilo L5 learner-{index} direct TCP syncer access",
        }
        key = json.dumps(rule, sort_keys=True)
        if key not in existing:
            rules.append(rule)
            existing.add(key)
    return rules


def _apply_temporary_firewall_rules(
    api_key: str,
    original_rules: list[dict[str, Any]],
    port: int,
    *,
    learner_ips: list[str],
    evidence_dir: Path,
) -> None:
    applied_rules = _temporary_firewall_rules(
        original_rules,
        port=port,
        learner_ips=learner_ips,
    )
    (evidence_dir / "firewall_before.json").write_text(
        json.dumps({"data": original_rules}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    response = _put_firewall_rules(api_key, applied_rules)
    (evidence_dir / "firewall_applied.json").write_text(
        json.dumps(
            {"request": {"data": applied_rules}, "response": response},
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _restore_firewall_rules(
    api_key: str,
    original_rules: list[dict[str, Any]],
    *,
    evidence_dir: Path,
    attempted: bool,
) -> None:
    restored = False
    error = None
    response: Any = None
    attempts: list[dict[str, Any]] = []
    for attempt in range(1, 6):
        try:
            response = _put_firewall_rules(api_key, original_rules)
            restored = True
            attempts.append({"attempt": attempt, "restored": True})
            break
        except Exception as exc:  # noqa: BLE001 - retry provider firewall propagation issues
            error = str(exc)
            attempts.append({"attempt": attempt, "restored": False, "error": error})
            time.sleep(min(2 * attempt, 10))
    evidence_dir.mkdir(parents=True, exist_ok=True)
    (evidence_dir / "firewall_audit.json").write_text(
        json.dumps(
            {
                "attempted": attempted,
                "restored": restored,
                "restore_attempts": attempts,
                "restore_error": error if not restored else None,
                "restore_response": response,
                "original_rule_count": len(original_rules),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _wait_direct_tcp(
    owned: list[Instance],
    syncer_ip: str,
    args: argparse.Namespace,
    evidence_dir: Path,
) -> None:
    results: dict[str, bool] = {}
    errors: dict[str, str] = {}
    for learner_id in _learner_roles(args):
        inst = _by_role(owned, learner_id)
        deadline = time.time() + 90
        while time.time() < deadline:
            try:
                _ssh(
                    inst.ip,
                    args.ssh_private_key,
                    (
                        "python3 - <<'PY'\n"
                        "import socket\n"
                        f"s=socket.create_connection(({syncer_ip!r},{args.port}),5)\n"
                        "s.close()\n"
                        "PY\n"
                    ),
                    timeout=15,
                )
                results[learner_id] = True
                break
            except Exception as exc:  # noqa: BLE001
                errors[learner_id] = str(exc)
                time.sleep(2)
        else:
            results[learner_id] = False
    probe_passed = all(results.get(role) for role in _learner_roles(args))
    evidence_dir.mkdir(parents=True, exist_ok=True)
    (evidence_dir / "network_probe.json").write_text(
        json.dumps(
            {
                "direct_tcp_probe_passed": probe_passed,
                "syncer_ip": syncer_ip,
                "syncer_port": args.port,
                "results": results,
                "errors": errors,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    if not probe_passed:
        raise TimeoutError(f"direct TCP probe failed: {errors}")


def _run_learners_for_experiment_mode(
    owned: list[Instance],
    syncer: Instance,
    args: argparse.Namespace,
    evidence_dir: Path,
) -> None:
    if getattr(args, "experiment_mode", "restart_recovery") == "scale_only_no_restart":
        _run_learners_scale_only(owned, syncer, args, evidence_dir)
        return
    _run_learners_with_restart(owned, syncer, args, evidence_dir)


def _run_learners_with_restart(
    owned: list[Instance],
    syncer: Instance,
    args: argparse.Namespace,
    evidence_dir: Path,
) -> None:
    procs: list[tuple[str, subprocess.Popen[bytes]]] = []
    for learner_id in _learner_roles(args):
        inst = _by_role(owned, learner_id)
        cmd = _learner_command(args, learner_id, syncer.ip)
        remote = (
            f"cd {REMOTE_SRC} && {_remote_env_prefix(args)}{cmd} "
            f"> {REMOTE_RUN}/{learner_id}.stdout "
            f"2> {REMOTE_RUN}/{learner_id}.stderr"
        )
        procs.append(
            (
                learner_id,
                subprocess.Popen([*_ssh_base(inst.ip, args.ssh_private_key), remote]),
            )
        )

    restart_round: int | None = None
    recovered = False
    restart_error: str | None = None
    try:
        deadline = time.time() + float(args.learner_run_timeout_seconds)
        while time.time() < deadline:
            live = [proc for _, proc in procs if proc.poll() is None]
            current_round = _remote_committed_rounds(syncer, args)
            if restart_round is None and current_round >= args.restart_after_round:
                restart_round = current_round
                try:
                    recovered = _pathway_restart_syncer(
                        owned,
                        syncer,
                        args,
                        evidence_dir,
                        restart_round=restart_round,
                    )
                    if not recovered:
                        restart_error = "pathway restart recovery fence not satisfied"
                        break
                except Exception as exc:  # noqa: BLE001 - record restart failure
                    restart_error = str(exc)
                    break
            if not live:
                break
            time.sleep(0.5)
        failures = []
        for learner_id, proc in procs:
            code = proc.wait(timeout=max(30, int(args.learner_run_timeout_seconds)))
            if code != 0:
                failures.append((learner_id, code))
        final_round = _remote_committed_rounds(syncer, args)
        recovery_sufficient = _restart_recovery_sufficient(
            restart_round=restart_round,
            recovered=recovered,
            final_round=final_round,
        )
        if failures and not recovery_sufficient:
            raise RuntimeError(f"learner failures before recovery acceptance: {failures}")
        if restart_round is None:
            raise RuntimeError("restart threshold was not reached before learners exited")
        if restart_error is not None:
            raise RuntimeError(f"syncer restart failed: {restart_error}")
    finally:
        final_round = _remote_committed_rounds(syncer, args)
        recovery_sufficient = _restart_recovery_sufficient(
            restart_round=restart_round,
            recovered=recovered,
            final_round=final_round,
        )
        restart_payload = {
            "attempted": restart_round is not None,
            "recovered": recovery_sufficient,
            "restart_round": restart_round,
            "final_round_before_shutdown": final_round,
            "rounds_after_restart": (
                0 if restart_round is None else max(final_round - restart_round, 0)
            ),
            "restart_error": restart_error,
            "graceful_shutdown_error": None,
            "late_learner_failures_ignored": bool(
                'failures' in locals() and failures and recovery_sufficient
            ),
            "learner_failures": [
                {"learner_id": learner_id, "exit_code": code}
                for learner_id, code in (failures if 'failures' in locals() else [])
            ],
        }
        evidence_dir.mkdir(parents=True, exist_ok=True)
        (evidence_dir / "restart_audit.json").write_text(
            json.dumps(restart_payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


def _run_learners_scale_only(
    owned: list[Instance],
    syncer: Instance,
    args: argparse.Namespace,
    evidence_dir: Path,
) -> None:
    procs: list[tuple[str, subprocess.Popen[bytes]]] = []
    for learner_id in _learner_roles(args):
        inst = _by_role(owned, learner_id)
        cmd = _learner_command(args, learner_id, syncer.ip)
        remote = (
            f"cd {REMOTE_SRC} && {_remote_env_prefix(args)}{cmd} "
            f"> {REMOTE_RUN}/{learner_id}.stdout "
            f"2> {REMOTE_RUN}/{learner_id}.stderr"
        )
        procs.append(
            (
                learner_id,
                subprocess.Popen([*_ssh_base(inst.ip, args.ssh_private_key), remote]),
            )
        )

    failures: list[tuple[str, int]] = []
    try:
        deadline = time.time() + float(args.learner_run_timeout_seconds)
        while time.time() < deadline:
            if all(proc.poll() is not None for _, proc in procs):
                break
            time.sleep(0.5)
        for learner_id, proc in procs:
            code = proc.wait(timeout=max(30, int(args.learner_run_timeout_seconds)))
            if code != 0:
                failures.append((learner_id, code))
        if failures:
            raise RuntimeError(f"learner failures: {failures}")
    finally:
        final_round = _remote_committed_rounds(syncer, args)
        restart_payload = {
            "attempted": False,
            "recovered": False,
            "skipped": True,
            "skip_reason": "scale_only_no_restart",
            "experiment_mode": "scale_only_no_restart",
            "restart_round": None,
            "final_round_before_shutdown": final_round,
            "rounds_after_restart": 0,
            "restart_error": None,
            "graceful_shutdown_error": None,
            "late_learner_failures_ignored": False,
            "learner_failures": [
                {"learner_id": learner_id, "exit_code": code}
                for learner_id, code in failures
            ],
        }
        evidence_dir.mkdir(parents=True, exist_ok=True)
        (evidence_dir / "restart_audit.json").write_text(
            json.dumps(restart_payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


def _restart_recovery_sufficient(
    *,
    restart_round: int | None,
    recovered: bool,
    final_round: int,
) -> bool:
    return bool(recovered and restart_round is not None and final_round > restart_round)


def _pathway_restart_syncer(
    owned: list[Instance],
    syncer: Instance,
    args: argparse.Namespace,
    evidence_dir: Path,
    *,
    restart_round: int,
) -> bool:
    """Run a fenced Pathway-style syncer restart sequence.

    This is intentionally an operator-side control graph, not full Google
    Pathways. It makes the fragile restart path explicit and auditable before
    we retry larger S3-backed model recovery experiments.
    """

    scheduler = PathwayScheduler(resource_policy=PathwayResourcePolicy(local_only=True))
    scheduler.add_task(
        PathwayTask(
            task_id="pause_learners",
            op="request_learners_pause",
            produces=["pause_requested"],
            run=lambda _ctx: (
                _request_learners_pause(owned, args, restart_round=restart_round)
                or {"pause_requested": True}
            ),
        )
    )
    scheduler.add_task(
        PathwayTask(
            task_id="pause_fence",
            op="wait_learners_paused",
            depends_on=["pause_learners"],
            consumes=["pause_requested"],
            produces=["paused_learners"],
            run=lambda _ctx: {"paused_learners": _wait_learners_paused(owned, args)},
        )
    )
    scheduler.add_task(
        PathwayTask(
            task_id="checkpoint_fence",
            op="wait_syncer_checkpoint_at_restart_round",
            depends_on=["pause_fence"],
            consumes=["paused_learners"],
            produces=["checkpoint_round"],
            run=lambda _ctx: {
                "checkpoint_round": _wait_remote_checkpoint_at_least(
                    syncer,
                    args,
                    restart_round,
                )
            },
        )
    )

    def shutdown_task(_ctx):
        try:
            _request_syncer_shutdown_for_restart(syncer, args)
            return {"shutdown_error": None}
        except Exception as exc:  # noqa: BLE001 - stop fence/force-stop handles this
            print(
                json.dumps(
                    {
                        "event": "syncer_graceful_shutdown_failed",
                        "error": str(exc),
                    }
                ),
                flush=True,
            )
            return {"shutdown_error": str(exc)}

    scheduler.add_task(
        PathwayTask(
            task_id="shutdown_syncer",
            op="request_syncer_shutdown",
            depends_on=["checkpoint_fence"],
            consumes=["checkpoint_round"],
            produces=["shutdown_error"],
            run=shutdown_task,
        )
    )
    scheduler.add_task(
        PathwayTask(
            task_id="stop_fence",
            op="wait_syncer_stopped_or_force",
            depends_on=["shutdown_syncer"],
            consumes=["shutdown_error"],
            produces=["stop_result"],
            run=lambda ctx: {
                "stop_result": _wait_syncer_stopped_or_force(
                    syncer,
                    args,
                    ctx.resolve("shutdown_error"),
                )
            },
        )
    )
    scheduler.add_task(
        PathwayTask(
            task_id="start_recovered_syncer",
            op="start_syncer_recover_from_checkpoint",
            depends_on=["stop_fence"],
            consumes=["stop_result"],
            produces=["recover_start"],
            run=lambda _ctx: (
                _start_syncer(syncer, args, recover=True) or {"recover_start": True}
            ),
        )
    )
    scheduler.add_task(
        PathwayTask(
            task_id="ready_fence",
            op="wait_recovered_syncer_ready_file",
            depends_on=["start_recovered_syncer"],
            consumes=["recover_start"],
            produces=["ready_file"],
            run=lambda _ctx: (
                _wait_remote_file(
                    syncer.ip,
                    args.ssh_private_key,
                    f"{REMOTE_RUN}/syncer_ready.json",
                )
                or {"ready_file": f"{REMOTE_RUN}/syncer_ready.json"}
            ),
        )
    )
    scheduler.add_task(
        PathwayTask(
            task_id="direct_tcp_fence",
            op="wait_learners_can_reach_recovered_syncer",
            depends_on=["ready_fence"],
            consumes=["ready_file"],
            produces=["direct_tcp_ready"],
            run=lambda _ctx: (
                _wait_direct_tcp(owned, syncer.ip, args, evidence_dir)
                or {"direct_tcp_ready": True}
            ),
        )
    )
    scheduler.add_task(
        PathwayTask(
            task_id="resume_learners",
            op="resume_paused_learners",
            depends_on=["direct_tcp_fence"],
            consumes=["direct_tcp_ready"],
            produces=["learners_resumed"],
            run=lambda _ctx: _resume_learners(owned, args) or {"learners_resumed": True},
        )
    )
    scheduler.add_task(
        PathwayTask(
            task_id="post_restart_round_fence",
            op="wait_post_restart_committed_round",
            depends_on=["resume_learners"],
            consumes=["learners_resumed"],
            produces=["post_restart_round"],
            run=lambda _ctx: {
                "post_restart_round": _wait_post_restart_round(
                    syncer,
                    args,
                    restart_round,
                )
            },
        )
    )

    try:
        result = scheduler.run()
    except PathwaySchedulerError as exc:
        _write_pathway_restart_audit(
            evidence_dir,
            {
                "status": "failed",
                "restart_round": restart_round,
                "error": str(exc),
                "failed_task": _failed_pathway_task_from_error(str(exc)),
                "launch_ready": False,
                "launch_allowed": False,
                "production_scale_ready": False,
            },
        )
        return False

    _write_pathway_restart_audit(
        evidence_dir,
        {
            **result.to_dict(),
            "restart_round": restart_round,
            "pathway_restart_orchestration": True,
        },
    )
    post_restart_round = result.artifacts["post_restart_round"].value
    return int(post_restart_round) > restart_round


def _write_pathway_restart_audit(evidence_dir: Path, payload: dict[str, Any]) -> None:
    evidence_dir.mkdir(parents=True, exist_ok=True)
    (evidence_dir / "pathway_restart_audit.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _failed_pathway_task_from_error(message: str) -> str | None:
    if message.startswith("task "):
        parts = message.split()
        if len(parts) >= 2:
            return parts[1]
    return None


def _wait_post_restart_round(
    syncer: Instance,
    args: argparse.Namespace,
    restart_round: int,
) -> int:
    deadline = time.time() + float(getattr(args, "learner_reconnect_timeout_seconds", 90.0))
    last_round = _remote_committed_rounds(syncer, args)
    while time.time() < deadline:
        last_round = _remote_committed_rounds(syncer, args)
        if last_round > restart_round:
            return last_round
        time.sleep(1)
    raise TimeoutError(
        f"post-restart round fence not satisfied: last_round={last_round}, "
        f"restart_round={restart_round}"
    )


def _remote_committed_rounds(syncer: Instance, args: argparse.Namespace) -> int:
    command = (
        f"grep -c '\"event_type\":\"sync_round_committed\"' "
        f"{REMOTE_RUN}/events.jsonl 2>/dev/null || echo 0"
    )
    try:
        result = _retry_operation(
            "remote_committed_rounds",
            lambda: _ssh(syncer.ip, args.ssh_private_key, command, timeout=15),
            attempts=3,
            delay_seconds=2.0,
        )
    except RuntimeError:
        return 0
    try:
        return int(result.stdout.strip().splitlines()[-1])
    except Exception:
        return 0

def _run_learners(owned: list[Instance], syncer_ip: str, args: argparse.Namespace) -> None:
    procs = []
    for learner_id in _learner_roles(args):
        inst = _by_role(owned, learner_id)
        cmd = _learner_command(args, learner_id, syncer_ip)
        remote = (
            f"cd {REMOTE_SRC} && {_remote_env_prefix(args)}{cmd} "
            f"> {REMOTE_RUN}/{learner_id}.stdout "
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



def _force_stop_syncer(syncer: Instance, args: argparse.Namespace) -> None:
    pattern = _syncer_process_pattern()
    command = (
        "pkill -TERM -f "
        + shlex.quote(pattern)
        + " || true; "
        "sleep 2; "
        "pkill -KILL -f "
        + shlex.quote(pattern)
        + " || true"
    )
    _ssh(syncer.ip, args.ssh_private_key, command, timeout=30)


def _syncer_process_pattern() -> str:
    return "[d]ecodilo.cli syncer serve"


def _request_learners_pause(
    owned: list[Instance],
    args: argparse.Namespace,
    *,
    restart_round: int,
) -> None:
    for learner_id in _learner_roles(args):
        inst = _by_role(owned, learner_id)
        pause_payload = json.dumps(
            {
                "pause": True,
                "reason": "pathway_restart_recovery",
                "restart_round": restart_round,
                "run_id": args.run_id,
            },
            sort_keys=True,
        )
        remote = (
            f"mkdir -p {REMOTE_RUN} && "
            f"cat > {REMOTE_RUN}/{learner_id}.pause.json <<'JSON'\n"
            f"{pause_payload}\n"
            "JSON\n"
        )
        _ssh(inst.ip, args.ssh_private_key, remote, timeout=15)


def _wait_learners_paused(
    owned: list[Instance],
    args: argparse.Namespace,
) -> list[str]:
    paused: set[str] = set()
    deadline = time.time() + float(getattr(args, "learner_pause_timeout_seconds", 120.0))
    errors: dict[str, str] = {}
    while time.time() < deadline:
        for learner_id in _learner_roles(args):
            if learner_id in paused:
                continue
            inst = _by_role(owned, learner_id)
            try:
                _ssh(
                    inst.ip,
                    args.ssh_private_key,
                    f"test -s {REMOTE_RUN}/{learner_id}.paused.json",
                    timeout=10,
                )
                paused.add(learner_id)
            except Exception as exc:  # noqa: BLE001 - learners may still be reaching pause point
                errors[learner_id] = str(exc)
        if len(paused) == int(args.learners):
            return sorted(paused)
        time.sleep(1)
    raise TimeoutError(
        f"timed out waiting for learners to pause: paused={sorted(paused)}, "
        f"errors={errors}"
    )


def _resume_learners(owned: list[Instance], args: argparse.Namespace) -> None:
    for learner_id in _learner_roles(args):
        inst = _by_role(owned, learner_id)
        _ssh(
            inst.ip,
            args.ssh_private_key,
            (
                f"rm -f {REMOTE_RUN}/{learner_id}.pause.json "
                f"{REMOTE_RUN}/{learner_id}.paused.json"
            ),
            timeout=15,
        )


def _wait_remote_checkpoint_at_least(
    syncer: Instance,
    args: argparse.Namespace,
    target_round: int,
) -> int:
    script = (
        "python3 - <<'PY'\n"
        "import json\n"
        "from pathlib import Path\n"
        f"target={int(target_round)}\n"
        f"path=Path({str(REMOTE_RUN + '/events.jsonl')!r})\n"
        "latest=0\n"
        "if path.exists():\n"
        "    for line in path.read_text(encoding='utf-8').splitlines():\n"
        "        if not line:\n"
        "            continue\n"
        "        event=json.loads(line)\n"
        "        checkpoint_events={'syncer_checkpoint_written','checkpoint_written'}\n"
        "        if event.get('event_type') not in checkpoint_events:\n"
        "            continue\n"
        "        payload=event.get('payload') or {}\n"
        "        latest=max(latest, int(payload.get('global_version') or 0))\n"
        "print(latest)\n"
        "raise SystemExit(0 if latest >= target else 1)\n"
        "PY\n"
    )
    deadline = time.time() + 180
    last_round = 0
    last_error: str | None = None
    while time.time() < deadline:
        try:
            result = _ssh(syncer.ip, args.ssh_private_key, script, timeout=15)
            last_round = int(result.stdout.strip().splitlines()[-1])
            if last_round >= target_round:
                return last_round
        except Exception as exc:  # noqa: BLE001 - checkpoint can lag commit briefly
            last_error = str(exc)
        time.sleep(1)
    raise TimeoutError(
        f"checkpoint fence not satisfied: latest={last_round}, "
        f"target={target_round}, last_error={last_error}"
    )


def _wait_syncer_stopped_or_force(
    syncer: Instance,
    args: argparse.Namespace,
    graceful_shutdown_error: str | None,
) -> dict[str, Any]:
    deadline = time.time() + float(getattr(args, "syncer_stop_timeout_seconds", 90.0))
    while time.time() < deadline:
        if not _syncer_process_running(syncer, args):
            return {
                "stopped": True,
                "forced": False,
                "graceful_shutdown_error": graceful_shutdown_error,
            }
        time.sleep(1)
    force_stop_error: str | None = None
    try:
        _retry_operation(
            "force_stop_syncer",
            lambda: _force_stop_syncer(syncer, args),
            attempts=1,
            delay_seconds=5.0,
        )
    except RuntimeError as exc:
        force_stop_error = str(exc)
    deadline = time.time() + 30
    while time.time() < deadline:
        if not _syncer_process_running(syncer, args):
            return {
                "stopped": True,
                "forced": True,
                "graceful_shutdown_error": graceful_shutdown_error,
                "force_stop_error": force_stop_error,
            }
        time.sleep(1)
    raise TimeoutError(
        f"syncer process still running after force-stop; force_stop_error={force_stop_error}"
    )


def _syncer_process_running(syncer: Instance, args: argparse.Namespace) -> bool:
    pattern = _syncer_process_pattern()
    try:
        _ssh(
            syncer.ip,
            args.ssh_private_key,
            "pgrep -f " + shlex.quote(pattern) + " >/dev/null",
            timeout=15,
        )
        return True
    except Exception:  # noqa: BLE001 - pgrep exit 1 means no process
        return False


def _shutdown_syncer_after_experiment(
    syncer: Instance,
    args: argparse.Namespace,
    evidence_dir: Path,
) -> None:
    try:
        _shutdown_syncer(syncer, args)
    except Exception as exc:
        evidence_dir.mkdir(parents=True, exist_ok=True)
        (evidence_dir / "syncer_shutdown_audit.json").write_text(
            json.dumps(
                {
                    "shutdown_succeeded": False,
                    "error": str(exc),
                    "experiment_mode": getattr(args, "experiment_mode", "restart_recovery"),
                    "accepted_as_nonfatal": (
                        getattr(args, "experiment_mode", "restart_recovery")
                        == "scale_only_no_restart"
                    ),
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        if getattr(args, "experiment_mode", "restart_recovery") == "scale_only_no_restart":
            return
        raise
    else:
        evidence_dir.mkdir(parents=True, exist_ok=True)
        (evidence_dir / "syncer_shutdown_audit.json").write_text(
            json.dumps(
                {
                    "shutdown_succeeded": True,
                    "error": None,
                    "experiment_mode": getattr(args, "experiment_mode", "restart_recovery"),
                    "accepted_as_nonfatal": False,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )


def _shutdown_syncer(syncer: Instance, args: argparse.Namespace) -> None:
    script = f"""
import asyncio, json
from decodilo.transport.tcp_client import JsonlTcpClient
from decodilo.transport.envelope import MessageType, make_envelope
async def main():
    async with JsonlTcpClient(host='127.0.0.1', port={args.port}, timeout_seconds=30) as client:
        envelope = make_envelope(
            run_id={args.run_id!r},
            sender_id='l2-supervisor',
            recipient_id='syncer',
            message_type=MessageType.SYNCER_SHUTDOWN,
            payload={{'reason': 'lambda_l5_complete'}},
        )
        response = await client.request(envelope)
        print(json.dumps(response.payload, sort_keys=True))
asyncio.run(main())
"""
    remote = (
        f"cd {REMOTE_SRC} && PYTHONPATH=src python3 - <<'PY' > "
        f"{REMOTE_RUN}/syncer_summary.json.tmp\n"
        + script
        + f"PY\nmv {REMOTE_RUN}/syncer_summary.json.tmp {REMOTE_RUN}/syncer_summary.json\n"
    )
    _retry_operation(
        "shutdown_syncer",
        lambda: _ssh(syncer.ip, args.ssh_private_key, remote, timeout=120),
        attempts=3,
        delay_seconds=5.0,
    )
    _wait_for_background_procs(timeout=30)


def _request_syncer_shutdown_for_restart(syncer: Instance, args: argparse.Namespace) -> None:
    timeout_seconds = float(getattr(args, "restart_shutdown_request_timeout_seconds", 20.0))
    script = f"""
import asyncio, json
from decodilo.transport.tcp_client import JsonlTcpClient
from decodilo.transport.envelope import MessageType, make_envelope
async def main():
    async with JsonlTcpClient(
        host='127.0.0.1',
        port={args.port},
        timeout_seconds={timeout_seconds!r},
    ) as client:
        envelope = make_envelope(
            run_id={args.run_id!r},
            sender_id='pathway-restart-supervisor',
            recipient_id='syncer',
            message_type=MessageType.SYNCER_SHUTDOWN,
            payload={{'reason': 'pathway_restart_recovery', 'immediate_server_close': True}},
        )
        response = await client.request(envelope)
        print(json.dumps(response.payload, sort_keys=True))
asyncio.run(main())
"""
    remote = (
        f"cd {REMOTE_SRC} && PYTHONPATH=src python3 - <<'PY' > "
        f"{REMOTE_RUN}/syncer_restart_shutdown_response.json.tmp\n"
        + script
        + f"PY\nmv {REMOTE_RUN}/syncer_restart_shutdown_response.json.tmp "
        f"{REMOTE_RUN}/syncer_restart_shutdown_response.json\n"
    )
    _ssh(syncer.ip, args.ssh_private_key, remote, timeout=int(timeout_seconds) + 15)


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
            "syncer.initial.stdout",
            "syncer.initial.stderr",
            "syncer.recover.stdout",
            "syncer.recover.stderr",
            f"{inst.role}.checkpoint.json",
            f"{inst.role}.log",
            f"{inst.role}.pause.json",
            f"{inst.role}.paused.json",
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
        if (
            inst.role == "syncer"
            and getattr(args, "artifact_storage_backend", "auto") != "s3_compatible"
        ):
            for dirname in ["artifacts", "live_checkpoints"]:
                remote = f"{REMOTE_RUN}/{dirname}"
                subprocess.run(
                    [
                        "scp",
                        "-r",
                        "-i",
                        str(args.ssh_private_key),
                        "-o",
                        "StrictHostKeyChecking=no",
                        "-o",
                        "UserKnownHostsFile=/dev/null",
                        f"ubuntu@{inst.ip}:{remote}",
                        str(role_dir / dirname),
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                    timeout=180,
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
                "network_path": "lambda_firewall_direct_tcp",
                "experiment_mode": getattr(args, "experiment_mode", "restart_recovery"),
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
    deadline = time.time() + 480
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
    print(
        json.dumps(
            {
                "ssh_key_configured": bool(ssh_key_name),
                "evidence_dir": str(evidence_dir),
                "experiment_mode": getattr(args, "experiment_mode", "restart_recovery"),
            }
        )
    )
    print(_syncer_command(args))
    for learner_id in _learner_roles(args):
        print(_learner_command(args, learner_id, "<syncer-ip>"))


if __name__ == "__main__":
    raise SystemExit(main())
