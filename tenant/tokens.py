from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any

import jwt

from core.settings import settings


class Audience(Enum):
    REGISTER = "register"
    LOGIN = "login"
    RE_PASS = "reset"

    @classmethod
    def has_value(cls, value):
        return value in cls._value2member_map_


class JWTUtils:

    @classmethod
    def encode_token(cls, payload, exp: timedelta):
        now = datetime.now(tz=timezone.utc)
        if "aud" not in payload:
            raise jwt.exceptions.InvalidAudienceError("Audience required to encode token")
        payload["iat"] = now
        payload["exp"] = now + exp
        key = settings.SECRET_KEY
        token = jwt.encode(payload=payload, key=key, algorithm=settings.JWT_ALGORITHM)
        return token

    @classmethod
    async def generate_access_token(cls, payload, exp: int = None):
        if not exp:
            exp = timedelta(hours=settings.JWT_ACCESS_EXPIRY)
        payload["type"] = "access"
        token = cls.encode_token(payload=payload, exp=exp)
        return token

    @classmethod
    async def generate_refresh_token(cls, payload, exp: int = None):
        if not exp:
            exp = timedelta(days=settings.JWT_REFRESH_EXPIRY)
        payload["type"] = "refresh"
        token = cls.encode_token(payload=payload, exp=exp)
        return token

    @classmethod
    async def decode(cls, token: str, aud: Any):
        key = settings.SECRET_KEY
        payload = jwt.decode(jwt=token, key=key, algorithms=[settings.JWT_ALGORITHM], audience=aud)
        return payload
