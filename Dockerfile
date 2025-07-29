# Multi-stage Dockerfile for Discord Bridge

# Build stage
FROM python:3.11-slim AS builder

# Install uv for fast dependency management
RUN pip install uv

# Set working directory
WORKDIR /app

# Copy project files
COPY pyproject.toml ./
COPY src/ ./src/

# Install dependencies and build the project
RUN uv venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN uv pip install -e .

# Runtime stage
FROM python:3.11-slim AS runtime

# Install ca-certificates for HTTPS requests
RUN apt-get update && apt-get install -y \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Activate virtual environment
ENV PATH="/opt/venv/bin:$PATH"

# Create non-root user for security
RUN groupadd -r discord && useradd -r -g discord discord

# Set working directory
WORKDIR /app

# Change ownership to non-root user
RUN chown -R discord:discord /app

# Switch to non-root user
USER discord

# Expose any ports if needed (none required for this application)

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Set default environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV LOG_LEVEL=INFO
ENV LOG_FORMAT=json

# Default command
CMD ["discord-bridge"]

# Labels for metadata
LABEL org.opencontainers.image.title="Discord Bridge"
LABEL org.opencontainers.image.description="Discord Gateway API bridge that forwards events to HTTP endpoints"
LABEL org.opencontainers.image.version="0.1.0"
LABEL org.opencontainers.image.authors="mark-j"
LABEL org.opencontainers.image.source="https://github.com/mark-j/discord-bridge"
LABEL org.opencontainers.image.licenses="MIT" 