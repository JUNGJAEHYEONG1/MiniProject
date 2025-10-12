from typing import Optional, Dict, Any
from account import account_schema, account_router
from sqlalchemy.orm import Session, joinedload
import models
from ai import ai_schema
from sqlalchemy.orm import joinedload

def get_meal_kit_info(user_no: int, db: Session):
    return db.query(models.MealKit).filter_by(user_no=user_no).all()

def get_latest_recommedations_for_user(db: Session, user_no : int) -> list:
    return(
        db.query(models.DailyRecommendation)
        .filter(models.DailyRecommendation.user_no == user_no)
        .order_by(models.DailyRecommendation.recommendation_id.desc())
        .limit(3)
        .all()
    )

def create_recommendation_from_analysis(db: Session, user_no: int, analysis_data: dict) -> models.DailyRecommendation:
    try:
        meal_kit_items = analysis_data.get("items", [])

        total_calories = sum(item.get("calories", 0) for item in meal_kit_items)
        total_carbs_g = sum(item.get("macros", {}).get("carb_g", 0) for item in meal_kit_items)
        total_protein_g = sum(item.get("macros", {}).get("protein_g", 0) for item in meal_kit_items)
        total_fat_g = sum(item.get("macros", {}).get("fat_g", 0) for item in meal_kit_items)

        db_recommendation = models.DailyRecommendation(
            user_no=user_no,
            food_name=analysis_data.get("title", "AI 추천 식단"),
            image_url=analysis_data.get("image_url"),
            calories=total_calories,
            carbs_g=total_carbs_g,
            protein_g=total_protein_g,
            fat_g=total_fat_g
        )
        db.add(db_recommendation)
        db.flush()

        for item in meal_kit_items:
            db_meal_kit = models.MealKit(
                meal_kit_name=item.get("name"),
                purchase_link=item.get("purchase_link") or item.get("meal_kit_link"),
                image_url=item.get("image_url"),
                calories=item.get("calories"),
                carbs_g=item.get("macros", {}).get("carb_g"),
                protein_g=item.get("macros", {}).get("protein_g"),
                fat_g=item.get("macros", {}).get("fat_g"),
                recommendation_id=db_recommendation.recommendation_id
            )
            db.add(db_meal_kit)

        if "recipe" in analysis_data and analysis_data["recipe"]:
            db_recipe = models.Recipe(
                recipe_name=analysis_data.get("recipe_name", f"{db_recommendation.food_name} 레시피"),
                cooking_method="\n".join(analysis_data.get("recipe", [])),
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
    return purchase_link