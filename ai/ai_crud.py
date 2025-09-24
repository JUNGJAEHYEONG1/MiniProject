from typing import Optional, Dict, Any
from account import account_schema, account_router
from sqlalchemy.orm import Session, joinedload
import models

def get_meal_kit_info(user_no: int, db: Session):
    return db.query(models.MealKit).filter_by(user_no=user_no).all()
