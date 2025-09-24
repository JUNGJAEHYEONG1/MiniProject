from database import get_db
from fastapi import APIRouter, Response, Request, HTTPException, status
from sqlalchemy.orm import Session
from fastapi.params import Depends
from account import account_crud, account_schema
from ai import ai_router, ai_crud, ai_schema

app = APIRouter(
    prefix="/ai",
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



