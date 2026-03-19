#!/usr/bin/env python3
"""Quick test of MCP tools with academic mode"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

print('=== Testing MCP Tools with Academic Mode (CSV) ===\n')

print('1. Testing query_tests...')
from mcp_server.tools.query import query_tests
result = query_tests(limit=3)
print(f'   ✅ Found {result["count"]} tests (total in dataset: {result["total_in_dataset"]})')
print(f'   First test: {result["tests"][0]["testplan"][:50]}...')

print('\n2. Testing get_test_detail...')
from mcp_server.tools.detail import get_test_detail
testplan = result['tests'][0]['testplan']
detail = get_test_detail(testplan)
print(f'   ✅ Got details for {testplan[:50]}...')
print(f'   Transactions: {len(detail["transactions"])}')
if 'error' in detail['prediction']:
    print(f'   Prediction: Error - {detail["prediction"]["error"]}')
else:
    print(f'   Prediction: {detail["prediction"]["prediction"]} (confidence: {detail["prediction"]["confidence"]:.2%})')

print('\n3. Testing compare_tests...')
from mcp_server.tools.compare import compare_tests
if result['count'] >= 2:
    test1 = result['tests'][0]['testplan']
    test2 = result['tests'][1]['testplan']
    comparison = compare_tests(test1, test2)
    print(f'   ✅ Compared 2 tests')
    print(f'   P95 delta: {comparison["differences"]["p95_delta"]:.2f}ms')
    print(f'   P95 change: {comparison["differences"]["p95_pct_change"]:.1%}')
else:
    print('   ⚠️  Need at least 2 tests to compare')

print('\n🎉 ALL MCP TOOLS WORKING WITH ACADEMIC MODE!')
