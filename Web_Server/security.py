import base64
import hashlib
import hmac
import json
import os
import time


JWT_SECRET = os.getenv("JWT_SECRET_KEY", "change-this-secret-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXP_SECONDS = 60 * 60 * 24


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("utf-8")


def _b64url_decode(value: str) -> bytes:
    padding = "=" * ((4 - len(value) % 4) % 4)
    return base64.urlsafe_b64decode((value + padding).encode("utf-8"))


def create_access_token(payload: dict, expires_in: int = JWT_EXP_SECONDS) -> str:
    header = {"alg": JWT_ALGORITHM, "typ": "JWT"}
    claims = {**payload, "exp": int(time.time()) + expires_in}

    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    claims_b64 = _b64url_encode(json.dumps(claims, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_b64}.{claims_b64}".encode("utf-8")

    signature = hmac.new(JWT_SECRET.encode("utf-8"), signing_input, hashlib.sha256).digest()
    signature_b64 = _b64url_encode(signature)

    return f"{header_b64}.{claims_b64}.{signature_b64}"


def decode_access_token(token: str) -> dict:
    try:
        header_b64, claims_b64, signature_b64 = token.split(".")
    except ValueError:
        raise ValueError("Invalid token format")

    signing_input = f"{header_b64}.{claims_b64}".encode("utf-8")
    expected_signature = hmac.new(
        JWT_SECRET.encode("utf-8"),
        signing_input,
        hashlib.sha256
    ).digest()
    provided_signature = _b64url_decode(signature_b64)

    if not hmac.compare_digest(expected_signature, provided_signature):
        raise ValueError("Invalid token signature")

    claims_raw = _b64url_decode(claims_b64)
    claims = json.loads(claims_raw.decode("utf-8"))

    exp = claims.get("exp")
    if exp is None or int(exp) < int(time.time()):
        raise ValueError("Token expired")

    return claims