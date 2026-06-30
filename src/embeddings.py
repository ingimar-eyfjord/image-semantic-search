"""CLIP embeddings: images and text mapped into one shared vector space.

A single model (OpenAI CLIP, ViT-B/32) encodes both images and natural-language
queries. Because both live in the same space, semantic search is just a cosine
similarity between the query vector and each image vector.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image
from sentence_transformers import SentenceTransformer

MODEL_NAME = "clip-ViT-B-32"


class ClipEmbedder:
    """Thin wrapper around the CLIP model that returns L2-normalized vectors.

    Vectors are normalized so a dot product equals cosine similarity, which keeps
    search a single fast matrix-vector multiply.
    """

    def __init__(self, model_name: str = MODEL_NAME) -> None:
        self.model = SentenceTransformer(model_name)

    def embed_images(self, paths: list[Path]) -> np.ndarray:
        images = [Image.open(p).convert("RGB") for p in paths]
        vectors = self.model.encode(
            images, batch_size=16, convert_to_numpy=True, show_progress_bar=False
        )
        return _normalize(vectors)

    def embed_text(self, text: str) -> np.ndarray:
        vector = self.model.encode([text], convert_to_numpy=True, show_progress_bar=False)
        return _normalize(vector)[0]


def _normalize(vectors: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    return vectors / np.clip(norms, 1e-12, None)
