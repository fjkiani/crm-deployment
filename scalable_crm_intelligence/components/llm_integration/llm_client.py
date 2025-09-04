"""
Unified LLM Client
Provides unified interface for multiple LLM providers with fallback support
"""

import asyncio
import json
import os
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
import aiohttp
import logging

@dataclass
class LLMConfig:
    """Configuration for LLM integration"""
    primary_provider: str = "gemini"
    fallback_providers: List[str] = field(default_factory=lambda: ["openai", "anthropic"])
    
    # API Keys (loaded from environment)
    openai_api_key: str = field(default_factory=lambda: os.getenv('OPENAI_API_KEY', ''))
    anthropic_api_key: str = field(default_factory=lambda: os.getenv('ANTHROPIC_API_KEY', ''))
    gemini_api_key: str = field(default_factory=lambda: os.getenv('GEMINI_API_KEY', ''))
    
    # Model Configuration
    models: Dict[str, str] = field(default_factory=lambda: {
        "question_decomposition": "gemini-1.5-pro",
        "synthesis": "gemini-1.5-pro", 
        "gap_analysis": "gemini-1.5-pro",
        "pattern_recognition": "gemini-1.5-pro"
    })
    
    # Generation Parameters
    temperature: float = 0.1  # Low temperature for consistency
    max_tokens: int = 4000
    timeout_seconds: int = 30

@dataclass
class LLMResponse:
    """Response from LLM provider"""
    content: str
    provider: str
    model: str
    tokens_used: int = 0
    cost_estimate: float = 0.0
    response_time: float = 0.0

class LLMGenerationError(Exception):
    """Error in LLM generation"""
    pass

class OpenAIProvider:
    """OpenAI API provider"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.openai.com/v1/chat/completions"
        self.logger = logging.getLogger("OpenAIProvider")
    
    async def generate(self, prompt: str, model: str = "gpt-4", **kwargs) -> LLMResponse:
        """Generate response using OpenAI API"""
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": kwargs.get("temperature", 0.1),
            "max_tokens": kwargs.get("max_tokens", 4000)
        }
        
        start_time = asyncio.get_event_loop().time()
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.base_url,
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=kwargs.get("timeout", 30))
            ) as response:
                
                if response.status == 200:
                    data = await response.json()
                    content = data["choices"][0]["message"]["content"]
                    tokens = data.get("usage", {}).get("total_tokens", 0)
                    
                    return LLMResponse(
                        content=content,
                        provider="openai",
                        model=model,
                        tokens_used=tokens,
                        response_time=asyncio.get_event_loop().time() - start_time
                    )
                else:
                    error_text = await response.text()
                    raise LLMGenerationError(f"OpenAI API error {response.status}: {error_text}")

class AnthropicProvider:
    """Anthropic (Claude) API provider"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.anthropic.com/v1/messages"
        self.logger = logging.getLogger("AnthropicProvider")
    
    async def generate(self, prompt: str, model: str = "claude-3-sonnet-20240229", **kwargs) -> LLMResponse:
        """Generate response using Anthropic API"""
        
        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }
        
        payload = {
            "model": model,
            "max_tokens": kwargs.get("max_tokens", 4000),
            "temperature": kwargs.get("temperature", 0.1),
            "messages": [{"role": "user", "content": prompt}]
        }
        
        start_time = asyncio.get_event_loop().time()
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.base_url,
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=kwargs.get("timeout", 30))
            ) as response:
                
                if response.status == 200:
                    data = await response.json()
                    content = data["content"][0]["text"]
                    tokens = data.get("usage", {}).get("input_tokens", 0) + data.get("usage", {}).get("output_tokens", 0)
                    
                    return LLMResponse(
                        content=content,
                        provider="anthropic",
                        model=model,
                        tokens_used=tokens,
                        response_time=asyncio.get_event_loop().time() - start_time
                    )
                else:
                    error_text = await response.text()
                    raise LLMGenerationError(f"Anthropic API error {response.status}: {error_text}")

