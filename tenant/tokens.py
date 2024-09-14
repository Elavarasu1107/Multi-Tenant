from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any

import jwt
from fastapi import Request

from core.settings import settings


class Audience(Enum):
    REGISTER = "register"
    LOGIN = "login"
    RE_PASS = "reset"
    INVITE = "invite"

    @classmethod
    def has_value(cls, value):
        return value in cls._value2member_map_


class JWTUtils:

    @classmethod
    async def encode_token(cls, payload, exp: timedelta):
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
        else:
            exp = timedelta(minutes=exp)
        payload["type"] = "access"
        token = await cls.encode_token(payload=payload, exp=exp)
        return token

    @classmethod
    async def generate_refresh_token(cls, payload, exp: int = None):
        if not exp:
            exp = timedelta(days=settings.JWT_REFRESH_EXPIRY)
        payload["type"] = "refresh"
        token = await cls.encode_token(payload=payload, exp=exp)
        return token

    @classmethod
    async def decode_token(cls, token: str, aud: Any, request: Request):
        try:
            key = settings.SECRET_KEY
            payload = jwt.decode(
                jwt=token, key=key, algorithms=[settings.JWT_ALGORITHM], audience=aud
            )
            return payload
        except jwt.exceptions.ExpiredSignatureError:
            # refresh_token = request.cookies.get("refresh_token")
            # if not refresh_token:
            #     return None
            # refresh_payload = await cls.decode_token(token=refresh_token, aud=aud, request=request)
            # payload = {"user_id": refresh_payload["user_id"], "aud": refresh_payload["aud"]}
            # new_access_token = await cls.generate_access_token(payload=payload)
            return None
        except jwt.exceptions.PyJWTError:
            return None
