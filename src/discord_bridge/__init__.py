"""Discord Gateway API bridge that forwards events to HTTP endpoints."""

__version__ = "0.1.0"

from .gateway import GatewayClient
from .config import BridgeConfig
from .router import EventRouter

__all__ = ["GatewayClient", "BridgeConfig", "EventRouter"]
