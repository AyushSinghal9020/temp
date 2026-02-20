# Stage 1: The Builder
FROM python:3.12-slim AS builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/

# Install system dependencies needed for building
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Enable bytecode compilation and set uv environment
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Copy only the dependency files first to leverage caching
COPY pyproject.toml uv.lock ./

# COPY agent/pyproject.toml ./agent/
# COPY call/pyproject.toml ./call/
# COPY rag/pyproject.toml ./rag/

# Install all workspace dependencies 
# (This creates a shared virtualenv for all packages)
RUN uv sync --frozen --no-install-project --no-dev

# Copy the rest of the application code
COPY . .

# Final sync to install the packages themselves
# RUN uv sync --frozen --no-dev --all-packages --no-editable

# Stage 2: The Final Runtime (The "Slim" part)
FROM python:3.12-slim

RUN apt-get update && apt-get install -y supervisor && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/

RUN useradd -m -u 1000 user
USER user
WORKDIR /home/user/app

# Copy the synced environment and code from the builder
COPY --from=builder --chown=user /app .

COPY --chown=user supervisord.conf /etc/supervisord/conf.d/supervisord.conf

# Set up the Path to use the uv-created virtualenv
ENV PATH="/home/user/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

CMD ["/usr/bin/supervisord" , "-c" , "/etc/supervisord/conf.d/supervisord.conf"]
