"""Main application entry point."""

import asyncio
import logging
import signal
import sys
from pathlib import Path
from typing import Optional

import structlog

from .config import BridgeConfig
from .gateway import GatewayClient
from .router import EventRouter


class DiscordBridge:
    """Main Discord Bridge application."""
    
    def __init__(self, config: BridgeConfig):
        self.config = config
        self.gateway_client: Optional[GatewayClient] = None
        self.event_router: Optional[EventRouter] = None
        self.running = False
        self.shutdown_event = asyncio.Event()
        
    def setup_logging(self):
        """Setup structured logging based on configuration."""
        level = getattr(logging, self.config.logging.level.upper(), logging.INFO)
        
        if self.config.logging.format == "json":
            structlog.configure(
                processors=[
                    structlog.stdlib.filter_by_level,
                    structlog.stdlib.add_logger_name,
                    structlog.stdlib.add_log_level,
                    structlog.stdlib.PositionalArgumentsFormatter(),
                    structlog.processors.StackInfoRenderer(),
                    structlog.processors.format_exc_info,
                    structlog.processors.UnicodeDecoder(),
                    structlog.processors.JSONRenderer()
                ],
                context_class=dict,
                logger_factory=structlog.stdlib.LoggerFactory(),
                wrapper_class=structlog.stdlib.BoundLogger,
                cache_logger_on_first_use=True,
            )
        else:
            # Console format
            structlog.configure(
                processors=[
                    structlog.stdlib.filter_by_level,
                    structlog.stdlib.add_logger_name,
                    structlog.stdlib.add_log_level,
                    structlog.stdlib.PositionalArgumentsFormatter(),
                    structlog.processors.TimeStamper(fmt="iso"),
                    structlog.dev.ConsoleRenderer()
                ],
                context_class=dict,
                logger_factory=structlog.stdlib.LoggerFactory(),
                wrapper_class=structlog.stdlib.BoundLogger,
                cache_logger_on_first_use=True,
            )
            
        logging.basicConfig(
            format="%(message)s",
            stream=sys.stdout,
            level=level,
        )
        
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            print(f"\nReceived signal {signum}, initiating graceful shutdown...")
            asyncio.create_task(self.shutdown())
            
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
    async def start(self):
        """Start the Discord Bridge application."""
        logger = structlog.get_logger(__name__)
        
        self.setup_logging()
        logger.info("Starting Discord Bridge", version="0.1.0")
        
        # Validate configuration
        if not self.config.routes:
            logger.warning("No event routes configured - events will be received but not forwarded")
        else:
            logger.info(f"Configured {len(self.config.routes)} event routes")
            for route in self.config.routes:
                if route.enabled:
                    logger.info(
                        f"Route enabled: {route.event_name} -> {len(route.endpoints)} endpoint(s)"
                    )
                    
        # Initialize components
        self.gateway_client = GatewayClient(self.config.discord)
        self.event_router = EventRouter(self.config)
        
        # Setup event handling
        self.gateway_client.on_event(self.event_router.handle_event)
        
        try:
            # Start router
            await self.event_router.start()
            
            # Start gateway client (this will run until disconnected)
            self.running = True
            await self.gateway_client.connect()
            
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        except Exception as e:
            logger.error(f"Application error: {e}")
            raise
        finally:
            await self.cleanup()
            
    async def shutdown(self):
        """Gracefully shutdown the application."""
        logger = structlog.get_logger(__name__)
        logger.info("Shutting down Discord Bridge...")
        
        self.running = False
        self.shutdown_event.set()
        
    async def cleanup(self):
        """Cleanup resources."""
        logger = structlog.get_logger(__name__)
        
        if self.gateway_client:
            logger.info("Disconnecting from Discord Gateway...")
            await self.gateway_client.disconnect()
            
        if self.event_router:
            logger.info("Stopping event router...")
            await self.event_router.stop()
            
            # Log final statistics
            stats = self.event_router.get_stats()
            logger.info("Final statistics", **stats)
            
        logger.info("Discord Bridge stopped")


async def async_main():
    """Async main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Discord Gateway API bridge")
    parser.add_argument(
        "--config", "-c",
        type=Path,
        help="Path to configuration YAML file"
    )
    parser.add_argument(
        "--token",
        help="Discord bot token (overrides config file)"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Log level (overrides config file)"
    )
    
    args = parser.parse_args()
    
    # Load configuration
    try:
        if args.config and args.config.exists():
            config = BridgeConfig.from_yaml(args.config)
        else:
            config = BridgeConfig.from_env()
            
        # Override with command line arguments
        if args.token:
            config.discord.token = args.token
        if args.log_level:
            config.logging.level = args.log_level
            
    except Exception as e:
        print(f"Configuration error: {e}")
        sys.exit(1)
        
    # Start the application
    bridge = DiscordBridge(config)
    
    # Setup signal handlers for graceful shutdown (Unix only)
    def signal_handler():
        print("\nReceived interrupt signal, shutting down gracefully...")
        asyncio.create_task(bridge.shutdown())
    
    # Only set up signal handlers on Unix systems    
    if sys.platform != 'win32':
        loop = asyncio.get_event_loop()
        for sig in [signal.SIGINT, signal.SIGTERM]:
            loop.add_signal_handler(sig, signal_handler)
        
    try:
        await bridge.start()
    except KeyboardInterrupt:
        print("\nReceived keyboard interrupt, shutting down gracefully...")
        await bridge.shutdown()


def main():
    """Main entry point for CLI."""
    asyncio.run(async_main())


if __name__ == "__main__":
    main() 