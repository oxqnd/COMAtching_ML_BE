from fastapi import APIRouter, Request
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
        # 필수 필드 확인
        required_fields = ["type", "uuid", "age", "contactFrequency", "gender", "hobby", "major", "mbti"]
        for field in required_fields:
            if field not in user:
                response_content = {"errorCode": "CRUD-001", "errorMessage": "Field Missing", "requestType": "CREATE", "userId": user["uuid"]}
                await send_to_queue(None, props, response_content)
                return JSONResponse(content=response_content, status_code=400)
                #raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
        
        csv_file_path = CSV_FILE_PATH
        props = user.get('props')

        # type 필드를 제거한 후 나머지 필드만 저장
        user_data_to_save = {k: v for k, v in user.items() if k not in ["type", "hobbyAsList", "props"]}
        user_data_to_save.update({"duplication": "FALSE", "": ""})

        if os.path.exists(csv_file_path):
                df = read_csv_data(csv_file_path)
                # 중복된 UUID 확인
                if user["uuid"] in df["uuid"].values:
                    response_content = {"stateCode": "CRUD-004", "message": "User Already Exists"}
                    await send_to_queue(None, props, response_content)
                    return JSONResponse(content=response_content, status_code=400)
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
        response_content = {"stateCode": "CRUD-005", "message": f"Error processing user: {str(e)}"}
        return JSONResponse(content=response_content, status_code=500)

