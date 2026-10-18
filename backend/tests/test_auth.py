"""Supabase Auth opcional: tokens firmados con una clave generada aquí y un JWKS falso, sin red."""

import json
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from httpx import ASGITransport, AsyncClient
from jwt.algorithms import ECAlgorithm

from app.api.auth import get_signing_keys
from app.api.routes.agent import get_agent_model
from app.core.config import Settings, get_settings
from app.main import app

SUPABASE_URL = "https://demo.supabase.co"
ISSUER = f"{SUPABASE_URL}/auth/v1"
KID = "test-key"
USER_ID = "8f1c2d3e-0000-4000-8000-000000000001"
EMAIL = "editor@example.com"
NOW = datetime.now(UTC)

_private_key = ec.generate_private_key(ec.SECP256R1())


class FakeJwks:
    def __init__(self) -> None:
        jwk = json.loads(ECAlgorithm.to_jwk(_private_key.public_key()))
        self._key = jwt.PyJWK({**jwk, "kid": KID, "alg": "ES256"})

    def get_signing_key_from_jwt(self, token: str) -> jwt.PyJWK:
        if jwt.get_unverified_header(token).get("kid") != KID:
            raise jwt.PyJWKClientError("kid desconocido")
        return self._key


def token(**overrides: object) -> str:
    claims = {
        "sub": USER_ID,
        "email": EMAIL,
        "aud": "authenticated",
        "iss": ISSUER,
        "exp": NOW + timedelta(hours=1),
        **overrides,
    }
    return jwt.encode(claims, _private_key, algorithm="ES256", headers={"kid": KID})


def bearer(value: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {value}"}


@pytest.fixture
def configure():
    def apply(*, auth_required: bool, supabase_url: str = SUPABASE_URL) -> None:
        settings = Settings(auth_required=auth_required, supabase_url=supabase_url)
        app.dependency_overrides[get_settings] = lambda: settings
        if supabase_url:
            app.dependency_overrides[get_signing_keys] = FakeJwks
        # Sin LLM, el agente responde 503 después de pasar la sesión: 503 = la sesión no bloqueó.
        app.dependency_overrides[get_agent_model] = lambda: None

    try:
        yield apply
    finally:
        app.dependency_overrides.clear()


async def post_agent(headers: dict[str, str] | None = None):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        return await client.post(
            "/api/v1/agent", json={"question": "¿Qué acelera?"}, headers=headers
        )


async def get_me(headers: dict[str, str] | None = None):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        return await client.get("/api/v1/me", headers=headers)


async def test_flag_off_needs_no_token(configure):
    configure(auth_required=False)

    response = await post_agent()

    assert response.status_code == 503


async def test_flag_on_accepts_a_valid_token(configure):
    configure(auth_required=True)

    response = await post_agent(bearer(token()))

    assert response.status_code == 503


@pytest.mark.parametrize(
    "headers",
    [
        None,
        bearer(token(exp=NOW - timedelta(minutes=1))),
        bearer(token(aud="anon")),
        bearer(token(iss="https://otro.supabase.co/auth/v1")),
        bearer(jwt.encode({"sub": USER_ID}, "x" * 32, algorithm="HS256")),
        bearer("no-es-un-jwt"),
    ],
    ids=["no-token", "expired", "wrong-aud", "wrong-iss", "hs256-without-kid", "garbage"],
)
async def test_flag_on_rejects_missing_or_invalid_token(configure, headers):
    configure(auth_required=True)

    response = await post_agent(headers)

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


async def test_flag_on_checks_the_token_before_the_brief_body(configure):
    configure(auth_required=True)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/editorial/brief", json={})

    assert response.status_code == 401


async def test_empty_supabase_url_is_401_not_500(configure):
    configure(auth_required=True, supabase_url="")

    response = await post_agent(bearer(token()))

    assert response.status_code == 401


@pytest.mark.parametrize("auth_required", [False, True], ids=["flag-off", "flag-on"])
async def test_me_returns_the_user_of_the_token(configure, auth_required):
    configure(auth_required=auth_required)

    response = await get_me(bearer(token()))

    assert response.status_code == 200
    assert response.json() == {"user_id": USER_ID, "email": EMAIL}


@pytest.mark.parametrize("auth_required", [False, True], ids=["flag-off", "flag-on"])
async def test_me_without_token_is_401(configure, auth_required):
    configure(auth_required=auth_required)

    response = await get_me()

    assert response.status_code == 401


async def test_me_with_empty_supabase_url_is_401(configure):
    configure(auth_required=False, supabase_url="")

    response = await get_me(bearer(token()))

    assert response.status_code == 401
