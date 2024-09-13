from pydantic import BaseModel, EmailStr, model_validator


class RegisterUserSchema(BaseModel):
    email: EmailStr
    password: str
    org_name: str
    role: str = "owner"
    description: str = None


class LoginUserSchema(BaseModel):
    email: EmailStr
    password: str


class ForgotPassSchema(BaseModel):
    email: EmailStr


class ResetPassSchema(BaseModel):
    new_password: str
    confirm_password: str

    @model_validator(mode="after")
    def check_password_match(self):
        new = self.new_password
        confirm = self.confirm_password
        if new is not None and confirm is not None and new != confirm:
            raise ValueError("passwords do not match")
        return self


class BaseResponseSchema(BaseModel):
    message: str
    status: str = "success"
    data: dict


class BaseErrorResponseSchema(BaseModel):
    message: str
    status: str = "error"
