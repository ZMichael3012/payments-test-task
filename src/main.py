from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.v1 import payments
from src.api.v1.payments import router as payments_router
from src.core.api.middleware import APIKeyMiddleware, StripTrailingSlashMiddleware
from src.core.config.di_container import Container
from src.core.config.logging import configure_logging
from src.core.config.settings import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    container.wire(modules=[payments])
    configure_logging()

    yield

    await container.engine().dispose()


app = FastAPI(
    title="Payment Processing Service",
    version="1.0.0",
    description="Async payment processing microservice",
    lifespan=lifespan,
)

container = Container()
container.config.from_dict(
    {
        "db": {
            "url": settings.database_url,
        }
    }
)
app.container = container

app.add_middleware(StripTrailingSlashMiddleware)
app.add_middleware(APIKeyMiddleware)

app.include_router(payments_router, prefix="/api/v1")


@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok"}
