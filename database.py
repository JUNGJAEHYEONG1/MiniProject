from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# PostgreSQL 연결 정보
DATABASE_URL = "postgresql+psycopg2://postgres:!a3525020@localhost:5432/postgres"

# 데이터베이스 엔진 생성
engine = create_engine(DATABASE_URL)
# 세션 생성
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()