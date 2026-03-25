import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # MQTT settings
    mqtt_host: str = "139.9.50.7"
    mqtt_port: int = 1883
    mqtt_topic: str = "sentinel"
    mqtt_username: str = None
    mqtt_password: str = None
    mqtt_client_id: str = "sentinel-api-client"
    mqtt_protocol_version: str = "3.1.1"
    
    # API settings
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    # Logging
    log_level: str = "INFO"

    # MySQL settings
    mysql_host: str = "139.9.50.7"
    mysql_port: int = 3306
    mysql_user: str = "sentinel"
    mysql_password: str = "7fd8cuda8dfd"
    mysql_database: str = "sentinel"

    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()