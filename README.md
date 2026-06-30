# Image Semantic Search

Search a folder of images by describing what you want in plain language. Type
"a dog running on the beach" and the gallery is ranked by *meaning*, not filenames
or tags.

It works because a single CLIP model maps both images and text into one shared
vector space. Indexing encodes every image once; a query encodes your text once and
compares it against the stored image vectors with a single dot product. No tagging,
no vector database, no external API.

## Demo

![Semantic image search demo](docs/demo.gif)

## How it works

A small FastAPI backend serves a precomputed index and a static single-page UI:

- **`src/embeddings.py`** wraps CLIP (`clip-ViT-B-32` via `sentence-transformers`)
  and returns L2-normalized vectors, so a dot product equals cosine similarity.
- **`src/index.py`** is a CLI that embeds a folder of images and persists three
  things to `data/index/`: `vectors.npy` (the matrix of image vectors),
  `filenames.json` (the row order), and `thumbs/` (400px JPEG thumbnails).
- **`src/app.py`** loads the model and the index once at startup, then answers
  `GET /api/search?q=...&k=...` with the top-k matches and serves the UI plus
  original images and thumbnails as static files.
- **`web/index.html`** is a zero-build (Tailwind via CDN) front end: a search bar,
  a masonry results grid with similarity scores, and a lightbox.

## Usage

```bash
# 1. Install dependencies (PyTorch, CLIP, FastAPI, etc.)
pip install -r requirements.txt

# 2. Build the index from a folder of images.
#    This embeds each image and writes vectors + thumbnails to data/index/.
python -m src.index data/images

# 3. Run the server.
uvicorn src.app:app --reload

# 4. Open the UI.
open http://localhost:8000
```

The first run downloads the CLIP model weights (a few hundred MB), so it takes a
moment; subsequent runs are fast. The server expects images in `data/images` and a
prebuilt index in `data/index` (both are the defaults baked into `src/app.py` and
`src/index.py`).

### Run with Docker

The image bundles CPU-only PyTorch, the CLIP model, and a prebuilt index for the
sample images, so it starts instantly and runs fully offline.

```bash
docker build -t imgsearch .
docker run --rm -p 8000:8000 imgsearch
# open http://localhost:8000
```

To search your own folder, mount it and rebuild the index at start:

```bash
docker run --rm -p 8000:8000 -v /path/to/photos:/app/data/images \
  imgsearch sh -c "python -m src.index data/images && uvicorn src.app:app --host 0.0.0.0 --port 8000"
```

### API

```
GET /api/search?q=<text>&k=<1..50>
```

Returns JSON: the query echoed back, `took_ms`, and a `results` array of
`{ filename, thumb_url, image_url, score }`, sorted by descending cosine similarity.

## Evaluation

`eval.py` is a small harness that scores retrieval quality against a set of labeled
queries. It reuses `ClipEmbedder` and `load_index` directly (no HTTP), so it measures
the same search path the API uses. For each query it reports top-1 accuracy and
precision@5, then sweeps the `min_score` cutoff from 0.15 to 0.30 and prints the value
that best separates relevant from irrelevant matches (highest F1 over every
query-image pair). That value is the floor exposed as `min_score` on `/api/search`.

```bash
python -m eval                       # local, needs deps + a prebuilt data/index
docker run --rm imgsearch python -m eval   # inside the container (index is bundled)
```

## Flow

```mermaid
flowchart TD
    subgraph Indexing["Indexing (offline, run once)"]
        A[Images in data/images] --> B[CLIP image encoder]
        B --> C[L2-normalized vectors]
        C --> D[(vectors.npy + filenames.json)]
        A --> E[Pillow thumbnailer]
        E --> F[(thumbs/ 400px JPEGs)]
    end

    subgraph Query["Query (per request)"]
        G[Text query] --> H[CLIP text encoder]
        H --> I[Normalized query vector]
        I --> J["Cosine similarity: vectors @ query"]
        D -. loaded at startup .-> J
        J --> K[argsort -> top-k]
        K --> L[Results JSON: thumb_url + image_url + score]
        L --> M[Web UI: masonry grid + lightbox]
        F -. static thumbnails .-> M
    end
```

## Core questions

**Why CLIP?** CLIP encodes images and text into the *same* embedding space, trained
so that an image and its matching caption land near each other. That shared space is
the whole trick: cross-modal search reduces to comparing a text vector against image
vectors with ordinary cosine similarity. No per-image captioning or tagging step is
needed, and queries can be arbitrary natural language rather than a fixed label set.

**Why no vector database?** At folder scale, the index is just a NumPy array and the
search is one matrix-vector multiply (`vectors @ query`). That is simpler to run,
reason about, and deploy than standing up a vector DB, and it is plenty fast for
thousands of images. You would reach for FAISS (in-process, scales to millions of
vectors with approximate nearest-neighbor indexes) or pgvector (when the vectors
should live next to relational data and be queried with SQL) once a linear scan over
every vector per query stops being instant, roughly in the hundreds-of-thousands to
millions range, or when you need persistence, filtering, and concurrent writers.

**How it stays cheap.** The model runs locally, so there is zero per-query API cost.
The index lives in memory as a single NumPy array loaded once at startup, and the UI
serves small precomputed thumbnails instead of full-resolution originals, keeping
bandwidth and memory low.

**How it achieves low latency.** All image vectors are embedded and L2-normalized
ahead of time, so a query is just one text embedding plus a single matrix-vector
multiply and an `argsort` for the top-k. Because vectors are normalized, the dot
product *is* the cosine similarity, with no extra division per comparison. The model
and index are loaded once at startup (not per request), and thumbnails are served as
static files, so rendering a page of results never touches the originals.

**Limitations / what is next.**
- The index is static: adding or removing images means rebuilding (`python -m src.index`).
  An incremental append + delete path would help.
- Everything is in memory and single-process; there is no auth, pagination, or
  horizontal scaling.
- Search is a full linear scan, fine at folder scale, but see the FAISS/pgvector note
  above for when to swap it out.
- Ranking quality is bounded by CLIP `ViT-B/32`; a larger CLIP variant trades latency
  for accuracy.
- No re-ranking, metadata filtering, or hybrid (keyword + vector) search yet.

## How this was built

This repository was built by orchestrating parallel AI agents under explicit
verification gates, not by coding linearly or trusting model output blindly. The
operating discipline is in [`CLAUDE.md`](CLAUDE.md), the orchestration scripts are in
[`workflows/`](workflows/), and the full build narrative is in
[`docs/HOW-THIS-WAS-BUILT.md`](docs/HOW-THIS-WAS-BUILT.md).
