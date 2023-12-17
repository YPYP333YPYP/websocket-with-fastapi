from fastapi import APIRouter, Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.orm import Session
import jwt
from datetime import datetime, timedelta

from models import User
from db.databast import SessionLocal

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


SECRET_KEY = "5e70bbb815042f7327bd27794af546b0"
ALGORITHM = "HS256"


class UserLogin(BaseModel):
    username: str
    password: str


class UserCreate(BaseModel):
    username: str
    password: str


def create_access_token(user_data: dict, expires_delta: timedelta = None):
    to_encode = user_data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(token: str = Header(...), db: Session = Depends(get_db)):
    print(f"Received token: {token}")  # 디버깅을 위해 추가

    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except jwt.InvalidTokenError:
        raise credentials_exception
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    return user


@router.post("/signup")
def create_user(user_data: UserCreate, db: Session = Depends(get_db)):
    # 사용자 생성 로직
    db_user = User(username=user_data.username)
    db_user.set_password(user_data.password)  # 비밀번호 해시화
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return {"user_id": db_user.id, "username": db_user.username}


@router.post("/login")
def login(user_data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == user_data.username).first()

    if user and user.verify_password(user_data.password):
        access_token_expires = timedelta(minutes=15)
        access_token = create_access_token({"sub": user.username}, expires_delta=access_token_expires)
        return {"access_token": access_token, "token_type": "bearer"}
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.get("/{user_id}")
def get_user(user_id: int, db: Session = Depends(get_db)):
    # 특정 사용자 정보 가져오기
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        return {"user_id": user.id, "username": user.username}
    else:
        raise HTTPException(status_code=404, detail="User not found")


