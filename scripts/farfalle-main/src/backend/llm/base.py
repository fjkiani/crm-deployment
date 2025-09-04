import os
import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import AsyncIterator, Any

import requests
from dotenv import load_dotenv

load_dotenv()


@dataclass
class _Delta:
    delta: str


class BaseLLM(ABC):
    @abstractmethod
    async def astream(self, prompt: str) -> AsyncIterator[_Delta]:
        pass

    @abstractmethod
    def complete(self, prompt: str) -> str:
        pass

    @abstractmethod
    def structured_complete(self, response_model: type[Any], prompt: str) -> Any:
        pass


class EveryLLM(BaseLLM):
    def __init__(self, model: str):
        self.model = self._normalize_model(model)
        self.gemini_key = os.getenv("GEMINI_API_KEY", "")
        if self._is_gemini(self.model) and not self.gemini_key:
            raise ValueError("GEMINI_API_KEY is required for Gemini models")

    def _is_gemini(self, model: str) -> bool:
        return model.startswith("gemini/") or model.startswith("gemini-")

    def _normalize_model(self, model: str) -> str:
        # Accept values like "gemini/gemini-1.5-pro" or "gemini-1.5-pro"
        if model.startswith("gemini/"):
            return model.split("/", 1)[1]
        return model

    def _gemini_generate(self, prompt: str) -> str:
        # Minimal Gemini text generation via REST
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [
                {
                    "parts": [{"text": prompt}],
                }
            ]
        }
        params = {"key": self.gemini_key}
        try:
            resp = requests.post(url, headers=headers, json=payload, params=params, timeout=60)
            resp.raise_for_status()
            data = resp.json() or {}
            candidates = data.get("candidates", [])
            if not candidates:
                return ""
            content = candidates[0].get("content", {})
            parts = content.get("parts", [])
            texts = [p.get("text", "") for p in parts if isinstance(p, dict)]
            return "".join(texts).strip()
        except Exception:
            return ""

    async def astream(self, prompt: str) -> AsyncIterator[_Delta]:
        # Simple one-shot streaming for compatibility
        text = self.complete(prompt)
        yield _Delta(delta=text)
        await asyncio.sleep(0)

    def complete(self, prompt: str) -> str:
        if self._is_gemini(self.model):
            return self._gemini_generate(prompt)
        # Fallback: return empty string to avoid crashes
        return ""

    def structured_complete(self, response_model: type[Any], prompt: str) -> Any:
        # Minimal stub – not used in chat path
        return self.complete(prompt)
