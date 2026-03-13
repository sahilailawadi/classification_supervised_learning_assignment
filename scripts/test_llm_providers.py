#!/usr/bin/env python3
"""
Test LLM providers to verify configuration and connectivity.

Usage:
    # Test academic mode
    python scripts/test_llm_providers.py --mode academic
    
    # Test work mode
    python scripts/test_llm_providers.py --mode work
    
    # Test both modes
    python scripts/test_llm_providers.py --mode both
"""

import argparse
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load environment variables from .env file
load_dotenv(PROJECT_ROOT / '.env')

from src.llm_provider import get_llm_provider, OpenAIProvider, WorkGatewayProvider


def test_provider(mode: str) -> bool:
    """
    Test a specific LLM provider.
    
    Args:
        mode: "academic" or "work"
        
    Returns:
        True if test passed, False otherwise
    """
    print("\n" + "="*60)
    print(f"Testing {mode.upper()} mode")
    print("="*60)
    
    try:
        # Create provider
        provider = get_llm_provider(mode=mode)
        print(f"✅ Provider created: {provider.__class__.__name__}")
        print(f"   Model: {provider.model}")
        
        # Test connection
        print("\n🔍 Testing connection...")
        if not provider.validate_connection():
            print("❌ Connection validation failed")
            return False
        print("✅ Connection validated")
        
        # Test simple query
        print("\n💬 Testing chat completion...")
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Say 'Hello from LLM provider test!' and nothing else."}
        ]
        
        response = provider.chat(messages=messages, max_tokens=50)
        
        print(f"✅ Chat completed")
        print(f"   Response: {response.content}")
        print(f"   Model: {response.model}")
        if response.tokens_used:
            print(f"   Tokens: {response.tokens_used}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Test LLM provider connectivity and configuration"
    )
    parser.add_argument(
        '--mode',
        choices=['academic', 'work', 'both'],
        default='both',
        help='Which mode to test (default: both)'
    )
    
    args = parser.parse_args()
    
    print("="*60)
    print("🧪 LLM PROVIDER TEST SUITE")
    print("="*60)
    
    # Check environment configuration
    print("\n📋 Environment Configuration:")
    print(f"   LLM_MODE: {os.getenv('LLM_MODE', 'not set (defaults to academic)')}")
    print(f"   OPENAI_API_KEY: {'✅ set' if os.getenv('OPENAI_API_KEY') else '❌ not set'}")
    print(f"   WORK_LLM_ENDPOINT: {os.getenv('WORK_LLM_ENDPOINT', '❌ not set')}")
    print(f"   WORK_LLM_API_KEY: {'✅ set' if os.getenv('WORK_LLM_API_KEY') else '❌ not set'}")
    
    # Run tests
    results = {}
    
    if args.mode == 'both':
        modes = ['academic', 'work']
    else:
        modes = [args.mode]
    
    for mode in modes:
        results[mode] = test_provider(mode)
    
    # Summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    
    for mode, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"   {mode.upper()}: {status}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print("\n⚠️  Some tests failed. Check your .env configuration.")
        print("\n💡 Configuration hints:")
        print("   1. Copy .env.example to .env")
        print("   2. Set OPENAI_API_KEY for academic mode")
        print("   3. Set WORK_LLM_ENDPOINT and WORK_LLM_API_KEY for work mode")
        print("   4. Run: python scripts/test_llm_providers.py --mode <mode>")
        return 1


if __name__ == '__main__':
    sys.exit(main())
