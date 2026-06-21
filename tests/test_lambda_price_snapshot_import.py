from decodilo.lambda_cloud.price_snapshot_import import (
    import_catalog_price_snapshot_from_html,
)


def test_import_catalog_price_snapshot_marks_non_sample(tmp_path):
    html = tmp_path / "lambda_instances.html"
    out = tmp_path / "price-snapshot.json"
    html.write_text(
        """
        <table>
        <tr><th>Instance Type</th><th>GPU Type</th><th>GPUs</th><th>Price / GPU Hour</th></tr>
        <tr><td>gpu_8x_h100_sxm</td><td>H100 SXM</td><td>8</td><td>$3.99</td></tr>
        </table>
        """,
        encoding="utf-8",
    )

    snapshot = import_catalog_price_snapshot_from_html(
        input_path=html,
        source_url="https://lambda.ai/instances",
        output_path=out,
        captured_at_utc="2026-06-18T00:00:00Z",
    )

    assert out.exists()
    assert snapshot.is_sample_data is False
    assert snapshot.records[0].price_per_instance_hour == 31.92
    assert snapshot.source_sha256
    assert snapshot.source_url == "https://lambda.ai/instances"
