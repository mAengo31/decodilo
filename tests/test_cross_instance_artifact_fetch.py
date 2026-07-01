from __future__ import annotations

import asyncio
import base64

import numpy as np

from decodilo.runtime.artifact_transport import (
    ArtifactTransportPolicy,
    LocalArtifactTransport,
)
from decodilo.runtime.chunked_update_delivery import apply_update_ref_to_vector
from decodilo.storage.chunk_store import ChunkStore
from decodilo.syncer.global_state_store import write_global_vector_artifact
from decodilo.transport.envelope import MessageType, make_envelope
from decodilo.transport.tcp_client import JsonlTcpClient
from decodilo.transport.tcp_server import JsonlTcpServer


def test_syncer_serves_artifact_bundle_that_learner_materializes(tmp_path) -> None:
    syncer_workdir = tmp_path / "syncer"
    learner_workdir = tmp_path / "learner"
    syncer_transport = LocalArtifactTransport(
        policy=ArtifactTransportPolicy(
            workdir=str(syncer_workdir),
            artifact_root=str(syncer_workdir / "artifacts"),
        )
    )
    ref = write_global_vector_artifact(
        vector=np.asarray([1.0, 2.0, 3.0], dtype=np.float64),
        run_id="run-artifact-fetch",
        global_version=7,
        artifact_id="run-artifact-fetch:global:7",
        artifact_type="global_update",
        transport=syncer_transport,
        manifest_path=syncer_workdir / "artifacts" / "global-v7.artifact.json",
        chunk_root=syncer_workdir / "artifacts" / "store",
        chunk_size_bytes=32,
    )
    learner_transport = LocalArtifactTransport(
        policy=ArtifactTransportPolicy(
            workdir=str(learner_workdir),
            artifact_root=str(learner_workdir / "artifacts"),
        )
    )

    async def scenario() -> None:
        from decodilo.runtime.remote_artifact_fetch import materialize_artifact_bundle

        async def handler(envelope):
            assert envelope.message_type == MessageType.FETCH_ARTIFACT
            manifest = syncer_transport.validate_ref(envelope.payload["artifact_ref"])
            _, chunk_root = syncer_transport.resolve_ref_paths(envelope.payload["artifact_ref"])
            store = ChunkStore(chunk_root)
            return make_envelope(
                run_id=envelope.run_id,
                sender_id="syncer",
                recipient_id=envelope.sender_id,
                message_type=MessageType.FETCH_ARTIFACT_RESPONSE,
                payload={
                    "artifact_ref": envelope.payload["artifact_ref"],
                    "manifest": manifest.model_dump(mode="json"),
                    "chunks": [
                        {
                            "sha256": chunk_hash,
                            "data_b64": base64.b64encode(store.cas.get_bytes(chunk_hash)).decode(
                                "ascii"
                            ),
                        }
                        for chunk_hash in manifest.chunk_hashes
                    ],
                },
            )

        server = JsonlTcpServer(handler=handler, run_id="run-artifact-fetch")
        await server.start()
        assert server.bound_port is not None
        async with JsonlTcpClient(host="127.0.0.1", port=server.bound_port) as client:
            response = await client.request(
                make_envelope(
                    run_id="run-artifact-fetch",
                    sender_id="learner-0",
                    recipient_id="syncer",
                    message_type=MessageType.FETCH_ARTIFACT,
                    payload={"artifact_ref": ref.model_dump(mode="json")},
                )
            )
        await server.close()
        materialize_artifact_bundle(response.payload, transport=learner_transport)

    asyncio.run(scenario())
    vector, version = apply_update_ref_to_vector(
        ref=ref.model_dump(mode="json"),
        transport=learner_transport,
    )
    np.testing.assert_allclose(vector, np.asarray([1.0, 2.0, 3.0]))
    assert version == 7


