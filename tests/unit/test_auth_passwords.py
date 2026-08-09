from limen.auth.passwords import hash_password, verify_password


def test_hash_is_salted_per_call() -> None:
    first = hash_password("umbral-seguro-2026")
    second = hash_password("umbral-seguro-2026")
    assert first != second
    assert verify_password("umbral-seguro-2026", first)
    assert verify_password("umbral-seguro-2026", second)


def test_wrong_password_does_not_verify() -> None:
    encoded = hash_password("umbral-seguro-2026")
    assert not verify_password("umbral-seguro-2025", encoded)


def test_plaintext_never_appears_in_the_encoded_hash() -> None:
    encoded = hash_password("umbral-seguro-2026")
    assert "umbral-seguro-2026" not in encoded
    assert encoded.startswith("scrypt$")


def test_malformed_hash_is_rejected_instead_of_raising() -> None:
    assert not verify_password("umbral-seguro-2026", "not-a-hash")
    assert not verify_password("umbral-seguro-2026", "")
    assert not verify_password("umbral-seguro-2026", "bcrypt$14$8$1$aaaa$bbbb")
