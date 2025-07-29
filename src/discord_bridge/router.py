"""Event routing and HTTP forwarding system."""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any

import aiohttp
from aiohttp import ClientTimeout, ClientError

from .config import BridgeConfig

logger = logging.getLogger(__name__)


class HTTPForwarder:
    """Handles HTTP requests with retry logic and error handling."""
    
    def __init__(self, config: BridgeConfig):
        self.config = config
        self.session: aiohttp.ClientSession = None
        
    async def start(self):
        """Start the HTTP session."""
        timeout = ClientTimeout(total=self.config.http.timeout)
        self.session = aiohttp.ClientSession(timeout=timeout)
        
    async def stop(self):
        """Stop the HTTP session."""
        if self.session:
            await self.session.close()
            
    async def forward_event(self, endpoint: str, event_type: str, event_data: Dict[str, Any]) -> bool:
        """Forward an event to an HTTP endpoint with retry logic.
        
        Returns True if successful, False otherwise.
        """
        if not self.session:
            logger.error("HTTP session not started")
            return False
            
        payload = {
            "event_type": event_type,
            "data": event_data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "discord-bridge"
        }
        
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "discord-bridge/0.1.0"
        }
        
        for attempt in range(self.config.http.retry_attempts):
            try:
                logger.debug(f"Forwarding {event_type} to {endpoint} (attempt {attempt + 1})")
                
                async with self.session.post(endpoint, json=payload, headers=headers) as response:
                    if response.status < 400:
                        logger.debug(f"Successfully forwarded {event_type} to {endpoint}")
                        return True
                    else:
                        logger.warning(
                            f"HTTP {response.status} when forwarding {event_type} to {endpoint}: "
                            f"{await response.text()}"
                        )
                        
            except ClientError as e:
                logger.warning(f"HTTP error forwarding {event_type} to {endpoint}: {e}")
            except asyncio.TimeoutError:
                logger.warning(f"Timeout forwarding {event_type} to {endpoint}")
            except Exception as e:
                logger.error(f"Unexpected error forwarding {event_type} to {endpoint}: {e}")
                
            # Wait before retry (except on last attempt)
            if attempt < self.config.http.retry_attempts - 1:
                await asyncio.sleep(self.config.http.retry_delay)
                
        logger.error(f"Failed to forward {event_type} to {endpoint} after {self.config.http.retry_attempts} attempts")
        return False


class EventRouter:
    """Routes Discord events to configured HTTP endpoints."""
    
    def __init__(self, config: BridgeConfig):
        self.config = config
        self.forwarder = HTTPForwarder(config)
        self.stats = {
            "events_received": 0,
            "events_forwarded": 0,
            "events_failed": 0,
            "routes_processed": 0
        }
        
    async def start(self):
        """Start the event router."""
        await self.forwarder.start()
        logger.info("Event router started")
        
    async def stop(self):
        """Stop the event router."""
        await self.forwarder.stop()
        logger.info("Event router stopped")
        
    async def handle_event(self, event_type: str, event_data: Dict[str, Any]):
        """Handle a Discord event by routing it to configured endpoints."""
        self.stats["events_received"] += 1
        
        # Get routes for this event type
        routes = self.config.get_routes_for_event(event_type)
        
        if not routes:
            logger.debug(f"No routes configured for event {event_type}")
            return
            
        logger.info(f"Processing {event_type} event with {len(routes)} route(s)")
        
        # Forward to all endpoints concurrently
        tasks = []
        for route in routes:
            for endpoint in route.endpoints:
                task = self._forward_to_endpoint(str(endpoint), event_type, event_data)
                tasks.append(task)
                
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Count successes and failures
            successes = sum(1 for result in results if result is True)
            failures = len(results) - successes
            
            self.stats["events_forwarded"] += successes
            self.stats["events_failed"] += failures
            self.stats["routes_processed"] += 1
            
            logger.info(
                f"Forwarded {event_type} event: {successes} success(es), {failures} failure(s)"
            )
            
    async def _forward_to_endpoint(self, endpoint: str, event_type: str, event_data: Dict[str, Any]) -> bool:
        """Forward an event to a single endpoint."""
        try:
            return await self.forwarder.forward_event(endpoint, event_type, event_data)
        except Exception as e:
            logger.error(f"Error forwarding to {endpoint}: {e}")
            return False
            
    def get_stats(self) -> Dict[str, Any]:
        """Get routing statistics."""
        return self.stats.copy()
        
    def reset_stats(self):
        """Reset routing statistics."""
        self.stats = {
            "events_received": 0,
            "events_forwarded": 0,
            "events_failed": 0,
            "routes_processed": 0
        } 