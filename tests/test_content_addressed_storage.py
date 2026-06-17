from decodilo.storage.content_addressed import ContentAddressedStore


def test_same_content_gets_same_hash_and_path(tmp_path) -> None:
    store = ContentAddressedStore(tmp_path)

    first = store.put_bytes(b"same")
    second = store.put_bytes(b"same")

    assert first == second
    assert store.get_bytes(first) == b"same"
    assert store.path_for_hash(first).exists()

