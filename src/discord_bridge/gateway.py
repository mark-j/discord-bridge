"""Discord Gateway WebSocket client."""

import asyncio
import json
import logging
import random
import sys
from typing import Callable, Optional, Dict, Any

import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException

from .config import DiscordConfig

logger = logging.getLogger(__name__)


class GatewayClient:
    """Discord Gateway WebSocket client with automatic reconnection and heartbeating."""
    
    GATEWAY_URL = "wss://gateway.discord.gg"
    API_VERSION = 10
    ENCODING = "json"
    
    def __init__(self, config: DiscordConfig):
        self.config = config
        self.websocket: Optional[Any] = None
        self.session_id: Optional[str] = None
        self.resume_gateway_url: Optional[str] = None
        self.last_sequence: Optional[int] = None
        self.heartbeat_interval: Optional[float] = None
        self.heartbeat_task: Optional[asyncio.Task] = None
        self.running = False
        self.event_handler: Optional[Callable[[str, Dict[str, Any]], Any]] = None
        
    def on_event(self, handler: Callable[[str, Dict[str, Any]], Any]):
        """Register an event handler function."""
        self.event_handler = handler
        
    async def connect(self):
        """Connect to Discord Gateway and start the event loop."""
        self.running = True
        
        while self.running:
            try:
                await self._connect_and_run()
            except Exception as e:
                logger.error(f"Gateway connection failed: {e}")
                if self.running:
                    logger.info("Reconnecting in 5 seconds...")
                    await asyncio.sleep(5)
                    
    async def disconnect(self):
        """Gracefully disconnect from the Gateway."""
        self.running = False
        
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass
                
        if self.websocket:
            await self.websocket.close()
            
    async def _connect_and_run(self):
        """Connect to Gateway and handle the connection lifecycle."""
        # Use resume URL if available, otherwise use main gateway URL
        url = self.resume_gateway_url or self.GATEWAY_URL
        uri = f"{url}/?v={self.API_VERSION}&encoding={self.ENCODING}"
        
        logger.info(f"Connecting to Discord Gateway: {uri}")
        
        async with websockets.connect(uri) as websocket:
            self.websocket = websocket
            
            # Wait for HELLO event
            hello_event = await self._receive_event()
            if hello_event["op"] != 10:
                raise Exception(f"Expected HELLO event, got opcode {hello_event['op']}")
                
            self.heartbeat_interval = hello_event["d"]["heartbeat_interval"] / 1000.0
            logger.info(f"Received HELLO, heartbeat interval: {self.heartbeat_interval}s")
            
            # Start heartbeating
            self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            
            # Identify or Resume
            if self.session_id and self.last_sequence is not None:
                await self._resume()
            else:
                await self._identify()
                
            # Process events
            await self._event_loop()
            
    async def _identify(self):
        """Send IDENTIFY payload to Discord."""
        logger.info("Identifying with Discord...")
        
        identify_payload = {
            "op": 2,  # IDENTIFY
            "d": {
                "token": self.config.token,
                "intents": self.config.intents,
                "properties": {
                    "$os": sys.platform,
                    "$browser": "discord-bridge",
                    "$device": "discord-bridge"
                }
            }
        }
        
        await self._send_payload(identify_payload)
        
    async def _resume(self):
        """Send RESUME payload to Discord."""
        logger.info("Resuming Discord session...")
        
        resume_payload = {
            "op": 6,  # RESUME
            "d": {
                "token": self.config.token,
                "session_id": self.session_id,
                "seq": self.last_sequence
            }
        }
        
        await self._send_payload(resume_payload)
        
    async def _heartbeat_loop(self):
        """Send periodic heartbeats to maintain connection."""
        # Add jitter to prevent thundering herd
        await asyncio.sleep(random.random() * self.heartbeat_interval)
        
        while self.running:
            try:
                heartbeat_payload = {
                    "op": 1,  # HEARTBEAT
                    "d": self.last_sequence
                }
                
                await self._send_payload(heartbeat_payload)
                logger.debug("Sent heartbeat")
                
                await asyncio.sleep(self.heartbeat_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat failed: {e}")
                break
                
    async def _event_loop(self):
        """Main event processing loop."""
        while self.running:
            try:
                event = await self._receive_event()
                await self._handle_event(event)
                
            except ConnectionClosed:
                logger.warning("WebSocket connection closed")
                break
            except WebSocketException as e:
                logger.error(f"WebSocket error: {e}")
                break
            except Exception as e:
                logger.error(f"Error processing event: {e}")
                
    async def _handle_event(self, event: Dict[str, Any]):
        """Handle incoming Gateway events."""
        opcode = event.get("op")
        
        if opcode == 0:  # DISPATCH
            self.last_sequence = event.get("s")
            event_type = event.get("t")
            event_data = event.get("d", {})
            
            logger.debug(f"Received {event_type} event")
            
            # Handle special events
            if event_type == "READY":
                self.session_id = event_data.get("session_id")
                self.resume_gateway_url = event_data.get("resume_gateway_url")
                logger.info("Gateway connection ready")
                
            elif event_type == "RESUMED":
                logger.info("Gateway session resumed")
                
            # Forward event to handler
            if self.event_handler and event_type:
                try:
                    await self.event_handler(event_type, event_data)
                except Exception as e:
                    logger.error(f"Error in event handler for {event_type}: {e}")
                    
        elif opcode == 1:  # HEARTBEAT REQUEST
            logger.debug("Received heartbeat request")
            heartbeat_payload = {
                "op": 1,  # HEARTBEAT
                "d": self.last_sequence
            }
            await self._send_payload(heartbeat_payload)
            
        elif opcode == 7:  # RECONNECT
            logger.info("Received reconnect request from Discord")
            raise ConnectionClosed(None, None)
            
        elif opcode == 9:  # INVALID SESSION
            resumable = event.get("d", False)
            if resumable:
                logger.warning("Invalid session, attempting to resume")
                await asyncio.sleep(5)
            else:
                logger.warning("Invalid session, will re-identify")
                self.session_id = None
                self.last_sequence = None
                await asyncio.sleep(5)
                
        elif opcode == 11:  # HEARTBEAT ACK
            logger.debug("Received heartbeat acknowledgment")
            
    async def _send_payload(self, payload: Dict[str, Any]):
        """Send a payload to the Gateway."""
        if not self.websocket:
            raise Exception("WebSocket not connected")
            
        data = json.dumps(payload)
        await self.websocket.send(data)
        
    async def _receive_event(self) -> Dict[str, Any]:
        """Receive and parse an event from the Gateway."""
        if not self.websocket:
            raise Exception("WebSocket not connected")
            
        data = await self.websocket.recv()
        return json.loads(data)  # type: ignore 