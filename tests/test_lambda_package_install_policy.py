from decodilo.lambda_cloud.package_install_policy import (
    build_lambda_package_install_policy,
    package_install_command_blocked,
)


def test_package_install_policy_denies_installs():
    report = build_lambda_package_install_policy()

    assert report.package_install_allowed is False
    assert package_install_command_blocked("pip install decodilo")
    assert package_install_command_blocked("apt-get install cuda")
    assert report.launch_ready is False
    assert report.launch_allowed is False
