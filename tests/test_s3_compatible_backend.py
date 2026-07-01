from __future__ import annotations

import io

import numpy as np
import pytest

from decodilo.errors import InvariantViolation
from decodilo.runtime.artifact_transport import ArtifactTransportPolicy, LocalArtifactTransport
from decodilo.runtime.syncer_service import SyncerService, SyncerServiceConfig
from decodilo.storage.artifact_backend import ArtifactBackendRef
from decodilo.storage.chunk_store import ChunkStore
from decodilo.storage.s3_compatible_backend import (
    S3CompatibleArtifactBackend,
    S3CompatibleBackendConfig,
    S3CompatibleBackendNotConfigured,
)


class FakeS3Client:
    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], dict] = {}

    def put_object(self, **kwargs):
        bucket = kwargs["Bucket"]
        key = kwargs["Key"]
        body = kwargs["Body"]
        metadata = dict(kwargs.get("Metadata") or {})
        existing_versions = [
            item for item in self.objects if item[0] == bucket and item[1] == key
        ]
        version = str(len(existing_versions) + 1)
        self.objects[(bucket, key)] = {
            "Body": bytes(body),
            "Metadata": metadata,
            "VersionId": version,
        }
        return {"VersionId": version}

    def get_object(self, **kwargs):
        obj = self.objects[(kwargs["Bucket"], kwargs["Key"])]
        data = obj["Body"]
        range_header = kwargs.get("Range")
        if range_header:
            start_text, end_text = range_header.removeprefix("bytes=").split("-", 1)
            data = data[int(start_text) : int(end_text) + 1]
        return {"Body": io.BytesIO(data), "VersionId": obj["VersionId"]}

    def head_object(self, **kwargs):
        obj = self.objects[(kwargs["Bucket"], kwargs["Key"])]
        return {"Metadata": obj["Metadata"], "VersionId": obj["VersionId"]}

    def list_objects_v2(self, **kwargs):
        bucket = kwargs["Bucket"]
        prefix = kwargs.get("Prefix", "")
        return {
            "Contents": [
                {"Key": key, "Size": len(obj["Body"])}
                for (item_bucket, key), obj in sorted(self.objects.items())
                if item_bucket == bucket and key.startswith(prefix)
            ]
        }

    def delete_object(self, **kwargs):
        self.objects.pop((kwargs["Bucket"], kwargs["Key"]), None)
        return {}


def _config() -> S3CompatibleBackendConfig:
    return S3CompatibleBackendConfig(
        endpoint_url="https://object.example.invalid",
        bucket="decodilo-test",
        prefix="runs/run-a",
        access_key_ref="S3_ACCESS_KEY_ID",
        secret_key_ref="S3_SECRET_ACCESS_KEY",
    )


def test_s3_compatible_backend_fails_closed_without_client() -> None:
    backend = S3CompatibleArtifactBackend(_config())

    assert backend.capabilities().remote is True
    assert backend.capabilities().write_supported is False
    assert backend.remote_capabilities().remote_backend_enabled is False
    with pytest.raises(S3CompatibleBackendNotConfigured):
        backend.write_bytes(artifact_id="x", data=b"x")


def test_s3_compatible_backend_write_read_range_list_and_delete_with_injected_client() -> None:
    backend = S3CompatibleArtifactBackend(_config(), client=FakeS3Client())
    ref = backend.write_bytes(artifact_id="global-update-v1", data=b"abcdef")

    assert ref.backend_type == "s3_compatible"
    assert ref.uri == "s3://decodilo-test/runs/run-a/global-update-v1"
    assert backend.read_bytes(ref) == b"abcdef"
    assert backend.read_range(ref, offset=2, length=3) == b"cde"
    assert backend.artifact_size(ref) == 6
    assert backend.list_refs() == [ref]
    assert backend.capabilities().write_supported is True
    assert backend.remote_capabilities().remote_backend_enabled is True

    backend.delete_ref(ref)
    assert backend.list_refs() == []


def test_s3_compatible_backend_rejects_raw_secret_like_config_values() -> None:
    with pytest.raises(ValueError):
        S3CompatibleBackendConfig(
            endpoint_url="https://object.example.invalid",
            bucket="decodilo-test",
            access_key_ref="AKIA1234567890123456" + "A" * 80,
        )


def test_s3_compatible_backend_rejects_wrong_ref_type() -> None:
    backend = S3CompatibleArtifactBackend(_config(), client=FakeS3Client())
    wrong = ArtifactBackendRef(backend_type="other", uri="x", artifact_id="x")

    with pytest.raises(ValueError):
        backend.read_bytes(wrong)


def test_s3_compatible_preflight_blocks_without_injected_client() -> None:
    from decodilo.storage.s3_compatible_backend import preflight_s3_compatible_backend

    report = preflight_s3_compatible_backend(_config())

    assert report.status == "blocked"
    assert report.symbolic_credentials_present is True
    assert report.client_injected is False
    assert "client_not_injected" in report.blockers
    assert report.remote_backend_enabled is False
    assert report.launch_allowed is False


