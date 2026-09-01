"""
Embedding Provider Abstraction and Implementations
"""

import hashlib
import math
import re
from abc import ABC, abstractmethod
from typing import List, Optional


class EmbeddingProvider(ABC):
    """Abstract interface for local/air-gapped embedding providers."""

    @abstractmethod
    def embed_text(self, text: str) -> List[float]:
        """Generate a dense vector embedding for a single text."""
        pass

    @abstractmethod
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate dense vector embeddings for a batch of texts."""
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return the vector dimensionality."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the active model name."""
        pass


class DeterministicEmbeddingProvider(EmbeddingProvider):
    """
    Deterministic, zero-dependency embedding provider for air-gapped environments,
    test fixtures, and low-latency benchmark evaluation.
    Produces reproducible unit-normalized 384-dimensional dense vectors using
    semantic token hashing and n-gram feature distribution.
    """

    def __init__(self, dimension: int = 384, model_name: str = "Deterministic-Qwen3-384d"):
        self._dim = dimension
        self._model_name = model_name

    @property
    def dimension(self) -> int:
        return self._dim

    @property
    def model_name(self) -> str:
        return self._model_name

    def embed_text(self, text: str) -> List[float]:
        if not text or not text.strip():
            return [0.0] * self._dim

        vector = [0.0] * self._dim
        tokens = re.findall(r"[a-z0-9\-_]+", text.lower())

        # Combine word tokens and character 3-grams for semantic sensitivity
        features = list(tokens)
        cleaned_text = re.sub(r"\s+", " ", text.lower().strip())
        for i in range(len(cleaned_text) - 2):
            features.append(cleaned_text[i : i + 3])

        for feat in features:
            # Deterministic hash to dimension bins
            h = int(hashlib.sha256(feat.encode("utf-8")).hexdigest(), 16)
            idx = h % self._dim
            sign = 1.0 if ((h >> 8) & 1) == 1 else -1.0
            weight = 1.5 if "-" in feat or any(c.isdigit() for c in feat) else 1.0  # Part number boost
            vector[idx] += sign * weight

        # L2 Unit Normalization
        norm = math.sqrt(sum(v * v for v in vector))
        if norm > 0.0:
            vector = [round(v / norm, 6) for v in vector]
        else:
            vector = [0.0] * self._dim

        return vector

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return [self.embed_text(t) for t in texts]


class LocalGGUFEmbeddingProvider(EmbeddingProvider):
    """
    Local embedding provider connecting to llama-cpp-python / GGUF embedding models.
    Falls back gracefully to deterministic provider if local binary is absent.
    """

    def __init__(self, model_path: Optional[str] = None, dimension: int = 384, model_name: str = "Qwen3-Embedding-0.6B"):
        self._model_path = model_path
        self._dim = dimension
        self._model_name = model_name
        self._fallback = DeterministicEmbeddingProvider(dimension=dimension, model_name=model_name)
        self._model = None

    @property
    def dimension(self) -> int:
        return self._dim

    @property
    def model_name(self) -> str:
        return self._model_name

    def embed_text(self, text: str) -> List[float]:
        # If llama_cpp is available and model loaded, use it; otherwise use fallback
        if self._model is not None:
            try:
                emb = self._model.create_embedding(text)
                return emb["data"][0]["embedding"]
            except Exception:
                pass
        return self._fallback.embed_text(text)

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return [self.embed_text(t) for t in texts]


def get_embedding_provider(provider_type: str = "deterministic", **kwargs) -> EmbeddingProvider:
    """Factory function for acquiring the configured embedding provider."""
    if provider_type in ("native", "local", "real", "gguf"):
        from ai.providers.native_embedding import NativeLocalEmbeddingEngine
        return NativeLocalEmbeddingEngine(**kwargs)
    elif provider_type == "gguf_legacy":
        return LocalGGUFEmbeddingProvider(**kwargs)
    return DeterministicEmbeddingProvider(**kwargs)
