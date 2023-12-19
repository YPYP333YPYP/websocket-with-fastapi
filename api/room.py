from typing import List

from fastapi import APIRouter, HTTPException, WebSocket, Depends, status, Query, Header, Path
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload
from api.user import get_current_user, get_current_user_from_parameter
from db.database import SessionLocal
from models import ChatRoom, Membership, User, Message, Hashtag, Category

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class ChatRoomCreate(BaseModel):
    room_name: str
    is_private: bool
    category: int


class HashtagSchema(BaseModel):
    id: int
    tag_name: str


class ChatRoomResponse(BaseModel):
    id: int
    room_name: str
    created_at: str
    is_private: bool
    hashtags: List[HashtagSchema]
    category: str


# 채팅방 생성
@router.post("/create")
def create_room(chatroom: ChatRoomCreate,
                db: Session = Depends(get_db),
                current_user: User = Depends(get_current_user)):
    # 채팅방 생성 로직
    chat_room = ChatRoom(room_name=chatroom.room_name, is_private=chatroom.is_private, category_id=chatroom.category)
    chat_room.generate_auth_code()
    db.add(chat_room)
    db.commit()
    db.refresh(chat_room)
    return {"room_id": chat_room.id, "room_name": chat_room.room_name}


# 채팅방 참여
@router.post("/join")
def join_room(user_id: int, room_id: int, db: Session = Depends(get_db),
              current_user: User = Depends(get_current_user)):
    user = db.query(User).filter(User.id == user_id).first()
    chat_room = db.query(ChatRoom).filter(ChatRoom.id == room_id).first()

    if user and chat_room:
        membership = db.query(Membership).filter(
            Membership.user_id == user_id, Membership.room_id == room_id
        ).first()

        if membership:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already a member of this room",
            )

        new_membership = Membership(user=user, room=chat_room)
        db.add(new_membership)
        db.commit()

        return {"message": f"User {user.username} joined room {chat_room.room_name}"}
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User or room not found")


# 모든 채팅방 조회
@router.get("/rooms", response_model=list[ChatRoomResponse])
def get_chat_rooms(skip: int = Query(0, description="Skip the first N items", ge=0),
                   limit: int = Query(10, description="Limit the number of items returned", le=100),
                   db: Session = Depends(get_db),
                   current_user: User = Depends(get_current_user)):
    chat_rooms = (
        db.query(ChatRoom)
            .options(joinedload(ChatRoom.hashtags), joinedload(ChatRoom.category))
            .offset(skip)
            .limit(limit)
            .all()
    )

    response_data = [
        {
            "id": room.id,
            "room_name": room.room_name,
            "created_at": room.created_at.isoformat(),
            "is_private": room.is_private,
            "hashtags": room.hashtags,
            "category": room.category.category_name if room.category else None
        }
        for room in chat_rooms
    ]

    return response_data


# 채팅방 멤버 조회
@router.get("/{room_id}/members")
def get_room_members(
        room_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    # 채팅방 멤버 리스트 가져오기
    chat_room = db.query(ChatRoom).filter(ChatRoom.id == room_id).first()
    if chat_room:
        members = db.query(Membership).filter(Membership.room_id == room_id).all()
        return [{"user_id": member.user.id, "username": member.user.username} for member in members]
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")


# 채팅방에 해시태그 추가
@router.get("/hashtag/{room_id}/add/{hashtag_id}", status_code=200)
def add_hashtag_to_chatroom(room_id: int, hashtag_id: int, db: Session = Depends(get_db)):
    db_hashtag = db.query(Hashtag).filter(Hashtag.id == hashtag_id).first()
    if db_hashtag is None:
        raise HTTPException(status_code=404, detail="Hashtag not found")

    db_chatroom = db.query(ChatRoom).filter(ChatRoom.id == room_id).first()
    if db_chatroom is None:
        raise HTTPException(status_code=404, detail="Chat room not found")

    db_hashtag.room_id = db_chatroom.id
    db.commit()
    db.refresh(db_chatroom)

    return f"ChatRoom : {db_chatroom.id} Add Hashtag: {db_hashtag.tag_name}"


# 채팅방에 해시태그 삭제
@router.delete("/hashtag/{room_id}/delete/{hashtag_id}", status_code=200)
def delete_hashtag_from_chatroom(room_id: int, hashtag_id: int, db: Session = Depends(get_db)):
    db_hashtag = db.query(Hashtag).filter(Hashtag.id == hashtag_id, Hashtag.room_id == room_id).first()
    if db_hashtag is None:
        raise HTTPException(status_code=404, detail="Hashtag not found")

    db_hashtag.room_id = None
    db.commit()
    return f"ChatRoom : {db_hashtag.room_id} Delete Hashtag: {db_hashtag.tag_name}"


# 채팅방에 카테고리 추가
@router.get("/category/{room_id}/add/{category_id}", status_code=200)
def add_category_to_chatroom(room_id: int, category_id: int, db: Session = Depends(get_db)):
    db_category = db.query(Category).filter(Category.id == category_id).first()
    if db_category is None:
        raise HTTPException(status_code=404, detail="Category not found")

    db_chatroom = db.query(ChatRoom).filter(ChatRoom.id == room_id).first()
    if db_chatroom is None:
        raise HTTPException(status_code=404, detail="Chat room not found")

    if db_chatroom.category_id is not None:
        raise HTTPException(status_code=409, detail="Category already exists")

    db_chatroom.category_id = db_category.id
    db.commit()
    db.refresh(db_chatroom)

    return f"ChatRoom: {db_chatroom.id} Add Category: {db_category.category_name}"


# 채팅방에 카테고리 삭제
@router.delete("/category/{room_id}/delete", status_code=200)
def delete_category_from_chatroom(room_id: int, db: Session = Depends(get_db)):
    db_chatroom = db.query(ChatRoom).filter(ChatRoom.id == room_id).first()
    if db_chatroom is None:
        raise HTTPException(status_code=404, detail="Chat room not found")
    db_chatroom.category_id = None
    db.commit()
    return f"ChatRoom : {db_chatroom.room_id} Delete Category"


# 카테고리 검색어로 채팅방 조회
@router.get("/search/")
def search_chatroom_with_category(query: str = Query(...), skip: int = Query(0), limit: int = Query(10), db: Session = Depends(get_db)):
    db_categories = db.query(Category).filter(Category.category_name.contains(query)).all()

    category_ids = [category.id for category in db_categories]

    chat_rooms = (
        db.query(ChatRoom)
        .options(joinedload(ChatRoom.hashtags), joinedload(ChatRoom.category))
        .filter(ChatRoom.category_id.in_(category_ids))
        .offset(skip)
        .limit(limit)
        .all()
    )

    response_data = [
        {
            "id": room.id,
            "room_name": room.room_name,
            "created_at": room.created_at.isoformat(),
            "is_private": room.is_private,
            "hashtags": room.hashtags,
            "category": room.category.category_name if room.category else None
        }
        for room in chat_rooms
    ]

    return response_data
