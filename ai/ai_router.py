from database import get_db
from fastapi import APIRouter, Response, Request, HTTPException, status
from sqlalchemy.orm import Session
from fastapi.params import Depends
from account import account_crud, account_schema
from api import test4, meal_to_food
from ai import ai_crud, ai_schema
import models
app = APIRouter(
    prefix="/ai",
)


@app.post("/generate-recommendation/food",
          description="AI 식단 추천 생성 및 분석 후 DB 저장")
async def generate_recommendation_analyze_and_save(
        db: Session = Depends(get_db),
        current_user: dict = Depends(account_crud.get_current_user),
):
    user_no = current_user.get("user_no")
    user_data = account_crud.get_user_data_from_no(user_no, db)
    user_id = user_data.user_id

    try:
        result, plan_path, food_names = test4.generate_for_user(user_id)

        detailed_analyses = meal_to_food.analyze_foods(food_names)

        plan_meta = result.get("plan_meta", {})
        total_nutrition = plan_meta.get("macros_total", {})

        final_analysis_data = {
            "food_name": plan_meta.get("goal_note", "AI 추천 식단"),
            "image_url": None, #일단 이미지 none
            "total_calories": total_nutrition.get("kcal") or plan_meta.get("total_calories"),
            "total_carbs_g": total_nutrition.get("carb_g"),
            "total_protein_g": total_nutrition.get("protein_g"),
            "total_fat_g": total_nutrition.get("fat_g"),
            "items": [],
        }

        all_meal_kits_for_db = []

        for meal_type in ['breakfast', 'lunch', 'dinner']:
            if meal_type in result and 'items' in result[meal_type]:
                for ai_item in result[meal_type]['items']:

                    matched_youtube_info = next(
                        (info for info in detailed_analyses if info.get('food_name') == ai_item.get('name_ko')),{} )

                    combined_kit_data = {
                        "name": ai_item.get("name_ko"),
                        "purchase_link": matched_youtube_info.get("youtube_link"),
                        "image_url": None,  #일단 이미지 none
                        "kcal": ai_item.get("kcal") or ai_item.get("calories"),  # 'kcal' 또는 'calories' 키 확인
                        "carb_g": ai_item.get("macros", {}).get("carb_g"),
                        "protein_g": ai_item.get("macros", {}).get("protein_g"),
                        "fat_g": ai_item.get("macros", {}).get("fat_g"),
                    }
                    all_meal_kits_for_db.append(combined_kit_data)

        final_analysis_data["items"] = all_meal_kits_for_db

        if detailed_analyses:
            first_recipe_info = detailed_analyses[0]
            final_analysis_data["food_name"] = first_recipe_info.get("food_name", final_analysis_data["food_name"])
            final_analysis_data["recipe"] = first_recipe_info.get("recipe", [])
            final_analysis_data["youtube_link"] = first_recipe_info.get("youtube_link")
            final_analysis_data["ingredients"] = first_recipe_info.get("ingredients", [])

        saved_item = ai_crud.create_recommendation_from_analysis(
            db=db,
            user_no=user_no,
            analysis_data=final_analysis_data,
        )

        return {
            "success": True,
            "message": "식단 추천 생성 및 저장 완료 되었습니다",
            "saved_recommendation": {
                "food_name": saved_item.food_name,
                "recommendation_id": saved_item.recommendation_id
            }
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"처리 중 서버 오류 발생: {str(e)}"
        )


@app.get("/meal-kit/detail",
         response_model=ai_schema.MealKitInfo,
         description="추천식단 id별 밀키트 조회")
def read_meal_kit_details(
        recommendation_id: int,
        db: Session = Depends(get_db),
        current_user: dict = Depends(account_crud.get_current_user)
):
    user_no = current_user.get("user_no")
    db_recommendation = ai_crud.get_meal_kit_by_id(
        db=db,
        recommendation_id=recommendation_id,
        user_no=user_no
    )

    if db_recommendation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recommendation not found or not token")

    return db_recommendation


@app.get("/recommendations/{recommendation_id}",
         response_model=ai_schema.RecommendationDetail,
         description="추천 음식 상세 정보")
def read_recommendation_details(recommendation_id: int, db: Session = Depends(get_db)):
    db_recommendation = ai_crud.get_recommendation_details(db, recommendation_id=recommendation_id)

    if db_recommendation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recommendation not found")

    return db_recommendation


@app.get("/recommendations/{recommendation_id}/recipe",
         response_model=ai_schema.RecipeDetail,
         description="레시피 상세 정보")
def read_recommendation_recipe(recommendation_id: int, db: Session = Depends(get_db)):

    db_recipe = ai_crud.get_recipe_for_recommendation(db, recommendation_id=recommendation_id)

    if db_recipe is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipe for this recommendation not found")

    return db_recipe

@app.get("/meal-kit/purchase-link/{meal_kit_id}",
         response_model=ai_schema.PurchaseLink,
         description="밀키트 구매 링크")
def get_purchase_link_for_meal_kit(meal_kit_id: int, db:Session = Depends(get_db)):
    db_meal_kit = ai_crud.get_meal_kit_by_id(db, meal_kit_id)

    if db_meal_kit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meal Kit not found")

    return db_meal_kit