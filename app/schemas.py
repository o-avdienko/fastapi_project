from datetime import datetime
from pydantic import BaseModel, HttpUrl, Field, field_validator


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., description="Email пользователя")
    password: str = Field(..., min_length=6)


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    created_at: datetime

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LinkCreate(BaseModel):
    original_url: HttpUrl = Field(..., description="Длинная ссылка для сокращения")
    custom_alias: str | None = Field(
        None,
        min_length=3,
        max_length=50,
        pattern=r"^[a-zA-Z0-9_-]+$"
    )
    expires_at: datetime | None = Field(None)

    @field_validator("original_url", mode="before")
    @classmethod
    def convert_url_to_str(cls, v):
        return str(v)


class LinkUpdate(BaseModel):
    original_url: HttpUrl | None = Field(None)
    new_short_code: str | None = Field(
        None,
        min_length=3,
        max_length=20,
        pattern=r"^[a-zA-Z0-9_-]+$"
    )

    @field_validator("original_url", mode="before")
    @classmethod
    def convert_url_to_str(cls, v):
        if v is not None:
            return str(v)
        return v


class LinkResponse(BaseModel):
    id: int
    original_url: str
    short_code: str
    custom_alias: str | None
    created_at: datetime
    expires_at: datetime | None
    click_count: int
    last_used_at: datetime | None
    owner_id: int | None

    model_config = {"from_attributes": True}


class LinkStats(BaseModel):
    original_url: str
    short_code: str
    created_at: datetime
    click_count: int
    last_used_at: datetime | None
    expires_at: datetime | None

    model_config = {"from_attributes": True}


class ExpiredLinkResponse(BaseModel):
    id: int
    original_url: str
    short_code: str
    custom_alias: str | None
    created_at: datetime
    expired_at: datetime
    click_count: int

    model_config = {"from_attributes": True}