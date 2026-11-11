import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=255)


class UserCreate(UserBase):
    password: str = Field(..., min_length=6, max_length=100)


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)


class UserResponse(UserBase):
    id: uuid.UUID
    created_at: datetime
    # Frontend compatibility fields
    name: Optional[str] = None
    avatar: Optional[str] = None
    plan: str = "enterprise"

    model_config = ConfigDict(from_attributes=True)

    def model_post_init(self, __context):
        if not self.name:
            self.name = self.full_name

