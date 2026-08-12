import hashlib
import hmac
import secrets

from pwdlib import PasswordHash

PASSWORD_HASHER = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return PASSWORD_HASHER.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return PASSWORD_HASHER.verify(password, password_hash)


def create_bearer_token() -> str:
    return secrets.token_urlsafe(32)


def digest_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def token_digest_matches(token: str, digest: str) -> bool:
    return hmac.compare_digest(digest_token(token), digest)
