from backend.auth_tokens import create_access_token, decode_access_token


def test_jwt_roundtrip():
    token = create_access_token(42, "admin")
    payload = decode_access_token(token)
    assert payload["sub"] == "42"
    assert payload["role"] == "admin"
