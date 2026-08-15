from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from backend.core.config import settings


class BaseAIProvider(ABC):
    """Abstract Base Class for AI Model Providers (Local Ollama, OpenAI, Mock, etc.)."""

    @abstractmethod
    async def classify_risk_factors(self, text: str, dimension: str) -> Dict[str, Any]:
        """Classify risk factors for a given governance dimension."""
        pass

    @abstractmethod
    async def summarize_evidence(self, query: str, context: str) -> str:
        """Summarize research evidence for risk assessment reasoning."""
        pass


class MockAIProvider(BaseAIProvider):
    """Fallback / Mock AI provider ensuring application stability when LLMs are unavailable."""

    async def classify_risk_factors(self, text: str, dimension: str) -> Dict[str, Any]:
        return {
            "dimension": dimension,
            "risk_flag": "Medium",
            "confidence": 0.85,
            "reasoning": f"Mock analysis for dimension '{dimension}'. Baseline risk pattern detected.",
        }

    async def summarize_evidence(self, query: str, context: str) -> str:
        return f"Mock AI summary based on query: {query}. Evidence context evaluated cleanly."


class AIService:
    """Service wrapper managing AI provider instantiation and fallback logic."""

    def __init__(self, provider_type: Optional[str] = None):
        self.provider_name = provider_type or settings.AI_PROVIDER
        self.provider = self._init_provider()

    def _init_provider(self) -> BaseAIProvider:
        # Defaults to MockAIProvider in Phase 1 setup
        return MockAIProvider()

    async def analyze(self, text: str, dimension: str) -> Dict[str, Any]:
        try:
            return await self.provider.classify_risk_factors(text, dimension)
        except Exception as e:
            # Fall back gracefully to mock provider on error
            fallback = MockAIProvider()
            return await fallback.classify_risk_factors(text, dimension)


ai_service = AIService()
