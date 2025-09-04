"""
Gemini Synthesizer (requests-based)
Simple wrapper to synthesize summaries via Google Gemini API
"""

from typing import Optional
import requests


class GeminiSynthesizer:
    """Minimal Gemini client for text synthesis"""

    def __init__(self, api_key: str, model: str = "gemini-1.5-pro", timeout: int = 30):
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"

    def synthesize(self, prompt: str, temperature: float = 0.2, max_output_tokens: int = 2000) -> str:
        url = f"{self.base_url}/{self.model}:generateContent?key={self.api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": temperature, "maxOutputTokens": max_output_tokens},
        }
        resp = requests.post(url, json=payload, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()
        if data.get("candidates"):
            cand = data["candidates"][0]
            content = cand.get("content", {})
            parts = content.get("parts", [])
            if parts and "text" in parts[0]:
                return parts[0]["text"]
        return ""


