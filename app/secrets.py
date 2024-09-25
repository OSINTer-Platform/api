import secrets
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from pydantic import SecretStr

hasher = PasswordHasher()


def generate_api_key() -> SecretStr:
    return SecretStr(secrets.token_urlsafe(64))


def hash_value(val: str) -> SecretStr:
    return SecretStr(hasher.hash(val))


def verify_hash(hashed_value: str, raw_value: str) -> bool:
    try:
        hasher.verify(hashed_value, raw_value)
    except VerifyMismatchError:
        return False

    return True
