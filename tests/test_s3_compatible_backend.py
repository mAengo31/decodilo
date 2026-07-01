from __future__ import annotations

import io

import pytest

from decodilo.storage.artifact_backend import ArtifactBackendRef
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
