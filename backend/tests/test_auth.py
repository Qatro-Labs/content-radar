"""Supabase Auth opcional: tokens firmados con una clave generada aquí y un JWKS falso, sin red."""

import base64
import json
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from httpx import ASGITransport, AsyncClient
from jwt.algorithms import ECAlgorithm

from app.api.auth import (
    JWKS_MAX_AGE_SECONDS,
    JWKS_REFRESH_INTERVAL_SECONDS,
    JWKS_STALE_LIMIT_SECONDS,
    SupabaseJwks,
    get_signing_keys,
)
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


class FakeFetcher:
    def __init__(self) -> None:
        jwk = json.loads(ECAlgorithm.to_jwk(_private_key.public_key()))
        self._jwk_set = jwt.PyJWKSet([{**jwk, "kid": KID, "alg": "ES256"}])
        self.calls = 0
        self.failing = False

    def rotate_out_the_key(self) -> None:
        other = ec.generate_private_key(ec.SECP256R1()).public_key()
        jwk = json.loads(ECAlgorithm.to_jwk(other))
        self._jwk_set = jwt.PyJWKSet([{**jwk, "kid": "new-key", "alg": "ES256"}])

    def get_jwk_set(self, refresh: bool = False) -> jwt.PyJWKSet:
        self.calls += 1
        if self.failing:
            raise jwt.PyJWKClientConnectionError("Supabase no responde")
        return self._jwk_set


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def unsigned_token(header: dict[str, object]) -> str:
    # PyJWT no deja codificar cabeceras inválidas; la firma da igual, el `kid` se mira antes.
    parts = [json.dumps(header).encode(), json.dumps({"sub": USER_ID}).encode(), b"firma"]
    return ".".join(base64.urlsafe_b64encode(p).rstrip(b"=").decode() for p in parts)


def token(*, kid: str = KID, **overrides: object) -> str:
    claims = {
        "sub": USER_ID,
        "email": EMAIL,
        "aud": "authenticated",
        "role": "authenticated",
        "iss": ISSUER,
        "exp": NOW + timedelta(hours=1),
        **overrides,
    }
    return jwt.encode(claims, _private_key, algorithm="ES256", headers={"kid": kid})


def bearer(value: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {value}"}


@pytest.fixture
def fetcher() -> FakeFetcher:
    return FakeFetcher()


@pytest.fixture
def configure(fetcher):
    def apply(*, auth_required: bool, supabase_url: str = SUPABASE_URL) -> None:
        settings = Settings(auth_required=auth_required, supabase_url=supabase_url)
        app.dependency_overrides[get_settings] = lambda: settings
        if supabase_url:
            keys = SupabaseJwks(fetcher)
            app.dependency_overrides[get_signing_keys] = lambda: keys
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
        bearer(token(is_anonymous=True)),
        bearer(token(role="anon")),
        bearer(token(sub="")),
    ],
    ids=[
        "no-token",
        "expired",
        "wrong-aud",
        "wrong-iss",
        "hs256-without-kid",
        "garbage",
        "anonymous-session",
        "anon-role",
        "empty-sub",
    ],
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


@pytest.mark.parametrize(
    "value",
    [
        unsigned_token({"alg": "ES256"}),
        token(kid=""),
        token(kid="../../etc"),
        token(kid="k" * 129),
        unsigned_token({"alg": "ES256", "kid": 42}),
    ],
    ids=["missing", "empty", "path-like", "too-long", "not-a-string"],
)
async def test_malformed_kid_is_401_without_fetching_the_jwks(configure, fetcher, value):
    configure(auth_required=True)

    response = await post_agent(bearer(value))

    assert response.status_code == 401
    assert fetcher.calls == 0


def test_unknown_kids_refresh_the_jwks_at_most_once_per_interval(fetcher):
    clock = FakeClock()
    keys = SupabaseJwks(fetcher, clock=clock)

    burst = [keys.signing_key(f"random-{i}") for i in range(50)]
    clock.now = JWKS_REFRESH_INTERVAL_SECONDS - 1
    keys.signing_key("random-late")
    calls_within_interval = fetcher.calls
    clock.now = JWKS_REFRESH_INTERVAL_SECONDS
    keys.signing_key("random-after")

    assert burst == [None] * 50
    assert calls_within_interval == 1
    assert fetcher.calls == 2


def test_known_kid_is_served_from_memory(fetcher):
    keys = SupabaseJwks(fetcher, clock=FakeClock())

    first, second = keys.signing_key(KID), keys.signing_key(KID)

    assert first is not None and second is first
    assert fetcher.calls == 1


def test_jwks_that_is_not_json_counts_as_unavailable():
    class HtmlFetcher:
        def get_jwk_set(self, refresh: bool = False) -> jwt.PyJWKSet:
            raise json.JSONDecodeError("Expecting value", "<html>", 0)

    keys = SupabaseJwks(HtmlFetcher(), clock=FakeClock())

    assert keys.signing_key(KID) is None


def test_known_kid_inside_max_age_makes_no_fetch(fetcher):
    clock = FakeClock()
    keys = SupabaseJwks(fetcher, clock=clock)
    keys.signing_key(KID)

    clock.now = JWKS_MAX_AGE_SECONDS - 1
    key = keys.signing_key(KID)

    assert key is not None
    assert fetcher.calls == 1


def test_key_removed_from_the_jwks_is_rejected_after_max_age(fetcher):
    clock = FakeClock()
    keys = SupabaseJwks(fetcher, clock=clock)
    keys.signing_key(KID)
    fetcher.rotate_out_the_key()

    clock.now = JWKS_MAX_AGE_SECONDS - 1
    before = keys.signing_key(KID)
    clock.now = JWKS_MAX_AGE_SECONDS
    after = keys.signing_key(KID)

    assert before is not None
    assert after is None
    assert fetcher.calls == 2


def test_failing_refresh_keeps_the_keys_until_the_stale_limit(fetcher):
    clock = FakeClock()
    keys = SupabaseJwks(fetcher, clock=clock)
    keys.signing_key(KID)
    fetcher.failing = True

    clock.now = JWKS_MAX_AGE_SECONDS
    at_max_age = keys.signing_key(KID)
    clock.now += 1
    retry_inside_interval = keys.signing_key(KID)
    calls_inside_interval = fetcher.calls
    clock.now = JWKS_STALE_LIMIT_SECONDS - 1
    inside_grace = keys.signing_key(KID)
    clock.now = JWKS_STALE_LIMIT_SECONDS
    after_grace = keys.signing_key(KID)

    assert at_max_age is not None and retry_inside_interval is not None
    assert calls_inside_interval == 2
    assert inside_grace is not None
    assert after_grace is None
