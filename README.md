# Discord Bridge

A Python application that connects to Discord's Gateway API, receives events, and forwards them to HTTP endpoints as POST requests.

## Features

- 🚀 **Reliable Gateway Connection**: Automatic reconnection, heartbeat management, and session resuming
- 📡 **Event Routing**: Configurable routing of Discord events to HTTP webhooks
- 🔄 **HTTP Forwarding**: Reliable HTTP POST requests with retry logic and error handling  
- ⚙️ **Flexible Configuration**: YAML files or environment variables
- 📊 **Structured Logging**: JSON or console logging with configurable levels
- 🐳 **Docker Ready**: Multi-stage Dockerfile with security best practices
- 🔧 **Development Friendly**: Built with `uv` for fast dependency management

## Quick Start

### Using Environment Variables

1. **Set your Discord bot token:**
   ```bash
   export DISCORD_TOKEN="Bot YOUR_BOT_TOKEN_HERE"
   ```

2. **Run with uv:**
   ```bash
   uv run discord-bridge
   ```

### Using Configuration File

1. **Create a configuration file:**
   ```bash
   cp config.example.yaml config.yaml
   # Edit config.yaml with your settings
   ```

2. **Run with config file:**
   ```bash
   uv run discord-bridge --config config.yaml
   ```

### Using Docker

```bash
docker run -e DISCORD_TOKEN="Bot YOUR_TOKEN" ghcr.io/mark-j/discord-bridge:latest
```

## Installation

### Prerequisites

