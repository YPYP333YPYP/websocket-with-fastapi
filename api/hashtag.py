from fastapi import APIRouter, HTTPException, Depends, Path
from pydantic import BaseModel
from sqlalchemy.orm import Session
from api.user import get_current_user, get_current_user_from_parameter
from db.database import SessionLocal
from models import Hashtag

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class HashtagCreate(BaseModel):
    tag_name: str


class HashtagUpdate(BaseModel):
    tag_name: str


class ChatRoomResponse(BaseModel):
    id: int
    room_name: str
    created_at: str


# 해시태그 생성
@router.post("/")
def create_hashtag(hashtag_create: HashtagCreate, db: Session = Depends(get_db)):
    db_hashtag = Hashtag(**hashtag_create.model_dump())
    db.add(db_hashtag)
    db.commit()
    db.refresh(db_hashtag)
    return db_hashtag


# 모든 해시태그 조회
@router.get("/all")
def select_hashtags(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    hashtags = db.query(Hashtag).offset(skip).limit(limit).all()
    return hashtags


# 해시태그 개별 조회
@router.get("/get/{hashtag_id}")
def read_hashtag(hashtag_id: int = Path(...), db: Session = Depends(get_db)):
    hashtag = db.query(Hashtag).filter(Hashtag.id == hashtag_id).first()
    if hashtag is None:
        raise HTTPException(status_code=404, detail="Hashtag not found")
    return hashtag


# 해시태그 업데이트
@router.put("/update{hashtag_id}")
def update_hashtag(hashtag_id: int, hashtag_update: HashtagUpdate, db: Session = Depends(get_db)):
    db_hashtag = db.query(Hashtag).filter(Hashtag.id == hashtag_id).first()

    if db_hashtag is None:
        raise HTTPException(status_code=404, detail="Hashtag not found")

    for key, value in hashtag_update.model_dump().items():
        setattr(db_hashtag, key, value)

    db.commit()
    db.refresh(db_hashtag)
    return db_hashtag


# 해시태그 삭제
@router.delete("/delete/{hashtag_id}")
def delete_hashtag(hashtag_id: int, db: Session = Depends(get_db)):
    db_hashtag = db.query(Hashtag).filter(Hashtag.id == hashtag_id).first()
    if db_hashtag is None:
        raise HTTPException(status_code=404, detail="Hashtag not found")

    db.delete(db_hashtag)
    db.commit()
    return db_hashtag
