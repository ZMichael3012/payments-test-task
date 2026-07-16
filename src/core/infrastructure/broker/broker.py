from faststream.rabbit import RabbitBroker, RabbitExchange, RabbitQueue

from src.core.config.settings import settings

EXCHANGE_NAME = "payments"
PAYMENTS_PROCESS_QUEUE = "payments.new"
RETRY_QUEUE = "payments.retry"
DEAD_LETTER_QUEUE = "payments.dlq"

exchange = RabbitExchange(EXCHANGE_NAME, durable=True)

retry_q = RabbitQueue(
    RETRY_QUEUE,
    durable=True,
    arguments={
        "x-dead-letter-exchange": EXCHANGE_NAME,
        "x-dead-letter-routing-key": PAYMENTS_PROCESS_QUEUE,
    },
)

main_q = RabbitQueue(
    PAYMENTS_PROCESS_QUEUE,
    durable=True,
    routing_key=PAYMENTS_PROCESS_QUEUE,
)

dlq_q = RabbitQueue(DEAD_LETTER_QUEUE, durable=True)

broker = RabbitBroker(settings.rabbitmq_url)
