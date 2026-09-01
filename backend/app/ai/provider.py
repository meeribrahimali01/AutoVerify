"""AI Provider interface and implementations."""

from __future__ import annotations

import json
import logging
import os
import urllib.request
import urllib.error
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class AIProvider(ABC):
    """Abstract interface for AI model inference."""

    @abstractmethod
    def is_configured(self) -> bool:
        """Return True if the provider has necessary credentials/configuration."""
        pass

    @abstractmethod
    def generate_json(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """Generate structured JSON response given system and user prompts."""
        pass


class GeminiProvider(AIProvider):
    """Gemini API Provider using HTTP request without heavy SDK dependencies."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-1.5-flash"):
        self.api_key = api_key or os.environ.get("AUTOVERIFY_AI_API_KEY") or os.environ.get("GEMINI_API_KEY")
        self.model = model

    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    def generate_json(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        if not self.is_configured():
            raise RuntimeError("Gemini AI API key is not configured.")

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"

        payload = {
            "system_instruction": {
                "parts": [{"text": system_prompt}]
            },
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": user_prompt}]
                }
            ],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.1,
            }
        }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))
                
                candidates = resp_data.get("candidates", [])
                if not candidates:
                    raise RuntimeError("No generation candidates returned by Gemini.")
                
                content_parts = candidates[0].get("content", {}).get("parts", [])
                if not content_parts:
                    raise RuntimeError("Empty response content from Gemini.")
                
                raw_text = content_parts[0].get("text", "{}")
                # Parse clean JSON
                cleaned_text = raw_text.strip()
                if cleaned_text.startswith("```json"):
                    cleaned_text = cleaned_text[7:]
                if cleaned_text.startswith("```"):
                    cleaned_text = cleaned_text[3:]
                if cleaned_text.endswith("```"):
                    cleaned_text = cleaned_text[:-3]
                
                return json.loads(cleaned_text.strip())

        except urllib.error.HTTPError as exc:
            err_body = exc.read().decode("utf-8", errors="ignore")
            logger.error("Gemini API error: %s - %s", exc, err_body)
            raise RuntimeError(f"Gemini API request failed: {exc.code} {exc.reason}") from exc
        except Exception as exc:
            logger.error("Failed to generate AI response: %s", exc)
            raise


class MockAIProvider(AIProvider):
    """Stub AI provider for automated unit testing and offline development."""

    def __init__(self, canned_response: Optional[Dict[str, Any]] = None, configured: bool = True):
        self.canned_response = canned_response or {}
        self._configured = configured

    def is_configured(self) -> bool:
        return self._configured

    def generate_json(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        if not self.is_configured():
            raise RuntimeError("Mock provider is not configured.")
        return self.canned_response


# Global active provider reference (can be replaced in tests)
_ACTIVE_PROVIDER: Optional[AIProvider] = None


def get_ai_provider() -> AIProvider:
    """Return the globally configured AI provider or default Gemini provider."""
    global _ACTIVE_PROVIDER
    if _ACTIVE_PROVIDER is not None:
        return _ACTIVE_PROVIDER
    return GeminiProvider()


def set_ai_provider(provider: Optional[AIProvider]) -> None:
    """Set global active AI provider (useful for testing)."""
    global _ACTIVE_PROVIDER
    _ACTIVE_PROVIDER = provider
