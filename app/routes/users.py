from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
import os
import csv
import subprocess
import pandas as pd
import json
from app.config import CSV_FILE_PATH
from app.utils.helpers import send_to_queue

router = APIRouter()

def read_csv_data(file_path):
    """CSV 파일 읽기"""
    if not os.path.exists(file_path):
        raise FileNotFoundError("CSV file not found")
    try:
        df = pd.read_csv(file_path, skiprows=2)
        return df
    except Exception as e:
        raise Exception(f"Error reading CSV file: {str(e)}")

def append_csv_data(file_path, new_data):
    """CSV 파일에 마지막 행만 추가"""
    try:
        file_exists = os.path.exists(file_path)

        with open(file_path, mode='a', newline='', encoding='utf-8') as file:
            new_data.to_csv(file, header=not file_exists, index=False, encoding='utf-8')
    except Exception as e:
        raise Exception(f"Error writing CSV file: {str(e)}")

def write_csv_data(file_path, updated_data=None, delete_uuid=None):
    try:
        if not os.path.exists(file_path):
            raise FileNotFoundError("CSV file not found")

        with open(file_path, mode="r", newline="", encoding="utf-8") as file:
            reader = list(csv.reader(file))
            header_rows = reader[:2]
            data_rows = reader[2:]  # 3번째 행부터 수정 또는 삭제

        updated_rows = []
        for row in data_rows:
            uuid_value = row[0]
            if delete_uuid and row[0] == delete_uuid:
                continue

            if updated_data and row[0] in updated_data:
                row = [updated_data[uuid_value].get(key, row[i]) for i, key in enumerate(updated_data[uuid_value].keys())]

            updated_rows.append(row)

        with open(file_path, mode="w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerows(header_rows)
            writer.writerows(updated_rows)

    except Exception as e:
        raise Exception(f"Error updating CSV file: {str(e)}")

@router.post("/users")
async def create_user(user: dict):
    try:
        props = user.get('props')
        if not props or not props.get('reply_to') or not props.get('correlation_id'):
            return JSONResponse(content={"error": "Missing properties (reply_to or correlation_id)"}, status_code=400)

        response_content = {}
        # 필수 필드 확인
        required_fields = ["type", "uuid", "age", "contactFrequency", "gender", "hobby", "major", "mbti"]
        for field in required_fields:
            if field not in user:
                response_content = {"stateCode": "CRUD-001", "message": "Field Missing", "requestType": "CREATE", "userId": user["uuid"]}
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")

        csv_file_path = CSV_FILE_PATH

        # type 필드를 제거한 후 나머지 필드만 저장
        user_data_to_save = {k: v for k, v in user.items() if k not in ["type", "props"]}
        user_data_to_save.update({"duplication": "FALSE", "": ""})

        if os.path.exists(csv_file_path):
                df = read_csv_data(csv_file_path)
                # 중복된 UUID 확인
                if user["uuid"] in df["uuid"].values:
                    response_content = {"stateCode": "CRUD-004", "message": "User Already Exists"}
                    raise HTTPException(status_code=400, detail=f"User Already Exists")
        else:
            response_content = {"stateCode": "GEN-001", "message": "File not found"}
            raise FileNotFoundError("CSV file not found")

        new_data = pd.DataFrame([user_data_to_save])
        append_csv_data(csv_file_path, new_data)

        # 성공 응답
        response_content = {"stateCode": "CRUD-000", "message": "CRUD Success"}
        await send_to_queue(None, props, response_content)
        return JSONResponse(content=response_content, status_code=201)

    except Exception as e:
        if not response_content:
            response_content = {"stateCode": "CRUD-005", "message": f"Error processing user: {str(e)}"}
        await send_to_queue(None, props, response_content)
        return JSONResponse(content=response_content, status_code=500)

@router.put("/users")
async def update_user(user: dict):
    try:
        props = user.get('props')
        if not props or not props.get('reply_to') or not props.get('correlation_id'):
            return JSONResponse(content={"error": "Missing properties (reply_to or correlation_id)"}, status_code=400)

        response_content = {}

        required_fields = ["type", "uuid", "age", "contactFrequency", "gender", "hobby", "major", "mbti"]
        for field in required_fields:
            if field not in user:
                response_content = {"stateCode": "CRUD-001", "message": "Field Missing", "requestType": "UPDATE", "userId": user["uuid"]}
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")

        user["duplication"] = "FALSE"
        csv_file_path = CSV_FILE_PATH

        if not os.path.exists(csv_file_path):
            response_content = {"stateCode": "GEN-001", "message": "File open fail", "requestType": "UPDATE", "userId": user["uuid"]}
            raise FileNotFoundError("CSV file not found")

        # CSV 파일 읽기
        df = read_csv_data(csv_file_path)

        # UUID를 기준으로 데이터 찾기
        if user["uuid"] not in df["uuid"].values:
            response_content = {
                "stateCode": "CRUD-003",
                "message": "Unmatched User",
                "requestType": "UPDATE",
                "userId": user["uuid"],
            }
            raise HTTPException(status_code=404, detail="User not found")

        # 업데이트할 데이터 준비
        updated_data = {user["uuid"]: {k: v for k, v in user.items() if k not in ["type", "props"]}}
        print("updated_data", updated_data)

        write_csv_data(csv_file_path, updated_data)

        # 성공 응답
        response_content = {"stateCode": "GEN-000", "message": "Success", "requestType": "UPDATE", "userId": user["uuid"]}
        await send_to_queue(None, props, response_content)
        return JSONResponse(content=response_content, status_code=201)

    except Exception as e:
        response_content = {"stateCode": "GEN-001", "message": f"An error occurred: {str(e)}", "requestType": "UPDATE", "userId": user["uuid"]}
        await send_to_queue(None, props, response_content)
        return JSONResponse(content=response_content, status_code=500)

@router.delete("/users")
async def delete_user(user: dict):
    try:
        props = user.get('props')
        if not props or not props.get('reply_to') or not props.get('correlation_id'):
            return JSONResponse(content={"error": "Missing properties (reply_to or correlation_id)"}, status_code=400)

        response_content = {}

        csv_file_path = CSV_FILE_PATH

        if not os.path.exists(csv_file_path):
            response_content = {"stateCode": "GEN-001", "message": "File open fail", "requestType": "DELETE", "userId": user["uuid"]}
            raise HTTPException(status_code=404, detail="CSV file not found")

        df = read_csv_data(csv_file_path)

        # UUID를 기준으로 데이터 필터링
        if user["uuid"] not in df["uuid"].values:
            response_content = {
                "stateCode": "CRUD-003",
                "message": "Unmatched User",
                "requestType": "DELETE",
                "userId": user["uuid"],
            }
            raise HTTPException(status_code=404, detail="User not found")

        # CSV 파일 업데이트 실행 (삭제된 행 반영)
        write_csv_data(csv_file_path, delete_uuid=user["uuid"])

        # 성공 응답
        response_content = {"stateCode": "GEN-000", "message": "Success", "requestType": "DELETE", "userId": user["uuid"]}
        await send_to_queue(None, props, response_content)
        return JSONResponse(content=response_content, status_code=201)

    except Exception as e:
        response_content = {"stateCode": "GEN-001", "message": f"An error occurred: {str(e)}", "requestType": "DELETE", "userId": user["uuid"]}
        await send_to_queue(None, props, response_content)
        return JSONResponse(content=response_content, status_code=500)
