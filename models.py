from sqlalchemy import Column, Integer, String, Date, DateTime, DECIMAL, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from sqlalchemy.orm import relationship

from database import Base

#DROP TABLE "Allergies", "DailyRecommendations", "Ingredients", "MealKits", "Recipes", "UserAllergies", "UserEatLevels", "UserEatenFoods", "Users" CASCADE;
class UserAllergy(Base): #유저와 알레르기의 중간 테이블
    __tablename__ = 'UserAllergies'

    user_no = Column(Integer, ForeignKey('Users.user_no'), primary_key=True)
    allergy_id = Column(Integer, ForeignKey('Allergies.allergy_id'), primary_key=True)


class User(Base):
    __tablename__ = "Users"

    user_no = Column(Integer, primary_key=True, autoincrement=True)

    user_id = Column(String(50), unique=True, nullable=False)

    hashed_password = Column(String(100), nullable=False)
    email = Column(String(100), nullable=False, unique=True)
    user_name = Column(String(20), nullable=False)
    gender = Column(String(10))
    age = Column(Integer)

    height = Column(DECIMAL(5, 2))
    weight = Column(DECIMAL(5, 2))
    activity_level = Column(String(50)) #운동 정도
    diet_goal = Column(String(50))
    preferred_food = Column(String(50))
    created_at = Column(DateTime, nullable=False, default=datetime.now)

    allergies = relationship("Allergy", secondary=UserAllergy.__table__, back_populates="users")

    eaten_foods = relationship("UserEatenFood", back_populates="user", cascade="all, delete-orphan")
    recommendations = relationship("DailyRecommendation", back_populates="user")
    eat_level = relationship("UserEatLevel", back_populates="user", cascade="all, delete-orphan", uselist=False)


class Allergy(Base):
    __tablename__ = "Allergies"

    allergy_id = Column(Integer, primary_key=True, autoincrement=True)
    allergy_name = Column(String(100), nullable=False, unique=True)

    users = relationship("User", secondary=UserAllergy.__table__, back_populates="allergies")

class UserEatenFood(Base): #유저가 먹은 음식 기록
    __tablename__ = "UserEatenFoods"

    no = Column(Integer, primary_key=True, autoincrement=True)

    user_no = Column(Integer, ForeignKey("Users.user_no"), nullable=False)
    image_url = Column(String(255))
    food_name = Column(String(100))
    calories = Column(DECIMAL(10, 2))
    carbs_g = Column(DECIMAL(10, 2))
    protein_g = Column(DECIMAL(10, 2))
    fat_g = Column(DECIMAL(10, 2))
    created_at = Column(DateTime, nullable=False, default=datetime.now)

    user = relationship("User", back_populates="eaten_foods")

class DailyRecommendation(Base):
    __tablename__ = "DailyRecommendations"

    recommendation_id = Column(Integer, primary_key=True, autoincrement=True)
    user_no = Column(Integer, ForeignKey("Users.user_no"), nullable=False)
    food_name = Column(String(100), nullable=False)
    image_url = Column(String(255))
    calories = Column(DECIMAL(10, 2))
    carbs_g = Column(DECIMAL(10, 2))
    protein_g = Column(DECIMAL(10, 2))
    fat_g = Column(DECIMAL(10, 2))

    user = relationship("User", back_populates="recommendations")

    #밀키트와 음식 N:1
    meal_kits = relationship("MealKit", back_populates="recommendation")

    #레시피와 음식 1:1
    recipe = relationship("Recipe", back_populates="recommendation", uselist=False)


class MealKit(Base):
    __tablename__ = 'MealKits'

    meal_kit_id = Column(Integer, primary_key=True, autoincrement=True)

    meal_kit_name = Column(String(50))
    purchase_link = Column(String(255))
    image_url = Column(String(255))

    calories = Column(DECIMAL(10, 2))
    carbs_g = Column(DECIMAL(10, 2))
    protein_g = Column(DECIMAL(10, 2))
    fat_g = Column(DECIMAL(10, 2))

    recommendation_id = Column(Integer, ForeignKey("DailyRecommendations.recommendation_id"))
    recommendation = relationship("DailyRecommendation", back_populates="meal_kits")


class Recipe(Base):
    __tablename__ = "Recipes"

    recipe_id = Column(Integer, primary_key=True, autoincrement=True)
    recipe_name = Column(String(50))
    cooking_method = Column(String)

    recipe_video_link = Column(String(255), default="None")

    recommendation_id = Column(Integer, ForeignKey("DailyRecommendations.recommendation_id"), unique=True)
    recommendation = relationship("DailyRecommendation", back_populates="recipe")
    ingredients = relationship("Ingredient", back_populates="recipes", cascade="all, delete-orphan")

class Ingredient(Base): #재료
    __tablename__ = "Ingredients"

    ingredient_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False)
    image_url = Column(String(255), default="None")
    purchase_link = Column(String(255), default="None")

    recipe_id = Column(Integer, ForeignKey("Recipes.recipe_id"), nullable=False)
    recipes = relationship("Recipe", back_populates="ingredients")

class UserEatLevel(Base): #유저 아점저 먹는 정도
    __tablename__ = "UserEatLevels"

    user_no = Column(Integer, ForeignKey("Users.user_no"), primary_key=True)

    breakfast = Column(String(50))
    lunch = Column(String(50))
    dinner = Column(String(50))

    user = relationship("User", back_populates="eat_level")