def test_syncer_object_store_transfers_artifact_chunk_by_chunk(tmp_path) -> None:
    syncer_workdir = tmp_path / "syncer"
    learner_workdir = tmp_path / "learner"
    syncer_transport = LocalArtifactTransport(
        policy=ArtifactTransportPolicy(
            workdir=str(syncer_workdir),
            artifact_root=str(syncer_workdir / "artifacts"),
            storage_backend="syncer_object_store",
        )
    )
    learner_transport = LocalArtifactTransport(
        policy=ArtifactTransportPolicy(
            workdir=str(learner_workdir),
            artifact_root=str(learner_workdir / "artifacts"),
            storage_backend="syncer_object_store",
        )
    )
    ref = write_global_vector_artifact(
        vector=np.arange(32, dtype=np.float64),
        run_id="run-object-store",
        global_version=3,
        artifact_id="run-object-store:global:3",
        artifact_type="global_update",
        transport=learner_transport,
        manifest_path=learner_workdir / "artifacts" / "global-v3.artifact.json",
        chunk_root=learner_workdir / "artifacts" / "store",
        chunk_size_bytes=64,
    )
    assert ref.storage_backend == "syncer_object_store"

    async def scenario() -> None:
        from decodilo.runtime.remote_artifact_fetch import (
            artifact_bundle_from_ref,
            artifact_chunk_from_ref,
            artifact_metadata_from_ref,
            materialize_artifact_chunk_upload,
        )

        async def handler(envelope):
            if envelope.message_type == MessageType.UPLOAD_ARTIFACT_CHUNK:
                result = materialize_artifact_chunk_upload(
                    envelope.payload,
                    transport=syncer_transport,
                )
                return make_envelope(
                    run_id=envelope.run_id,
                    sender_id="syncer",
                    recipient_id=envelope.sender_id,
                    message_type=MessageType.UPLOAD_ARTIFACT_CHUNK_ACK,
                    payload=result,
                )
            if envelope.message_type == MessageType.FETCH_ARTIFACT:
                return make_envelope(
                    run_id=envelope.run_id,
                    sender_id="syncer",
                    recipient_id=envelope.sender_id,
                    message_type=MessageType.FETCH_ARTIFACT_RESPONSE,
                    payload=artifact_metadata_from_ref(
                        envelope.payload["artifact_ref"],
                        transport=syncer_transport,
                    ),
                )
            if envelope.message_type == MessageType.FETCH_ARTIFACT_CHUNK:
                return make_envelope(
                    run_id=envelope.run_id,
                    sender_id="syncer",
                    recipient_id=envelope.sender_id,
                    message_type=MessageType.FETCH_ARTIFACT_CHUNK_RESPONSE,
                    payload=artifact_chunk_from_ref(
                        envelope.payload["artifact_ref"],
                        chunk_hash=envelope.payload["sha256"],
                        transport=syncer_transport,
                    ),
                )
            raise AssertionError(envelope.message_type)

        server = JsonlTcpServer(handler=handler, run_id="run-object-store")
        await server.start()
        assert server.bound_port is not None
        bundle = artifact_bundle_from_ref(ref, transport=learner_transport)
        upload_messages = 0
        async with JsonlTcpClient(host="127.0.0.1", port=server.bound_port) as client:
            for index, chunk in enumerate(bundle["chunks"]):
                upload_messages += 1
                response = await client.request(
                    make_envelope(
                        run_id="run-object-store",
                        sender_id="learner-0",
                        recipient_id="syncer",
                        message_type=MessageType.UPLOAD_ARTIFACT_CHUNK,
                        payload={
                            "artifact_ref": bundle["artifact_ref"],
                            "manifest": bundle["manifest"],
                            "chunk": chunk,
                            "final": index == len(bundle["chunks"]) - 1,
                        },
                    )
                )
                assert response.message_type == MessageType.UPLOAD_ARTIFACT_CHUNK_ACK
            assert upload_messages == len(bundle["chunks"])

            metadata = await client.request(
                make_envelope(
                    run_id="run-object-store",
                    sender_id="learner-1",
                    recipient_id="syncer",
                    message_type=MessageType.FETCH_ARTIFACT,
                    payload={
                        "artifact_ref": ref.model_dump(mode="json"),
                        "response_mode": "metadata_only",
                    },
                )
            )
            assert metadata.message_type == MessageType.FETCH_ARTIFACT_RESPONSE
            assert all("data_b64" not in item for item in metadata.payload["chunks"])
            for index, chunk_meta in enumerate(metadata.payload["chunks"]):
                chunk = await client.request(
                    make_envelope(
                        run_id="run-object-store",
                        sender_id="learner-1",
                        recipient_id="syncer",
                        message_type=MessageType.FETCH_ARTIFACT_CHUNK,
                        payload={
                            "artifact_ref": metadata.payload["artifact_ref"],
                            "sha256": chunk_meta["sha256"],
                        },
                    )
                )
                materialize_artifact_chunk_upload(
                    {
                        "artifact_ref": metadata.payload["artifact_ref"],
                        "manifest": metadata.payload["manifest"],
                        "chunk": chunk.payload,
                        "final": index == len(metadata.payload["chunks"]) - 1,
                    },
                    transport=learner_transport,
                )
        await server.close()

    asyncio.run(scenario())
    vector, version = apply_update_ref_to_vector(
        ref=ref.model_dump(mode="json"),
        transport=learner_transport,
    )
    np.testing.assert_allclose(vector, np.arange(32, dtype=np.float64))
    assert version == 3

