"""Embedder port — provider-agnostic interface for text embedding."""

from __future__ import annotations

from typing import Protocol


class Embedder(Protocol):
    @property
    def dimension(self) -> int: ...

    async def embed(self, text: str) -> list[float]: ...
