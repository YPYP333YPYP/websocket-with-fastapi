import asyncio
import logging
from typing import Union

from broadcaster import Broadcast
from fastapi import APIRouter, HTTPException, WebSocket, Depends, status, Query, Header
from pydantic import BaseModel, AnyHttpUrl
from sqlalchemy.orm import Session
from starlette.websockets import WebSocketDisconnect
from api.user import get_current_user, get_current_user_from_parameter
from db.database import SessionLocal
from models import ChatRoom, Membership, User, Message

router = APIRouter()

broadcast = Broadcast("redis://localhost:6379")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class MessageEvent(BaseModel):
    user_id: int
    message: str
    file_url: AnyHttpUrl = None


async def receive_message(websocket: WebSocket, room_id: int):
    async with broadcast.subscribe(channel=str(room_id)) as subscriber:
        async for event in subscriber:
            message_event = MessageEvent.model_validate_json(event.message)
            await websocket.send_json(message_event.model_dump_json())


def save_message_to_database(db: Session, message_event: MessageEvent, room_id: int):
    message = Message(user_id=message_event.user_id, content=message_event.message, room_id=room_id)
    db.add(message)
    db.commit()


async def send_message(websocket: WebSocket,
                       user_id: int,
                       room_id: int,
                       message: Union[str, bytes],
                       db: Session,
                       file_url: AnyHttpUrl = None,
                       ):
    data = await websocket.receive_text()
    event = MessageEvent(user_id=user_id, message=message, file_url=file_url)
    save_message_to_database(db, event, room_id)
    await broadcast.publish(channel=str(room_id), message=event.model_dump_json())


@router.websocket("/ws/{room_id}/{user_id}")
async def chat_ws(
    websocket: WebSocket,
    room_id: int,
    user_id: int,
    db: Session = Depends(get_db),
):

    # WebSocket 연결 허용
    await websocket.accept()

    try:
        while True:
            # 채팅 메시지 수신
            receive_message_task = asyncio.create_task(
                receive_message(websocket, room_id)
            )

            send_message_task = asyncio.create_task(
                send_message(websocket, user_id, room_id, await websocket.receive_bytes(), db)
            )

            done, pending = await asyncio.wait(
                {receive_message_task, send_message_task},
                return_when=asyncio.FIRST_COMPLETED,
            )

            for task in pending:
                task.cancel()

            for task in done:
                task.result()
    except WebSocketDisconnect:
        await websocket.close()


@router.on_event("startup")
async def startup():
    await broadcast.connect()


@router.on_event("shutdown")
async def shutdown():
    await broadcast.disconnect()