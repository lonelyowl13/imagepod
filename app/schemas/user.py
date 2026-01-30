import re
from pydantic import BaseModel, field_validator, model_validator


def _alphanumeric(v: str) -> str:
    if not v or not re.match(r"^[a-zA-Z0-9]+$", v):
        raise ValueError("must be alphanumeric")
    return v


def _password_min_length(v: str) -> str:
    if len(v) < 8:
        raise ValueError("password must be at least 8 characters")
    return v


class RegisterRequest(BaseModel):
    username: str
    password: str
    password2: str

    @field_validator("username")
    @classmethod
    def username_alphanumeric(cls, v: str) -> str:
        return _alphanumeric(v)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return _password_min_length(v)

    @field_validator("password2")
    @classmethod
    def password2_strength(cls, v: str) -> str:
        return _password_min_length(v)

    @model_validator(mode="after")
    def passwords_match(self):
        if self.password != self.password2:
            raise ValueError("passwords do not match")
        return self


class UserResponse(BaseModel):
    id: int
    username: str

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str
