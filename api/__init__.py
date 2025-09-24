from fastapi import APIRouter
from .meal_to_food import analyze_foods
from .meal_to_img import make_pictures_for_meals
from .user_to_meal import run_generation, load_user_payload_from_db
from .test4 import generate_for_user

# API 라우터 생성
app = APIRouter(prefix="/api", tags=["API"])

@app.get("/health")
async def health_check():
    """API 상태 확인"""
    return {"status": "healthy", "message": "API 모듈이 정상적으로 작동 중입니다."}

@app.post("/generate-recommendation/{user_id}")
async def generate_recommendation(user_id: str):
    """사용자별 맞춤 식단 추천 생성"""
    try:
        result, plan_path, foods = generate_for_user(user_id)
        return {
            "success": True,
            "user_id": user_id,
            "recommendation": result,
            "plan_path": plan_path,
            "extracted_foods": foods
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "user_id": user_id
        }

@app.post("/analyze-foods")
async def analyze_foods_endpoint(foods: list[str]):
    """음식 분석 (재료 및 레시피 추출)"""
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

@app.post("/generate-images")
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