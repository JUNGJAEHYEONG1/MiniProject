from fastapi import FastAPI
import models
from database import engine


from account import account_router
from ai import ai_router
from api import app as api_app

models.Base.metadata.create_all(bind=engine)
app = FastAPI()


app.include_router(account_router.app, tags = ["Account"])
app.include_router(ai_router.app, tags = ["AI"])
app.include_router(api_app, tags = ["API"])


@app.get("/")
def read_root():
    return {"hi"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)