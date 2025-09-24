import os
from dotenv import load_dotenv

# .env 파일 연결
load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here-change-this-in-production")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = float(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# S3 Configuration
S3_BUCKET = os.getenv("S3_BUCKET")
S3_REGION = os.getenv("AWS_REGION", "ap-northeast-2")
MEAL_PIC_OUT_DIR = os.getenv("MEAL_PIC_OUT_DIR", "meal_pics")