class GeminiProvider:
    """Google Gemini API provider"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"
        self.logger = logging.getLogger("GeminiProvider")
    
    async def generate(self, prompt: str, model: str = "gemini-1.5-pro", **kwargs) -> LLMResponse:
        """Generate response using Gemini API"""
        
        url = f"{self.base_url}/{model}:generateContent?key={self.api_key}"
        
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": kwargs.get("temperature", 0.1),
                "maxOutputTokens": kwargs.get("max_tokens", 4000)
            }
        }
        
        start_time = asyncio.get_event_loop().time()
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=kwargs.get("timeout", 30))
            ) as response:
                
                if response.status == 200:
                    data = await response.json()
                    
                    if "candidates" in data and len(data["candidates"]) > 0:
                        candidate = data["candidates"][0]
                        if "content" in candidate and "parts" in candidate["content"]:
                            content = candidate["content"]["parts"][0]["text"]
                            
                            # Extract token usage if available
                            tokens = 0
                            if "usageMetadata" in data:
                                tokens = data["usageMetadata"].get("totalTokenCount", 0)
                            
                            return LLMResponse(
                                content=content,
                                provider="gemini",
                                model=model,
                                tokens_used=tokens,
                                response_time=asyncio.get_event_loop().time() - start_time
                            )
                    
                    # If no valid content found
                    raise LLMGenerationError(f"Gemini API returned no valid content: {data}")
                else:
                    error_text = await response.text()
                    raise LLMGenerationError(f"Gemini API error {response.status}: {error_text}")

class UnifiedLLMClient:
    """Unified interface for multiple LLM providers with automatic fallback"""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self.logger = logging.getLogger("UnifiedLLMClient")
        self.providers = self._initialize_providers()
    
    def _initialize_providers(self) -> Dict[str, Any]:
        """Initialize configured LLM providers"""
        providers = {}
        
        if self.config.openai_api_key:
            providers['openai'] = OpenAIProvider(self.config.openai_api_key)
            self.logger.info("OpenAI provider initialized")
        
        if self.config.anthropic_api_key:
            providers['anthropic'] = AnthropicProvider(self.config.anthropic_api_key)
            self.logger.info("Anthropic provider initialized")
        
        if self.config.gemini_api_key:
            providers['gemini'] = GeminiProvider(self.config.gemini_api_key)
            self.logger.info("Gemini provider initialized")
        
        if not providers:
            raise ValueError("No LLM providers configured. Please set API keys.")
        
        return providers
    
    async def generate(self, prompt: str, task_type: str = "general", provider: str = None, **kwargs) -> LLMResponse:
        """Generate response with automatic fallback"""
        
        # Determine target provider and model
        target_provider = provider or self.config.primary_provider
        model = self.config.models.get(task_type, "gpt-4")
        
        # Build fallback chain
        fallback_chain = [target_provider] + [p for p in self.config.fallback_providers if p != target_provider]
        
        for attempt_provider in fallback_chain:
            if attempt_provider not in self.providers:
                self.logger.warning(f"Provider {attempt_provider} not available, skipping")
                continue
                
            try:
                self.logger.debug(f"Attempting generation with {attempt_provider}")
                provider_instance = self.providers[attempt_provider]
                
                response = await provider_instance.generate(
                    prompt=prompt,
                    model=model,
                    temperature=kwargs.get("temperature", self.config.temperature),
                    max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
                    timeout=kwargs.get("timeout", self.config.timeout_seconds)
                )
                
                if self._validate_response(response):
                    self.logger.info(f"Successful generation with {attempt_provider}")
                    return response
                else:
                    self.logger.warning(f"Invalid response from {attempt_provider}")
                    
            except Exception as e:
                self.logger.warning(f"Provider {attempt_provider} failed: {e}")
                continue
        
        raise LLMGenerationError("All LLM providers failed")
    
    def _validate_response(self, response: LLMResponse) -> bool:
        """Validate LLM response quality"""
        if not response.content or len(response.content.strip()) < 10:
            return False
        
        # Check for common error indicators
        error_indicators = ["error", "sorry", "cannot", "unable to"]
        content_lower = response.content.lower()
        
        if any(indicator in content_lower for indicator in error_indicators):
            if len(response.content) < 100:  # Short responses with error words are likely errors
                return False
        
        return True
    
    async def generate_json(self, prompt: str, task_type: str = "general", **kwargs) -> Dict[str, Any]:
        """Generate JSON response with parsing"""
        
        # Add JSON formatting instruction to prompt
        json_prompt = f"""{prompt}

Return your response as valid JSON only. Do not include any text outside the JSON structure."""
        
        response = await self.generate(json_prompt, task_type, **kwargs)
        
        try:
            # Extract JSON from response (handle cases where LLM adds extra text)
            content = response.content.strip()
            
            # Find JSON boundaries
            start_idx = content.find('{')
            end_idx = content.rfind('}') + 1
            
            if start_idx >= 0 and end_idx > start_idx:
                json_content = content[start_idx:end_idx]
                return json.loads(json_content)
            else:
                # Fallback: try parsing entire content
                return json.loads(content)
                
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse JSON response: {e}")
            self.logger.error(f"Response content: {response.content}")
            raise LLMGenerationError(f"Invalid JSON response: {e}")
    
    def get_available_providers(self) -> List[str]:
        """Get list of available providers"""
        return list(self.providers.keys())
    
    def get_provider_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all providers"""
        status = {}
        
        for provider_name, provider in self.providers.items():
            status[provider_name] = {
                "available": True,
                "type": provider.__class__.__name__
            }
        
        return status
