from datetime import timedelta, datetime, timezone, date
from typing import Optional, Dict, Any
from sqlalchemy import func
from jose import jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session, joinedload
import models
import config
from account import account_schema, account_router
from fastapi import HTTPException, status, Response,Request

from models import UserEatenFood

pwd_context = CryptContext(schemes = ["bcrypt"], deprecated="auto")


def get_calories(db: Session, user_no: int):
    db.query(models.DailyRecommendation).filter(models.DailyRecommendation.user_no == user_no).first()

def get_eaten_food_by_no(db: Session, eaten_food_no: int, user_no: int):
    return (
        db.query(models.UserEatenFood)
        .filter(
            models.UserEatenFood.no == eaten_food_no,
            models.UserEatenFood.user_no == user_no
        )
        .first()
    )


def create_eaten_food_record(db: Session, user_no: int, image_url: str, nutrition_data: dict):
    food_items = nutrition_data.get("items", {})
    food_name_list = [item.get("name_ko", "알수없음") for item in food_items.values()]
    food_name = ", ".join(food_name_list)

    total_nutrition = nutrition_data.get("total", {})

    db_eaten_food = models.UserEatenFood(
        user_no=user_no,
        image_url=image_url,
        food_name=food_name,
        calories=total_nutrition.get("kcal", 0),
        carbs_g=total_nutrition.get("carb_g", 0),
        protein_g=total_nutrition.get("protein_g", 0),
        fat_g=total_nutrition.get("fat_g", 0)
    )
    db.add(db_eaten_food)
    db.commit()
    db.refresh(db_eaten_food)
    return db_eaten_food

def get_user_eaten_foods(db: Session, user_no : int, target_date: date):
    return (db.query(models.UserEatenFood)
            .filter(
        models.UserEatenFood.user_no == user_no,
        func.date(models.UserEatenFood.created_at) == target_date
    )
    .order_by(models.UserEatenFood.no.asc()).all())


def update_user_profile(db: Session,
                        user_no : int,
                        data: account_schema.UserProfileUpdate
                        ):

    db_user = get_user_data_from_no(user_no, db)

    if not db_user:
        return None

    update_data = data.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        if key == "allergies":
            allergies_list = (db.query(models.Allergy)
                              .filter(models.Allergy.allergy_name.in_(value))
                              .all())
            db_user.allergies = allergies_list
        elif key == "eat_level":
            db_eat_level = db_user.eat_level

            if db_eat_level:
                db_eat_level.breakfast = value.get("breakfast")
                db_eat_level.lunch = value.get("lunch")
                db_eat_level.dinner = value.get("dinner")
            else:
                db_user.eat_level = models.UserEatLevel(
                    user_no= user_no,
                    breakfast=value.get('breakfast'),
                    lunch=value.get('lunch'),
                    dinner=value.get('dinner')
                )
        else:
            setattr(db_user, key, value)

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return db_user

def get_user_profile(db: Session, user_no: int) -> Optional[models.User]:
    user = (
        db.query(models.User)
        .options(joinedload(models.User.eat_level))
        .filter(models.User.user_no == user_no)
        .first()
    )
    return user

def food_setting(db: Session, user_no: int):
    return db.query(models.User).options(
        joinedload(models.User.allergies),
        joinedload(models.User.eat_level)
    ).filter(models.User.user_no == user_no).first()

def get_user_data_from_id(user_id: str, db: Session):
    return db.query(models.User).filter(models.User.user_id == user_id).first()

def get_user_data_from_no(user_no: int, db: Session):
    return db.query(models.User).filter(models.User.user_no == user_no).first()

def get_user_data_from_email(email: str, db: Session):
    return db.query(models.User).filter(models.User.email == email).first()

def create_user(new_user: account_schema.CreateUserForm, db: Session):
    db_user = get_user_data_from_id(new_user.id, db)
    db_email = get_user_data_from_email(new_user.email, db)

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
    db_user = get_user_data_from_id(login_form.id, db)
    if not db_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid username or password")


    res = verify_password(login_form.password, db_user.hashed_password)
    if not res:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid username or password")

    access_token_expires = timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data = {"user_no": db_user.user_no}, expires_delta = access_token_expires)
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

def get_current_user(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not token authenticated")

    user_data = decode_access_token(token)
    return user_data