from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Infrastructure
    # Database
    postgres_host: str
    postgres_port: int
    postgres_user: str
    postgres_password: str
    postgres_db: str

    db_pool_size: int = 30
    db_max_overflow: int = 10
    db_pool_timeout: int = 30
    db_pool_recycle: int = 1800

    # RabbitMQ / Consumer
    broker_host: str
    broker_port: int
    broker_user: str
    broker_password: str

    max_retries: int = 3
    retry_delay_ms: int = 5000

    # Security
    api_key: str
    webhook_secret: str

    # Observability
    log_level: str = "INFO"
    log_json: bool = True

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def database_url(self):
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@"
            f"{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def rabbitmq_url(self):
        return f"amqp://{self.broker_user}:{self.broker_password}@{self.broker_host}:{self.broker_port}/"


settings = Settings()
