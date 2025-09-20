from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from datetime import datetime

from sqlalchemy.orm import relationship

from database import Base


class Account(Base):
    __tablename__ = "Account"

    no = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(40), nullable=False, unique=True)
    email = Column(String(100), nullable=False, unique=True)
    hashed_password = Column(String(100), nullable=False)
    name = Column(String(10), nullable=False, unique=True)
    regdate = Column(DateTime, nullable=False, default=datetime.now)
