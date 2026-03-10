import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    """App configuration — loaded from .env or environment variables."""
    keepz_base_url: str = Field(default="https://gateway.keepz.me/ecommerce-service")
    keepz_public_key: str = Field(default="")
    keepz_private_key: str = Field(default="")
    keepz_integrator_id: str = Field(default="")
    keepz_receiver_id: str = Field(default="")
    
    db_host: str = Field(default="127.0.0.1")
    db_port: int = Field(default=3306)
    db_user: str = Field(default="plugshub")
    db_password: str = Field(default="")
    db_name: str = Field(default="plugshub")
    
    ocpp_server_url: str = Field(default="http://localhost:9000")
    callback_base_url: str = Field(default="https://api.plugshub.io/terminal")

    # Hardcoded tenant ID (temporary)
    tenant_id: str = Field(default="239cca94-9c80-4bcd-915e-445f35b6a260")

    rabbitmq_url: str = Field(default="amqp://guest:guest@localhost:5672/")

    api_port: int = Field(default=8100)
    api_host: str = Field(default="0.0.0.0")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
