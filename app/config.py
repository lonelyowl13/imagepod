from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    
    postgres_db: str = "imagepod"
    postgres_user: str = ""
    postgres_password: str = ""
    postgres_host: str = "localhost"
    redis_password: str = ""

    redis_port: int = 6379
    redis_db: int = 0
    redis_host: str = "localhost"

    rabbitmq_default_user: str = "imagepod"
    rabbitmq_default_pass: str = ""
    rabbitmq_host: str = "localhost"

    # Security
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    
    # Kubernetes
    kubeconfig_path: Optional[str] = None

    # FRP tunneling
    # Base domain for tunnel subdomains; your DNS provider should have a wildcard
    # record *.proxy_domain pointing at the public IP of the frps host.
    proxy_domain: str = "proxy.mydomain.com"

    # Environment
    environment: str = "development"
    debug: bool = True

    # Test environment. If true, database tables gonna be nuked and recreated after each restart
    test: bool = False
    
    class Config:
        env_file = ".env"
        case_sensitive = False

    def get_db_url(self):
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:5432/{self.postgres_db}"

    def get_rabbitmq_url(self):

        rabbitmq_url: str = f"amqp://{self.rabbitmq_default_user}:{self.rabbitmq_default_pass}@{self.rabbitmq_host}:5672/"

        return rabbitmq_url

    def get_redis_url(self):
        return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/0"


settings = Settings()
