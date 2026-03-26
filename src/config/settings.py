import os
from pydantic_settings import BaseSettings
from pydantic import computed_field, Field
from urllib.parse import quote

class Settings(BaseSettings):
    # MQTT settings
    mqtt_host: str = Field(default="139.9.50.7", env="MQTT_HOST")
    mqtt_port: int = Field(default=1883, env="MQTT_PORT")
    mqtt_topic: str = Field(default="sentinel", env="MQTT_TOPIC")
    mqtt_username: str | None = Field(default=None, env="MQTT_USERNAME")
    mqtt_password: str | None = Field(default=None, env="MQTT_PASSWORD")
    mqtt_client_id: str = Field(default="sentinel-api-client", env="MQTT_CLIENT_ID")
    mqtt_protocol_version: str = Field(default="3.1.1", env="MQTT_PROTOCOL_VERSION")

    # API settings
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")

    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")

    # MySQL settings
    mysql_host: str = Field(default="139.9.50.7", env="MYSQL_HOST")
    mysql_port: int = Field(default=3306, env="MYSQL_PORT")
    mysql_user: str = Field(default="sentinel", env="MYSQL_USER")
    mysql_password: str = Field(default="7fd8cuda8dfd", env="MYSQL_PASSWORD")
    mysql_database: str = Field(default="sentinel", env="MYSQL_DATABASE")

    @computed_field
    @property
    def SQLALCHEMY_DATABASE_URL(self) -> str:
        password = quote(self.mysql_password)
        return f"mysql+pymysql://{self.mysql_user}:{password}@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"

    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()