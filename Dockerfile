# Self-contained image: CPU-only PyTorch, the CLIP model, and a prebuilt index for the
# bundled sample images. The container starts instantly and runs fully offline.
FROM python:3.13-slim

WORKDIR /app

# libgomp is required by torch's CPU kernels on slim images.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Install CPU-only torch first (avoids pulling the multi-GB CUDA build), then the rest.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/
COPY web/ web/
COPY data/images/ data/images/

# Bake the CLIP model + index into the image so first request is fast and offline.
RUN python -m src.index data/images

EXPOSE 8000
CMD ["uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8000"]
