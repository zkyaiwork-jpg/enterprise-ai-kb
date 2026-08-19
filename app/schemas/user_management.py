from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from app.utils.datetime import serialize_utc_datetime


class ManagedUserCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=8, max_length=72)
    real_name: str | None = Field(default=None, min_length=1, max_length=100)
    role_id: int
    department_id: int | None = None
    team_id: int | None = None

    @field_validator("password")
    @classmethod
    def validate_password_bytes(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("密码长度不能超过72字节")
        return value


class ManagedUserUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    username: str | None = Field(default=None, min_length=1, max_length=100)
    real_name: str | None = Field(default=None, min_length=1, max_length=100)
    role_id: int | None = None
    department_id: int | None = None
    team_id: int | None = None
    status: Literal["active", "inactive"] | None = None


class PasswordResetRequest(BaseModel):
    new_password: str = Field(min_length=8, max_length=72)

    @field_validator("new_password")
    @classmethod
    def validate_password_bytes(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("密码长度不能超过72字节")
        return value


class DepartmentCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=100)
    description: str | None = None


class TeamCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=100)
    department_id: int
    description: str | None = None


class ManagedUserResponse(BaseModel):
    id: int
    username: str
    real_name: str
    role: dict | None
    department: dict | None
    team: dict | None
    status: str
    created_time: datetime

    @field_serializer("created_time")
    def serialize_created_time(self, value: datetime) -> str:
        return serialize_utc_datetime(value)
