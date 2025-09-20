from pydantic import BaseModel, EmailStr, validator
from fastapi import HTTPException, Form

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