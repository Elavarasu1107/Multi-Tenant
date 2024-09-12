from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from core.db_manager import DatabaseManager

from .models import Member, Organisation, Role, User, get_db_session
from .schemas import *
from .tokens import Audience, JWTUtils

user = APIRouter(prefix="/api/user")


@user.post(
    "/signUp",
    response_model=BaseResponseSchema,
    status_code=status.HTTP_201_CREATED,
    responses={400: {"model": BaseErrorResponseSchema}},
)
async def register_user(body: RegisterUserSchema, db: DatabaseManager = Depends(get_db_session)):
    payload = body.model_dump()
    email = payload.get("email")
    password = payload.get("password")
    is_user_exist = await db.model(User).get_or_none(email=email)
    if is_user_exist:
        raise SQLAlchemyError("User already exists")
    user: User = await db.model(User).create(email=email, password=password)

    org_name = payload.get("org_name")
    organisation = await db.model(Organisation).get_or_create(name=org_name)

    role = payload.get("role")
    description = payload.get("description")

    role = await db.model(Role).get_or_create(name=role, org_id=organisation.id)
    if description:
        role.description = description
        await db.save()

    user_data = user.to_dict
    user_data.update(organisation=organisation.to_dict, role=role.to_dict)
    return {
        "message": "User Registered!",
        "status": "success",
        "data": user_data,
    }


@user.post(
    "/signIn",
    status_code=status.HTTP_200_OK,
    responses={400: {"model": BaseErrorResponseSchema}},
    response_model=BaseResponseSchema,
)
async def login_user(body: LoginUserSchema, db: DatabaseManager = Depends(get_db_session)):
    payload = body.model_dump()
    user = await db.model(User).authenticate(**payload)
    if not user:
        return JSONResponse(
            content={
                "message": "Invalid email or password!",
                "status": "fail",
            },
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
    token_payload = {"user_id": user.id, "aud": Audience.LOGIN.value}
    access = await JWTUtils.generate_access_token(payload=token_payload)
    refresh = await JWTUtils.generate_refresh_token(payload=token_payload)
    return {
        "message": "Login Successfull",
        "status": "success",
        "data": {"access_token": access, "refresh_token": refresh},
    }
