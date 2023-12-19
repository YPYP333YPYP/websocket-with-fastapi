from fastapi import APIRouter, HTTPException, Depends, Path
from pydantic import BaseModel
from sqlalchemy.orm import Session
from api.user import get_current_user, get_current_user_from_parameter
from db.database import SessionLocal
from models import Category

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class CategoryCreate(BaseModel):
    category_name: str


class CategoryUpdate(BaseModel):
    category_name: str


# 카테고리 생성
@router.post("/")
def create_category(category_create: CategoryCreate, db: Session = Depends(get_db)):
    db_category = Category(**category_create.model_dump())
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category


# 모든 카테고리 조회
@router.get("/all")
def get_all_categories(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    categories = db.query(Category).offset(skip).limit(limit).all()
    return categories


# 카테고리 개별 조회
@router.get("/get/{category_id}")
def get_category(category_id: int = Path(...), db: Session = Depends(get_db)):
    category = db.query(Category).filter(Category.id == category_id).first()
    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")
    return category


# 카테고리 업데이트
@router.put("/update/{category_id}")
def update_category(category_id: int, category_update: CategoryUpdate, db: Session = Depends(get_db)):
    db_category = db.query(Category).filter(Category.id == category_id).first()

    if db_category is None:
        raise HTTPException(status_code=404, detail="Category not found")

    for key, value in category_update.model_dump().items():
        setattr(db_category, key, value)

    db.commit()
    db.refresh(db_category)
    return db_category


# 카테고리 삭제
@router.delete("/delete/{category_id}")
def delete_category(category_id: int, db: Session = Depends(get_db)):
    db_category = db.query(Category).filter(Category.id == category_id).first()
    if db_category is None:
        raise HTTPException(status_code=404, detail="Category not found")

    db.delete(db_category)
    db.commit()
    return db_category
