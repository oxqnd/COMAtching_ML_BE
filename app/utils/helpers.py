import aio_pika
import json
from app.config import RABBITMQ_URL

async def send_to_queue(method, props, message):
    try:
        print(f"Sending message to queue: {message}")
        connection = await aio_pika.connect_robust(RABBITMQ_URL)
        async with connection:
            channel = await connection.channel()

            await channel.default_exchange.publish(
                aio_pika.Message(
                    body=json.dumps(message).encode(),
                    correlation_id=props["correlation_id"]
                ),
                routing_key=props["reply_to"],
            )
            print(f"Message sent to queue '{props['reply_to']}'")
    except Exception as e:
        print(f"Error sending message to queue: {str(e)}")
