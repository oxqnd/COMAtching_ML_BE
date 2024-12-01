from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
import subprocess
import time
import pandas as pd
from app.config import CSV_FILE_PATH, ML_FILE_PATH
from app.utils.helpers import send_to_queue

user_router = APIRouter()

csv_file_path = CSV_FILE_PATH

@user_router.get("/users")
async def get_users():
    try:
        users = read_users_from_csv(csv_file_path)
        return JSONResponse(content=users, status_code=200)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@user_router.post("/users")
async def create_user(user: dict):
    try:
        write_user_to_csv(csv_file_path, user)
        message_data = {"requestType": "CREATE", "userId": user["uuid"]}
        await send_to_crud_queue(message_data)
        return JSONResponse(message_data, status_code=201)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@user_router.put("/users")
async def update_user(user: dict):
    try:
        update_user_in_csv(csv_file_path, user)
        message_data = {"requestType": "UPDATE", "userId": user["uuid"]}
        await send_to_crud_queue(message_data)
        return JSONResponse(content=message_data, status_code=201)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@user_router.delete("/users")
async def delete_user(user: dict):
    try:
        delete_user_from_csv(csv_file_path, user["uuid"])
        message_data = {"requestType": "DELETE", "userId": user["uuid"]}
        await send_to_crud_queue(message_data)
        return JSONResponse(content=message_data, status_code=201)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
