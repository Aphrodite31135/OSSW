FROM saladtechnologies/comfyui:comfy0.3.61-api1.9.2-torch2.8.0-cuda12.8-dreamshaper8

ENV COMFYUI_CHECKPOINT_NAME=SSD-1B-A1111.safetensors
ENV COMFYUI_CHECKPOINT_URL=https://huggingface.co/segmind/SSD-1B/resolve/main/SSD-1B-A1111.safetensors

COPY comfyui_custom/entrypoint.sh /usr/local/bin/ossw-comfyui-entrypoint.sh
COPY comfyui_custom/object_txt2img.ts /workflows/object_txt2img.ts
COPY comfyui_custom/warmup.json /opt/ComfyUI/warmup.json

RUN chmod +x /usr/local/bin/ossw-comfyui-entrypoint.sh

ENTRYPOINT ["/usr/local/bin/ossw-comfyui-entrypoint.sh"]
