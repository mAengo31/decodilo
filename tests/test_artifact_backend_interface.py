from decodilo.storage.durable_object_backend import DurableFilesystemObjectStoreBackend
from decodilo.storage.local_backend import LocalFilesystemArtifactBackend
from decodilo.storage.s3_compatible_backend import (
    S3CompatibleArtifactBackend,
    S3CompatibleBackendConfig,
)


class _InterfaceFakeS3Client:
    def __init__(self) -> None:
        self.objects = {}

    def put_object(self, **kwargs):
        self.objects[(kwargs["Bucket"], kwargs["Key"])] = {
            "Body": bytes(kwargs["Body"]),
            "Metadata": dict(kwargs.get("Metadata") or {}),
            "VersionId": "1",
        }
        return {"VersionId": "1"}

    def get_object(self, **kwargs):
        import io

        obj = self.objects[(kwargs["Bucket"], kwargs["Key"])]
        data = obj["Body"]
        if "Range" in kwargs:
            start_text, end_text = kwargs["Range"].removeprefix("bytes=").split("-", 1)
            data = data[int(start_text) : int(end_text) + 1]
        return {"Body": io.BytesIO(data), "VersionId": obj["VersionId"]}

    def head_object(self, **kwargs):
        obj = self.objects[(kwargs["Bucket"], kwargs["Key"])]
        return {"Metadata": obj["Metadata"], "VersionId": obj["VersionId"]}

    def list_objects_v2(self, **kwargs):
        return {
            "Contents": [
                {"Key": key, "Size": len(obj["Body"])}
                for (bucket, key), obj in sorted(self.objects.items())
                if bucket == kwargs["Bucket"] and key.startswith(kwargs.get("Prefix", ""))
            ]
        }

    def delete_object(self, **kwargs):
        self.objects.pop((kwargs["Bucket"], kwargs["Key"]), None)
        return {}


def _s3_config() -> S3CompatibleBackendConfig:
    return S3CompatibleBackendConfig(
        endpoint_url="https://object.example.invalid",
        bucket="decodilo-test",
        prefix="interface",
        access_key_ref="S3_ACCESS_KEY_ID",
        secret_key_ref="S3_SECRET_ACCESS_KEY",
    )



def test_local_artifact_backend_write_read_and_capabilities(tmp_path) -> None:
    backend = LocalFilesystemArtifactBackend(tmp_path)
    ref = backend.write_bytes(artifact_id="artifact", data=b"payload")

    assert backend.read_bytes(ref) == b"payload"
    assert backend.list_refs() == [ref]
    capabilities = backend.capabilities()
    assert capabilities.local_filesystem is True
    assert capabilities.remote is False
    assert capabilities.model_dump(mode="json")["backend_type"] == "local_filesystem"


def test_durable_object_backend_write_read_and_capabilities(tmp_path) -> None:
    backend = DurableFilesystemObjectStoreBackend(tmp_path)
    ref = backend.write_bytes(artifact_id="artifact", data=b"payload")

    assert backend.read_bytes(ref) == b"payload"
    assert backend.read_range(ref, offset=0, length=4) == b"payl"
    assert backend.list_refs() == [ref]
    capabilities = backend.capabilities()
    assert capabilities.local_filesystem is True
    assert capabilities.remote is False
    assert capabilities.model_dump(mode="json")["backend_type"] == (
        "durable_filesystem_object_store"
    )



def test_s3_compatible_backend_can_satisfy_artifact_backend_interface() -> None:
    backend = S3CompatibleArtifactBackend(_s3_config(), client=_InterfaceFakeS3Client())
    ref = backend.write_bytes(artifact_id="artifact", data=b"payload")

    assert backend.read_bytes(ref) == b"payload"
    assert backend.read_range(ref, offset=1, length=3) == b"ayl"
    assert backend.list_refs() == [ref]
    assert backend.capabilities().remote is True
    assert backend.capabilities().credentials_required is True

