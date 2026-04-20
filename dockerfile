FROM nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=compute,utility \
    MARIMO_HOST=0.0.0.0 \
    MARIMO_PORT=2718 \
    HF_HOME=/workspace/.cache/huggingface \
    TRANSFORMERS_CACHE=/workspace/.cache/huggingface

WORKDIR /workspace

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-venv \
    git \
    curl \
    ca-certificates \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN ln -sf /usr/bin/python3 /usr/bin/python && \
    python -m pip install --upgrade pip setuptools wheel

COPY requirements.txt /workspace/requirements.txt
RUN python -m pip install -r /workspace/requirements.txt

RUN mkdir -p /workspace/notebooks /workspace/.cache/huggingface

EXPOSE 2718

CMD ["sh", "-lc", "marimo edit /workspace --host ${MARIMO_HOST} --port ${MARIMO_PORT} --headless --no-token"]