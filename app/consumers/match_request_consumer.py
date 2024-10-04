import aio_pika
import asyncio
import json
import aiohttp
from app.config import RABBITMQ_URL

async def consume_from_queue():
    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    async with connection:
        channel = await connection.channel()
        queue = await channel.declare_queue('match-request', durable=True, arguments={'x-message-ttl': 60000})

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

                    async with aiohttp.ClientSession() as session:
                        async with session.post("http://localhost:8080/recommend", json=message_data) as response:
                            response_json = await response.json()
                            print(f"Response from /recommend: {response.status}, {response_json}")

                except Exception as e:
                    print(f"Error sending request to /recommend: {str(e)}")
