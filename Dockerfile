FROM python:3.9-slim AS base
SHELL ["/bin/bash", "-c"]
WORKDIR /project
ENV PYTHONPATH "${PYTHONPATH}:/project"
COPY pyproject.toml .
COPY scripts scripts
COPY app app

FROM base AS development
CMD rm -rf .venv/* \    
    && bash scripts/poetry_install.sh \
    && bash scripts/run_jupyter.sh

FROM base AS production
COPY poetry.lock .
ARG build_env
RUN scripts/poetry_install.sh
RUN rm -r scripts
CMD poetry run python app/runner.py