"""
conftest.py — Shared fixtures for E2E tests (DEV-37)

Environment variables (set before running):
  BASE_URL           — API root, default http://localhost:8000
  ADMIN_TOKEN        — X-Admin-Token for seed-team, default from .env
  INTERNAL_API_TOKEN — X-Internal-Token for /chat, default "internal-secret-token"
"""
import os
import pytest
import httpx

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "codexy-admin-secret-2026")
INTERNAL_API_TOKEN = os.getenv("INTERNAL_API_TOKEN", "internal-secret-token")

# Default seed-team credentials (must match user_management_routes.py)
CEO_EMAIL = "ceo@codexy.com"
CEO_PASSWORD = "Codexy2026!"
SETTER_EMAIL = "setter1@codexy.com"
SETTER_PASSWORD = "Setter2026!"
CLOSER_EMAIL = "closer1@codexy.com"
CLOSER_PASSWORD = "Closer2026!"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def base_url() -> str:
    return BASE_URL.rstrip("/")


@pytest.fixture(scope="session")
def admin_token() -> str:
    return ADMIN_TOKEN


@pytest.fixture(scope="session")
def internal_token() -> str:
    return INTERNAL_API_TOKEN


@pytest.fixture(scope="session")
def client(base_url) -> httpx.Client:
    """Synchronous httpx client reused across the whole session."""
    with httpx.Client(base_url=base_url, timeout=30.0) as c:
        yield c


# --- Auth token helpers ---------------------------------------------------

def _login(client: httpx.Client, email: str, password: str) -> dict:
    """Login and return {"token": ..., "user": ...}."""
    resp = client.post("/login", json={"email": email, "password": password})
    assert resp.status_code == 200, f"Login failed for {email}: {resp.status_code} {resp.text}"
    data = resp.json()
    return {
        "token": data["access_token"],
        "user": data.get("user", {}),
    }


@pytest.fixture(scope="session")
def ceo_auth(client) -> dict:
    """Returns {"token": str, "user": dict} for CEO."""
    return _login(client, CEO_EMAIL, CEO_PASSWORD)


@pytest.fixture(scope="session")
def setter_auth(client) -> dict:
    """Returns {"token": str, "user": dict} for Setter 1."""
    return _login(client, SETTER_EMAIL, SETTER_PASSWORD)


@pytest.fixture(scope="session")
def closer_auth(client) -> dict:
    """Returns {"token": str, "user": dict} for Closer 1."""
    return _login(client, CLOSER_EMAIL, CLOSER_PASSWORD)


def auth_headers(token: str) -> dict:
    """Build Authorization header dict from a JWT token."""
    return {"Authorization": f"Bearer {token}"}
