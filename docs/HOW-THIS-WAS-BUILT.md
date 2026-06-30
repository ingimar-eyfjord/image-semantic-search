<!-- PUBLIC. Fill the <...> at the end of the build. This is the orchestration narrative. -->

# How this was built

This solution was built in a fixed timebox by orchestrating parallel AI agents under explicit
verification gates. The goal of this document is to show the *method and the judgment*, not to
claim the code wrote itself. Every design decision and every shipped line was reviewed and is
explainable.

## The orchestration approach

1. **Scope.** The problem was restated in one sentence and the work-list (data shape,
   independent tasks) was mapped directly before any delegation.
2. **Decompose into independent seams.** The build was split into tasks that own distinct
   modules so they can be implemented concurrently without collision.
3. **Fan out with structured output.** Each task was implemented by a dedicated agent that
   returns a typed result, so integration is code over data rather than reading prose.
4. **Adversarial verification.** Every implementation was checked by an independent agent
   prompted to refute it, and confirmed with a real run. Passing linters alone was never
   treated as proof of correctness.
5. **Integrate and harden.** Results were merged on a always-runnable main, then a final
   find-and-verify pass hunted for remaining defects.

The scripts that drove this are in [`workflows/`](../workflows): `scope-map`, `implement-fanout`,
`find-verify`, and `judge-panel`. The operating discipline is in [`CLAUDE.md`](../CLAUDE.md).

## What I actually did for this problem

The problem in one sentence: let a user find images in a folder by describing them in plain
language, ranked by meaning rather than filenames or tags.

- **Scoped the data shape first.** The input is a flat folder of images and the query is free
  text. That immediately framed the core decision as cross-modal retrieval, which is what fixed
  the architecture before any code was written.
- **Chose CLIP + a NumPy index over a tagging pipeline or a vector database.** CLIP puts images
  and text in one shared space, so search is a cosine similarity and no captioning step is
  needed. At folder scale a single normalized matrix and one matrix-vector multiply beats
  standing up FAISS or pgvector, which would have added operational weight for no latency win.
- **Fanned out along independent seams that own distinct modules:** the embedding wrapper
  (`src/embeddings.py`), the index builder CLI (`src/index.py`), the FastAPI service
  (`src/app.py`), and the zero-build front end (`web/index.html`). These share only a small,
  fixed contract (the on-disk index format and the `/api/search` JSON shape), so they were built
  concurrently without collision.
- **Verified adversarially, then ran it end to end.** The key correctness gate was that the
  vectors are L2-normalized in exactly one place so the dot product genuinely equals cosine
  similarity, and that the static mounts are ordered after the API and root routes so `/api` and
  `/` are not shadowed. A real indexing run plus live queries confirmed both, which a linter
  alone could not.

## Where I used judgment over automation

- **No vector database, on purpose.** The easy "scalable" answer is to reach for FAISS or
  pgvector. The right call at this scale was a plain NumPy dot product: simpler to run, trivial
  to reason about, and fast enough. The README documents the exact threshold at which that
  decision flips.
- **Normalize once, multiply many.** Pushing L2 normalization into the embedder (rather than at
  query time) is what lets every search be a single matrix-vector multiply. That is a
  performance-shaping choice, not something to leave to chance in generated code.
- **Precomputed thumbnails and a single startup load.** Serving 400px thumbnails and loading the
  model and index once at import keeps both cost and latency down; these were deliberate trade-offs
  for a snappy demo, not defaults.

## Trade-offs made for the timebox

- The index is static; adding or removing images requires a rebuild. No incremental update path.
- Single-process and in-memory: no auth, pagination, or horizontal scaling.
- Linear scan over all vectors per query, which is fine at folder scale but would need FAISS or
  pgvector at hundreds of thousands of images and up.
- Ranking quality is capped by CLIP `ViT-B/32`; no re-ranking or hybrid keyword+vector search.
