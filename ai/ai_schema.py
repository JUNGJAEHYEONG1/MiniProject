from datetime import date
from pydantic import BaseModel,Field
from fastapi import HTTPException, Form
from typing import Optional
from decimal import Decimal

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

class MealKitInfo(BaseModel):
    name: str = Field(alias='meal_kit_name')
    calories: Decimal
    carbs_g: Decimal
    protein_g: Decimal
    fat_g: Decimal

    class Config:
        from_attributes = True
        populate_by_name = True


class RecommendationDetail(BaseModel):
    food_name: str
    image_url: Optional[str] = None
    total_calories: Decimal = Field(alias='calories')
    total_carbs_g: Decimal = Field(alias='carbs_g')
    total_protein_g: Decimal = Field(alias='protein_g')
    total_fat_g: Decimal = Field(alias='fat_g')

    meal_kit_list: list[MealKitInfo] = Field(alias='meal_kits')

    class Config:
        from_attributes = True
        populate_by_name = True

class IngredientDetail(BaseModel):
    name: str
    image_url: Optional[str] = None

    class Config:
        from_attributes = True

class RecipeDetail(BaseModel):
    recipe_name: str
    cooking_method: str
    recipe_video_link: Optional[str] = None
    ingredients: list[IngredientDetail] = []

    class Config:
        from_attributes = True

class PurchaseLink(BaseModel):
    purchase_link: Optional[str] = None


