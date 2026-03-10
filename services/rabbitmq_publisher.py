import logging
import json
import aio_pika
from config import settings

LOGGER = logging.getLogger(__name__)

class RabbitMQPublisher:
    def __init__(self):
        self.connection = None
        self.channel = None
        self.exchange = None

    async def connect(self):
        try:
            self.connection = await aio_pika.connect_robust(settings.rabbitmq_url)
            self.channel = await self.connection.channel()
            # Publish to exchange just like session-service
            self.exchange = await self.channel.declare_exchange(
                "billing_events", aio_pika.ExchangeType.TOPIC, durable=True
            )
            LOGGER.info("Connected to RabbitMQ for terminal-service")
        except Exception as e:
            LOGGER.error("Failed to connect to RabbitMQ: %s", e)

    async def close(self):
        if self.connection:
            await self.connection.close()
            LOGGER.info("Closed RabbitMQ connection")

    async def publish_terminal_transaction(self, tenant_id: str, terminal_id: str, order_id: str, keepz_status: str, amount: float,  currency: str):
        if not self.exchange:
            LOGGER.warning("RabbitMQ not connected. Skipping publish for %s", order_id)
            return

        payload = {
            "source": "terminal-service",
            "tenant_id": tenant_id,
            "terminal_id": terminal_id,
            "order_id": order_id,
            "status": keepz_status,
            "amount": amount,
            "currency": currency,
            "type": "PAYMENT_INTENT"
        }

        routing_key = f"terminal.transaction.{keepz_status.lower()}"

        try:
            msg = aio_pika.Message(
                body=json.dumps(payload).encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            )
            await self.exchange.publish(msg, routing_key=routing_key)
            LOGGER.info("Published terminal transaction event %s for order %s", routing_key, order_id)
        except Exception as e:
            LOGGER.error("Error publishing terminal event via RabbitMQ: %s", e)

rmq_publisher = RabbitMQPublisher()
