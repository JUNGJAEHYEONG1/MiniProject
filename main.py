from fastapi import FastAPI
import models
from database import engine


from account import account_router

models.Base.metadata.create_all(bind=engine)
app = FastAPI()

app.include_router(account_router.app, tags = ["Account"])


@app.get("/")
def read_root():
    return {"hi"}