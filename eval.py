"""Evaluation harness for the image semantic search.

Runs a small set of labeled queries through the *same* search logic the API uses
(reusing ``ClipEmbedder`` and ``load_index`` directly, no HTTP), and reports:

  * top-1 accuracy      - was the #1 result a relevant image?
  * precision@5         - of the top 5, how many were relevant (normalized by the
                          number of truly relevant images, capped at 5, so a query
                          with a single correct image is not unfairly capped at 0.20)

It then sweeps the ``min_score`` cutoff from 0.15 to 0.30 and prints the value that
best separates relevant from irrelevant matches (highest F1 over every
query-image pair), which is the knob ``/api/search`` exposes as ``min_score``.

Run it with:

    python -m eval
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from src.embeddings import ClipEmbedder
from src.index import load_index

INDEX_DIR = Path("data/index")

# Labeled queries -> the filenames that should count as a relevant match.
# Built against the sample gallery in data/images. A mix of single-subject
# queries (which stress top-1) and multi-subject queries (which stress precision@5).
TEST_QUERIES: list[tuple[str, set[str]]] = [
    (
        "something to eat",
        {
            "bread-loaf.jpg", "chocolate-cake.jpg", "fruit-bowl.jpg", "hamburger.jpg",
            "ice-cream.jpg", "pancakes.jpg", "pasta.jpg", "pizza.jpg", "ramen.jpg",
            "salad.jpg", "sandwich.jpg", "steak.jpg", "sushi.jpg", "tacos.jpg",
        },
    ),
    ("a dog", {"dog.jpg"}),
    ("a cat", {"cat.jpg"}),
    ("snowy mountains", {"snowy-mountains.jpg"}),
    ("the beach", {"sandy-beach.jpg", "tropical-beach.jpg"}),
    ("a fast car", {"red-sports-car.jpg"}),
    ("a musical instrument", {"acoustic-guitar.jpg", "violin.jpg"}),
    ("an aircraft flying", {"airplane.jpg", "helicopter.jpg", "hot-air-balloon.jpg"}),
    ("a flower", {"sunflower.jpg", "field-of-tulips.jpg"}),
    ("public transport", {"bus.jpg", "train.jpg"}),
    ("a cup of coffee", {"coffee-cup.jpg"}),
    ("books on a shelf", {"stack-of-books.jpg"}),
]

SWEEP_START = 0.15
SWEEP_STOP = 0.30
SWEEP_STEP = 0.01


def rank(embedder: ClipEmbedder, vectors: np.ndarray, filenames: list[str], query: str):
    """Return ``[(filename, score), ...]`` sorted by descending cosine similarity.

    This mirrors ``src.app.search`` (vectors are normalized, so the dot product is
    cosine similarity) but skips the HTTP layer and the ``min_score`` cutoff so the
    harness can evaluate every score.
    """
    query_vec = embedder.embed_text(query)
    scores = vectors @ query_vec
    order = np.argsort(-scores)
    return [(filenames[i], float(scores[i])) for i in order]


def evaluate() -> None:
    vectors, filenames = load_index(INDEX_DIR)
    known = set(filenames)
    embedder = ClipEmbedder()

    # Sanity-check the labels so a typo fails loudly instead of silently scoring 0.
    for query, relevant in TEST_QUERIES:
        missing = relevant - known
        if missing:
            raise SystemExit(f"Query {query!r} references unknown files: {sorted(missing)}")

    print(f"Evaluating {len(TEST_QUERIES)} queries over {len(filenames)} images\n")
    header = f"{'query':<24} {'top-1':<7} {'P@5':<6} top result"
    print(header)
    print("-" * len(header))

    top1_hits = 0
    p5_sum = 0.0
    # (score, is_relevant) for every query-image pair, used for the threshold sweep.
    pairs: list[tuple[float, bool]] = []

    for query, relevant in TEST_QUERIES:
        ranked = rank(embedder, vectors, filenames, query)
        for name, score in ranked:
            pairs.append((score, name in relevant))

        top_name, top_score = ranked[0]
        top1 = top_name in relevant
        top1_hits += int(top1)

        top5 = ranked[:5]
        hits_at_5 = sum(1 for name, _ in top5 if name in relevant)
        # Normalize by the achievable maximum so single-subject queries are scored fairly.
        denom = min(5, len(relevant))
        p5 = hits_at_5 / denom
        p5_sum += p5

        mark = "ok " if top1 else "MISS"
        print(f"{query:<24} {mark:<7} {p5:<6.2f} {top_name} ({top_score:.3f})")

    n = len(TEST_QUERIES)
    print(
        f"\nTop-1 accuracy: {top1_hits}/{n} = {top1_hits / n:.1%}"
        f"   |   Mean precision@5: {p5_sum / n:.3f}"
    )

    sweep_min_score(pairs)


def sweep_min_score(pairs: list[tuple[float, bool]]) -> None:
    """Sweep the score cutoff and report the value with the best relevant/irrelevant split."""
    total_relevant = sum(1 for _, rel in pairs if rel)

    print(f"\nThreshold sweep ({SWEEP_START:.2f} -> {SWEEP_STOP:.2f}) over {len(pairs)} pairs")
    print(f"{'min_score':<11} {'precision':<11} {'recall':<9} {'F1':<7}")
    print("-" * 38)

    best = None  # (f1, threshold, precision, recall)
    # +half-step on the stop so the inclusive endpoint survives float rounding.
    thresholds = np.arange(SWEEP_START, SWEEP_STOP + SWEEP_STEP / 2, SWEEP_STEP)
    for threshold in thresholds:
        kept = [(score, rel) for score, rel in pairs if score >= threshold]
        tp = sum(1 for _, rel in kept if rel)
        fp = len(kept) - tp
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / total_relevant if total_relevant else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
        print(f"{threshold:<11.2f} {precision:<11.3f} {recall:<9.3f} {f1:<7.3f}")
        if best is None or f1 > best[0]:
            best = (f1, float(threshold), precision, recall)

    f1, threshold, precision, recall = best
    print(
        f"\nBest separation at min_score = {threshold:.2f} "
        f"(F1={f1:.3f}, precision={precision:.3f}, recall={recall:.3f})"
    )


if __name__ == "__main__":
    evaluate()
