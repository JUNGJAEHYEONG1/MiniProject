import os
from dotenv import load_dotenv

# .env 파일 연결
load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = float(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))

# S3 Configuration
S3_BUCKET = os.getenv("S3_BUCKET")
S3_REGION = os.getenv("AWS_REGION", "ap-northeast-2")
MEAL_PIC_OUT_DIR = os.getenv("MEAL_PIC_OUT_DIR", "meal_pics")

#AI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")