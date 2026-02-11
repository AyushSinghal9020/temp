FROM python:3.12-slim AS build
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/

USER root
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1000 user
USER user

ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    UV_PYTHON=python3.12 \ 
    UV_COMPILE_BYTECODE=1 \ 
    PYTHONUNBUFFERED=1

WORKDIR $HOME/app

# Copy workspace files
COPY --chown=user pyproject.toml uv.lock ./
COPY --chown=user agent ./agent
COPY --chown=user llm ./llm
COPY --chown=user src ./src

RUN uv sync --package agent --python 3.12

CMD ["uv", "run", "--package", "agent", "agent"]