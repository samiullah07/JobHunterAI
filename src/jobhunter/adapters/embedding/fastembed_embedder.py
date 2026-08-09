"""Local fastembed-based embedder — runs on CPU, no API key needed."""

from __future__ import annotations

import asyncio
from typing import Any


class FastEmbedEmbedder:
    """Implements Embedder port using fastembed (BAAI/bge-small-en-v1.5 → 384 dims)."""

    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5", dimension: int = 384) -> None:
        self._model_name = model_name
        self._dimension = dimension
        self._model: Any = None

    @property
    def dimension(self) -> int:
        return self._dimension

    def _get_model(self) -> Any:
        if self._model is None:
            from fastembed import TextEmbedding

            self._model = TextEmbedding(model_name=self._model_name)
        return self._model

    async def embed(self, text: str) -> list[float]:
        model = self._get_model()
        embeddings = await asyncio.to_thread(lambda: list(model.embed([text])))
        return [float(x) for x in embeddings[0]]
