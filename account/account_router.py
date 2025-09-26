from account.account_crud import get_current_user
from database import get_db
from fastapi import APIRouter, Response, Request, HTTPException, status, Depends, UploadFile, File
from sqlalchemy.orm import Session
from account import account_crud, account_schema
from utils.s3 import upload_file_to_s3

app = APIRouter(
    prefix="/users",
)

@app.get("/eaten/foods/info")
def get_user_eaten_foods(db:Session = Depends(get_db),
                         current_user: dict = Depends(account_crud.get_current_user)):

    user_no = current_user.get("user_no")
    foods = account_crud.get_user_eaten_foods(db = db, user_no = user_no)
    return foods

@app.post("/eaten-food-image")
def upload_eaten_food_image(
        image_file: UploadFile = File(...),
        db: Session = Depends(get_db),
        current_user: dict = Depends(account_crud.get_current_user)
):
    user_no = current_user.get("user_no")
    image_url = upload_file_to_s3(file=image_file, user_no=user_no)

    if not image_url:
        return {"error": "S3 이미지 업로드에 실패했습니다."}

    saved_data = account_crud.create_eaten_food_record(db=db, user_no = user_no, image_url = image_url)

    return {
        "message" :"이미지가 성공적으로 업로드 되었습니다.",
        "image_url": image_url,
        "no:" : saved_data.no}


@app.post(path="/signup")
async def signup(new_user: account_schema.CreateUserForm = Depends(), db:Session = Depends(get_db)):
    return account_crud.create_user(new_user, db)

@app.post("/login")
async def login(response: Response, login_form: account_schema.LoginForm = Depends(), db: Session = Depends(get_db)):
    return account_crud.login(response, login_form, db)

@app.get(path="/logout")
async def logout(response: Response, request: Request):
    return account_crud.logout(response, request)

@app.patch("/inital/info")
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

@app.get("/profile/info", response_model=account_schema.UserInfo)
def get_my_info(
        db: Session = Depends(get_db),
        current_user: dict = Depends(account_crud.get_current_user)
):
    user_no = current_user.get("user_no")
    db_user = account_crud.get_user_data_from_no(db=db, user_no=user_no)

    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_BAD_REQUEST, detail="User not found")
    return db_user

@app.get("/food-setting", response_model=account_schema.UserFoodSetting)
def get_food_setting(
        db: Session = Depends(get_db),
        current_user: dict = Depends(account_crud.get_current_user)
):
    user_no = current_user.get("user_no")
    db_user = account_crud.get_user_data_from_no(db=db, user_no=user_no)

    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_BAD_REQUEST, detail="User not found")

    return db_user

@app.patch("/food-setting", response_model=account_schema.UserFoodSetting)
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