from pathlib import Path


def test_binary_codec_modules_do_not_use_pickle_or_torch_save() -> None:
    for path in [
        Path("src/decodilo/storage/tensor_binary_format.py"),
        Path("src/decodilo/storage/tensor_codec.py"),
        Path("src/decodilo/storage/tensor_artifact.py"),
        Path("src/decodilo/trainer/binary_fragment_codec.py"),
    ]:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        assert "pickle" not in text
        assert "torch.save" not in text
