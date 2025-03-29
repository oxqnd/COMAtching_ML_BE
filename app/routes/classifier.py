from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
import subprocess
import json
from app.utils.helpers import send_to_queue

router = APIRouter()

@router.post("/classify")
async def classify_categories(request: Request):
    try:
        data = await request.json()

        small_categories = data.get("smallCategory", [])
        if not isinstance(small_categories, list):
            response_content = {"stateCode": "MTCH-001", "message": "smallCategory must be a list"}
            await send_to_queue(None, data.get("props", {}), response_content)
            return JSONResponse(content=response_content, status_code=400)

        props = data.get("props", {})

        if not props or not props.get('reply_to') or not props.get('correlation_id'):
            response_content = {"stateCode": "MTCH-001", "message": "Field Missing"}
            await send_to_queue(None, props, response_content)
            return JSONResponse(content={"error": "Missing properties (reply_to or correlation_id)"}, status_code=400)

        if not small_categories:
            response_content = {"stateCode": "MTCH-002", "message": "smallCategory list cannot be empty"}
            await send_to_queue(None, props, response_content)
            return JSONResponse(content=response_content, status_code=400)

        big_categories = []
        for small_cat in small_categories:
            big_cat = CATEGORY_MAPPING.get(small_cat, "기타")
            big_categories.append(big_cat)

        response_content = {
            "bigCategory": big_categories
        }

        await send_to_queue(None, props, response_content)

        return JSONResponse(content=response_content, status_code=200)

    except json.JSONDecodeError as e:
        response_content = {"stateCode": "MTCH-003", "message": "Invalid JSON format"}
        await send_to_queue(None, data.get("props", {}), response_content)
        response_content.update({"details": str(e)})
        return JSONResponse(content=response_content, status_code=400)

    except Exception as e:
        response_content = {"stateCode": "MTCH-004", "message": "An unexpected error occurred"}
        await send_to_queue(None, data.get("props", {}), response_content)
        response_content.update({"details": str(e)})
        return JSONResponse(content=response_content, status_code=500)
