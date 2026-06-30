from __future__ import annotations

import asyncio
import base64

import numpy as np

from decodilo.runtime.artifact_transport import ArtifactTransportPolicy, LocalArtifactTransport
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
