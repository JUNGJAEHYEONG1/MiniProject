from database import get_db
from fastapi import APIRouter, Response, Request
from sqlalchemy.orm import Session
from fastapi.params import Depends
from account import account_crud, account_schema

app = APIRouter(
    prefix="/users",
)


@app.post(path="/signup")
async def signup(new_user: account_schema.CreateUserForm = Depends(), db:Session = Depends(get_db)):
    return account_crud.create_user(new_user, db)

@app.post("/login")
async def login(response: Response, login_form: account_schema.LoginForm = Depends(), db: Session = Depends(get_db)):
    return account_crud.login(response, login_form, db)

@app.get(path="/logout")
async def logout(response: Response, request: Request):
    return account_crud.logout(response, request)