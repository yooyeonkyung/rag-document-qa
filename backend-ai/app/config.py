"""
Settings (env vars) + JWT auth, in one place since auth just reads settings.
"""
import base64

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Must match `jwt.secret` in backend/src/main/resources/application.yml
    # byte-for-byte - Spring issues the tokens, we only verify them.
    jwt_secret: str
    jwt_algorithm: str = "HS256"

    # Read-only access to the bucket Spring already uploaded the file to.
    aws_access_key_id: str
    aws_secret_access_key: str
    aws_region: str = "ap-northeast-2"

    allowed_origins: str = "http://localhost:3000,http://localhost:5173"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


settings = Settings()

_bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user_email(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> str:
    """FastAPI dependency: verify the Spring-issued JWT, return its subject (email).

    Spring's JwtTokenProvider signs with
    Keys.hmacShaKeyFor(Base64.decode(jwt.secret)) using HS256, and the token's
    only claim is `sub` = email. We decode the same way so a single Spring
    login is trusted here too, with no separate FastAPI login system.
    """
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")

    try:
        key_bytes = base64.b64decode(settings.jwt_secret)
        claims = jwt.decode(credentials.credentials, key_bytes, algorithms=[settings.jwt_algorithm])
    except jwt.InvalidTokenError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")

    email = claims.get("sub")
    if not email:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token has no subject")
    return email
