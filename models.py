from pathlib import Path
from passlib.context import CryptContext
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from sqlalchemy import TEXT
import random
import string

Base = declarative_base()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

"""
alembic revision --autogenerate -m "Messages"
alembic upgrade head
alembic downgrade -1
"""


class User(Base):
    __tablename__ = "users"

    # 필수 정보
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(255), unique=True, index=True)
    password_hash = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    phone_number = Column(String(20), unique=True, index=True)

    # 추가 정보
    profile_picture = Column(String(255), default="default_profile.jpg")
    status_message = Column(String(255), default="")
    email = Column(String(255), unique=True, index=True, nullable=True)
    is_active = Column(Boolean, default=True)
    inactive_date = Column(DateTime(timezone=True), nullable=True)

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

    # 유저 정보 가져오기
    def get_profile_info(self):
        return {
            "username": self.username,
            "profile_picture": self.profile_picture,
            "status_message": self.status_message,
            "email": self.email,
            "phone_number": self.phone_number,
            "is_active": self.is_active,
            "inactive_date": self.inactive_date
        }

    # profile 업데이트
    def update_profile(self, profile_picture=None, status_message=None, email=None):
        if profile_picture:
            # 현재는 로컬 환경에 저장
            self.profile_picture = self.save_profile_picture_to_local(profile_picture)
        if status_message:
            self.status_message = status_message
        if email:
            self.email = email

    # local 저장 시
    @staticmethod
    def save_profile_picture_to_local(profile_picture):
        # 로컬에 이미지 저장
        upload_folder = Path("Images")
        upload_folder.mkdir(parents=True, exist_ok=True)
        filename = profile_picture.filename
        filepath = upload_folder / filename

        with open(filepath, "wb") as file:
            file.write(profile_picture.file.read())

        return str(filepath)

    # # AWS S3 저장 시
    # def save_profile_picture_to_s3(self, s3_bucket, s):
    #     return None


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    category_name = Column(String(50), index=True)
    chat_rooms = relationship("ChatRoom", back_populates="category")


class ChatRoom(Base):
    __tablename__ = "chat_rooms"

    id = Column(Integer, primary_key=True, index=True)
    room_name = Column(String(255), index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_private = Column(Boolean, default=False)
    hashtags = relationship("Hashtag", back_populates="room", cascade="all, delete-orphan")
    category_id = Column(Integer, ForeignKey("categories.id"))
    category = relationship("Category", back_populates="chat_rooms")
    memberships = relationship("Membership", back_populates="room")
    messages = relationship("Message", back_populates="room")
    auth_code = Column(String(20), unique=True)

    def generate_auth_code(self):
        characters = string.ascii_uppercase + string.digits
        auth_code = ''.join(random.choice(characters) for _ in range(4))
        self.auth_code = auth_code


class Hashtag(Base):
    __tablename__ = "hashtags"

    id = Column(Integer, primary_key=True, index=True)
    tag_name = Column(String(50), index=True)
    room_id = Column(Integer, ForeignKey("chat_rooms.id"))
    room = relationship("ChatRoom", back_populates="hashtags")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, ForeignKey("chat_rooms.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    content = Column(TEXT)
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