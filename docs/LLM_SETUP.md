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

The `WorkGatewayProvider` is designed to work with OpenAI-compatible enterprise gateways. It supports:

- **Custom endpoints**: Any base URL
- **Flexible authentication**: API keys via header
- **Multiple models**: Configurable model selection
- **Standard format**: Uses OpenAI chat completion format

### Common Gateway Patterns

**Pattern 1: OpenAI-Compatible (Most Common)**
```bash
WORK_LLM_ENDPOINT=https://llm-gateway.company.com/v1
WORK_LLM_API_KEY=your_token
WORK_LLM_MODEL=gpt-4
```

**Pattern 2: Internal Gateway (No Auth)**
```bash
WORK_LLM_ENDPOINT=http://internal-llm.company.local/v1
# WORK_LLM_API_KEY not needed
WORK_LLM_MODEL=default
```

**Pattern 3: Azure OpenAI-style**
```bash
WORK_LLM_ENDPOINT=https://your-resource.openai.azure.com
WORK_LLM_API_KEY=your_azure_key
WORK_LLM_MODEL=gpt-4
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
