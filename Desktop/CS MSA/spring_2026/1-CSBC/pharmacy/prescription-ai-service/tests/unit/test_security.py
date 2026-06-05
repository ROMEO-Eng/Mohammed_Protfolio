"""Unit tests for JWT security utilities — no DB or network needed."""

import pytest
from datetime import timedelta

# Patch settings before importing security so tests use deterministic values
import os
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-unit-tests")
os.environ.setdefault("ALGORITHM", "HS256")
os.environ.setdefault("MONGODB_URL", "mongodb://localhost:27017")
os.environ.setdefault("MONGODB_DB_NAME", "pharmacy_ai_test")


from app.core.security import create_access_token, decode_token, ROLE_CUSTOMER, ROLE_ADMIN
from app.core.exceptions import AuthenticationException


class TestCreateAccessToken:
    def test_creates_valid_token(self):
        token = create_access_token("user-123", ROLE_CUSTOMER)
        assert isinstance(token, str)
        assert len(token) > 20

    def test_token_contains_correct_claims(self):
        token = create_access_token("user-abc", ROLE_ADMIN)
        payload = decode_token(token)
        assert payload["sub"] == "user-abc"
        assert payload["role"] == ROLE_ADMIN

    def test_custom_expiry(self):
        token = create_access_token("u1", expires_delta=timedelta(hours=2))
        payload = decode_token(token)
        assert payload["exp"] > payload["iat"]

    def test_role_normalised_to_lowercase(self):
        token = create_access_token("u2", role="PHARMACIST")
        payload = decode_token(token)
        assert payload["role"] == "pharmacist"


class TestDecodeToken:
    def test_valid_token_returns_payload(self):
        token = create_access_token("user-xyz", ROLE_CUSTOMER)
        payload = decode_token(token)
        assert payload["sub"] == "user-xyz"

    def test_expired_token_raises(self):
        token = create_access_token(
            "user-1", expires_delta=timedelta(seconds=-1)
        )
        with pytest.raises(AuthenticationException, match="expired"):
            decode_token(token)

    def test_tampered_token_raises(self):
        token = create_access_token("user-1") + "tampered"
        with pytest.raises(AuthenticationException):
            decode_token(token)

    def test_garbage_token_raises(self):
        with pytest.raises(AuthenticationException):
            decode_token("not.a.jwt")

    def test_unknown_role_defaults_to_customer(self):
        """Unknown roles should degrade gracefully."""
        from jose import jwt
        from app.config.settings import settings
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        payload = {
            "sub": "u99",
            "role": "super_hacker",
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=10)).timestamp()),
        }
        token = jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)
        result = decode_token(token)
        assert result["role"] == ROLE_CUSTOMER  # degraded to default
