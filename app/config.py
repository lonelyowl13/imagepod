from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    
    postgres_db: str = ""
    postgres_user: str = ""
    postgres_password: str = ""
    postgres_host: str = "localhost"
    redis_password: str = ""

    redis_url: str = "redis://localhost:6379/0"
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"

    rabbitmq_default_user: str = "imagepod"
    rabbitmq_default_pass: str = ""
    rabbitmq_host: str = "localhost"

    # Security
    secret_key: str = os.getenv("SECRET_KEY")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    
    # Kubernetes
    kubeconfig_path: Optional[str] = None
    
    # Environment
    environment: str = "development"
    debug: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = False

    def get_db_url(self):
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:5432/{self.postgres_db}"

    def get_rabbitmq_url(self):

        rabbitmq_url: str = f"amqp://{self.rabbitmq_default_user}:{self.rabbitmq_default_pass}@{self.rabbitmq_host}:5672/"

        return rabbitmq_url


settings = Settings()
