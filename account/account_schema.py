from datetime import datetime, date
from pydantic import BaseModel, EmailStr, validator
from fastapi import HTTPException, Form
from typing import Optional
from decimal import Decimal

class EatenFoodDetail(BaseModel):
    no: int
    food_name: Optional[str] = None
    image_url: Optional[str] = None
    created_at: datetime
    calories: Optional[Decimal] = None
    carbs_g: Optional[Decimal] = None
    protein_g: Optional[Decimal] = None
    fat_g: Optional[Decimal] = None

    class Config:
        from_attributes = True

class EatLevel(BaseModel):
    breakfast: Optional[str] = None
    lunch: Optional[str] = None
    dinner: Optional[str] = None

class UserProfileUpdate(BaseModel):
    gender: Optional[str] = None
    age: Optional[int] = None
    height: Optional[float] = None
    weight: Optional[float] = None
    activity_level: Optional[str] = None
    goal: Optional[str] = None
    preferred_food: Optional[str] = None
    allergies : Optional[list[str]] = None
    eat_level: Optional[EatLevel] = None

class UserInfo(BaseModel):
    gender: Optional[str] = None
    birth_date: Optional[date] = None
    height: Optional[float] = None
    weight: Optional[float] = None

    class Config:
        from_attributes = True

class UserFoodSetting(BaseModel):
    weight: Optional[float] = None
    activity_level: Optional[str] = None
    diet_goal: Optional[str] = None
    allergies: list[str] = None
    eat_level: Optional[EatLevel] = None

    class Config:
        from_attributes = True


class CreateUserForm(BaseModel):
    id : str = Form(...)
    email: EmailStr = Form(...)
    username: str = Form(...)
    phone: str = Form(...)
    password: str = Form(...)
    password_confirm: str = Form(...)

    @validator('email', 'username', 'phone', 'password')
    def check_empty(cls, v):
        if not v or v.isspace():
            raise HTTPException(status_code=422, detail='필수 항목을 입력해주세요.')
        return v

    @validator('phone')
    def check_phone(cls, v):
        if '-' not in v or len(v) != 13:
            raise HTTPException(status_code=422, detail="올바른 형식의 번호를 입력해주세요")
        return v

    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise HTTPException(status_code=422, detail="비밀번호는 8자리 이상 영문과 숫자를 포함하여 작성해 주세요.")
        if not any(char.isdigit() for char in v):
            raise HTTPException(status_code=422, detail="비밀번호는 8자리 이상 영문과 숫자를 포함하여 작성해 주세요.")
        if not any(char.isalpha() for char in v):
            raise HTTPException(status_code=422, detail="비밀번호는 8자리 이상 영문과 숫자를 포함하여 작성해 주세요.")
        return v

class LoginForm(BaseModel):
    id : str = Form(...)
    password: str = Form(...)

class Token(BaseModel):
    access_token: str
    token_type: str

