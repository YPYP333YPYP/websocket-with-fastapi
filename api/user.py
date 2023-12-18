from fastapi import APIRouter, Depends, HTTPException, status, Header, Query
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
    phone_number: str


class UserUpdate(BaseModel):
    email: str
    profile_picture: str
    status_message: str


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


async def get_current_user_from_parameter(
        token: str = Query(..., description="User access token passed in the WebSocket URL."),
        db: Session = Depends(get_db)
):
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
    user = User(username=user_data.username, phone_number=user_data.phone_number)
    user.set_password(user_data.password)  # 비밀번호 해시화
    db.add(user)
    db.commit()
    db.refresh(user)

    return {"user_id": user.id, "username": user.username}


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


# 특정 사용자 정보 가져오기
@router.get("/{user_id}")
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        return user.get_profile_info()
    else:
        raise HTTPException(status_code=404, detail="User not found")


# 유저 프로필 추가 정보 수정
@router.put("/update_profile/{user_id}")
def update_user_profile(user_id: int, user_data: UserUpdate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    user.email = user_data.email
    user.profile_picture = user_data.profile_picture
    user.status_message = user_data.status_message
    db.commit()
    db.refresh(user)

    return {"user_id": user.id, "username": user.username}


# 유저 비활성화
@router.get("/deactivate/{user_id}")
def deactivate_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = False
    user.inactive_date = datetime.utcnow()
    db.commit()
    db.refresh(user)

    return f'{user.username} deactivate account'

