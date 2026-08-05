import hashlib
import hmac
import re
import secrets

from app.core.config import get_settings


def generate_secret() -> str:
    return secrets.token_urlsafe(48)


def hash_secret(value: str) -> str:
    """HMAC-SHA256 of a secret using the app secret key as HMAC key."""
    settings = get_settings()
    return hmac.new(settings.secret_key.encode(), value.encode(), hashlib.sha256).hexdigest()


def constant_time_equals(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode(), b.encode())


def validate_password_strength(password: str) -> list[str]:
    """Return a list of password policy violations (empty when strong enough)."""
    settings = get_settings()
    issues: list[str] = []
    if len(password) < settings.password_min_length:
        issues.append(f"Password must be at least {settings.password_min_length} characters")
    if not re.search(r"[A-Z]", password):
        issues.append("Password must contain an uppercase letter")
    if not re.search(r"[a-z]", password):
        issues.append("Password must contain a lowercase letter")
    if not re.search(r"\d", password):
        issues.append("Password must contain a number")
    return issues
