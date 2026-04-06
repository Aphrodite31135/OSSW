FROM pytorch/pytorch:2.4.0-cuda12.1-cudnn9-runtime

ENV DEBIAN_FRONTEND=noninteractive
ENV PIP_NO_CACHE_DIR=1
ENV PYTHONUNBUFFERED=1
ENV HF_HOME=/models/hf-cache

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

RUN pip install --no-cache-dir \
    fastapi==0.115.0 \
    uvicorn[standard]==0.30.6 \
    diffusers==0.30.3 \
    transformers==4.44.2 \
    accelerate==0.33.0 \
    safetensors==0.4.4 \
    pillow==11.0.0

COPY text2image_backend/server.py /workspace/server.py

RUN mkdir -p /workspace/cache /models/hf-cache

EXPOSE 8090

CMD ["python", "/workspace/server.py"]
