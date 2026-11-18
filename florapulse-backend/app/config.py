
"""
Configuration and environment variables for FloraPulse backend.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from .env file."""

    # Database
    database_url: str = "sqlite:///./florapulse.db"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # OpenWeather
    openweather_api_key: str = ""
    default_city: str = "Mumbai"
    weather_cache_minutes: int = 10

    # Device Authentication
    device_api_key: str = ""

    # Irrigation Thresholds
    moisture_threshold_dry: float = 35.0
    moisture_threshold_optimal: float = 50.0
    moisture_threshold_wet: float = 70.0

    # Pump Configuration
    pump_duration_seconds: int = 10
    pump_cooldown_minutes: int = 5

    # Simulation
    simulation_enabled: bool = True
    simulation_interval_seconds: int = 10

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore"
    )


# Create global settings instance
settings = Settings()
