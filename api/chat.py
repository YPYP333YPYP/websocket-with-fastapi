import asyncio
import logging

from broadcaster import Broadcast
from fastapi import APIRouter, HTTPException, WebSocket, Depends, status, Query, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session
from starlette.websockets import WebSocketDisconnect
from api.user import get_current_user, get_current_user_from_parameter
from db.database import SessionLocal
from models import ChatRoom, Membership, User, Message

router = APIRouter()

broadcast = Broadcast("redis://localhost:6379")
CHANNEL = "CHAT"


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class MessageEvent(BaseModel):
    user_id: int
    message: str


async def receive_message(websocket: WebSocket):
    async with broadcast.subscribe(channel=CHANNEL) as subscriber:
        async for event in subscriber:
            message_event = MessageEvent.model_validate_json(event.message)
            await websocket.send_json(message_event.model_dump_json())


async def send_message(websocket: WebSocket, user_id: int):
    data = await websocket.receive_text()
    event = MessageEvent(user_id=user_id, message=data)
    await broadcast.publish(channel=CHANNEL, message=event.model_dump_json())
    return event


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
                receive_message(websocket)
            )

            data = send_message(websocket, user_id)
            print(data)

            send_message_task = asyncio.create_task(send_message(websocket, user_id))
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