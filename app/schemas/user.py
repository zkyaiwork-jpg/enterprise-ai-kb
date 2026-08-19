from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from app.utils.datetime import serialize_utc_datetime


class UserRegister(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    username: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=8, max_length=72)
    real_name: str = Field(min_length=1, max_length=100)
    role_id: int | None = None
    department_id: int | None = None

    @field_validator("password")
    @classmethod
    def validate_bcrypt_password_length(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("密码长度不能超过72字节")
        return value


class UserLogin(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=72)

    @field_validator("password")
    @classmethod
    def validate_bcrypt_password_length(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("密码长度不能超过72字节")
        return value


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    real_name: str
    role_id: int | None
    department_id: int | None
    status: str
    created_time: datetime

    @field_serializer("created_time")
    def serialize_created_time(self, value: datetime) -> str:
        return serialize_utc_datetime(value)
