"""Configuration management for IoT Telemetry Dashboard Backend."""

from typing import List, Optional

from pydantic import Field, validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )
    
    # Application settings
    app_name: str = "IoT Telemetry Dashboard"
    app_version: str = "0.1.0"
    debug: bool = False
    
    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False
    
    # CORS settings
    cors_origins: List[str] = Field(default=["http://localhost:3000"])
    
    # Database settings - PostgreSQL
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "postgres"
    postgres_password: str = "password"
    postgres_db: str = "iot_dashboard"
    
    @property
    def postgres_url(self) -> str:
        """Construct PostgreSQL connection URL."""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )
    
    # Database settings - InfluxDB
    influxdb_url: str = "http://localhost:8086"
    influxdb_token: Optional[str] = None
    influxdb_org: str = "iot-dashboard"
    influxdb_bucket: str = "telemetry"
    
    # MQTT settings
    mqtt_broker_host: str = "localhost"
    mqtt_broker_port: int = 1883
    mqtt_username: Optional[str] = None
    mqtt_password: Optional[str] = None
    mqtt_topic_pattern: str = "iot/+/+/+/+/telemetry/v1"
    
    # Authentication settings
    secret_key: str = Field(
        default="your-secret-key-change-in-production",
        description="Secret key for JWT token generation"
    )
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Telemetry settings
    telemetry_retention_days: int = 90
    telemetry_batch_size: int = 1000
    telemetry_flush_interval_seconds: int = 5
    
    # Real-time streaming settings
    sse_ping_interval: int = 30  # seconds
    max_sse_connections: int = 100
    
    @validator("cors_origins", pre=True)
    def validate_cors_origins(cls, v):
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    class Config:
        """Pydantic configuration."""
        case_sensitive = False


# Global settings instance
settings = Settings()