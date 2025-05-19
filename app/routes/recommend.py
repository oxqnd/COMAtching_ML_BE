from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
import subprocess
import pandas as pd
from app.config import CSV_FILE_PATH, ML_FILE_PATH
from app.utils.helpers import send_to_queue

router = APIRouter()

@router.post("/recommend")
async def recommend_user(request: Request):
    data = await request.json()
    csv_file_path = CSV_FILE_PATH
    ml_file_path = ML_FILE_PATH

    props = data.get('props')
    print("[DEBUG] props:", props)

    if not props or not props.get('reply_to') or not props.get('correlation_id'):
        response_content = {"stateCode": "MTCH-001", "message": "Field Missing"}
        await send_to_queue(None, props, response_content)
        return JSONResponse(content={"error": "Missing properties (reply_to or correlation_id)"}, status_code=400)

    # 필수 필드 확인
    required_fields = [
        "matcherUuid", "contactFrequencyOption", "genderOption", "hobbyOption",
        "sameMajorOption", "ageOption",
        "mbtiOption",
        "myMajor"
    ]
    for field in required_fields:
        if field not in data:
            response_content = {"stateCode": "MTCH-001", "message": f"Missing field: {field}"}
            await send_to_queue(None, props, response_content)
            return JSONResponse(content=response_content, status_code=400)

    # CSV 수정
    try:
        df = pd.read_csv(csv_file_path, encoding='utf-8')
        print("[DEBUG] CSV columns:", df.columns.tolist())

        if df.empty:
            response_content = {"stateCode": "MTCH-003", "message": "CSV file is empty"}
            await send_to_queue(None, props, response_content)
            return JSONResponse(content=response_content, status_code=404)

        df.at[0, 'matcherUuid'] = data['matcherUuid']
        df.at[0, 'contactFrequencyOption'] = data['contactFrequencyOption']
        df.at[0, 'genderOption'] = data['genderOption']
        df.at[0, 'hobbyOption'] = data['hobbyOption']
        df.at[0, 'sameMajorOption'] = data['sameMajorOption']
        df.at[0, 'ageOption'] = data['ageOption']
        df.at[0, 'mbtiOption'] = data['mbtiOption']
        df.at[0, 'myMajor'] = data['myMajor']

        df.to_csv(csv_file_path, index=False, encoding='utf-8')

    except Exception as e:
        response_content = {"stateCode": "MTCH-004", "message": "File open fail", "details": str(e)}
        await send_to_queue(None, props, response_content)
        return JSONResponse(content=response_content, status_code=500)

    # run.py 실행 (인자 없이)
    try:
        result = subprocess.run(['python', ml_file_path], capture_output=True, text=True)
        if result.returncode != 0:
            response_content = {"stateCode": "MTCH-005", "message": "Error running model"}
            await send_to_queue(None, props, response_content)
            response_content.update({"details": str(result.stderr.strip())})
            return JSONResponse(content=response_content, status_code=500)

        recommended_candidate = result.stdout.strip()

        if 'Top 1 Similar Person:' in recommended_candidate:
            start_index = recommended_candidate.find('Top 1 Similar Person:') + len('Top 1 Similar Person:')
            recommended_user_data = recommended_candidate[start_index:].strip()

            lines = recommended_user_data.split('\n')
            user_info = {}
            for line in lines:
                line = line.strip()
                if not line or line.startswith('---'):
                    continue
                if 'uuid:' in line:
                    parts = line.split('uuid:')
                    if len(parts) == 2:
                        user_info['matcherUuid'] = parts[1].strip().split()[0]
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
            response_content.update({"details": "Recommended result format error"})
            return JSONResponse(content=response_content, status_code=500)

    except Exception as e:
        response_content = {"stateCode": "MTCH-005", "message": "Error running model"}
        await send_to_queue(None, props, response_content)
        response_content.update({"details": str(e)})
        return JSONResponse(content=response_content, status_code=500)


    # 최종 응답
    response_content = {"stateCode": "MTCH-000", "message": "Success"}
    response_content.update(recommended_user)
    print("[DEBUG] Final response content:", response_content)
    print("[DEBUG] Sending to queue:", props.get('reply_to'))
    await send_to_queue(None, props, response_content)
    return JSONResponse(content=response_content, status_code=200)
