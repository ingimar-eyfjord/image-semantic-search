"""Build and load the image search index.

The index is intentionally simple: a NumPy array of image vectors plus the list of
filenames. For a folder of images this is fast, cheap, and trivial to reason about
(no vector database to run). Thumbnails are generated once so the UI serves small
files for low latency.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image

from .embeddings import ClipEmbedder

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}
THUMB_SIZE = (400, 400)


def list_images(image_dir: Path) -> list[Path]:
    return sorted(p for p in image_dir.iterdir() if p.suffix.lower() in IMAGE_EXTENSIONS)


def build_index(image_dir: Path, index_dir: Path) -> int:
    """Embed every image in ``image_dir`` and persist vectors, names, and thumbnails."""
    index_dir.mkdir(parents=True, exist_ok=True)
    thumb_dir = index_dir / "thumbs"
    thumb_dir.mkdir(exist_ok=True)

    paths = list_images(image_dir)
    if not paths:
        raise SystemExit(f"No images found in {image_dir}")

    embedder = ClipEmbedder()
    vectors = embedder.embed_images(paths)

    for p in paths:
        thumb = Image.open(p).convert("RGB")
        thumb.thumbnail(THUMB_SIZE)
        thumb.save(thumb_dir / f"{p.stem}.jpg", "JPEG", quality=82)

    np.save(index_dir / "vectors.npy", vectors)
    (index_dir / "filenames.json").write_text(json.dumps([p.name for p in paths], indent=2))
    print(f"Indexed {len(paths)} images -> {index_dir}")
    return len(paths)


def load_index(index_dir: Path) -> tuple[np.ndarray, list[str]]:
    vectors = np.load(index_dir / "vectors.npy")
    filenames = json.loads((index_dir / "filenames.json").read_text())
    return vectors, filenames


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the image search index.")
    parser.add_argument("image_dir", type=Path, help="Folder of images to index")
    parser.add_argument("--index-dir", type=Path, default=Path("data/index"))
    args = parser.parse_args()
    build_index(args.image_dir, args.index_dir)


if __name__ == "__main__":
    main()