- Python 3.11 or higher
- [uv](https://docs.astral.sh/uv/) package manager
- Discord bot token (get one from [Discord Developer Portal](https://discord.com/developers/applications))

### Local Development

1. **Clone the repository:**
   ```bash
   git clone https://github.com/mark-j/discord-bridge.git
   cd discord-bridge
   ```

2. **Install dependencies:**
   ```bash
   uv sync
   ```

3. **Run the application:**
   ```bash
   uv run discord-bridge --help
   ```

## Configuration

### Discord Bot Setup

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application
3. Go to the "Bot" section
4. Create a bot and copy the token
5. Under "Privileged Gateway Intents", enable the intents you need:
   - **Server Members Intent** (for member events)
   - **Message Content Intent** (for message content)

### Configuration Methods

#### 1. YAML Configuration File

Create a `config.yaml` file (see `config.example.yaml` for a template):

```yaml
discord:
  token: "Bot YOUR_BOT_TOKEN_HERE"
  intents: 513  # GUILDS + GUILD_MESSAGES

http:
  timeout: 30
  retry_attempts: 3
  retry_delay: 2

logging:
  level: "INFO"
  format: "console"

routes:
  - event_name: "MESSAGE_CREATE"
    enabled: true
    endpoints:
      - "https://your-webhook.example.com/discord/messages"
  
  - event_name: "GUILD_MEMBER_ADD"
    enabled: true
    endpoints:
      - "https://your-api.example.com/webhooks/member-join"
```

#### 2. Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DISCORD_TOKEN` | Discord bot token (required) | - |
| `DISCORD_INTENTS` | Gateway intents bitmask | `513` |
| `HTTP_TIMEOUT` | HTTP request timeout (seconds) | `30` |
| `HTTP_RETRY_ATTEMPTS` | Number of retry attempts | `3` |
| `HTTP_RETRY_DELAY` | Delay between retries (seconds) | `1` |
| `LOG_LEVEL` | Log level (DEBUG, INFO, WARNING, ERROR) | `INFO` |
| `LOG_FORMAT` | Log format (json, console) | `json` |

### Discord Gateway Intents

Common intent combinations:

| Intent | Value | Description |
|--------|-------|-------------|
| `GUILDS` | 1 | Guild events (join, leave, update) |
| `GUILD_MEMBERS` | 2 | Member join/leave events |
| `GUILD_MODERATION` | 4 | Ban/unban events |
| `GUILD_MESSAGES` | 512 | Message events in guilds |
| `MESSAGE_CONTENT` | 32768 | Access to message content |

**Default (513)** = `GUILDS` + `GUILD_MESSAGES`

Calculate custom intents: [Discord Intents Calculator](https://discord-intents-calculator.vercel.app/)

### Event Types

Common Discord events you can route:

- `MESSAGE_CREATE` - New message posted
- `MESSAGE_UPDATE` - Message edited
- `MESSAGE_DELETE` - Message deleted
- `GUILD_MEMBER_ADD` - User joins guild
- `GUILD_MEMBER_REMOVE` - User leaves guild
- `GUILD_CREATE` - Bot joins a guild
- `CHANNEL_CREATE` - New channel created
- `CHANNEL_DELETE` - Channel deleted
- `GUILD_BAN_ADD` - User banned
- `GUILD_BAN_REMOVE` - User unbanned
- `VOICE_STATE_UPDATE` - Voice channel activity

[Full list of Gateway events](https://discord.com/developers/docs/topics/gateway-events)

## HTTP Webhook Format

Events are forwarded as POST requests with the following JSON structure:

```json
{
  "event_type": "MESSAGE_CREATE",
  "data": {
    "id": "1234567890123456789",
    "content": "Hello, world!",
    "author": {
      "id": "1234567890123456789", 
      "username": "example_user"
    }
  },
  "timestamp": "2024-01-15T10:30:00.000Z",
  "source": "discord-bridge"
}
```

## Running in Production

### Docker

#### Using Pre-built Image

```bash
# Pull from GitHub Container Registry
docker pull ghcr.io/mark-j/discord-bridge:latest

# Run with environment variables
docker run -d \
  --name discord-bridge \
  -e DISCORD_TOKEN="Bot YOUR_TOKEN_HERE" \
  -e LOG_LEVEL="INFO" \
  -e LOG_FORMAT="json" \
  ghcr.io/mark-j/discord-bridge:latest

# Run with config file
docker run -d \
  --name discord-bridge \
  -v $(pwd)/config.yaml:/app/config.yaml \
  ghcr.io/mark-j/discord-bridge:latest \
  discord-bridge --config /app/config.yaml
```

#### Building Locally

```bash
# Build the image
docker build -t discord-bridge .

# Run the container  
docker run -e DISCORD_TOKEN="Bot YOUR_TOKEN" discord-bridge
```

### Docker Compose

Create a `docker-compose.yml`:

```yaml
version: '3.8'

services:
  discord-bridge:
    image: ghcr.io/mark-j/discord-bridge:latest
    restart: unless-stopped
    environment:
      - DISCORD_TOKEN=Bot YOUR_TOKEN_HERE
      - LOG_LEVEL=INFO
      - LOG_FORMAT=json
    # Optional: mount config file
    # volumes:
    #   - ./config.yaml:/app/config.yaml
    # command: discord-bridge --config /app/config.yaml
```

Run with:
```bash
docker-compose up -d
```

## Development

### Project Structure

```
discord-bridge/
├── src/discord_bridge/    # Main application code
│   ├── __init__.py       # Package exports
│   ├── config.py         # Configuration management
│   ├── gateway.py        # Discord Gateway client
│   ├── router.py         # Event routing and HTTP forwarding
│   └── main.py           # Application entry point
├── tests/                # Test files
├── config.example.yaml   # Example configuration
├── Dockerfile           # Container build instructions
├── pyproject.toml       # Python project configuration
└── README.md           # This file
```

### Local Development Setup

1. **Clone and setup:**
   ```bash
   git clone https://github.com/mark-j/discord-bridge.git
   cd discord-bridge
   uv sync
   ```

2. **Run tests:**
   ```bash
   uv run pytest
   ```

3. **Run linting:**
   ```bash
   uv run ruff check src/
   uv run mypy src/discord_bridge/
   ```

4. **Run locally with debug logging:**
   ```bash
   uv run discord-bridge --log-level DEBUG
   ```

### Debugging

#### Enable Debug Logging

```bash
# Command line
uv run discord-bridge --log-level DEBUG

# Environment variable
export LOG_LEVEL=DEBUG
uv run discord-bridge

# Config file
# Set logging.level: "DEBUG" in config.yaml
```

#### Common Issues

**Connection Issues:**
- Verify your bot token is correct and properly formatted (`Bot YOUR_TOKEN`)
- Check if your bot has the required permissions in Discord guilds
- Ensure your intents are properly configured for the events you want

**No Events Received:**
- Check your intent configuration - many events require specific intents
- Verify your bot is in the guilds where events are happening
- Enable debug logging to see connection status

**HTTP Forwarding Failures:**
- Check endpoint URLs are accessible from your network
- Verify endpoints accept POST requests with JSON content
- Check logs for HTTP status codes and error messages

#### Testing Webhooks Locally

Use tools like [ngrok](https://ngrok.com/) to expose a local server:

```bash
# Start a simple HTTP server for testing
python -m http.server 8000

# In another terminal, expose it publicly
ngrok http 8000

# Use the ngrok URL in your configuration
```

### Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes and add tests
4. Run the test suite: `uv run pytest`
5. Run linting: `uv run ruff check src/`
6. Commit your changes: `git commit -am 'Add feature'`
7. Push to the branch: `git push origin feature-name`
8. Create a Pull Request

## CI/CD

This project uses GitHub Actions for continuous integration:

- **Tests**: Runs on Python 3.11 with pytest, ruff, and mypy
- **Docker Build**: Multi-architecture builds (amd64/arm64) pushed to GitHub Container Registry
- **Security**: Container images are signed and have build provenance attestation

### Automatic Builds

The workflow triggers on:
- **Push to `main` or `develop`** - Creates `main`/`develop` and `main-abc1234` tags
- **Pull requests to `main`** - Runs tests only (no image build)
- **Version tags (`v*`)** - Creates semantic version tags (see Releases below)

### Releases

To create a new release with semantic versioning:

```bash
# 1. Tag your commit with semantic version
git tag v1.0.0

# 2. Push the tag to trigger release build
git push origin v1.0.0
```

This creates Docker images with multiple tags:
- `ghcr.io/mark-j/discord-bridge:v1.0.0` (exact version)
- `ghcr.io/mark-j/discord-bridge:1.0` (minor version)
- `ghcr.io/mark-j/discord-bridge:1` (major version)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- 📖 [Discord API Documentation](https://discord.com/developers/docs)
- 🐛 [Report Issues](https://github.com/mark-j/discord-bridge/issues)
- 💬 [Discussions](https://github.com/mark-j/discord-bridge/discussions)

## Security

This application handles sensitive Discord bot tokens. Best practices:

- Never commit tokens to version control
- Use environment variables or secure secret management
- Run containers with non-root users (handled automatically)
- Keep dependencies updated
- Monitor logs for security events

For security issues, please create an issue on the GitHub repository.
