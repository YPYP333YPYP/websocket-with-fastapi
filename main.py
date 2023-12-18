from api.user import router as user_router
from api.chat import router as chat_router
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

# logging 옵션
# logging.basicConfig(level=logging.DEBUG)

app = FastAPI()

app.include_router(chat_router, prefix="/chat", tags=["chat"])
app.include_router(user_router, prefix="/user", tags=["user"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8001)