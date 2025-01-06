import aio_pika
import asyncio
import json
import aiohttp
from app.config import RABBITMQ_URL, ML_BE_URL, ML_BE_PORT

async def consume_from_match_request_queue():
    try:
        connection = await aio_pika.connect_robust(RABBITMQ_URL)
        async with connection:
            channel = await connection.channel()
            queue = await channel.declare_queue('match-request', durable=True)

            async for message in queue:
                async with message.process():
                    try:
                        print(f"Received message: {message.body}")
                        print(f"Message properties: {message.properties}")
                        props = message.properties

                        message_data = json.loads(message.body)
                        message_data["props"] = {
                            "reply_to": props.reply_to,
                            "correlation_id": props.correlation_id
                        }

                        try:
                            async with aiohttp.ClientSession() as session:
                                async with session.post(f"http://{ML_BE_URL}:{ML_BE_PORT}/recommend", json=message_data) as response:
                                    response_json = await response.json()
                                    print(f"Response from /recommend: {response.status}, {response_json}")
                        except Exception as e:
                            print(f"Error sending request to /recommend: {str(e)}")

                    except Exception as e:
                        print(f"Exception in callback: {str(e)}")
    except Exception as conn_error:
        print(f"Connection error: {conn_error}")