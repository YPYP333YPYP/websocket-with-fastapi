from typing import List

from fastapi import APIRouter, HTTPException, WebSocket, Depends, status, Query, Header, Path
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload
from api.user import get_current_user, get_current_user_from_parameter
from db.database import SessionLocal
from models import ChatRoom, Membership, User, Hashtag, Category

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
    user_id: int


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
               ):
    # 채팅방 생성 로직
    chat_room = ChatRoom(room_name=chatroom.room_name, is_private=chatroom.is_private, category_id=chatroom.category, manager_id=chatroom.user_id)
    chat_room.generate_auth_code()
    db.add(chat_room)
    db.commit()
    db.refresh(chat_room)
    return {"room_id": chat_room.id, "room_name": chat_room.room_name}


# 채팅방 참여
@router.post("/join")
def join_room(user_id: int,
              room_id: int,
              auth_code: str = None,
              db: Session = Depends(get_db),
              current_user: User = Depends(get_current_user)
              ):
    user = db.query(User).filter(User.id == user_id).first()
    if current_user.id == user.id:
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

            # 사설 채팅방 일 경우 초대코드
            if chat_room.is_private:
                if auth_code == chat_room.auth_code:
                    new_membership = Membership(user=user, room=chat_room)
                    db.add(new_membership)
                else:
                    raise HTTPException(status_code=401, detail="Not match Code")
            else:
                new_membership = Membership(user=user, room=chat_room)
                db.add(new_membership)

            db.commit()

            return {"message": f"User {user.username} joined room {chat_room.room_name}"}
        else:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User or room not found")
    else:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token not match user ")


# 채팅방 이름, 사설 채팅방 수정
@router.put("/update/{room_id}")
async def update_chat_room(room_id: int, room_update: dict, db: Session = Depends(get_db)):

    try:
        chat_room = db.query(ChatRoom).filter(ChatRoom.id == room_id).first()

        if not chat_room:
            raise HTTPException(status_code=404, detail="Chat room not found")

        if 'room_name' in room_update:
            chat_room.room_name = room_update['room_name']

        if 'is_private' in room_update:
            chat_room.is_private = room_update['is_private']

        db.commit()
        return {"message": "Chat room updated successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        db.close()


# 모든 채팅방 조회
@router.get("/rooms", response_model=list[ChatRoomResponse])
def get_chat_rooms(skip: int = Query(0, description="Skip the first N items", ge=0),
                   limit: int = Query(10, description="Limit the number of items returned", le=100),
                   db: Session = Depends(get_db),
                   ):
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


@router.get("/{room_id}/{manager_id}/expel/{user_id}")
def expel_user_by_manager(room_id: int, manager_id: int, user_id: int, db: Session = Depends(get_db)):
    db_chatroom = db.query(ChatRoom).filter(room_id == ChatRoom.id).first()
    user_name = db.query(User).filter(user_id == User.id).first().username
    if not db_chatroom:
        raise HTTPException(status_code=404, detail="Chat room not found")

    if not user_name:
        raise HTTPException(status_code=404, detail="User not found")

    if db_chatroom.manager_id == manager_id:
        membership = db.query(Membership).filter(Membership.room_id == room_id, Membership.user_id == user_id).first()
        db.delete(membership)
        db.commit()
    else:
        raise HTTPException(status_code=204, detail="User is not manager")

    return f'{user_name} has been banned '


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
