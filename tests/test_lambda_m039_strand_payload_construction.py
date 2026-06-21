from __future__ import annotations

from lambda_m038_helpers import write_m038_inputs
from lambda_m039a_helpers import RAW_TEST_SSH_KEY_NAME, load_lower_cost_gates

from decodilo.cli import _m039_resource_lock_from_lower_cost_attempt
from decodilo.lambda_cloud.real_launch_arming import LambdaM029ArmingToken
from decodilo.lambda_cloud.real_launch_client import LambdaM029RealLaunchClient
from decodilo.lambda_cloud.real_mutation_transport import (
    LambdaM029RealMutationTransport,
    LambdaM029TransportConfig,
)


def test_m039_lower_cost_path_constructs_strand_payload(tmp_path):
    paths = write_m038_inputs(tmp_path, approval_complete=True)
    gates = load_lower_cost_gates(paths)
    resource_lock = _m039_resource_lock_from_lower_cost_attempt(gates)
    transport = LambdaM029RealMutationTransport(
        config=LambdaM029TransportConfig(
            base_url="memory://lambda-m039-test",
            fake_server_mode=True,
        )
    )
    token = LambdaM029ArmingToken(
        token_id="fake",
        run_id="m039-test",
        max_budget=50,
        max_runtime_minutes=30,
        max_instances=1,
        arming_succeeded=True,
        fake_server_mode=True,
        real_lambda_api_allowed=False,
    )

    LambdaM029RealLaunchClient(transport).launch_one_instance(
        resource_lock=resource_lock,
        arming_token=token,
        idempotency_key="m039-idempotency",
    )

    body = transport.audit_log[-1].request_body_redacted
    assert body["region_name"] == "us-west-1"
    assert body["instance_type_name"] == "gpu_1x_h100_pcie"
    assert body["quantity"] == 1
    assert body["ssh_key_names"] == "<redacted>"
    assert "region" not in body
    assert "gpu_type" not in body
    assert "setup_script" not in body
    assert "cloud_init" not in body
    assert "user_data" not in body
    assert "training" not in body
    assert RAW_TEST_SSH_KEY_NAME not in str(body)
