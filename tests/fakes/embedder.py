"""Fake embedder for deterministic offline testing — 384 dims, no model download."""

from __future__ import annotations

import hashlib
import struct


class FakeEmbedder:
    """Returns a deterministic 384-dim vector seeded by text hash."""

    @property
    def dimension(self) -> int:
        return 384

    async def embed(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode()).digest()
        result: list[float] = []
        for i in range(384):
            offset = (i * 7 + struct.unpack("B", digest[i % 32 : i % 32 + 1])[0]) % 256
            result.append(offset / 255.0)
        return result
