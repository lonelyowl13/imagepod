from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    
    postgres_db: str = ""
    postgres_user: str = ""
    postgres_password: str = ""
    redis_password: str = ""

    redis_url: str = "redis://localhost:6379/0"
    
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
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@localhost:5432/{self.postgres_db}"


settings = Settings()
