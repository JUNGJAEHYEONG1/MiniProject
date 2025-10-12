from sqlalchemy.sql.functions import current_user

from account.account_crud import get_current_user
from database import get_db
from fastapi import APIRouter, Response, Request, HTTPException, status
from sqlalchemy.orm import Session
from fastapi.params import Depends
from account import account_crud, account_schema
from api import test4, meal_to_food
from ai import ai_crud, ai_schema
import models
import json
import re
from utils.s3 import upload_file_to_s3
import os # os 모듈을 import 합니다 (파일 삭제용)
import traceback
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
app = APIRouter(
    prefix="/ai",
)

@app.get("/recommendations/latest",
         description="가장 최근에 추천 받은 식단 목록(아점저) 가져오기",
         response_model = list[ai_schema.RecommendationSimple])
def read_latest_recommendations(
        db: Session = Depends(get_db),
        current_user: dict = Depends(account_crud.get_current_user)
):
    user_no = current_user.get("user_no")

    if user_no is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail = "Invalid token data")

    latest_recommendations = ai_crud.get_latest_recommedations_for_user(db=db, user_no = user_no)

    if not latest_recommendations:
        return []

    return latest_recommendations
@app.post("/generate-recommendation/food",
          description="AI 식단 추천 생성 및 분석 후 DB 저장")
async def generate_recommendation_analyze_and_save(
        request: Request,
        db: Session = Depends(get_db),
        current_user: dict = Depends(account_crud.get_current_user),
):
    user_no = current_user.get("user_no")
    user_data = account_crud.get_user_data_from_no(user_no, db)
    user_id = user_data.user_id

    try:
        result, plan_path, food_names, generated_image_paths = test4.generate_for_user(user_id)
        detailed_analyses = meal_to_food.analyze_foods(food_names)

        base_url = str(request.base_url)

        saved_recommendations = []

        for meal_type in ['breakfast', 'lunch', 'dinner']:
            if meal_type in result and isinstance(result[meal_type], dict):

                meal_data = result[meal_type]

                s3_image_url = None
                # 2. 해당 끼니(meal_type)의 로컬 이미지 경로를 가져옵니다.
                local_image_path = generated_image_paths.get(meal_type)

                if local_image_path and os.path.exists(local_image_path):
                    try:
                        # 3. 로컬 이미지 파일을 열어서 S3에 업로드합니다.
                        with open(local_image_path, "rb") as image_file:
                            # 기존 S3 업로드 함수를 재활용합니다.
                            # 이 함수는 파일 객체를 받아 S3 URL을 반환해야 합니다.
                            s3_image_url = upload_file_to_s3(file=image_file, user_no=user_no,
                                                             save_path="ai_recommendations")

                        # 4. (선택사항) 서버에 남은 임시 이미지 파일을 삭제합니다.
                        os.remove(local_image_path)

                    except Exception as s3_error:
                        print(f"S3 업로드 실패: {s3_error}")
                        # 업로드에 실패해도 일단 진행하도록 s3_image_url은 None으로 둡니다.

                # 5. meal_data에 최종 S3 URL을 저장합니다.
                meal_data["image_url"] = s3_image_url

                first_item_name = meal_data.get("items", [{}])[0].get("name")
                if first_item_name:
                    matched_youtube_info = next(
                        (info for info in detailed_analyses if info.get('food_name') == first_item_name),
                        None
                    )
                    if matched_youtube_info:
                        matched_youtube_info["recipe_name"] = matched_youtube_info.get("food_name", "AI 추천 레시피")
                        meal_data.update(matched_youtube_info)

                saved_item = ai_crud.create_recommendation_from_analysis(
                    db=db,
                    user_no=user_no,
                    analysis_data=meal_data,
                )
                saved_recommendations.append({
                    "food_name": saved_item.food_name,
                    "recommendation_id": saved_item.recommendation_id,
                    "image_url" : saved_item.image_url,
                    "calories" : saved_item.calories
                })

        return {
            "success": True,
            "message": "식단 추천 생성 및 저장 완료 되었습니다",
            "saved_recommendations": saved_recommendations
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"처리 중 서버 오류 발생: {str(e)}"
        )


@app.get("/meal-kit/detail{recommendation_id}",
         response_model=ai_schema.RecommendationDetail,
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
def get_purchase_link_for_meal_kit(
        meal_kit_id: int,
        db:Session = Depends(get_db),
        current_user : dict = Depends(account_crud.get_current_user)):

    user_no = current_user.get("user_no")

    if user_no is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token data")

    db_meal_kit = ai_crud.get_meal_kit_purchase_link(db = db, meal_kit_id = meal_kit_id, user_no = user_no)

    if db_meal_kit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meal Kit not found")

    return db_meal_kit