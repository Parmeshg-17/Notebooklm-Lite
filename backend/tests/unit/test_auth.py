import uuid
from app.core.security import create_access_token, decode_access_token, hash_password, verify_password


def test_password_hashing():
    password = "SuperSecurePassword123!"
    hashed = hash_password(password)
    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword", hashed) is False


def test_jwt_token_roundtrip():
    user_id = uuid.uuid4()
    token = create_access_token(subject=user_id)
    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == str(user_id)

