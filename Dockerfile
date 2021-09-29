FROM python:3.9.7-slim AS base
SHELL ["/bin/bash", "-c"]
WORKDIR /project
COPY pyproject.toml .
COPY scripts scripts
COPY app app

FROM base AS development
CMD rm -rf .venv/* \    
    && bash scripts/poetry_install.sh \
    && sleep infinity