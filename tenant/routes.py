from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from core.db_manager import DatabaseManager

from .models import Member, Organisation, Role, User, get_db_session
from .schemas import *
from .tokens import Audience, JWTUtils
from .utils import send_mail

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
    async with db.session.begin():
        try:
            payload = body.model_dump()
            email = payload.get("email")
            password = payload.get("password")
            is_user_exist = await db.model(User).get_or_none(email=email)
            if is_user_exist:
                raise SQLAlchemyError("User already exists")
            user: User = await db.model(User).create_instance(email=email, password=password)

            org_name = payload.get("org_name")
            organisation = await db.model(Organisation).get_or_create_instance(name=org_name)

            role = payload.get("role")
            description = payload.get("description")

            role = await db.model(Role).get_or_create_instance(name=role, org_id=organisation.id)
            if description:
                role.description = description
                # await db.save()

            invitation_payload = {
                "user_id": user.id,
                "org_id": organisation.id,
                "role_id": role.id,
                "aud": Audience.INVITE.value,
            }

            token = await JWTUtils.generate_access_token(invitation_payload, exp=15)
            url = request.url_for("invite_member", token=token)

            status_code = await send_mail(
                to_email=user.email, subject="MultiTenant Member Invitation", content=str(url)
            )
            if status_code >= 400:
                await db.session.rollback()
                raise HTTPException(
                    detail="Error occured when trying to send mail",
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            await db.save()

            user_data = user.to_dict
            user_data.update(organisation=organisation.to_dict, role=role.to_dict)
            return {
                "message": "User Registered and Member invitation send to registered E-mail!",
                "status": "success",
                "data": user_data,
            }
        except Exception as e:
            raise HTTPException(
                detail=str(e), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            ) from e


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

    status_code = await send_mail(
        to_email=user.email,
        subject="MultiTenant Login Alert",
        content="""We noticed a new sign-in to your MultiTenant Account""",
    )
    if status_code >= 400:
        await db.session.rollback()
        raise HTTPException(
            detail="Error occured when trying to send mail",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    return {
        "message": "Login Successfull",
        "status": "success",
        "data": {"access_token": access, "refresh_token": refresh},
    }


@user.post("/forgotPassword")
async def forgot_password(
    body: ForgotPassSchema, request: Request, db: DatabaseManager = Depends(get_db_session)
):
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
    url = request.url_for("reset_password", token=token)

    status_code = await send_mail(
        to_email=user.email, subject="MultiTenant Reset Password", content=str(url)
    )
    if status_code >= 400:
        await db.session.rollback()
        raise HTTPException(
            detail="Error occured when trying to send mail",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

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

    status_code = await send_mail(
        to_email=user.email,
        subject="MultiTenant Password Change Alert",
        content="""Recently password associated with this mail id has been changed.""",
    )
    if status_code >= 400:
        await db.session.rollback()
        raise HTTPException(
            detail="Error occured when trying to send mail",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return {"message": "Password reset successful", "status": "success", "data": {}}


@user.get("/inviteMember/{token}")
async def invite_member(
    token: str, request: Request, db: DatabaseManager = Depends(get_db_session)
):
    if not token:
        raise HTTPException(detail="Token not found", status_code=status.HTTP_404_NOT_FOUND)

    payload = await JWTUtils.decode_token(token=token, aud=Audience.INVITE.value, request=request)
    if "user_id" not in payload or "org_id" not in payload or "role_id" not in payload:
        raise HTTPException(detail="Improper data provided", status_code=status.HTTP_403_FORBIDDEN)

    user_id = payload["user_id"]
    org_id = payload["org_id"]
    role_id = payload["role_id"]

    await db.model(Member).create(user_id=user_id, org_id=org_id, role_id=role_id)

    return {
        "message": "Successfully added as member to organisation",
        "status": "success",
        "data": {},
    }


@user.delete("/{user_id}/deleteMember/{member_id}")
async def delete_member(
    user_id: int, member_id: int, db: DatabaseManager = Depends(get_db_session)
):
    if not user_id or member_id:
        raise HTTPException(
            detail="Improper data provided", status_code=status.HTTP_400_BAD_REQUEST
        )

    member: Member = await db.model(Member).get_or_none(id=member_id)
    if not member:
        raise HTTPException(
            detail="Invalid member details", status_code=status.HTTP_400_BAD_REQUEST
        )

    if member.user_id != user_id:
        raise HTTPException(detail="You are not a member", status_code=status.HTTP_400_BAD_REQUEST)

    await db.model(Member).delete(id=member_id)

    return {
        "message": "Successfully Membership Removed",
        "status": "success",
        "data": {},
    }


@user.patch("/updateRole")
async def update_member_role(
    body: UpdateMemberSchema, db: DatabaseManager = Depends(get_db_session)
):
    payload = body.model_dump()
    org_id = payload.get("org_id")
    user_id = payload.get("user_id")
    role_id = payload.get("role_id")

    role = await db.model(Role).get_or_none(id=role_id)

    if not role:
        raise HTTPException(detail="Role not found", status_code=status.HTTP_404_NOT_FOUND)

    member = await db.model(Member).get_or_none(org_id=org_id, user_id=user_id)

    if not member:
        raise HTTPException(detail="Member not found", status_code=status.HTTP_404_NOT_FOUND)

    if member.role_id == role_id:
        return {
            "message": "Role update to date",
            "status": "success",
            "data": {},
        }

    member.role_id = role.id

    await db.save()

    return {
        "message": "Successfully Role has been Updated",
        "status": "success",
        "data": {},
    }
