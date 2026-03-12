"""
LLM Provider Abstractions for Dual-Mode Architecture.

Supports two modes:
- ACADEMIC: Uses OpenAI API (GPT-4) with anonymized Excel data
- WORK: Uses work LLM gateway with live database access
"""

import os
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

import openai


@dataclass
class LLMResponse:
    """Standardized response from any LLM provider."""
    content: str
    model: str
    tokens_used: Optional[int] = None
    finish_reason: Optional[str] = None
    raw_response: Optional[Any] = None


class BaseLLMProvider(ABC):
    """Abstract base class for all LLM providers."""
    
    def __init__(self, model: str):
        """
        Initialize the LLM provider.
        
        Args:
            model: Model identifier (e.g., "gpt-4", "llama3:8b")
        """
        self.model = model
    
    @abstractmethod
    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> LLMResponse:
        """
        Send a chat completion request.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens to generate
            
        Returns:
            LLMResponse with standardized fields
        """
        pass
    
    @abstractmethod
    def validate_connection(self) -> bool:
        """
        Test if the provider is accessible.
        
        Returns:
            True if connection successful, False otherwise
        """
        pass


class OpenAIProvider(BaseLLMProvider):
    """OpenAI API provider for academic mode."""
    
    def __init__(self, model: str = "gpt-4-turbo-preview", api_key: Optional[str] = None):
        """
        Initialize OpenAI provider.
        
        Args:
            model: OpenAI model name
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
        """
        super().__init__(model)
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        
        if not self.api_key:
            raise ValueError(
                "OpenAI API key required. Set OPENAI_API_KEY environment variable "
                "or pass api_key parameter."
            )
        
        self.client = openai.OpenAI(api_key=self.api_key)
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> LLMResponse:
        """Send chat completion to OpenAI API."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            return LLMResponse(
                content=response.choices[0].message.content,
                model=response.model,
                tokens_used=response.usage.total_tokens if response.usage else None,
                finish_reason=response.choices[0].finish_reason,
                raw_response=response
            )
        except Exception as e:
            raise RuntimeError(f"OpenAI API error: {e}") from e
    
    def validate_connection(self) -> bool:
        """Test OpenAI API connection."""
        try:
            # Send minimal test request
            response = self.chat(
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5
            )
            return response.content is not None
        except Exception as e:
            print(f"OpenAI connection validation failed: {e}")
            return False


class WorkGatewayProvider(BaseLLMProvider):
    """
    Work LLM Gateway provider for enterprise environments.
    
    Supports OpenAI-compatible APIs and custom authentication patterns.
    Configure via environment variables:
    - WORK_LLM_ENDPOINT: Gateway base URL
    - WORK_LLM_API_KEY: Authentication key (if required)
    - WORK_LLM_MODEL: Model identifier
    """
    
    def __init__(
        self,
        endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        auth_header: str = "Authorization"
    ):
        """
        Initialize work gateway provider.
        
        Args:
            endpoint: Gateway base URL (e.g., "https://llm-gateway.company.com")
            api_key: Authentication key
            model: Model identifier on the gateway
            auth_header: Header name for authentication (default: "Authorization")
        """
        # Environment variable fallbacks
        self.endpoint = endpoint or os.getenv('WORK_LLM_ENDPOINT')
        self.api_key = api_key or os.getenv('WORK_LLM_API_KEY')
        model = model or os.getenv('WORK_LLM_MODEL', 'default')
        
        super().__init__(model)
        
        if not self.endpoint:
            raise ValueError(
                "Work LLM gateway endpoint required. Set WORK_LLM_ENDPOINT environment "
                "variable or pass endpoint parameter."
            )
        
        self.auth_header = auth_header
        
        # Initialize OpenAI client with custom base URL (for OpenAI-compatible gateways)
        if self.api_key:
            self.client = openai.OpenAI(
                base_url=self.endpoint,
                api_key=self.api_key
            )
        else:
            # No auth required (internal network, etc.)
            self.client = openai.OpenAI(
                base_url=self.endpoint,
                api_key="not-needed"  # Some gateways ignore this
            )
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> LLMResponse:
        """Send chat completion to work gateway."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            return LLMResponse(
                content=response.choices[0].message.content,
                model=response.model,
                tokens_used=response.usage.total_tokens if response.usage else None,
                finish_reason=response.choices[0].finish_reason,
                raw_response=response
            )
        except Exception as e:
            raise RuntimeError(f"Work LLM gateway error: {e}") from e
    
    def validate_connection(self) -> bool:
        """Test work gateway connection."""
        try:
            response = self.chat(
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5
            )
            return response.content is not None
        except Exception as e:
            print(f"Work gateway connection validation failed: {e}")
            return False


class LLMFactory:
    """
    Factory for creating appropriate LLM provider based on mode.
    
    Mode is determined by LLM_MODE environment variable:
    - "academic": Uses OpenAI API
    - "work": Uses work LLM gateway
    """
    
    @staticmethod
    def create_provider(mode: Optional[str] = None) -> BaseLLMProvider:
        """
        Create LLM provider based on mode.
        
        Args:
            mode: Override mode ("academic" or "work"). 
                  If None, reads from LLM_MODE environment variable.
                  
        Returns:
            Configured LLM provider instance
            
        Raises:
            ValueError: If mode is invalid or required config is missing
        """
        mode = mode or os.getenv('LLM_MODE', 'academic')
        mode = mode.lower()
        
        if mode == 'academic':
            print("🎓 Initializing ACADEMIC mode (OpenAI GPT-4)")
            return OpenAIProvider(
                model=os.getenv('OPENAI_MODEL', 'gpt-4-turbo-preview')
            )
        
        elif mode == 'work':
            print("💼 Initializing WORK mode (LLM Gateway)")
            return WorkGatewayProvider()
        
        else:
            raise ValueError(
                f"Invalid LLM_MODE: '{mode}'. Must be 'academic' or 'work'. "
                f"Set LLM_MODE environment variable."
            )
    
    @staticmethod
    def get_mode() -> str:
        """Get current LLM mode from environment."""
        return os.getenv('LLM_MODE', 'academic').lower()


# Convenience function for getting a provider
def get_llm_provider(mode: Optional[str] = None) -> BaseLLMProvider:
    """
    Get configured LLM provider.
    
    Args:
        mode: Override mode ("academic" or "work")
        
    Returns:
        Configured LLM provider
    """
    return LLMFactory.create_provider(mode)
