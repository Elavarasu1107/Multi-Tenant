from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from core.db_manager import DatabaseManager

from .models import Member, Organisation, Role, User, get_db_session
from .schemas import *
from .tokens import Audience, JWTUtils

user = APIRouter(prefix="/api/user", tags=["User"])


@user.post(
    "/signUp",
    response_model=BaseResponseSchema,
    status_code=status.HTTP_201_CREATED,
    responses={400: {"model": BaseErrorResponseSchema}},
)
async def register_user(
    body: RegisterUserSchema, request: Request, db: DatabaseManager = Depends(get_db_session)
):
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

    invitation_payload = {
        "user_id": user.id,
        "org_id": organisation.id,
        "role_id": role.id,
        "aud": Audience.INVITE.value,
    }

    token = await JWTUtils.generate_access_token(invitation_payload, exp=15)
    url = request.url_for("invite_member", token=token)

    user_data = user.to_dict
    user_data.update(organisation=organisation.to_dict, role=role.to_dict)
    return {
        "message": "User Registered and Member invitation send to registered E-mail!",
        "status": "success",
        "data": user_data,
    }


@user.post(
    "/signIn",
    status_code=status.HTTP_200_OK,
    responses={400: {"model": BaseErrorResponseSchema}},
    response_model=BaseResponseSchema,
)
async def login_user(
    body: LoginUserSchema, response: Response, db: DatabaseManager = Depends(get_db_session)
):
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

    # response.set_cookie(key="refresh_token", value=refresh, secure=False)
    return {
        "message": "Login Successfull",
        "status": "success",
        "data": {"access_token": access, "refresh_token": refresh},
    }


@user.post("/forgotPassword")
async def forgot_password(body: ForgotPassSchema, db: DatabaseManager = Depends(get_db_session)):
    user = await db.model(User).get_or_none(email=body.email)
    if not user:
        return JSONResponse(
            content={
                "message": "Email does not exist",
                "status": "fail",
            },
            status_code=status.HTTP_404_NOT_FOUND,
        )
    token_payload = {"user_id": user.id, "aud": Audience.RE_PASS.value}
    token = await JWTUtils.generate_access_token(payload=token_payload, exp=5)
    return {
        "message": "Reset link sent to registered email",
        "status": "success",
        "data": {"token": token},
    }


@user.post("/resetPassword/{token}")
async def reset_password(
    body: ResetPassSchema,
    request: Request,
    token: str,
    db: DatabaseManager = Depends(get_db_session),
):
    if not token:
        return JSONResponse(
            content={
                "message": "Token required to reset password",
                "status": "fail",
            },
            status_code=status.HTTP_403_FORBIDDEN,
        )
    token_payload = await JWTUtils.decode_token(
        token=token, aud=Audience.RE_PASS.value, request=request
    )
    user_id = token_payload.get("user_id")
    if not user_id:
        raise KeyError("Invalid token")
    user = await db.model(User).get_or_none(id=user_id)
    if not user:
        raise HTTPException(detail="User does not exist", status_code=status.HTTP_400_BAD_REQUEST)

    user.password = user.set_password(body.new_password)
    await db.save()
    return {"message": "Password reset successful", "status": "success"}


@user.post("/inviteMember/{token}")
async def invite_member(token: str):
    pass


@user.delete("/deleteMember/{id}")
async def delete_member(id: int, db: DatabaseManager = Depends(get_db_session)):
    pass


@user.post("/updateRole")
async def update_member_role():
    pass
