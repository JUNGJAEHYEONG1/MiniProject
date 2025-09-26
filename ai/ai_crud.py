from typing import Optional, Dict, Any
from account import account_schema, account_router
from sqlalchemy.orm import Session, joinedload
import models

def get_meal_kit_info(user_no: int, db: Session):
    return db.query(models.MealKit).filter_by(user_no=user_no).all()


def create_recommendation_from_analysis(db: Session, user_no: int, analysis_data: dict) -> models.DailyRecommendation:
    try:

        db_recommendation = models.DailyRecommendation(
            user_no=user_no,
            food_name=analysis_data["food_name"]
        )
        db.add(db_recommendation)
        db.flush()

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