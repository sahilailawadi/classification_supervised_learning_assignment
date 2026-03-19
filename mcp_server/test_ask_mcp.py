#!/usr/bin/env python3
"""Test the updated ask() method with MCP tool integration"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.analyzer import TestAnalyzer

print('=== Testing ask() Method with MCP Integration ===\n')

# Initialize analyzer
print('Initializing TestAnalyzer...')
analyzer = TestAnalyzer()

# Test 1: Natural language query for last 5 tests (should use query_tests tool)
print('\n1. Testing: "What are the last 5 test runs?"')
print('   Expected: Should call query_tests(limit=5)')
result = analyzer.ask("What are the last 5 test runs?")
print(f'   ✅ Tools used: {result["tools_used"]}')
print(f'   Answer preview: {result["answer"][:150]}...')

# Test 2: Natural language query for failed tests
print('\n2. Testing: "Show me all failed tests"')
print('   Expected: Should call query_tests(exit_code=2)')
result = analyzer.ask("Show me all failed tests")
print(f'   ✅ Tools used: {result["tools_used"]}')
print(f'   Answer preview: {result["answer"][:150]}...')

# Test 3: Backward compatibility with about_test parameter
print('\n3. Testing: about_test parameter (backward compatibility)')
print('   Expected: Should NOT use MCP tools')
result = analyzer.ask("What are the slowest transactions?", about_test=0)
print(f'   ✅ Tools used: {result["tools_used"]} (should be empty)')
print(f'   Answer preview: {result["answer"][:150]}...')

# Test 4: General dataset question
print('\n4. Testing: "What is the pass rate?"')
print('   Expected: Should NOT need tools (dataset overview sufficient)')
result = analyzer.ask("What is the overall pass rate?")
print(f'   ✅ Tools used: {result["tools_used"]}')  
print(f'   Answer preview: {result["answer"][:150]}...')

print('\n🎉 All tests completed!')
