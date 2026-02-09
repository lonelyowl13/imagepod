"""
RabbitMQ executor notifications: publish when a job is enqueued or an endpoint is assigned.
One queue per executor: executor.{executor_id}. Long-poll wakes on any update.
"""
import asyncio
from aio_pika import connect_robust, Message, DeliveryMode
from aio_pika.abc import AbstractConnection, AbstractChannel

QUEUE_PREFIX = "executor"


def _queue_name(executor_id: int) -> str:
    return f"{QUEUE_PREFIX}.{executor_id}"


async def connect(rabbitmq_url: str) -> AbstractConnection:
    """Create a robust connection (reconnects on failure)."""
    return await connect_robust(rabbitmq_url)


async def publish_job_notification(connection: AbstractConnection, executor_id: int) -> None:
    """Notify executor of an update (new job or endpoint). Wakes long-poll /executors/updates."""
    channel: AbstractChannel = await connection.channel()
    queue_name = _queue_name(executor_id)
    await channel.declare_queue(queue_name, durable=False, auto_delete=True)
    await channel.default_exchange.publish(
        Message(body=b"", delivery_mode=DeliveryMode.NOT_PERSISTENT),
        routing_key=queue_name,
    )
    await channel.close()


async def wait_for_executor_notification(
    connection: AbstractConnection,
    executor_id: int,
    timeout: float,
) -> bool:
    """
    Block until an executor notification arrives (new job or endpoint) or timeout.
    Returns True if a message was received.
    Uses consume() + event because basic_get returns immediately when queue is empty.
    """
    channel: AbstractChannel = await connection.channel()
    queue_name = _queue_name(executor_id)
    queue = await channel.declare_queue(queue_name, durable=False, auto_delete=True)
    got_message: asyncio.Event = asyncio.Event()
    received_message = False

    async def on_message(message):
        nonlocal received_message
        await message.ack()
        received_message = True
        got_message.set()

    consumer_tag = await queue.consume(on_message, no_ack=False)
    try:
        await asyncio.wait_for(got_message.wait(), timeout=timeout)
        return received_message
    except asyncio.TimeoutError:
        return False
    finally:
        await queue.cancel(consumer_tag)
        await channel.close()