@router.put("/users")
async def update_user(user: dict):
    # props가 데이터에 포함되어 있는지 확인
    props = user.get('props')
    if not props or not props.get('reply_to') or not props.get('correlation_id'):
        return JSONResponse(content={"error": "Missing properties (reply_to or correlation_id)"}, status_code=400)
    
    required_fields = ["type", "uuid", "age", "contactFrequency", "gender", "hobby", "major", "mbti"]
    ## 에러 처리 예시
    for field in required_fields:
        if field not in user:
            response_content = {"errorCode": "CRUD-001", "errorMessage": "Field Missing", "requestType": "UPDATE", "userId": user["uuid"]}
            #response_content.update(user)
            
            await send_to_queue(None, props, response_content)
            return JSONResponse(content=response_content, status_code=400)
        else:
            if user["type"] != "UPDATE":
                response_content = {"error": "CRUD-002", "errorMessage": "Wrong Method", "requestType": "UPDATE", "userId": user["uuid"]}
                #response_content.update(user)
                
                await send_to_queue(None, props, response_content)
                return JSONResponse(content=response_content, status_code=400)
    
    if not os.path.exists(CSV_FILE_PATH):
        response_content = {"errorCode": "GEN-001", "errorMessage": "File open fail", "requestType": "UPDATE", "userId": user["uuid"]}
        #response_content.update(user)
                
        await send_to_queue(None, props, response_content)
        raise HTTPException(status_code=404, detail="File not found")
    
    users = []
    updated = False
    fieldnames = []

    try:
        with open(CSV_FILE_PATH, mode='r', newline='', encoding='utf-8') as file:
            reader = csv.reader(file)
            first_row = next(reader)
            second_row = next(reader)
            fieldnames = next(reader)

            reader = csv.DictReader(file, fieldnames=fieldnames)
            for row in reader:
                if row["uuid"] == user["uuid"]:
                    row.update(user)
                    updated = True
                users.append(row)
                
    except AssertionError as e:
        response_content = {"errorCode": "GEN-002", "errorMessage": "assert fail", "requestType": "UPDATE", "userId": user["uuid"]}
        #response_content.update(user)
        
        await send_to_queue(None, props, response_content)
        return JSONResponse(content=response_content, status_code=500)

    except Exception as e:
        response_content = {"errorCode": "GEN-001", "errorMessage": "File open fail", "requestType": "UPDATE", "userId": user["uuid"]}
        #response_content.update(user)
                
        await send_to_queue(None, props, response_content)
        return JSONResponse(content={"error": str(e)}, status_code=500)
    
    if not updated:
        response_content = {"errorCode": "CRUD-003", "errorMessage": "Unmatched User", "requestType": "UPDATE", "userId": user["uuid"]}
        #response_content.update(user)
                
        await send_to_queue(None, props, response_content)
        return JSONResponse(content=response_content, status_code=404)

    try:
        with open(CSV_FILE_PATH, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(first_row)
            writer.writerow(second_row)
            writer.writerow(fieldnames)
            for user_row in users:
                writer.writerow([user_row.get(fieldname, '') for fieldname in fieldnames])
    
    except Exception as e:
        response_content = {"errorCode": "GEN-003", "errorMessage": "File close fail", "requestType": "UPDATE", "userId": user["uuid"]}
        #response_content.update(user)
                
        await send_to_queue(None, props, response_content)
        return JSONResponse(content={"error": str(e)}, status_code=500)
    
    # 동작 성공 시 응답 생성
    response_content = {"errorCode": "GEN-000", "errorMessage": "Success", "requestType": "UPDATE", "userId": user["uuid"]}

    await send_to_queue(None, props, response_content)
    return JSONResponse(content=response_content, status_code=201)

@router.delete("/users")
async def delete_user(user: dict):
    props = user.get('props')
    if not props or not props.get('reply_to') or not props.get('correlation_id'):
        return JSONResponse(content={"error": "Missing properties (reply_to or correlation_id)"}, status_code=400)
    
    # 필수 필드 확인
    required_fields = ["type", "uuid", "age", "contactFrequency", "gender", "hobby", "major", "mbti"]
    for field in required_fields:
        if field not in user:
            response_content = {"errorCode": "CRUD-001", "errorMessage": "Field Missing", "requestType": "DELETE", "userId": user["uuid"]}
            #response_content.update(user)
                    
            await send_to_queue(None, props, response_content)
            return JSONResponse(content=response_content, status_code=400)

    # type 필드가 "DELETE"인지 확인
    if user["type"] != "DELETE":
        response_content = {"errorCode": "CRUD-002", "errorMessage": "Wrong Method", "requestType": "DELETE", "userId": user["uuid"]}
        #response_content.update(user)
                
        await send_to_queue(None, props, response_content)
        return JSONResponse(content=response_content, status_code=400)
    
    # CSV 파일이 존재하는 경우, uuid가 일치하는 row를 삭제
    if os.path.exists(CSV_FILE_PATH):
        try:
            users = []
            row_deleted = False
            with open(CSV_FILE_PATH, mode='r', newline='', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                fieldnames = reader.fieldnames  # 기존 필드명 저장
                # 4번째 행부터 조회
                for index, row in enumerate(reader, start=1):
                    if index < 3 or row["matcherUuid"] != user["uuid"]:
                        users.append(row)  # 삭제할 row가 아닌 경우 저장
                    else:
                        row_deleted = True  # 일치하는 row가 있음을 표시

            if not row_deleted:
                response_content = {"errorCode": "CRUD-003", "errorMessage": "Unmatched User", "requestType": "DELETE", "userId": user["uuid"]}
                #response_content.update(user)
                        
                await send_to_queue(None, props, response_content)
                return JSONResponse(content=response_content, status_code=404)
            
            # 변경된 데이터를 CSV 파일에 다시 저장
            with open(CSV_FILE_PATH, mode='w', newline='', encoding='utf-8') as file:
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(users)
        except AssertionError as e:
            response_content = {"errorCode": "GEN-002", "errorMessage": "assert fail", "requestType": "DELETE", "userId": user["uuid"]}
           #response_content.update(user)
            await send_to_queue(None, props, response_content)
            return JSONResponse(content=response_content, status_code=500)
        
        except Exception as e:
            response_content = {"errorCode": "GEN-001", "errorMessage": "File open fail", "requestType": "DELETE", "userId": user["uuid"]}
            #response_content.update(user)
                    
            await send_to_queue(None, props, response_content)
            return JSONResponse(content={"error": str(e)}, status_code=500)
    
    else:
        response_content = {"errorCode": "GEN-001", "errorMessage": "File open fail", "requestType": "DELETE", "userId": user["uuid"]}
        #response_content.update(user)
                
        await send_to_queue(None, props, response_content)
        raise HTTPException(status_code=404, detail="CSV file not found.")
    
    # 동작 성공 시 응답 생성
    response_content = {"errorCode": "GEN-000", "errorMessage": "Success", "requestType": "DELETE", "userId": user["uuid"]}

    await send_to_queue(None, props, response_content)
    
    return JSONResponse(response_content, status_code=201)