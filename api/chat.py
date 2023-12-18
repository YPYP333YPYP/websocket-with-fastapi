from fastapi import APIRouter, HTTPException, WebSocket, Depends, status, Query, Header
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional

from api.user import get_current_user, get_current_user_from_parameter
from db.databast  import SessionLocal
from models import ChatRoom, Membership, User, Message

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


@router.post("/create_room")
def create_room(room_name: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # 채팅방 생성 로직
    chat_room = ChatRoom(room_name=room_name)
    db.add(chat_room)
    db.commit()
    db.refresh(chat_room)
    return {"room_id": chat_room.id, "room_name": chat_room.room_name}


@router.post("/join_room")
def join_room(user_id: int, room_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # 채팅방 참여 로직
    user = db.query(User).filter(User.id == user_id).first()
    chat_room = db.query(ChatRoom).filter(ChatRoom.id == room_id).first()

    if user and chat_room:
        # Check if the membership already exists
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


@router.get("/chat_rooms", response_model=list[ChatRoomResponse])
def get_chat_rooms(skip: int = Query(0, description="Skip the first N items", ge=0),
                    limit: int = Query(10, description="Limit the number of items returned", le=100),
                    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    chat_rooms = db.query(ChatRoom).offset(skip).limit(limit).all()
    response_data = [{"id": room.id, "room_name": room.room_name, "created_at": room.created_at.isoformat()} for room in chat_rooms]
    return response_data


@router.get("/room/{room_id}/members")
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


def is_valid_websocket_connection(room_id: int, user_id: int, db: Session = Depends(get_db)):
    # 여기에 적절한 조건을 추가하세요.
    # 예: 유효한 조건이면 True, 그렇지 않으면 False 반환

    # 예제 조건: 채팅방에 미리 정의된 특정 조건을 만족하는 경우에만 연결 허용
    chat_room = db.query(ChatRoom).filter(ChatRoom.id == room_id).first()

    # 예제 조건: 사용자가 채팅방에 속하고, 채팅방이 특정 조건을 만족하면 연결 허용
    is_member = db.query(Membership).filter_by(user_id=user_id, room_id=room_id).first()

    return chat_room is not None and is_member is not None


# 적절한 로직을 사용하여 WebSocket 연결을 거부하는 함수
async def validate_websocket_connection(websocket: WebSocket, room_id: int, user_id: int,
                                        db: Session = Depends(get_db)):
    # 적절한 조건을 확인하고 연결을 거부하는 로직을 추가하세요.
    # 예: 특정 조건에 따라 연결을 거부하고 로그를 출력
    if not is_valid_websocket_connection(room_id, user_id, db):
        await websocket.close(code=1008)
        print("WebSocket connection rejected")
        return False
    else:
        return True


@router.websocket("/ws/{room_id}/{user_id}")
async def chat_ws(
        websocket: WebSocket,
        room_id: int,
        user_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user_from_parameter)
):
    # WebSocket 연결 허용 여부 확인
    if not await validate_websocket_connection(websocket, room_id, user_id, db):
        return

    # WebSocket 연결 허용
    await websocket.accept()

    # User 객체에 WebSocket 객체 할당
    user = db.query(User).filter(User.id == user_id).first()
    user.websocket = websocket

    # 채팅방의 모든 멤버에게 현재 사용자의 입장을 알리는 메시지를 전송
    user = db.query(User).filter(User.id == user_id).first()
    await broadcast_message(db, f"User {user.username} joined the room.", room_id)

    # 현재 사용자가 속한 채팅방에 대한 메시지를 모두 가져옴
    messages = db.query(Message).filter(Message.room_id == room_id).order_by(Message.created_at.desc()).limit(10).all()

    # 채팅방의 이전 메시지를 전송
    for message in reversed(messages):
        await websocket.send_text(f"{message.user.username}: {message.content}")

    while True:
        # 채팅 메시지 수신
        data = await websocket.receive_text()

        # 수신한 메시지를 데이터베이스에 저장
        message = Message(room_id=room_id, user_id=user_id, content=data)
        db.add(message)
        db.commit()

        # 채팅 메시지를 채팅방의 다른 사용자에게 브로드캐스트
        await broadcast_message(db, f"{user.username}: {data}", room_id)


@router.websocket("/ws/{room_id}/{user_id}")
async def chat_ws(
    websocket: WebSocket,
    room_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_parameter)
):
    # WebSocket 연결 종료 처리
    user = db.query(User).filter(User.id == user_id).first()

    if user:
        # User 객체에서 WebSocket 객체 제거 또는 마킹
        user.websocket = None

    user = db.query(User).filter(User.id == user_id).first()
    await broadcast_message(db, f"User {user.username} joined the room.", room_id)

    # 현재 사용자가 속한 채팅방에 대한 메시지를 모두 가져옴
    messages = db.query(Message).filter(Message.room_id == room_id).order_by(Message.created_at.desc()).limit(10).all()

    # 채팅방의 이전 메시지를 전송
    for message in reversed(messages):
        await websocket.send_text(f"{message.user.username}: {message.content}")

    while True:
        # 채팅 메시지 수신
        data = await websocket.receive_text()

        # 수신한 메시지를 데이터베이스에 저장
        message = Message(room_id=room_id, user_id=user_id, content=data)
        db.add(message)
        db.commit()

        # 채팅 메시지를 채팅방의 다른 사용자에게 브로드캐스트
        await broadcast_message(db, f"{user.username}: {data}", room_id)


async def broadcast_message(db: Session, message: str, room_id: int):
    # 채팅방의 모든 멤버에게 메시지를 전송
    members = db.query(Membership).filter(Membership.room_id == room_id).all()
    for member in members:
        if member.user.websocket is not None:
            await member.user.websocket.send_text(message)
