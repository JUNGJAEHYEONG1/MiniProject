from datetime import date
from pydantic import BaseModel, EmailStr, validator
from fastapi import HTTPException, Form
from typing import Optional

class FoodDetailPage(BaseModel):
    food_name: Optional[str] = None
    calories: Optional[float] = None
    carbs_g : Optional[float] = None
    protein_g : Optional[float] = None
    fat_g : Optional[float] = None

class MealKitDetailPage(BaseModel):
    meal_kit_name: Optional[str] = None
    calories : Optional[float] = None
    carbs_g : Optional[float] = None
    protein_g : Optional[float] = None
    fat_g : Optional[float] = None

class MealKitPurchase(BaseModel):
    meal_kit_url: Optional[str] = None

class FoodsRequest(BaseModel):
    foods: list[str]



