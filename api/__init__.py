from fastapi import APIRouter, Depends
from api.meal_to_food import analyze_foods
from api.meal_to_img import make_pictures_for_meals
from api.user_to_meal import run_generation, load_user_payload_from_db
from api.test4 import generate_for_user
from sqlalchemy.orm import Session
from database import get_db
from account import account_crud

# API 라우터 생성
app = APIRouter(prefix="/api", tags=["API"])

@app.get("/health")
async def health_check():
    """API 상태 확인"""
    return {"status": "healthy", "message": "API 모듈이 정상적으로 작동 중입니다."}

# @app.get("/generate-recommendation/{user_id}")
# async def generate_recommendation(
#         db: Session = Depends(get_db),
#         current_user: dict = Depends(account_crud.get_current_user)
# ):
#     user_id = current_user.get("user_id")
#     """사용자별 맞춤 식단 추천 생성"""
#     try:
#         result, plan_path, foods = generate_for_user(user_id)
#         return {
#             "success": True,
#             "user_id": user_id,
#             "recommendation": result,
#             "plan_path": plan_path,
#             "extracted_foods": foods
#         }
#     except Exception as e:
#         return {
#             "success": False,
#             "error": str(e),
#             "user_id": user_id
#         }

@app.post("/analyze-foods", description="test")
async def analyze_foods_endpoint(foods: list[str]):
    try:
        result = analyze_foods(foods)
        return {
            "success": True,
            "analyzed_foods": result
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@app.post("/generate-images", description="test")
async def generate_images_endpoint(plan_json_path: str):
    """식단 이미지 생성"""
    try:
        make_pictures_for_meals(plan_json_path)
        return {
            "success": True,
            "message": "이미지 생성 완료",
            "plan_path": plan_json_path
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }