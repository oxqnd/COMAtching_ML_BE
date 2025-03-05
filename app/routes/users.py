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

# 공통 유틸 함수
def read_csv_data(file_path):
    """CSV 파일 읽기"""
    if not os.path.exists(file_path):
        raise FileNotFoundError("CSV file not found")
    try:
        # 4번째 행부터 읽기
        df = pd.read_csv(file_path, skiprows=3)
        return df
    except Exception as e:
        raise Exception(f"Error reading CSV file: {str(e)}")

def write_csv_data(file_path, df, header_rows=None):
    """CSV 파일 쓰기"""
    try:
        # header_rows가 있는 경우 추가
        if header_rows:
            with open(file_path, mode='w', newline='', encoding='utf-8') as file:
                for row in header_rows:
                    file.write(",".join(row) + "\n")
        # 데이터프레임 저장
        df.to_csv(file_path, mode='a', index=False, encoding='utf-8')
    except Exception as e:
        raise Exception(f"Error writing CSV file: {str(e)}")

@router.post("/users")
async def create_user(user: dict):
    try:
        props = user.get('props')
        if not props or not props.get('reply_to') or not props.get('correlation_id'):
            return JSONResponse(content={"error": "Missing properties (reply_to or correlation_id)"}, status_code=400)

        response_content = {}
        # 필수 필드 확인
        required_fields = ["type", "uuid", "age", "contactFrequency", "gender", "hobby", "major", "mbti", "duplication"]
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
            # 파일이 없으면 새 데이터프레임 생성
            df = pd.DataFrame(columns=required_fields)

        # 새 데이터 추가
        df = pd.concat([df, pd.DataFrame([user_data_to_save])], ignore_index=True)

        # CSV 파일 쓰기
        write_csv_data(csv_file_path, df)

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

        required_fields = ["type", "uuid", "age", "contactFrequency", "gender", "hobby", "major", "mbti", "duplication"]
        ## 에러 처리 예시
        for field in required_fields:
            if field not in user:
                response_content = {"stateCode": "CRUD-001", "message": "Field Missing", "requestType": "UPDATE", "userId": user["uuid"]}
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")

        csv_file_path = CSV_FILE_PATH

        # type 필드를 제거한 후 나머지 필드만 저장
        user_data_to_save = {k: v for k, v in user.items() if k not in ["type", "props"]}
        user_data_to_save.update({"duplication": "FALSE", "": ""})

        if not os.path.exists(CSV_FILE_PATH):
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

        # 데이터 업데이트
        df.loc[df["uuid"] == user["uuid"], df.columns] = list(user_data_to_save.values())

        # CSV 파일 쓰기
        write_csv_data(csv_file_path, df)

        # 동작 성공 시 응답 생성
        response_content = {"stateCode": "GEN-000", "message": "Success", "requestType": "UPDATE", "userId": user["uuid"]}

        await send_to_queue(None, props, response_content)
        return JSONResponse(content=response_content, status_code=201)

    except HTTPException as e:
        if not response_content:
            response_content = {"stateCode": "GEN-001", "message": f"An error occurred: {str(e.detail)}", "requestType": "UPDATE", "userId": user["uuid"]}
        await send_to_queue(None, props, response_content)
        return JSONResponse(content={"error": str(e.detail)}, status_code=e.status_code)
    except Exception as e:
        if not response_content:
            response_content = {
                "stateCode": "GEN-001",
                "message": f"An error occurred: {str(e)}",
                "requestType": "UPDATE",
                "userId": user["uuid"],
            }
        await send_to_queue(None, props, response_content)
        return JSONResponse(content=response_content, status_code=500)


@router.delete("/users")
async def delete_user(user: dict):
    try:
        props = user.get('props')
        if not props or not props.get('reply_to') or not props.get('correlation_id'):
            return JSONResponse(content={"error": "Missing properties (reply_to or correlation_id)"}, status_code=400)

        response_content = {}

        required_fields = ["type", "uuid", "age", "contactFrequency", "gender", "hobby", "major", "mbti", "duplication"]
        ## 에러 처리 예시
        for field in required_fields:
            if field not in user:
                response_content = {"stateCode": "CRUD-001", "message": "Field Missing", "requestType": "UPDATE", "userId": user["uuid"]}
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")

        csv_file_path = CSV_FILE_PATH

        if not os.path.exists(csv_file_path):
            response_content = {
                "stateCode": "GEN-001",
                "message": "File open fail",
                "requestType": "DELETE",
                "userId": user["uuid"],
            }
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

        # UUID가 일치하지 않는 데이터만 남기기
        df = df[df["uuid"] != user["uuid"]]

        # CSV 파일 쓰기
        write_csv_data(csv_file_path, df)

        # 동작 성공 시 응답 생성
        response_content = {"stateCode": "GEN-000", "message": "Success", "requestType": "DELETE", "userId": user["uuid"]}

        await send_to_queue(None, props, response_content)

        return JSONResponse(response_content, status_code=201)
    except HTTPException as e:
        if not response_content:
            response_content = {"stateCode": "GEN-001", "message": f"An error occurred: {str(e.detail)}", "requestType": "DELETE", "userId": user["uuid"]}
        await send_to_queue(None, props, response_content)
        return JSONResponse(content={"error": str(e.detail)}, status_code=e.status_code)
    except Exception as e:
        if not response_content:
            response_content = {
                "stateCode": "GEN-001",
                "message": f"An error occurred: {str(e)}",
                "requestType": "DELETE",
                "userId": user["uuid"],
            }
        await send_to_queue(None, props, response_content)
        return JSONResponse(content=response_content, status_code=500)
