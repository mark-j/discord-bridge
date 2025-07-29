"""Tests for configuration module."""

import os
import tempfile
from pathlib import Path

import pytest
import yaml

from discord_bridge.config import BridgeConfig, DiscordConfig, EventRoute


def test_discord_config_validation():
    """Test Discord configuration validation."""
    # Valid token
    config = DiscordConfig(token="valid_token_here")
    assert config.token == "valid_token_here"
    assert config.intents == 513  # Default value
    
    # Invalid token
    with pytest.raises(ValueError):
        DiscordConfig(token="")
        
    with pytest.raises(ValueError):
        DiscordConfig(token="short")


def test_event_route():
    """Test event route configuration."""
    route = EventRoute(
        event_name="MESSAGE_CREATE",
        endpoints=["https://example.com/webhook"]
    )
    assert route.event_name == "MESSAGE_CREATE"
    assert route.enabled is True  # Default value
    assert len(route.endpoints) == 1


def test_bridge_config_from_env():
    """Test loading configuration from environment variables."""
    # Set environment variables
    os.environ["DISCORD_TOKEN"] = "test_token"
    os.environ["DISCORD_INTENTS"] = "1024"
    os.environ["LOG_LEVEL"] = "DEBUG"
    
    try:
        config = BridgeConfig.from_env()
        assert config.discord.token == "test_token"
        assert config.discord.intents == 1024
        assert config.logging.level == "DEBUG"
    finally:
        # Clean up environment variables
        for key in ["DISCORD_TOKEN", "DISCORD_INTENTS", "LOG_LEVEL"]:
            os.environ.pop(key, None)


def test_bridge_config_from_yaml():
    """Test loading configuration from YAML file."""
    config_data = {
        "discord": {
            "token": "yaml_token",
            "intents": 2048
        },
        "http": {
            "timeout": 60,
            "retry_attempts": 5
        },
        "routes": [
            {
                "event_name": "MESSAGE_CREATE",
                "endpoints": ["https://example.com/webhook1", "https://example.com/webhook2"],
                "enabled": True
            }
        ]
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config_data, f)
        temp_path = Path(f.name)
        
    try:
        config = BridgeConfig.from_yaml(temp_path)
        assert config.discord.token == "yaml_token"
        assert config.discord.intents == 2048
        assert config.http.timeout == 60
        assert config.http.retry_attempts == 5
        assert len(config.routes) == 1
        assert config.routes[0].event_name == "MESSAGE_CREATE"
        assert len(config.routes[0].endpoints) == 2
    finally:
        temp_path.unlink()


def test_get_routes_for_event():
    """Test getting routes for specific events."""
    config = BridgeConfig(
        discord=DiscordConfig(token="test_token"),
        routes=[
            EventRoute(
                event_name="MESSAGE_CREATE",
                endpoints=["https://example.com/messages"],
                enabled=True
            ),
            EventRoute(
                event_name="MESSAGE_CREATE",
                endpoints=["https://backup.com/messages"],
                enabled=False  # Disabled
            ),
            EventRoute(
                event_name="GUILD_MEMBER_ADD",
                endpoints=["https://example.com/members"],
                enabled=True
            )
        ]
    )
    
    # Should only return enabled routes for MESSAGE_CREATE
    message_routes = config.get_routes_for_event("MESSAGE_CREATE")
    assert len(message_routes) == 1
    assert str(message_routes[0].endpoints[0]) == "https://example.com/messages"
    
    # Should return one route for GUILD_MEMBER_ADD
    member_routes = config.get_routes_for_event("GUILD_MEMBER_ADD")
    assert len(member_routes) == 1
    
    # Should return no routes for non-configured event
    unknown_routes = config.get_routes_for_event("UNKNOWN_EVENT")
    assert len(unknown_routes) == 0 