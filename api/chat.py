from fastapi import APIRouter, HTTPException, WebSocket, Depends, status, Query, Header
from sqlalchemy.orm import Session
from api.user import get_current_user, get_current_user_from_parameter
from db.database import SessionLocal
from models import ChatRoom, Membership, User, Message

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def is_valid_websocket_connection(room_id: int, user_id: int, db: Session = Depends(get_db)):
    # 예제 조건: 채팅방에 미리 정의된 특정 조건을 만족하는 경우에만 연결 허용
    chat_room = db.query(ChatRoom).filter(ChatRoom.id == room_id).first()

    # 예제 조건: 사용자가 채팅방에 속하고, 채팅방이 특정 조건을 만족하면 연결 허용
    is_member = db.query(Membership).filter_by(user_id=user_id, room_id=room_id).first()

    return chat_room is not None and is_member is not None


# Websocket 연결 거부 함수
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


# 초기 연결 시
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


# Websocket 접속 종료 시
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


# 채팅방의 모든 멤버에게 메시지를 전송
async def broadcast_message(db: Session, message: str, room_id: int):
    members = db.query(Membership).filter(Membership.room_id == room_id).all()
    for member in members:
        if member.user.websocket is not None:
            await member.user.websocket.send_text(message)
