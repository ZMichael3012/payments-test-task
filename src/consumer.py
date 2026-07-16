import asyncio
from asyncio import Task

from faststream import ContextRepo, FastStream

from src.core.config.di_container import Container
from src.core.config.logging import configure_logging, get_logger
from src.core.config.settings import settings
from src.core.infrastructure.broker.broker import broker, dlq_q, retry_q
from src.modules.outbox.infrastructure.events import handlers as outbox_handlers_module
from src.modules.outbox.infrastructure.events.handlers import listen_loop, publish_loop
from src.modules.payments.infrastructure.events import handlers as payments_handlers_module

logger = get_logger(__name__)

_bg_tasks: set[Task] = set()

app = FastStream(broker)

container = Container()
container.config.from_dict(
    {
        "db": {
            "url": settings.database_url,
        }
    }
)
app.container = container


@app.on_startup
async def setup_dependency_injection(context: ContextRepo):
    container.wire(modules=[outbox_handlers_module, payments_handlers_module])
    configure_logging()


@app.after_startup
async def setup_queues_and_tasks():
    await broker.declare_queue(retry_q)
    await broker.declare_queue(dlq_q)

    listen_task = asyncio.create_task(listen_loop())
    publish_task = asyncio.create_task(publish_loop())

    _bg_tasks.update({listen_task, publish_task})


@app.on_shutdown
async def cleanup_tasks():
    for task in _bg_tasks:
        task.cancel()
