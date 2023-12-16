from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
import jwt
from datetime import datetime, timedelta

from models import User
from db.databast import SessionLocal

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


SECRET_KEY = "5e70bbb815042f7327bd27794af546b0"
ALGORITHM = "HS256"


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


@router.post("/signup")
def create_user(username: str, password: str, db: Session = Depends(get_db)):
    # 사용자 생성 로직
    db_user = User(username=username)
    db_user.set_password(password)  # 비밀번호 해시화
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return {"user_id": db_user.id, "username": db_user.username}


@router.post("/login")
def login(username: str, password: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()

    if user and user.verify_password(password):
        # Generate JWT token
        access_token_expires = timedelta(minutes=15)
        access_token = create_access_token(data={"sub": user.username}, expires_delta=access_token_expires)
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


