from app.core.security import constant_time_equals, hash_secret, validate_password_strength


def test_constant_time_equals_matches():
    assert constant_time_equals("abc", "abc") is True
    assert constant_time_equals("abc", "abd") is False


def test_hash_secret_is_deterministic_and_salted():
    a = hash_secret("secret-value")
    b = hash_secret("secret-value")
    c = hash_secret("other-value")
    assert a == b
    assert a != c
    assert len(a) == 64


def test_password_policy():
    assert validate_password_strength("short") != []
    assert validate_password_strength("alllowercase1") != []  # no uppercase
    assert validate_password_strength("ALLUPPER1") != []  # no lowercase
    assert validate_password_strength("NoDigits") != []  # no number
    assert validate_password_strength("ValidPass1") == []
