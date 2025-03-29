from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
import subprocess
import time
import pandas as pd
from app.config import CSV_FILE_PATH, ML_FILE_PATH
from app.utils.helpers import send_to_queue

router = APIRouter()

@router.post("/recommend")
async def recommend_user(request: Request):
    data = await request.json()
    csv_file_path = CSV_FILE_PATH
    ml_file_path = ML_FILE_PATH

    # props가 데이터에 포함되어 있는지 확인
    props = data.get('props')

    # 만약 props에 reply_to나 correlation_id가 없으면 오류 반환
    if not props or not props.get('reply_to') or not props.get('correlation_id'):
        response_content = {"stateCode": "MTCH-001", "message": "Field Missing"}
        await send_to_queue(None, props, response_content)
        return JSONResponse(content={"error": "Missing properties (reply_to or correlation_id)"}, status_code=400)

    # 필수 필드 확인
    required_fields = ["matcherUuid", "contactfrequencyOption", "genderOption", "hobbyOption",
                       "sameMajorOption", "ageOption", "mbtiOption", "myMajor", "myAge", "duplicationList"]
    for field in required_fields:
        if field not in data:
            response_content = {"stateCode": "MTCH-001", "message": "Field Missing"}
            await send_to_queue(None, props, response_content)
            return JSONResponse(content=response_content, status_code=400)

    # CSV 파일의 첫 번째 행 수정 및 처리
    try:
        df = pd.read_csv(csv_file_path, encoding='utf-8')
        if df.empty:
            response_content = {"stateCode": "MTCH-003", "message": "CSV file is empty"}
            await send_to_queue(None, props, response_content)
            return JSONResponse(content=response_content, status_code=404)

        # 데이터 업데이트 (첫 번째 행에 데이터를 반영)
        df.iloc[0, df.columns.get_loc('matcherUuid')] = data['matcherUuid']
        df.iloc[0, df.columns.get_loc('contactfrequencyOption')] = data['contactfrequencyOption']
        df.iloc[0, df.columns.get_loc('genderOption')] = data['genderOption']
        df.iloc[0, df.columns.get_loc('hobbyOption')] = data['hobbyOption']
        df.iloc[0, df.columns.get_loc('sameMajorOption')] = data['sameMajorOption']
        df.iloc[0, df.columns.get_loc('ageOption')] = data['ageOption']
        df.iloc[0, df.columns.get_loc('mbtiOption')] = data['mbtiOption']
        df.iloc[0, df.columns.get_loc('myMajor')] = data['myMajor']
        df.iloc[0, df.columns.get_loc('myAge')] = data['myAge']

        duplication_list = data.get('duplicationList', [])
        if duplication_list:
            df.iloc[df['matcherUuid'].isin(duplication_list), 'duplication'] = "TRUE"

        # 수정된 내용을 CSV 파일에 저장
        df.to_csv(csv_file_path, index=False, encoding='utf-8')

    except Exception as e:
        response_content = {"stateCode": "MTCH-004", "message": "File open fail"}
        await send_to_queue(None, props, response_content)
        response_content.update({"details": str(e)})
        return JSONResponse(content=response_content, status_code=500)

    # ./new/run.py 파일 실행
    try:
        result = subprocess.run(['python', ml_file_path], capture_output=True, text=True)
        if result.returncode != 0:

            response_content = {"stateCode": "MTCH-005", "message": "Error running model"}
            await send_to_queue(None, props, response_content)
            response_content.update({"details": str(e)})
            return JSONResponse(content=response_content, status_code=500)

        recommended_candidate = result.stdout.strip()

        if '===== Cosine Similarity 추천 결과 =====' in recommended_candidate:
            start_index = recommended_candidate.find('===== Cosine Similarity 추천 결과 =====') + len('===== Cosine Similarity 추천 결과 =====')
            recommended_user_data = recommended_candidate[start_index:].strip()

            lines = recommended_user_data.split('\n')
            user_info = {}
            for line in lines:
                line = line.strip()
                if not line or line.startswith('---'):
                    continue
                if 'uuid:' in line:
                    user_info['matcherUuid'] = line.split('uuid:')[1].strip()
                elif ':' in line:
                    key_value = line.split(':', 1)
                    if len(key_value) == 2:
                        key, value = key_value
                        user_info[key.strip()] = value.strip()

            user_index = user_info.get('matcherUuid')
            if user_index:
                recommended_user = {"enemyUuid": user_index}

            else:
                recommended_user = {}

        else:
            response_content = {"stateCode": "MTCH-006", "message": "Model return error"}
            await send_to_queue(None, props, response_content)
            response_content.update({"details": str(e)})
            return JSONResponse(content=response_content, status_code=500)

    except Exception as e:
        response_content = {"stateCode": "MTCH-005", "message": "Error running model"}
        await send_to_queue(None, props, response_content)
        response_content.update({"details": str(e)})
        return JSONResponse(content=response_content, status_code=500)

    # 추가
    response_content = {"stateCode": "MTCH-000", "message": "Success"}
    # 수정
    response_content.update(recommended_user)
    await send_to_queue(None, props, response_content)

    return JSONResponse(content=response_content, status_code=200)