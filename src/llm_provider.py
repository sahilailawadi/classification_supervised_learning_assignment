"""
LLM Provider Abstractions for Dual-Mode Architecture.

Supports two modes:
- ACADEMIC: Uses OpenAI API (GPT-4) with anonymized Excel data
- WORK: Uses work LLM gateway with live database access
"""

import os
import time
import requests
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
    Work LLM Gateway provider for enterprise environments with OAuth.
    
    Supports OAuth token flow:
    1. Fetch bearer token from SAT OAuth endpoint
    2. Use token to authenticate LLM gateway requests
    3. Cache token until expiration
    
    Configure via environment variables:
    - WORK_LLM_ENDPOINT: Gateway base URL
    - WORK_LLM_MODEL: Model identifier
    - SAT_OAUTH_URL: OAuth token endpoint
    - SAT_CLIENT_ID: OAuth client ID
    - SAT_CLIENT_SECRET: OAuth client secret
    - SAT_GRANT_TYPE: OAuth grant type (usually "client_credentials")
    """
    
    def __init__(
        self,
        endpoint: Optional[str] = None,
        model: Optional[str] = None,
        oauth_url: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        grant_type: Optional[str] = None
    ):
        """
        Initialize work gateway provider with OAuth.
        
        Args:
            endpoint: Gateway base URL
            model: Model identifier on the gateway
            oauth_url: SAT OAuth token endpoint
            client_id: OAuth client ID
            client_secret: OAuth client secret
            grant_type: OAuth grant type
        """
        # Environment variable fallbacks
        self.endpoint = endpoint or os.getenv('WORK_LLM_ENDPOINT')
        model = model or os.getenv('WORK_LLM_MODEL', 'gpt-4')
        
        # OAuth configuration
        self.oauth_url = oauth_url or os.getenv('SAT_OAUTH_URL')
        self.client_id = client_id or os.getenv('SAT_CLIENT_ID')
        self.client_secret = client_secret or os.getenv('SAT_CLIENT_SECRET')
        self.grant_type = grant_type or os.getenv('SAT_GRANT_TYPE', 'client_credentials')
        
        super().__init__(model)
        
        if not self.endpoint:
            raise ValueError(
                "Work LLM gateway endpoint required. Set WORK_LLM_ENDPOINT environment "
                "variable or pass endpoint parameter."
            )
        
        if not self.oauth_url or not self.client_id or not self.client_secret:
            raise ValueError(
                "OAuth configuration required. Set SAT_OAUTH_URL, SAT_CLIENT_ID, and "
                "SAT_CLIENT_SECRET environment variables."
            )
        
        # Token cache
        self._token = None
        self._token_expires_at = 0
    
    def _get_oauth_token(self) -> str:
        """
        Fetch OAuth bearer token from SAT endpoint.
        
        Returns:
            Bearer token string
            
        Raises:
            RuntimeError: If token fetch fails
        """
        # Check if cached token is still valid
        if self._token and time.time() < self._token_expires_at:
            return self._token
        
        # Fetch new token
        try:
            response = requests.post(
                self.oauth_url,
                data={
                    'client_id': self.client_id,
                    'client_secret': self.client_secret,
                    'grant_type': self.grant_type
                },
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                timeout=10
            )
            response.raise_for_status()
            
            token_data = response.json()
            self._token = token_data.get('access_token')
            
            if not self._token:
                raise RuntimeError("No access_token in OAuth response")
            
            # Cache token with 5 minute buffer before expiration
            expires_in = token_data.get('expires_in', 3600)  # Default 1 hour
            self._token_expires_at = time.time() + expires_in - 300
            
            return self._token
            
        except requests.RequestException as e:
            raise RuntimeError(f"Failed to fetch OAuth token: {e}") from e
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False
    ) -> LLMResponse:
        """
        Send chat completion to work gateway.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens to generate
            stream: Whether to stream the response (not yet implemented)
            
        Returns:
            LLMResponse with standardized fields
        """
        # Get OAuth token
        token = self._get_oauth_token()
        
        # Build request
        url = self.endpoint.rstrip('/') + '/chat/completions'
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'model': self.model,
            'messages': messages,
            'temperature': temperature,
            'stream': stream
        }
        
        if max_tokens:
            payload['max_tokens'] = max_tokens
        
        try:
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=60
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Parse OpenAI-compatible response
            choice = data.get('choices', [{}])[0]
            message = choice.get('message', {})
            usage = data.get('usage', {})
            
            return LLMResponse(
                content=message.get('content', ''),
                model=data.get('model', self.model),
                tokens_used=usage.get('total_tokens'),
                finish_reason=choice.get('finish_reason'),
                raw_response=data
            )
            
        except requests.RequestException as e:
            raise RuntimeError(f"Work LLM gateway error: {e}") from e
    
    def validate_connection(self) -> bool:
        """Test work gateway connection."""
        try:
            # Test OAuth token fetch
            token = self._get_oauth_token()
            if not token:
                return False
            
            # Test minimal chat request
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
