from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
import os
import csv
import subprocess
import json
from app.config import CSV_FILE_PATH
from app.utils.helpers import send_to_queue

router = APIRouter()

@router.post("/recommend")
async def recommend_user(request: Request):
    data = await request.json()

    # 필수 필드 확인
    required_fields = ["matcherUuid", "contactFrequencyOption", "myGender", "hobbyOption", 
                       "sameMajorOption", "ageOption", "mbtiOption", "myMajor", "myAge", "duplicationList"]
    for field in required_fields:
        if field not in data:
            response_content = {"errorCode": "CRUD-001", "errorMessage": "Field Missing"}
            response_content.update(data)
            await send_to_queue(None, props, response_content)
            return JSONResponse(content=response_content, status_code=400)
    
    # props가 데이터에 포함되어 있는지 확인
    props = data.get('props')

    # 만약 props에 reply_to나 correlation_id가 없으면 오류 반환
    if not props or not props.get('reply_to') or not props.get('correlation_id'):
        return JSONResponse(content={"error": "Missing properties (reply_to or correlation_id)"}, status_code=400)
    
    # CSV 파일의 첫 번째 행 수정
    users = []
    updated = False
    try:
        with open(CSV_FILE_PATH, mode='r', newline='', encoding='utf-8') as file:
            reader = csv.reader(file)
            rows = list(reader)
            
            if rows:
                rows[1][0] = data['matcherUuid']
                rows[1][1] = data['contactFrequencyOption']
                rows[1][2] = data['myGender']
                rows[1][3] = data['hobbyOption']
                rows[1][4] = 'TRUE' if data['sameMajorOption'] else 'FALSE'
                rows[1][5] = data['ageOption']
                rows[1][6] = data['mbtiOption']
                rows[1][7] = data['myMajor']
                rows[1][8] = data['myAge']
                rows[1][9] = data['duplicationList']
                updated = True

            users = rows

        if updated:
            try:
                # 수정된 내용을 CSV 파일에 저장
                with open(CSV_FILE_PATH, mode='w', newline='', encoding='utf-8') as file:
                    writer = csv.writer(file)
                    writer.writerows(rows)
            except Exception as e:
                response_content = {"errorCode": "GEN-003", "errorMessage": "File close fail"}
                response_content.update(data)
                await send_to_queue(None, props, response_content)
                return JSONResponse(content=response_content, status_code=500)
        else:
            response_content = {"errorCode": "GEN-004", "errorMessage": "User not found in CSV file"}
            response_content.update(data)
            await send_to_queue(None, props, response_content)
            return JSONResponse(content=response_content, status_code=404)

    except Exception as e:
        response_content = {"errorCode": "GEN-001", "errorMessage": "File open fail"}
        response_content.update(data)
        await send_to_queue(None, props, response_content)
        return JSONResponse(content=response_content, status_code=500)

    # ./new/run.py 파일 실행
    try:
        result = subprocess.run(['python', '/home/ads_lj/comatching/v6/main8.py'], capture_output=True, text=True)
        if result.returncode != 0:
            response_content = {"error": "GEN-002", "message": "Error running main7.py", "details": result.stderr}
            response_content.update(data)
            await send_to_queue(None, props, response_content)
            return JSONResponse(content=response_content, status_code=500)

        recommended_candidate = result.stdout.strip()

        if 'Recommended Candidate Information:' in recommended_candidate:
            start_index = recommended_candidate.find('Recommended Candidate Information:') + len('Recommended Candidate Information')
            recommended_user_data = recommended_candidate[start_index:].strip()
            
            lines = recommended_user_data.split('\n')
            user_info = {}
            for line in lines:
                if line.strip():
                    key_value = line.split(maxsplit=1)
                    if len(key_value) == 2:
                        key, value = key_value
                        user_info[key.strip()] = value.strip()

            user_index = user_info.get('uuid')
            if user_index:
                recommended_user = {"enemyUuid": user_index}

            else:
                recommended_user = {}

        else:
            response_content = {"errorCode": "GEN-002", "errorMessage": "assert fail"}
            response_content.update(data)
            await send_to_queue(None, props, response_content)
            return JSONResponse(content=response_content, status_code=500)

    except Exception as e:
        response_content = {"errorCode": "GEN-002", "errorMessage": "assert fail"}
        response_content.update(data)
        await send_to_queue(None, props, response_content)
        return JSONResponse(content=response_content, status_code=500)
    
    # 추가
    response_content = {"errorCode": "GEN-000", "errorMessage": "Success"}
    # 수정
    response_content.update(recommended_user)
    await send_to_queue(None, props, response_content)
    
    return JSONResponse(content=response_content, status_code=200)