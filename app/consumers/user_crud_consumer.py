import aio_pika
import asyncio
import json
import aiohttp
from app.config import RABBITMQ_URL
from app.utils.helpers import send_to_queue

async def consume_user_crud_request_queue():
    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    async with connection:
        channel = await connection.channel()
        queue = await channel.declare_queue('user-crud-request', durable=True, arguments={'x-message-ttl': 120000})

        async for message in queue:
            async with message.process():
                try:
                    print(f"Received message: {message.body}")
                    props = message.properties
                    message_data = json.loads(message.body)
                    message_data["props"] = {
                        "reply_to": props.reply_to,
                        "correlation_id": props.correlation_id
                    }

                    request_type = message_data.get("type")
                    user_uuid = message_data.get("uuid")

                    if not request_type or not user_uuid:
                        print(f"Invalid message: {message_data}")
                        continue

                    url = f"http://localhost:8080/users"
                    method = None

                    if request_type == "CREATE":
                        method = "POST"
                    elif request_type == "UPDATE":
                        method = "PUT"
                    elif request_type == "DELETE":
                        method = "DELETE"

                    if method:
                        async with aiohttp.ClientSession() as session:
                            response_json = None
                            if method == "POST":
                                async with session.post(url, json=message_data) as response:
                                    response_json = await response.json()
                            elif method == "PUT":
                                async with session.put(url, json=message_data) as response:
                                    response_json = await response.json()
                            elif method == "DELETE":
                                async with session.delete(url, json=message_data) as response:
                                    response_json = await response.json()

                            # response_json을 props.reply_to로 다시 전송
                            if response_json:
                                await send_to_queue(method, props, response_json)
                                print(f"Response from {method} {url}: {response.status}, {response_json}")
                    else:
                        print(f"Unknown request type: {request_type}")

                except Exception as e:
                    print(f"Exception in callback: {str(e)}")
