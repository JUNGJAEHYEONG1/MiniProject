from fastapi import FastAPI
import models
from database import engine

models.Base.metadata.create_all(bind=engine)

from account import account_router

app = FastAPI()

app.include_router(account_router.app, tags = ["Account"])

@app.get("/")
def read_root():
    return {}