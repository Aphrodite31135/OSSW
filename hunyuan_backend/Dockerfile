FROM pytorch/pytorch:2.4.0-cuda12.1-cudnn9-runtime

ENV DEBIAN_FRONTEND=noninteractive
ENV PIP_NO_CACHE_DIR=1
ENV PYTHONUNBUFFERED=1
ENV HF_HOME=/models/hf-cache
ENV U2NET_HOME=/models/u2net

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    git-lfs \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt

RUN git clone https://github.com/Tencent-Hunyuan/Hunyuan3D-2.git

WORKDIR /opt/Hunyuan3D-2

RUN pip install -r requirements.txt && pip install -e .

WORKDIR /workspace

COPY hunyuan_backend/server.py /workspace/server.py
COPY hunyuan_backend/entrypoint.sh /workspace/entrypoint.sh

RUN chmod +x /workspace/entrypoint.sh && mkdir -p /workspace/cache /models/hf-cache /models/u2net

EXPOSE 8081

ENTRYPOINT ["/workspace/entrypoint.sh"]
