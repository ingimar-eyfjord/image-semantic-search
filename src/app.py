"""FastAPI app: semantic image search over a pre-built index.

At startup it loads the cached vectors and the CLIP model once. Each query is a
single text embedding plus a dot product against the (normalized) image vectors,
so search is fast even on CPU. Images and thumbnails are served as static files.
"""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .embeddings import ClipEmbedder
from .index import _make_thumbnail, _save, load_index

IMAGE_DIR = Path("data/images")
INDEX_DIR = Path("data/index")
WEB_DIR = Path("web")

app = FastAPI(title="Image Semantic Search")

# Loaded once at import/startup so requests stay cheap.
_embedder = ClipEmbedder()
_vectors, _filenames = load_index(INDEX_DIR)


@app.get("/api/search")
def search(
    q: str = Query(..., min_length=1),
    k: int = Query(12, ge=1, le=50),
    min_score: float = Query(0.23, ge=0.0, le=1.0),
) -> dict:
    """Return the top-k images most similar to the query text.

    ``min_score`` drops weak matches so a query with few true matches returns a short,
    relevant list instead of padding the grid with unrelated images. The default of 0.23
    was tuned with the eval harness (see eval.py): it maximized F1 across a labeled set of
    queries. CLIP cosine scores run ~0.15 for unrelated and ~0.25+ for a strong match.
    """
    start = time.perf_counter()
    query_vec = _embedder.embed_text(q)
    scores = _vectors @ query_vec  # cosine similarity (vectors are normalized)
    ranked = [i for i in np.argsort(-scores) if scores[i] >= min_score][:k]
    results = [
        {
            "filename": _filenames[i],
            "thumb_url": f"/thumbs/{Path(_filenames[i]).stem}.jpg",
            "image_url": f"/images/{_filenames[i]}",
            "score": round(float(scores[i]), 4),
        }
        for i in ranked
    ]
    took_ms = round((time.perf_counter() - start) * 1000, 1)
    return {"query": q, "took_ms": took_ms, "results": results}


@app.post("/api/images")
async def add_image(file: UploadFile = File(...)) -> dict:  # noqa: B008 (FastAPI idiom)
    """Add one uploaded image to the live index, embedding only that image.

    This is the incremental index path exposed over HTTP: the new vector is appended to
    the in-memory matrix (and persisted) so the image is searchable immediately, without
    re-embedding the rest of the folder.
    """
    global _vectors, _filenames
    name = Path(file.filename or "upload.jpg").name
    dest = IMAGE_DIR / name
    if dest.exists():  # don't clobber an existing image
        dest = IMAGE_DIR / f"{dest.stem}-{len(_filenames)}{dest.suffix}"

    dest.write_bytes(await file.read())
    try:
        vector = _embedder.embed_images([dest])  # opening the file validates it is an image
    except Exception as exc:
        dest.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="Could not read that file as an image") from exc

    _make_thumbnail(dest, INDEX_DIR / "thumbs")
    _vectors = np.vstack([_vectors, vector])
    _filenames.append(dest.name)
    _save(INDEX_DIR, _vectors, _filenames)
    return {"filename": dest.name, "indexed": True, "total": len(_filenames)}


@app.get("/")
def home() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


# Static mounts come last so /api and / take precedence.
app.mount("/thumbs", StaticFiles(directory=INDEX_DIR / "thumbs"), name="thumbs")
app.mount("/images", StaticFiles(directory=IMAGE_DIR), name="images")
