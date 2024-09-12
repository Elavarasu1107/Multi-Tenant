from pydantic import BaseModel, EmailStr


class RegisterUserSchema(BaseModel):
    email: EmailStr
    password: str
    org_name: str
    role: str = "owner"
    description: str = None


class LoginUserSchema(BaseModel):
    email: EmailStr
    password: str


class BaseResponseSchema(BaseModel):
    message: str
    status: str = "success"
    data: dict


class BaseErrorResponseSchema(BaseModel):
    message: str
    status: str = "error"
