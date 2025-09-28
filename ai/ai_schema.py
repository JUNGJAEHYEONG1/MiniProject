from datetime import date
from pydantic import BaseModel,Field
from fastapi import HTTPException, Form
from typing import Optional
from decimal import Decimal

class FoodDetailPage(BaseModel):
    food_name: Optional[str] = None
    calories: Optional[Decimal] = None
    carbs_g : Optional[Decimal] = None
    protein_g : Optional[Decimal] = None
    fat_g : Optional[Decimal] = None

class MealKitDetailPage(BaseModel):
    meal_kit_name: Optional[str] = None
    calories : Optional[Decimal] = None
    carbs_g : Optional[Decimal] = None
    protein_g : Optional[Decimal] = None
    fat_g : Optional[Decimal] = None

class MealKitPurchase(BaseModel):
    meal_kit_url: Optional[str] = None

class FoodsRequest(BaseModel):
    foods: list[str]

class MealKitInfo(BaseModel):
    name: str = Field(alias='meal_kit_name')
    calories: Optional[Decimal] = None
    carbs_g: Optional[Decimal] = None
    protein_g: Optional[Decimal] = None
    fat_g: Optional[Decimal] = None

    class Config:
        from_attributes = True
        populate_by_name = True


class RecommendationDetail(BaseModel):
    food_name: str
    image_url: Optional[str] = None
    total_calories: Optional[Decimal] = Field(default=None, alias='calories')
    total_carbs_g: Optional[Decimal] = Field(default=None, alias='carbs_g')
    total_protein_g: Optional[Decimal] = Field(default=None, alias='protein_g')
    total_fat_g: Optional[Decimal] = Field(default=None, alias='fat_g')

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


