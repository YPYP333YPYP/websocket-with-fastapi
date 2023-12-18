from typing import List

from fastapi import APIRouter, HTTPException, WebSocket, Depends, status, Query, Header, Path
from pydantic import BaseModel
from sqlalchemy.orm import Session
from api.user import get_current_user, get_current_user_from_parameter
from db.database import SessionLocal
from models import ChatRoom, Membership, User, Message, Hashtag

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class ChatRoomResponse(BaseModel):
    id: int
    room_name: str
    created_at: str


# 채팅방에 해시태그 추가
@router.get("/{room_id}/add/{hashtag_id}", status_code=200)
def add_hashtag_with_chatroom(room_id: int, hashtag_id:int,  db: Session = Depends(get_db)):
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


@router.delete("/{room_id}/delete/{hashtag_id}", status_code=200)
def delete_hashtag_from_chatroom(room_id: int, hashtag_id: int, db: Session = Depends(get_db)):
    db_hashtag = db.query(Hashtag).filter(Hashtag.id == hashtag_id, Hashtag.room_id == room_id).first()
    if db_hashtag is None:
        raise HTTPException(status_code=404, detail="Hashtag not found")

    db_hashtag.room_id = None
    db.commit()
    return f"ChatRoom : {db_hashtag.room_id} Delete Hashtag: {db_hashtag.tag_name}"


# 채팅방 생성
@router.post("/create")
def create_room(room_name: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # 채팅방 생성 로직
    chat_room = ChatRoom(room_name=room_name)
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

        # Create the membership
        new_membership = Membership(user=user, room=chat_room)
        db.add(new_membership)
        db.commit()

        return {"message": f"User {user.username} joined room {chat_room.room_name}"}
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User or room not found")


@router.get("/rooms", response_model=list[ChatRoomResponse])
def get_chat_rooms(skip: int = Query(0, description="Skip the first N items", ge=0),
                   limit: int = Query(10, description="Limit the number of items returned", le=100),
                   db: Session = Depends(get_db),
                   current_user: User = Depends(get_current_user)):
    chat_rooms = db.query(ChatRoom).offset(skip).limit(limit).all()
    response_data = [{"id": room.id, "room_name": room.room_name, "created_at": room.created_at.isoformat()} for room in
                     chat_rooms]
    return response_data


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


