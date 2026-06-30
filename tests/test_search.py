"""Unit tests for the pure logic that does not require the CLIP model."""

from __future__ import annotations

import numpy as np

from src.embeddings import _normalize
from src.index import list_images


def test_normalize_produces_unit_vectors():
    vectors = np.array([[3.0, 4.0], [0.0, 2.0], [0.0, 0.0]])
    out = _normalize(vectors)
    norms = np.linalg.norm(out, axis=1)
    # Non-zero rows become unit length; the zero row stays finite (no divide-by-zero).
    assert np.allclose(norms[:2], 1.0)
    assert np.isfinite(out).all()


def test_list_images_filters_and_sorts(tmp_path):
    (tmp_path / "b.jpg").write_bytes(b"x")
    (tmp_path / "a.PNG").write_bytes(b"y")
    (tmp_path / "notes.txt").write_text("ignore me")
    names = [p.name for p in list_images(tmp_path)]
    assert names == ["a.PNG", "b.jpg"]
