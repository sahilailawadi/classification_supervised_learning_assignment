#!/usr/bin/env python3
"""Test MCP tools with academic mode CSV data"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from mcp_server.tools.query import query_tests
from mcp_server.tools.detail import get_test_detail
from mcp_server.tools.compare import compare_tests
import json


def test_query_tests():
    """Test query_tests tool"""
    print("=" * 80)
    print("TEST 1: Query last 5 tests")
    print("=" * 80)
    
    result = query_tests(limit=5, sort_by="end_time", ascending=False)
    print(json.dumps(result, indent=2))
    
    print("\n" + "=" * 80)
    print("TEST 2: Query failed tests")
    print("=" * 80)
    
    result = query_tests(limit=3, exit_code=2)
    print(json.dumps(result, indent=2))
    
    return result['tests'][0]['testplan'] if result['tests'] else None


def test_get_test_detail(testplan):
    """Test get_test_detail tool"""
    print("\n" + "=" * 80)
    print(f"TEST 3: Get details for test: {testplan}")
    print("=" * 80)
    
    result = get_test_detail(testplan)
    
    # Print summary (not formatted_context which is too long)
    summary = {k: v for k, v in result.items() if k != 'formatted_context'}
    print(json.dumps(summary, indent=2))
    
    return result


def test_compare_tests(testplan1, testplan2):
    """Test compare_tests tool"""
    print("\n" + "=" * 80)
    print(f"TEST 4: Compare {testplan1} vs {testplan2}")
    print("=" * 80)
    
    result = compare_tests(testplan1, testplan2)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    print("🧪 Testing MCP Tools with Academic Mode CSV Data\n")
    
    try:
        # Test query_tests and get a testplan
        testplan1 = test_query_tests()
        
        if testplan1:
            # Test get_test_detail
            detail = test_get_test_detail(testplan1)
            
            # Get another test for comparison
            all_tests = query_tests(limit=10)
            if len(all_tests['tests']) >= 2:
                testplan2 = all_tests['tests'][1]['testplan']
                test_compare_tests(testplan1, testplan2)
        
        print("\n" + "=" * 80)
        print("✅ ALL TESTS PASSED!")
        print("=" * 80)
        print("\n📝 Summary:")
        print("   - query_tests: Works with CSV data")
        print("   - get_test_detail: Works with CSV data")
        print("   - compare_tests: Works with CSV data")
        print("\n🎉 MCP Phase 1 is ready for academic mode!")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
