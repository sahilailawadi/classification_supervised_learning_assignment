#!/usr/bin/env python3
"""
Quick test of work LLM gateway with OAuth.

This script validates:
1. SAT OAuth token fetch
2. LLM gateway connectivity
3. Chat completion request

Usage:
    python scripts/test_work_gateway.py
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load environment variables from .env file
load_dotenv(PROJECT_ROOT / '.env')

from src.llm_provider import WorkGatewayProvider


def main():
    print("="*60)
    print("🧪 Testing Work LLM Gateway with OAuth")
    print("="*60)
    
    # Check configuration
    print("\n📋 Configuration:")
    config_items = [
        ('WORK_LLM_ENDPOINT', os.getenv('WORK_LLM_ENDPOINT')),
        ('WORK_LLM_MODEL', os.getenv('WORK_LLM_MODEL')),
        ('SAT_OAUTH_URL', os.getenv('SAT_OAUTH_URL')),
        ('SAT_CLIENT_ID', os.getenv('SAT_CLIENT_ID')),
        ('SAT_CLIENT_SECRET', '***' if os.getenv('SAT_CLIENT_SECRET') else None),
        ('SAT_GRANT_TYPE', os.getenv('SAT_GRANT_TYPE')),
    ]
    
    missing = []
    for key, value in config_items:
        status = "✅" if value else "❌"
        display_value = value if key != 'SAT_CLIENT_SECRET' else ('***' if value else 'not set')
        print(f"   {status} {key}: {display_value or 'NOT SET'}")
        if not value:
            missing.append(key)
    
    if missing:
        print(f"\n❌ Missing required configuration: {', '.join(missing)}")
        print("\n💡 Add these to your .env file:")
        for key in missing:
            print(f"   {key}=your_value_here")
        return 1
    
    try:
        # Initialize provider
        print("\n🔧 Initializing WorkGatewayProvider...")
        provider = WorkGatewayProvider()
        print(f"✅ Provider initialized: {provider.model}")
        
        # Test OAuth token fetch
        print("\n🔐 Fetching OAuth token...")
        token = provider._get_oauth_token()
        print(f"✅ Token acquired: {token[:20]}...{token[-10:]}")
        
        # Test chat completion
        print("\n💬 Testing chat completion...")
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Say 'Hello from Comcast LLM Gateway!' and nothing else."}
        ]
        
        response = provider.chat(messages=messages, max_tokens=50)
        
        print(f"✅ Chat completed successfully!")
        print(f"   Model: {response.model}")
        print(f"   Response: {response.content}")
        if response.tokens_used:
            print(f"   Tokens: {response.tokens_used}")
        
        print("\n" + "="*60)
        print("🎉 All tests passed!")
        print("="*60)
        return 0
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        
        print("\n💡 Troubleshooting:")
        print("   1. Verify your SAT credentials are correct")
        print("   2. Check network connectivity to SAT OAuth endpoint")
        print("   3. Verify LLM gateway endpoint is accessible")
        print("   4. Ensure you have necessary permissions/roles")
        return 1


if __name__ == '__main__':
    sys.exit(main())
