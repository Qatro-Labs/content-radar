from functools import lru_cache
from typing import Annotated, Protocol

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
AUTH_PATH = "/auth/v1"
JWKS_PATH = f"{AUTH_PATH}/.well-known/jwks.json"
JWKS_TIMEOUT_SECONDS = 5
REQUIRED_CLAIMS = ["exp", "sub", "aud", "iss"]
INVALID_TOKEN = "Inicia sesión para usar esta función."

# auto_error=False: sin cabecera, el 401 lo decide `_verify` y no FastAPI (que daría 403).
_bearer = HTTPBearer(auto_error=False)


class CurrentUser(BaseModel):
    user_id: str
    email: str | None = None


class SigningKeySource(Protocol):
    def get_signing_key_from_jwt(self, token: str) -> jwt.PyJWK: ...


@lru_cache
def _jwks_client(jwks_url: str) -> jwt.PyJWKClient:
    # PyJWKClient guarda el JWKS en memoria: solo vuelve a pedirlo si llega un `kid` nuevo.
    return jwt.PyJWKClient(jwks_url, timeout=JWKS_TIMEOUT_SECONDS)


def get_signing_keys(
    settings: Annotated[Settings, Depends(get_settings)],
) -> SigningKeySource | None:
    base = settings.supabase_url.rstrip("/")
    return _jwks_client(f"{base}{JWKS_PATH}") if base else None


def _unauthorized() -> HTTPException:
    return HTTPException(
        status.HTTP_401_UNAUTHORIZED, INVALID_TOKEN, headers={"WWW-Authenticate": "Bearer"}
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
    token = credentials.credentials
    try:
        signing_key = keys.get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=ALLOWED_ALGORITHMS,
            audience=SUPABASE_AUDIENCE,
            issuer=f"{settings.supabase_url.rstrip('/')}{AUTH_PATH}",
            options={"require": REQUIRED_CLAIMS},
        )
    except jwt.PyJWKClientConnectionError:
        log.warning("auth_jwks_unreachable")
        raise _unauthorized() from None
    except jwt.PyJWTError:
        raise _unauthorized() from None
    return CurrentUser(user_id=claims["sub"], email=claims.get("email"))


# Dependencias síncronas a propósito: FastAPI las corre en un hilo, y la primera descarga del
# JWKS (urllib, bloqueante) no frena el event loop.
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
