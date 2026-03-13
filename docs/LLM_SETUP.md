# LLM Provider Configuration Guide

## Phase 1 Complete! ✅

The LLM provider architecture is now implemented with support for:
- **Academic Mode**: OpenAI GPT-4 API
- **Work Mode**: Enterprise LLM Gateway

## Quick Start

### 1. Configure Environment Variables

Add these to your `.env` file:

```bash
# Set mode: "academic" or "work"
LLM_MODE=work

# ============================================================
# WORK MODE - LLM Gateway (Primary for Comcast)
# ============================================================
WORK_LLM_ENDPOINT=https://your-llm-gateway.company.com/v1
WORK_LLM_API_KEY=your_gateway_token_here
WORK_LLM_MODEL=default

# ============================================================
# ACADEMIC MODE - OpenAI (For assignments only)
# ============================================================
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4-turbo-preview
```

### 2. Test Your Configuration

```bash
# Test work mode
python scripts/test_llm_providers.py --mode work

# Test academic mode  
python scripts/test_llm_providers.py --mode academic

# Test both
python scripts/test_llm_providers.py --mode both
```

## Usage in Code

```python
from src.llm_provider import get_llm_provider

# Get provider (automatically detects mode from LLM_MODE env var)
llm = get_llm_provider()

# Send a chat request
messages = [
    {"role": "system", "content": "You are a test analysis assistant."},
    {"role": "user", "content": "Analyze this test result..."}
]

response = llm.chat(messages=messages, temperature=0.7)
print(response.content)
print(f"Tokens used: {response.tokens_used}")
```

## Work Gateway Provider Details

The `WorkGatewayProvider` is designed to work with enterprise LLM gateways that use OAuth authentication. It supports:

- **OAuth token flow**: Fetches bearer tokens from SAT OAuth endpoint
- **Token caching**: Reuses tokens until expiration (with 5-min buffer)
- **Custom endpoints**: Any OpenAI-compatible gateway URL
- **Standard format**: Uses OpenAI chat completion format

### OAuth Flow

1. Request token from SAT OAuth endpoint with client credentials
2. Cache token until expiration
3. Use token as Bearer authentication for LLM requests
4. Auto-refresh when token expires

### Comcast Configuration

```bash
# Set mode to work
LLM_MODE=work

# LLM Gateway endpoint
WORK_LLM_ENDPOINT=https://api.context.flow.cnap.comcast.net/modelgw/models/openai/v1
WORK_LLM_MODEL=gpt-4

# SAT OAuth credentials (get these from your team)
SAT_OAUTH_URL=https://sat-prod.codebig2.net/v2/oauth/token
SAT_CLIENT_ID=your-client-id-here
SAT_CLIENT_SECRET=your-client-secret-here
SAT_GRANT_TYPE=client_credentials
```

## What to Configure for Comcast

You'll need:
1. **Gateway URL**: The base endpoint for your LLM gateway
2. **API Key/Token**: Authentication credentials
3. **Model Name**: What model identifier to request

Ask your team/DevOps for these values, or check your internal documentation for LLM/AI platform access.

## Architecture Overview

```
┌─────────────────────────────────────────────┐
│         LLMFactory.create_provider()        │
│                                             │
│  Reads LLM_MODE env var                     │
└──────────────┬──────────────────────────────┘
               │
        ┌──────┴──────┐
        │             │
        v             v
┌───────────────┐  ┌──────────────────┐
│ OpenAIProvider│  │WorkGatewayProvider│
│               │  │                  │
│ - GPT-4       │  │ - Custom Gateway │
│ - Excel data  │  │ - Live DB        │
│ - Academic    │  │ - Production     │
└───────────────┘  └──────────────────┘
```

## Next Steps

Once configured, you can:
1. Test the provider: `python scripts/test_llm_providers.py`
2. Integrate into prediction flow (Phase 2)
3. Build LLM-augmented analysis features (Phase 3)
