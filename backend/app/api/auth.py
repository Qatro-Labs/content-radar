import re
import threading
import time
from collections.abc import Callable
from functools import lru_cache
from typing import Annotated, Any, Protocol

import jwt
import structlog
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from app.core.config import Settings, get_settings

log = structlog.get_logger()

# Supabase firma los access tokens con claves asimétricas publicadas en su JWKS.
ALLOWED_ALGORITHMS = ["ES256", "RS256"]
SUPABASE_AUDIENCE = "authenticated"
AUTHENTICATED_ROLE = "authenticated"
AUTH_PATH = "/auth/v1"
JWKS_PATH = f"{AUTH_PATH}/.well-known/jwks.json"
JWKS_TIMEOUT_SECONDS = 5
# Un token con un `kid` inventado obliga a pedir el JWKS de nuevo: como mucho una vez por
# intervalo y proceso, para que nadie sin sesión convierta la API en un amplificador de peticiones.
JWKS_REFRESH_INTERVAL_SECONDS = 60
# Pasado este tiempo se vuelve a pedir el JWKS aunque el `kid` sea conocido: una clave que Supabase
# revocó o rotó deja de aceptarse sin reiniciar el proceso.
JWKS_MAX_AGE_SECONDS = 600
# Si Supabase no responde, las claves en memoria siguen valiendo hasta este límite; después, 401.
JWKS_STALE_LIMIT_SECONDS = 2 * JWKS_MAX_AGE_SECONDS
# Supabase usa UUIDs como `kid`; esto deja margen sin aceptar texto arbitrario.
KID_PATTERN = re.compile(r"[A-Za-z0-9_.-]{1,128}")
REQUIRED_CLAIMS = ["exp", "sub", "aud", "iss"]
INVALID_TOKEN = "Inicia sesión para usar esta función."

# auto_error=False: sin cabecera, el 401 lo decide `_verify` y no FastAPI (que daría 403).
_bearer = HTTPBearer(auto_error=False)


class CurrentUser(BaseModel):
    user_id: str
    email: str | None = None


class JwksFetcher(Protocol):
    def get_jwk_set(self, refresh: bool = False) -> jwt.PyJWKSet: ...


class SupabaseJwks:
    def __init__(
        self,
        fetcher: JwksFetcher,
        *,
        clock: Callable[[], float] = time.monotonic,
        refresh_interval: float = JWKS_REFRESH_INTERVAL_SECONDS,
        max_age: float = JWKS_MAX_AGE_SECONDS,
        stale_limit: float = JWKS_STALE_LIMIT_SECONDS,
    ) -> None:
        self._fetcher = fetcher
        self._clock = clock
        self._refresh_interval = refresh_interval
        self._max_age = max_age
        self._stale_limit = stale_limit
        self._keys: dict[str, jwt.PyJWK] = {}
        self._last_fetch: float | None = None
        self._last_success: float | None = None
        self._lock = threading.Lock()

    def signing_key(self, kid: str) -> jwt.PyJWK | None:
        with self._lock:
            if self._needs_refresh(kid) and self._may_refresh():
                self._refresh()
            if self._age() >= self._stale_limit:
                return None
            return self._keys.get(kid)

    def _age(self) -> float:
        if self._last_success is None:
            return float("inf")
        return self._clock() - self._last_success

    def _needs_refresh(self, kid: str) -> bool:
        return kid not in self._keys or self._age() >= self._max_age

    def _may_refresh(self) -> bool:
        return self._last_fetch is None or (
            self._clock() - self._last_fetch >= self._refresh_interval
        )

    def _refresh(self) -> None:
        # El intento cuenta aunque falle: un JWKS caído tampoco se pide en cada request.
        self._last_fetch = self._clock()
        try:
            jwk_set = self._fetcher.get_jwk_set(refresh=True)
        # ValueError: PyJWT no envuelve el error de una respuesta 200 que no es JSON (p. ej. una
        # página HTML si SUPABASE_URL apunta a otro host).
        except (jwt.PyJWTError, ValueError) as e:
            log.warning("auth_jwks_unavailable", error=type(e).__name__)
            return
        # Se sustituye el conjunto entero: una clave que ya no publica Supabase deja de valer.
        self._keys = {key.key_id: key for key in jwk_set.keys if key.key_id}
        self._last_success = self._last_fetch


class SigningKeySource(Protocol):
    def signing_key(self, kid: str) -> jwt.PyJWK | None: ...


@lru_cache
def _supabase_jwks(jwks_url: str) -> SupabaseJwks:
    return SupabaseJwks(jwt.PyJWKClient(jwks_url, timeout=JWKS_TIMEOUT_SECONDS))


def get_signing_keys(
    settings: Annotated[Settings, Depends(get_settings)],
) -> SigningKeySource | None:
    base = settings.supabase_url.rstrip("/")
    return _supabase_jwks(f"{base}{JWKS_PATH}") if base else None


def _unauthorized() -> HTTPException:
    return HTTPException(
        status.HTTP_401_UNAUTHORIZED, INVALID_TOKEN, headers={"WWW-Authenticate": "Bearer"}
    )


def _valid_kid(token: str) -> str | None:
    # Antes de buscar la clave: un token mal formado nunca provoca una petición al JWKS.
    header = jwt.get_unverified_header(token)
    kid = header.get("kid")
    if header.get("alg") not in ALLOWED_ALGORITHMS or not isinstance(kid, str):
        return None
    return kid if KID_PATTERN.fullmatch(kid) else None


def _is_signed_in_user(claims: dict[str, Any]) -> bool:
    # Las sesiones anónimas de Supabase también llevan aud "authenticated".
    sub = claims.get("sub")
    return (
        isinstance(sub, str)
        and sub != ""
        and claims.get("role") == AUTHENTICATED_ROLE
        and claims.get("is_anonymous") is not True
    )


def _decode(token: str, settings: Settings, keys: SigningKeySource) -> dict[str, Any] | None:
    kid = _valid_kid(token)
    signing_key = keys.signing_key(kid) if kid else None
    if signing_key is None:
        return None
    return jwt.decode(
        token,
        signing_key.key,
        algorithms=ALLOWED_ALGORITHMS,
        audience=SUPABASE_AUDIENCE,
        issuer=f"{settings.supabase_url.rstrip('/')}{AUTH_PATH}",
        options={"require": REQUIRED_CLAIMS},
    )


def _verify(
    credentials: HTTPAuthorizationCredentials | None,
    settings: Settings,
    keys: SigningKeySource | None,
) -> CurrentUser:
    if credentials is None:
        raise _unauthorized()
    if keys is None:
        log.warning("auth_without_supabase_url")
        raise _unauthorized()
    try:
        claims = _decode(credentials.credentials, settings, keys)
    except jwt.PyJWTError:
        raise _unauthorized() from None
    if claims is None or not _is_signed_in_user(claims):
        raise _unauthorized()
    return CurrentUser(user_id=claims["sub"], email=claims.get("email"))


# Dependencias síncronas a propósito: FastAPI las corre en un hilo, y la descarga del JWKS
# (urllib, bloqueante) no frena el event loop.
def require_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    settings: Annotated[Settings, Depends(get_settings)],
    keys: Annotated[SigningKeySource | None, Depends(get_signing_keys)],
) -> CurrentUser:
    return _verify(credentials, settings, keys)


def require_user_if_enabled(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    settings: Annotated[Settings, Depends(get_settings)],
    keys: Annotated[SigningKeySource | None, Depends(get_signing_keys)],
) -> CurrentUser | None:
    if not settings.auth_required:
        return None
    return _verify(credentials, settings, keys)
