import hashlib
import hmac
import json
import time

from src.core.config.settings import settings


def sign_payload(payload: dict) -> tuple[str, dict]:
    timestamp = str(int(time.time()))
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    signed_content = f"{timestamp}.{body}".encode()

    sig = hmac.new(
        settings.webhook_secret.encode(),
        signed_content,
        hashlib.sha256,
    ).hexdigest()

    header_value = f"t={timestamp},v1={sig}"
    return header_value, {
        "X-Signature-256": header_value,
        "Content-Type": "application/json",
    }


def verify_signature(payload: dict, signature_header: str, tolerance_seconds: int = 300) -> bool:
    try:
        parts = dict(p.split("=", 1) for p in signature_header.split(","))
        timestamp = int(parts["t"])
        received_sig = parts["v1"]
    except (KeyError, ValueError):
        return False

    if abs(time.time() - timestamp) > tolerance_seconds:
        return False

    body = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    signed_content = f"{timestamp}.{body}".encode()
    expected = hmac.new(
        settings.webhook_secret.encode(),
        signed_content,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, received_sig)
