from passlib.context import CryptContext
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(255), unique=True, index=True)
    password_hash = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    # is_active, email, phone_number 설정 가능

    # websocket 통신을 위한 지역 변수
    websocket = None

    memberships = relationship("Membership", back_populates="user")
    messages = relationship("Message", back_populates="user")

    # hash 함수를 이용해서 password를 암호화
    def set_password(self, password: str):
        self.password_hash = pwd_context.hash(password)

    # hash 값을 복호화해서 기존의 비밀번호와 비교하여 검증
    def verify_password(self, plain_password):
        return pwd_context.verify(plain_password, self.password_hash)


class ChatRoom(Base):
    __tablename__ = "chat_rooms"

    id = Column(Integer, primary_key=True, index=True)
    room_name = Column(String(255), index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    memberships = relationship("Membership", back_populates="room")
    messages = relationship("Message", back_populates="room")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, ForeignKey("chat_rooms.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    content = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="messages")
    room = relationship("ChatRoom", back_populates="messages")


class Membership(Base):
    __tablename__ = "memberships"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    room_id = Column(Integer, ForeignKey("chat_rooms.id"))

    user = relationship("User", back_populates="memberships")
    room = relationship("ChatRoom", back_populates="memberships")