def test_s3_compatible_preflight_passes_with_injected_client_probe() -> None:
    from decodilo.storage.s3_compatible_backend import preflight_s3_compatible_backend

    report = preflight_s3_compatible_backend(
        _config(),
        client=FakeS3Client(),
        require_probe=True,
    )

    assert report.status == "passed"
    assert report.client_injected is True
    assert report.probe_attempted is True
    assert report.probe_passed is True
    assert report.remote_backend_enabled is True
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_s3_compatible_client_factory_requires_explicit_client_or_factory() -> None:
    from decodilo.storage.s3_client_factory import create_s3_compatible_backend

    with pytest.raises(S3CompatibleBackendNotConfigured):
        create_s3_compatible_backend(config=_config())


def test_s3_compatible_client_factory_builds_backend_from_injected_factory() -> None:
    from decodilo.storage.s3_client_factory import create_s3_compatible_backend

    fake = FakeS3Client()
    calls = []

    def factory(config: S3CompatibleBackendConfig):
        calls.append(config)
        return fake

    backend = create_s3_compatible_backend(
        config=_config(),
        client_factory=factory,
        require_probe=True,
    )

    assert calls == [_config()]
    assert backend.remote_capabilities().remote_backend_enabled is True
    ref = backend.write_bytes(artifact_id="factory-object", data=b"factory-data")
    assert backend.read_bytes(ref) == b"factory-data"


def test_s3_compatible_artifact_transport_fails_closed_without_injected_backend(tmp_path) -> None:
    chunk_root = tmp_path / "chunks"
    manifest_path = tmp_path / "artifacts" / "sample.artifact.json"
    manifest = ChunkStore(chunk_root).write_bytes(
        artifact_id="sample",
        artifact_type="test",
        run_id="run-s3",
        data=b"abcdef",
        chunk_size_bytes=3,
        manifest_path=manifest_path,
    )
    transport = LocalArtifactTransport(
        policy=ArtifactTransportPolicy(
            workdir=str(tmp_path),
            artifact_root=str(tmp_path / "artifacts"),
            storage_backend="s3_compatible",
        )
    )

    with pytest.raises(InvariantViolation, match="S3-compatible.*injected"):
        transport.make_ref(
            manifest=manifest,
            manifest_path=manifest_path,
            chunk_root=chunk_root,
            created_by="test",
        )


def test_s3_compatible_artifact_transport_mirrors_manifest_and_chunks_with_fake_client(
    tmp_path,
) -> None:
    fake = FakeS3Client()
    backend = S3CompatibleArtifactBackend(_config(), client=fake)
    chunk_root = tmp_path / "chunks"
    manifest_path = tmp_path / "artifacts" / "sample.artifact.json"
    manifest = ChunkStore(chunk_root).write_bytes(
        artifact_id="sample",
        artifact_type="test",
        run_id="run-s3",
        data=b"abcdef",
        chunk_size_bytes=3,
        manifest_path=manifest_path,
    )
    transport = LocalArtifactTransport(
        policy=ArtifactTransportPolicy(
            workdir=str(tmp_path),
            artifact_root=str(tmp_path / "artifacts"),
            storage_backend="s3_compatible",
        ),
        s3_backend=backend,
    )

    ref = transport.make_ref(
        manifest=manifest,
        manifest_path=manifest_path,
        chunk_root=chunk_root,
        created_by="test",
    )

    assert ref.storage_backend == "s3_compatible"
    assert ref.metadata["s3_compatible_manifest_ref"]["backend_type"] == "s3_compatible"
    assert len(ref.metadata["s3_compatible_chunk_refs"]) == 2
    assert transport.validate_ref(ref) == manifest

    first_chunk_key = ref.metadata["s3_compatible_chunk_refs"][0]["metadata"]["key"]
    fake.objects[(_config().bucket, first_chunk_key)]["Body"] = b"corrupt"
    with pytest.raises(InvariantViolation, match="S3-compatible artifact chunk mirror mismatch"):
        transport.validate_ref(ref)


def test_syncer_runtime_uses_injected_s3_backend_for_global_artifacts(tmp_path) -> None:
    backend = S3CompatibleArtifactBackend(_config(), client=FakeS3Client())
    service = SyncerService(
        SyncerServiceConfig(
            run_id="run-s3-runtime",
            workdir=tmp_path,
            learners=1,
            vector_dim=2,
            num_fragments=1,
            steps=1,
            min_quorum=1,
            artifact_transfer_mode="object_store",
            artifact_storage_backend="s3_compatible",
            s3_artifact_backend=backend,
        )
    )

    ref = service._write_global_vector_artifact(
        "global_update",
        np.asarray([1.0, 2.0], dtype=np.float64),
        0,
    )

    assert ref["storage_backend"] == "s3_compatible"
    assert ref["metadata"]["s3_compatible_manifest_ref"]["backend_type"] == "s3_compatible"
    assert service.artifact_transport.validate_ref(ref).run_id == "run-s3-runtime"
