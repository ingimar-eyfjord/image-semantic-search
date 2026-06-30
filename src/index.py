"""Build, update, and load the image search index.

The index is intentionally simple: a NumPy array of image vectors plus the list of
filenames. For a folder of images this is fast, cheap, and trivial to reason about
(no vector database to run). Thumbnails are generated once so the UI serves small
files for low latency.

Two modes:
- ``build``  embeds every image from scratch.
- ``update`` syncs the index to the folder, embedding only newly added images and
  dropping deleted ones, so a changing folder does not pay a full re-embed each time.
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


def _make_thumbnail(path: Path, thumb_dir: Path) -> None:
    thumb = Image.open(path).convert("RGB")
    thumb.thumbnail(THUMB_SIZE)
    thumb.save(thumb_dir / f"{path.stem}.jpg", "JPEG", quality=82)


def _save(index_dir: Path, vectors: np.ndarray, filenames: list[str]) -> None:
    np.save(index_dir / "vectors.npy", vectors)
    (index_dir / "filenames.json").write_text(json.dumps(filenames, indent=2))


def build_index(image_dir: Path, index_dir: Path) -> int:
    """Embed every image in ``image_dir`` and persist vectors, names, and thumbnails."""
    thumb_dir = index_dir / "thumbs"
    thumb_dir.mkdir(parents=True, exist_ok=True)

    paths = list_images(image_dir)
    if not paths:
        raise SystemExit(f"No images found in {image_dir}")

    embedder = ClipEmbedder()
    vectors = embedder.embed_images(paths)
    for p in paths:
        _make_thumbnail(p, thumb_dir)

    _save(index_dir, vectors, [p.name for p in paths])
    print(f"Indexed {len(paths)} images -> {index_dir}")
    return len(paths)


def update_index(image_dir: Path, index_dir: Path) -> int:
    """Incrementally sync the index to the folder.

    Embeds only images not already in the index, drops images no longer in the folder,
    and keeps the existing vectors for everything unchanged. Falls back to a full build
    if no index exists yet.
    """
    if not (index_dir / "vectors.npy").exists():
        return build_index(image_dir, index_dir)

    vectors, filenames = load_index(index_dir)
    thumb_dir = index_dir / "thumbs"
    thumb_dir.mkdir(exist_ok=True)

    current = {p.name: p for p in list_images(image_dir)}
    existing = set(filenames)

    # Keep unchanged rows (preserving vector/name alignment), drop deletions.
    keep_idx = [i for i, name in enumerate(filenames) if name in current]
    removed = [name for name in filenames if name not in current]
    new_paths = [p for name, p in current.items() if name not in existing]

    kept_names = [filenames[i] for i in keep_idx]
    kept_vectors = vectors[keep_idx]  # vectors[[]] is a valid (0, dim) array

    if new_paths:
        new_vectors = ClipEmbedder().embed_images(new_paths)
        for p in new_paths:
            _make_thumbnail(p, thumb_dir)
        out_vectors = np.vstack([kept_vectors, new_vectors])
        out_names = kept_names + [p.name for p in new_paths]
    else:
        out_vectors, out_names = kept_vectors, kept_names

    for name in removed:
        (thumb_dir / f"{Path(name).stem}.jpg").unlink(missing_ok=True)

    _save(index_dir, out_vectors, out_names)
    print(
        f"Updated {index_dir}: +{len(new_paths)} new, "
        f"-{len(removed)} removed, {len(out_names)} total"
    )
    return len(out_names)


def load_index(index_dir: Path) -> tuple[np.ndarray, list[str]]:
    vectors = np.load(index_dir / "vectors.npy")
    filenames = json.loads((index_dir / "filenames.json").read_text())
    return vectors, filenames


def main() -> None:
    parser = argparse.ArgumentParser(description="Build or update the image search index.")
    parser.add_argument("image_dir", type=Path, help="Folder of images to index")
    parser.add_argument("--index-dir", type=Path, default=Path("data/index"))
    parser.add_argument(
        "--update",
        action="store_true",
        help="Incrementally sync the index (embed only new images, drop deleted)",
    )
    args = parser.parse_args()
    if args.update:
        update_index(args.image_dir, args.index_dir)
    else:
        build_index(args.image_dir, args.index_dir)


if __name__ == "__main__":
    main()
