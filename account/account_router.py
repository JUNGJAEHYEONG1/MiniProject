from account.account_crud import get_current_user
from database import get_db
from fastapi import APIRouter, Response, Request, HTTPException, status, Depends, UploadFile, File
from sqlalchemy.orm import Session
from account import account_crud, account_schema
from utils.s3 import upload_file_to_s3
from api import Image

app = APIRouter(
    prefix="/users",
)

@app.get("recommended-amount/calories", description="총 칼로리 대체")
def get_user_calories(db:Session = Depends(get_db),
                      current_user: dict = Depends(account_crud.get_current_user)):
    user_no = current_user.get("user_no")
    data = account_crud.get_calories(db = db, user_no = user_no)
    total_calories = data.get("total_calories")
    return total_calories

@app.get("/eaten/foods/{eaten_food_no}",
         response_model=account_schema.EatenFoodDetail,
         description="먹은 음식 상세 정보")
def read_eaten_food_details(
        eaten_food_no: int,
        db: Session = Depends(get_db),
        current_user: dict = Depends(account_crud.get_current_user)
):
    user_no = current_user.get("user_no")

    db_eaten_food = account_crud.get_eaten_food_by_no(
        db=db,
        eaten_food_no=eaten_food_no,
        user_no=user_no
    )

    if db_eaten_food is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="해당 음식 기록을 찾을 수 없습니다.")

    return db_eaten_food

@app.get("/eaten/foods/info",description="먹은 음식 전체 불러오기 test")
def get_user_eaten_foods(db:Session = Depends(get_db),
                         current_user: dict = Depends(account_crud.get_current_user)):

    user_no = current_user.get("user_no")
    foods = account_crud.get_user_eaten_foods(db = db, user_no = user_no)
    return foods

@app.post("/eaten-food-image", description= "먹은 음식 사진 올리기")
async def upload_eaten_food_image(
        image_file: UploadFile = File(...),
        db: Session = Depends(get_db),
        current_user: dict = Depends(account_crud.get_current_user)
):
    image_bytes = await image_file.read()

    await image_file.seek(0)

    user_no = current_user.get("user_no")
    image_url = upload_file_to_s3(file=image_file, user_no=user_no)



    if not image_url:
        return {"error": "S3 이미지 업로드에 실패했습니다."}

    try:
        analysis_result = Image.analyze_image_bytes(
            image_bytes=image_bytes,
            filename=image_file.filename,
            detail=2
        )

    except Exception as e:
        print(f"OpenAI API 호출 중 오류 발생: {e}")
        raise HTTPException(status_code=500, detail="이미지 영양 정보 분석에 실패했습니다.")

    saved_data = account_crud.create_eaten_food_record(
        db=db,
        user_no=user_no,
        image_url=image_url,
        nutrition_data=analysis_result
    )

    return {
        "message": "이미지가 성공적으로 업로드 및 분석되었습니다.",
        "image_url": image_url,
        "no": saved_data.no,
        "analysis": analysis_result
    }


@app.post(path="/signup", description="회원가입")
async def signup(new_user: account_schema.CreateUserForm = Depends(), db:Session = Depends(get_db)):
    return account_crud.create_user(new_user, db)

@app.post("/login", description="로그인")
async def login(response: Response, login_form: account_schema.LoginForm = Depends(), db: Session = Depends(get_db)):
    return account_crud.login(response, login_form, db)

@app.get(path="/logout", description="로그아웃")
async def logout(response: Response, request: Request):
    return account_crud.logout(response, request)

@app.patch("/inital/info", description="초기 설문")
def get_inital_profile(data: account_schema.UserProfileUpdate,
                   db: Session = Depends(get_db),
                   current_user: dict = Depends(account_crud.get_current_user)
                   ):
    user_no = current_user.get("user_no")

    if user_no is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token data")

    updated_user = account_crud.update_user_profile(db=db, user_no=user_no, data=data)

    if not updated_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return updated_user

@app.get("/profile/info",
         response_model=account_schema.UserInfo,
         description="개인 프로필")
def get_my_info(
        db: Session = Depends(get_db),
        current_user: dict = Depends(account_crud.get_current_user)
):
    user_no = current_user.get("user_no")
    db_user = account_crud.get_user_data_from_no(db=db, user_no=user_no)

    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_BAD_REQUEST, detail="User not found")
    return db_user

@app.get("/food-setting",
         response_model=account_schema.UserFoodSetting,
         description="음식 설정 정보")
def get_food_setting(
        db: Session = Depends(get_db),
        current_user: dict = Depends(account_crud.get_current_user)
):
    user_no = current_user.get("user_no")
    db_user = account_crud.get_user_data_from_no(db=db, user_no=user_no)

    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_BAD_REQUEST, detail="User not found")

    return db_user

@app.patch("/food-setting",
           response_model=account_schema.UserFoodSetting,
           description="음식 설정 하기")
def update_food_setting(
        data: account_schema.UserFoodSetting,
        db: Session = Depends(get_db),
        current_user: dict = Depends(account_crud.get_current_user)
):
    user_no = current_user.get("user_no")
    if not user_no:
        raise HTTPException(status_code=401, detail="Invalid token")

    account_crud.update_user_profile(db=db, user_no=user_no, data=data)

    db_user_updated = account_crud.food_setting(db, user_no=user_no)

    return db_user_updated