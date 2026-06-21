from decodilo.lambda_cloud.product_catalog_evidence import (
    import_lambda_product_catalog_html,
)


def test_product_catalog_parses_lambda_instances_fixture(tmp_path):
    html = tmp_path / "lambda_instances.html"
    html.write_text(
        """
        <html><head><meta name="snapshot-timestamp" content="2026-06-18T00:00:00Z"></head>
        <body><table>
        <tr><th>Instance Type</th><th>GPU Type</th><th>GPUs</th>
            <th>GPU Memory (GB)</th><th>Price / GPU Hour</th></tr>
        <tr><td>gpu_8x_h100_sxm</td><td>H100 SXM</td><td>8</td><td>80</td><td>$3.99</td></tr>
        <tr><td>gpu_1x_h100_pcie</td><td>H100 PCIe</td><td>1</td><td>80</td><td>$3.29</td></tr>
        </table></body></html>
        """,
        encoding="utf-8",
    )

    report = import_lambda_product_catalog_html(
        html,
        source_url="https://lambda.ai/instances",
    )
    h100_sxm = next(
        record for record in report.records if record.instance_type == "gpu_8x_h100_sxm"
    )
    h100_pcie = next(
        record for record in report.records if record.instance_type == "gpu_1x_h100_pcie"
    )

    assert h100_sxm.price_per_gpu_hour == 3.99
    assert h100_sxm.price_per_instance_hour == 31.92
    assert h100_pcie.price_per_gpu_hour == 3.29
    assert report.is_sample_data is False
    assert report.source_hash
    assert report.launch_allowed is False
