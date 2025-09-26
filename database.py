import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from dotenv import load_dotenv

load_dotenv()

# 데이터베이스 엔진 생성
database_url = os.getenv("DATABASE_URL")

# database_url = os.getenv("DATABASE_URL", "sqlite:///./miniproject.db")
engine = create_engine(database_url)

# 세션 생성
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
