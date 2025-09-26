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


@app.post("/generate-recommendation/food", description="AI 식단 추천 생성 및 분석 후 DB 저장")
async def generate_recommendation_analyze_and_save(
        db: Session = Depends(get_db),
        current_user: dict = Depends(account_crud.get_current_user),
):
    user_no = current_user.get("user_no")

    user_data = account_crud.get_user_data_from_no(user_no, db)
    user_id = user_data.user_id

    try:
        result, plan_path, foods = test4.generate_for_user(user_id)

        detailed_analyses = meal_to_food.analyze_foods(foods)
        saved_items = []
        for analysis_data in detailed_analyses:
            saved_item = ai_crud.create_recommendation_from_analysis(
                db=db,
                user_no=user_no,
                analysis_data=analysis_data,
            )
            saved_items.append({
                "food_name": saved_item.food_name,
                "recommendation_id": saved_item.recommendation_id
            })
        return {
            "success": True,
            "message": "식단 추천 생성 및 저장 완료 되었습니다",
            "saved_recommendations": saved_items
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"처리 중 서버 오류 발생: {str(e)}"
        )

@app.get("/detail/page", response_model=ai_schema.MealKitDetailPage)
def get_mealkit_detail_page(
        db: Session = Depends(get_db),
        current_user: dict = Depends(account_crud.get_current_user)
):
    user_no = current_user.get("user_no")
    db_user = ai_crud.get_meal_kit_info(db=db, user_no=user_no)


    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_BAD_REQUEST, detail="User not found")
    return db_user



