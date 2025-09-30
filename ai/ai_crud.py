from typing import Optional, Dict, Any
from account import account_schema, account_router
from sqlalchemy.orm import Session, joinedload
import models
from ai import ai_schema
from sqlalchemy.orm import joinedload

def get_meal_kit_info(user_no: int, db: Session):
    return db.query(models.MealKit).filter_by(user_no=user_no).all()


def create_recommendation_from_analysis(db: Session, user_no: int, analysis_data: dict) -> models.DailyRecommendation:
    try:

        db_recommendation = models.DailyRecommendation(
            user_no=user_no,
            food_name=analysis_data.get("food_name", "AI 추천 식단"),
            image_url=analysis_data.get("image_url"),
            calories=analysis_data.get("total_calories"),
            carbs_g=analysis_data.get("total_carbs_g"),
            protein_g=analysis_data.get("total_protein_g"),
            fat_g=analysis_data.get("total_fat_g")
        )
        db.add(db_recommendation)
        db.flush()

        meal_kit_items = analysis_data.get("items", [])

        for item in meal_kit_items:
            db_meal_kit = models.MealKit(
                meal_kit_name=item.get("name"),
                purchase_link=item.get("purchase_link"),
                image_url=item.get("image_url"),
                calories=item.get("kcal"),
                carbs_g=item.get("carb_g"),
                protein_g=item.get("protein_g"),
                fat_g=item.get("fat_g"),
                recommendation_id=db_recommendation.recommendation_id
            )
            db.add(db_meal_kit)

        recipe_steps = analysis_data.get("recipe", [])
        cooking_method_str = "\n".join(recipe_steps)

        db_recipe = models.Recipe(
            recipe_name=f"{analysis_data['food_name']} 레시피",
            cooking_method=cooking_method_str,
            recipe_video_link=analysis_data.get("youtube_link"),
            recommendation_id=db_recommendation.recommendation_id
        )
        db.add(db_recipe)
        db.flush()

        for item_str in analysis_data.get("ingredients", []):
            db_ingredient = models.Ingredient(
                name=item_str,
                recipe_id=db_recipe.recipe_id
            )
            db.add(db_ingredient)

        db.commit()
        db.refresh(db_recommendation)
        return db_recommendation

    except Exception as e:
        db.rollback()
        raise e


def get_recipe_for_recommendation(db: Session, recommendation_id: int) -> Optional[models.Recipe]:

    recommendation = (
        db.query(models.DailyRecommendation)
        .options(
            joinedload(models.DailyRecommendation.recipe)
            .joinedload(models.Recipe.ingredients)
        )
        .filter(models.DailyRecommendation.recommendation_id == recommendation_id)
        .first()
    )

    if not recommendation or not recommendation.recipe:
        return None

    return recommendation.recipe

def get_meal_kit_by_id(db: Session, recommendation_id : int, user_no: int):
    recommendation = (
        db.query(models.DailyRecommendation)
        .options(
            joinedload(models.DailyRecommendation.meal_kits)
        )
        .filter(
            models.DailyRecommendation.recommendation_id == recommendation_id,
            models.DailyRecommendation.user_no == user_no
        )
        .first()
    )
    return recommendation


def get_meal_kit_purchase_link(db: Session, meal_kit_id: int, user_no: int) -> Optional[str]:
    purchase_link = (
        db.query(models.MealKit.purchase_link)
        .join(models.DailyRecommendation)
        .filter(
            models.DailyRecommendation.user_no == user_no,
            models.MealKit.meal_kit_id == meal_kit_id
        )
        .first()
    )
    return purchase_link[0] if purchase_link else None