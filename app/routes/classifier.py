from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
import subprocess
import json
from app.config import CSV_FILE_PATH, CLASSIFIER_FILE_PATH
from app.utils.helpers import send_to_queue

router = APIRouter()

@router.post("/classify")
async def classify_categories(request: Request):
		try:
			data = await request.json()
			csv_file_path = CSV_FILE_PATH
			classifier_file_path = CLASSIFIER_FILE_PATH

			# props가 데이터에 포함되어 있는지 확인
			props = data.get('props')

			# 만약 props에 reply_to나 correlation_id가 없으면 오류 반환
			if not props or not props.get('reply_to') or not props.get('correlation_id'):
					response_content = {"stateCode": "MTCH-001", "bigCategory": [], "message": "Field Missing"}
					await send_to_queue(None, props, response_content)
					return JSONResponse(content={"error": "Missing properties (reply_to or correlation_id)"}, status_code=400)

			# 필수 필드 확인
			required_fields = ["uuid", "smallCategory"]
			for field in required_fields:
					if field not in data:
							response_content = {"stateCode": "MTCH-001", "bigCategory": [], "message": "Field Missing"}
							await send_to_queue(None, props, response_content)
							return JSONResponse(content=response_content, status_code=400)

			if not isinstance(data["smallCategory"], list):
					response_content = {"stateCode": "MTCH-002", "bigCategory": [], "message": "smallCategory must be a list"}
					await send_to_queue(None, props, response_content)
					return JSONResponse(content=response_content, status_code=400)

			command = ['python', classifier_file_path, '--uuid', data["uuid"], '--subcategory'] + data["smallCategory"]
			result = subprocess.run(command, capture_output=True, text=True)

			if result.returncode != 0:
				response_content = {
						"stateCode": "MTCH-005",
						"bigCategory": [],
						"message": "Error running classifier script",
				}
				await send_to_queue(None, props, response_content)
				response_content.update({"details": result.stderr.strip()})
				return JSONResponse(content=response_content, status_code=500)

			output_lines = result.stdout.strip().split('\n')
			if len(output_lines) < 2:
					response_content = {"stateCode": "MTCH-006", "bigCategory": [], "message": "Invalid script output"}
					await send_to_queue(None, props, response_content)
					return JSONResponse(content=response_content, status_code=500)

			# 출력에서 대분류 추출 (예: "대분류: 스포츠, 자기계발")
			big_category_line = output_lines[1]
			if not big_category_line.startswith("대분류: "):
					response_content = {"stateCode": "MTCH-006", "bigCategory": [], "message": "Invalid big category output"}
					await send_to_queue(None, props, response_content)
					return JSONResponse(content=response_content, status_code=500)

			# 대분류 문자열을 리스트로 변환
			big_categories = [cat.strip() for cat in big_category_line.replace("대분류: ", "").split(",")]

			# 요청된 smallCategory 개수와 결과 개수 확인
			if len(big_categories) == 1 and len(data["smallCategory"]) > 1:
					# 단일 대분류를 smallCategory 개수만큼 반복
					big_categories = [big_categories[0]] * len(data["smallCategory"])
			elif len(big_categories) != len(data["smallCategory"]):
					response_content = {"stateCode": "MTCH-006", "bigCategory": [], "message": "Mismatch in category count"}
					await send_to_queue(None, props, response_content)
					return JSONResponse(content=response_content, status_code=500)

			# 응답 형식 생성
			response_content = {"stateCode": "MTCH-000", "bigCategory": big_categories, "message": "Success"}
			await send_to_queue(None, props, response_content)
			return JSONResponse(content=response_content, status_code=200)

		except json.JSONDecodeError as e:
			response_content = {"stateCode": "MTCH-003", "bigCategory": [], "message": "Invalid JSON format"}
			await send_to_queue(None, data.get("props", {}), response_content)
			response_content.update({"details": str(e)})
			return JSONResponse(content=response_content, status_code=400)

		except Exception as e:
			response_content = {"stateCode": "MTCH-004", "bigCategory": [], "message": "An unexpected error occurred"}
			await send_to_queue(None, data.get("props", {}), response_content)
			response_content.update({"details": str(e)})
			return JSONResponse(content=response_content, status_code=500)
