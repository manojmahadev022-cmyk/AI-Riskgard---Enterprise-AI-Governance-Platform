"""AI Provider abstraction for AI RiskGuard.

Provides an optional AI layer for text summarisation only.
All research retrieval and deterministic scoring work without any AI provider.

Configured via environment variable AI_PROVIDER:
    local   → FallbackProvider (sentence extraction, no network call)
    ollama  → OllamaProvider   (calls local Ollama REST API)
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Optional

import httpx

from backend.core.config import settings

logger = logging.getLogger(__name__)


class AIProvider(ABC):
    """Abstract base class for optional AI summarisation."""

    @abstractmethod
    def generate_summary(self, text: str, max_sentences: int = 3) -> str:
        """Return a short summary of the given text."""

    @abstractmethod
    def extract_key_sentences(self, text: str, topic: str, max_sentences: int = 3) -> str:
        """Return sentences from text most relevant to topic."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable provider name."""


class FallbackProvider(AIProvider):
    """No-LLM fallback: returns first N sentences of the text.

    Guaranteed to work without any external service. Evidence summaries
    will be the leading sentences of the extracted page text.
    """

    @property
    def name(self) -> str:
        return "FallbackProvider (no LLM)"

    def generate_summary(self, text: str, max_sentences: int = 3) -> str:
        """Return first max_sentences sentences of text."""
        if not text:
            return ""
        sentences = [s.strip() for s in text.replace("\n", " ").split(".") if len(s.strip()) > 20]
        return ". ".join(sentences[:max_sentences]) + ("." if sentences else "")

    def extract_key_sentences(self, text: str, topic: str, max_sentences: int = 3) -> str:
        """Return sentences that contain the topic keyword(s)."""
        if not text or not topic:
            return self.generate_summary(text, max_sentences)

        topic_words = [w.lower().strip() for w in topic.split() if len(w) > 3]
        sentences = [s.strip() for s in text.replace("\n", " ").split(".") if len(s.strip()) > 20]

        scored: list[tuple[int, str]] = []
        for sent in sentences:
            sl = sent.lower()
            hits = sum(1 for w in topic_words if w in sl)
            if hits > 0:
                scored.append((hits, sent))

        scored.sort(key=lambda x: x[0], reverse=True)
        top = [s for _, s in scored[:max_sentences]]
        return ". ".join(top) + ("." if top else "")


class OllamaProvider(AIProvider):
    """Ollama local LLM provider for optional AI summarisation.

    Requires Ollama to be running at OLLAMA_BASE_URL with OLLAMA_MODEL pulled.
    Falls back to FallbackProvider if Ollama is unreachable.
    """

    def __init__(self) -> None:
        self._base_url = settings.OLLAMA_BASE_URL.rstrip("/")
        self._model = settings.OLLAMA_MODEL
        self._fallback = FallbackProvider()
        self._available: Optional[bool] = None   # cached after first check

    @property
    def name(self) -> str:
        return f"OllamaProvider ({self._model})"

    def _is_available(self) -> bool:
        if self._available is not None:
            return self._available
        try:
            r = httpx.get(f"{self._base_url}/api/tags", timeout=3.0)
            self._available = r.status_code == 200
        except Exception:
            self._available = False
        return self._available

    def _call_ollama(self, prompt: str) -> str:
        try:
            r = httpx.post(
                f"{self._base_url}/api/generate",
                json={"model": self._model, "prompt": prompt, "stream": False},
                timeout=30.0,
            )
            if r.status_code == 200:
                return r.json().get("response", "").strip()
        except Exception as exc:
            logger.warning("Ollama call failed: %s", exc)
        return ""

    def generate_summary(self, text: str, max_sentences: int = 3) -> str:
        if not self._is_available():
            return self._fallback.generate_summary(text, max_sentences)
        prompt = (
            f"Summarise the following text in {max_sentences} sentences. "
            f"Be factual; do not add information not present in the text.\n\nText:\n{text[:3000]}"
        )
        result = self._call_ollama(prompt)
        return result if result else self._fallback.generate_summary(text, max_sentences)

    def extract_key_sentences(self, text: str, topic: str, max_sentences: int = 3) -> str:
        if not self._is_available():
            return self._fallback.extract_key_sentences(text, topic, max_sentences)
        prompt = (
            f"From the following text, extract up to {max_sentences} sentences most relevant to '{topic}'. "
            f"Only quote sentences that exist in the text. Do not paraphrase or add information.\n\nText:\n{text[:3000]}"
        )
        result = self._call_ollama(prompt)
        return result if result else self._fallback.extract_key_sentences(text, topic, max_sentences)


def get_ai_provider() -> AIProvider:
    """Return the configured AI provider instance."""
    provider_name = settings.AI_PROVIDER.lower()
    if provider_name == "ollama":
        return OllamaProvider()
    return FallbackProvider()


# Module-level singleton
ai_provider = get_ai_provider()
