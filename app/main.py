from app import app
from app.api import users, recommend
from app.services import match_request_consumer, user_crud_consumer
import asyncio

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(match_request_consumer.consume_from_match_request_queue())
    asyncio.create_task(user_crud_consumer.consume_user_crud_request_queue())

@app.get("/")
async def read_root():
    return {"message": "Hello World"}

# 라우터 등록
app.include_router(users.router)
app.include_router(recommend.router)