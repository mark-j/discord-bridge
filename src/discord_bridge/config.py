"""Configuration management for Discord Bridge."""

import os
from pathlib import Path
from typing import List

import yaml
from pydantic import BaseModel, HttpUrl, Field, field_validator


class EventRoute(BaseModel):
    """Configuration for routing a specific Discord event to HTTP endpoints."""
    
    event_name: str = Field(..., description="Discord event name (e.g., MESSAGE_CREATE)")
    endpoints: List[HttpUrl] = Field(..., description="HTTP endpoints to forward the event to")
    enabled: bool = Field(default=True, description="Whether this route is enabled")


class DiscordConfig(BaseModel):
    """Discord API configuration."""
    
    token: str = Field(..., description="Discord bot token")
    intents: int = Field(default=513, description="Discord Gateway intents (default: GUILDS + GUILD_MESSAGES)")
    
    @field_validator("token")
    @classmethod
    def validate_token(cls, v):
        if not v or len(v) < 10:
            raise ValueError("Discord token must be provided and valid")
        return v


class HTTPConfig(BaseModel):
    """HTTP client configuration."""
    
    timeout: int = Field(default=30, description="HTTP request timeout in seconds")
    retry_attempts: int = Field(default=3, description="Number of retry attempts for failed requests")
    retry_delay: int = Field(default=1, description="Delay between retry attempts in seconds")


class LoggingConfig(BaseModel):
    """Logging configuration."""
    
    level: str = Field(default="INFO", description="Log level")
    format: str = Field(default="json", description="Log format (json or console)")


class BridgeConfig(BaseModel):
    """Main bridge configuration."""
    
    discord: DiscordConfig
    http: HTTPConfig = HTTPConfig()
    logging: LoggingConfig = LoggingConfig()
    routes: List[EventRoute] = Field(default_factory=list, description="Event routing configuration")
    
    @classmethod
    def from_yaml(cls, path: Path) -> "BridgeConfig":
        """Load configuration from YAML file."""
        with open(path, "r") as f:
            data = yaml.safe_load(f)
        return cls(**data)
    
    @classmethod
    def from_env(cls) -> "BridgeConfig":
        """Load configuration from environment variables."""
        discord_token = os.getenv("DISCORD_TOKEN")
        if not discord_token:
            raise ValueError("DISCORD_TOKEN environment variable is required")
        
        return cls(
            discord=DiscordConfig(
                token=discord_token,
                intents=int(os.getenv("DISCORD_INTENTS", "513"))
            ),
            http=HTTPConfig(
                timeout=int(os.getenv("HTTP_TIMEOUT", "30")),
                retry_attempts=int(os.getenv("HTTP_RETRY_ATTEMPTS", "3")),
                retry_delay=int(os.getenv("HTTP_RETRY_DELAY", "1"))
            ),
            logging=LoggingConfig(
                level=os.getenv("LOG_LEVEL", "INFO"),
                format=os.getenv("LOG_FORMAT", "json")
            )
        )
    
    def get_routes_for_event(self, event_name: str) -> List[EventRoute]:
        """Get all enabled routes for a specific event."""
        return [route for route in self.routes if route.event_name == event_name and route.enabled] 