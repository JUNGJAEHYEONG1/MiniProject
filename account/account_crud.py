from datetime import timedelta, datetime, timezone
from typing import Optional, Dict, Any

from jose import jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
import models, config, account_schema
from account import account_schema, account_router
from fastapi import HTTPException, status, Response,Request

pwd_context = CryptContext(schemes = ["bcrypt"], deprecated="auto")

def update_user_initial_info(db: Session, user_id: int, user_info: account_schema.UserInitialInfoUpdate):
    db_user = db.query(models.User).filter(models.User.user_id == user_id).first()

    if db_user:
        db_user.gender = user_info.gender
        db_user.birth_date = user_info.birth_date
        db_user.height = user_info.height
        db_user.weight = user_info.weight
        db_user.activity_level = user_info.activity_level

        db.commit()
        db.refresh(db_user)

    return db_user

def get_user(user_id: str, db: Session):
    return db.query(models.User).filter(models.User.user_id == user_id).first()

def get_email(email: str, db: Session):
    return db.query(models.User).filter(models.User.email == email).first()

def create_user(new_user: account_schema.CreateUserForm, db: Session):
    db_user = get_user(new_user.id, db)
    db_email = get_email(new_user.email, db)

    if db_user:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="id is already exists")
    if db_email:
        raise HTTPException(status_code = status.HTTP_409_CONFLICT, detail="email is already exists")
    if not new_user.password == new_user.password_confirm:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Password does not match")
    user = models.User(
        user_name = new_user.username,
        user_id = new_user.id,
        email = new_user.email,
        hashed_password = pwd_context.hash(new_user.password),

    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return {"message" : "Signup successful"}

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        config.SECRET_KEY,
        algorithm=config.ALGORITHM
    )
    return encoded_jwt

def decode_access_token(token: str):
    try:
        payload = jwt.decode(
            token,
            config.SECRET_KEY,
            algorithms=[config.ALGORITHM]
        )
        return payload
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

def login(response : Response, login_form : account_schema.LoginForm, db: Session):
    db_user = get_user(login_form.id, db)

    if not db_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalidd username or password")

    res = verify_password(login_form.password, db_user.hashed_password)
    if not res:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid username or password")

    access_token_expires = timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data = {"user_no": db_user.no}, expires_delta = access_token_expires)
    #쿠키 만료 시간 ( 세계 시간 utc로 설정 )
    cookie_expiration = (datetime.utcnow() + access_token_expires).replace(tzinfo=timezone.utc)
    response.set_cookie(key = "access_token", value = access_token, expires=cookie_expiration ,httponly=True)

    return {"message": "Login successful"}

def logout(response: Response, request: Request):
    access_token = request.cookies.get("access_token")

    if not access_token:
        raise HTTPException(status_code=400, detail="Token is not found")
    response.delete_cookie(key="access_token")

    return {"message": "Logout successful"}

def get_current_user(request: Request) -> dict:
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not token authenticated")

    user_data = decode_access_token(token)
    return user_data