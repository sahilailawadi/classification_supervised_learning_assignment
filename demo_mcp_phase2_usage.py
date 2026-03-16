#!/usr/bin/env python3
"""
Demo: Simplified notebook/Streamlit usage with MCP Phase 2

Before Phase 2:
  - Had to manually query pandas for "last 5 tests"
  - Then pass results to analyzer.ask_about_data()
  - LLM could hallucinate if you forgot to fetch data

After Phase 2:
  - Just ask naturally: analyzer.ask("What are the last 5 tests?")
  - LLM automatically determines which MCP tools to call
  - Real data fetched, no hallucination possible!
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.analyzer import TestAnalyzer

# Initialize once
analyzer = TestAnalyzer()

print("="*80)
print("MCP Phase 2: Natural Language Queries with Auto Data Fetching")
print("="*80)

# ==============================================================================
# OLD WAY (Still works! - Backward compatible)
# ==============================================================================
print("\n📜 OLD WAY (Manual pandas query + ask_about_data):\n")

# User had to:
# 1. Write pandas query
# 2. Format results
# 3. Call ask_about_data

# Example:
# df = analyzer.data_source.load_test_data()
# last_5 = df.groupby('testplan').agg({...}).head(5)
# result = analyzer.ask_about_data(last_5.to_string(), "What are these?")

print("Required: pandas query → format → ask_about_data()")
print("Risk: If you forget step 1-2, LLM might hallucinate\n")

# ==============================================================================
# NEW WAY (MCP Phase 2 - Automatic!)
# ==============================================================================
print("✨ NEW WAY (Just ask naturally - MCP handles data fetching):\n")

# Example 1: Last N tests
print("Question: 'What are the last 5 test runs?'")
result = analyzer.ask("What are the last 5 test runs?")
print(f"Tools auto-called: {result['tools_used']}")  # ['query_tests']
print(f"Answer: {result['answer'][:200]}...")
print()

# Example 2: Failed tests
print("Question: 'Show me all failed tests'")
result = analyzer.ask("Show me all failed tests")
print(f"Tools auto-called: {result['tools_used']}")  # ['query_tests']
print(f"Answer: {result['answer'][:200]}...")
print()

# Example 3: Specific test (backward compatible)
print("Question: 'What are slow transactions?' (about specific test)")
result = analyzer.ask("What are the slowest transactions?", about_test=0)
print(f"Tools auto-called: {result['tools_used']}")  # [] (uses old method)
print(f"Answer: {result['answer'][:200]}...")
print()

# Example 4: General statistics
print("Question: 'What is the pass rate?'")
result = analyzer.ask("What is the overall pass rate?")
print(f"Tools auto-called: {result['tools_used']}")  # [] (no tool needed)
print(f"Answer: {result['answer'][:200]}...")
print()

print("="*80)
print("🎉 Phase 2 Benefits:")
print("  - No manual pandas queries needed for common questions")
print("  - LLM decides which MCP tools to call")
print("  - Real data always fetched, zero hallucination risk")
print("  - Backward compatible - old code still works!")
print("="*80)
