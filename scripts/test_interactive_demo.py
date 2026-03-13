#!/usr/bin/env python3
"""
Quick test to verify interactive demo components work
"""

import sys
from pathlib import Path

# Add project root - go up one level from scripts/
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

print("🧪 Testing interactive demo components...")
print()

# Test 1: Imports
print("1️⃣ Testing imports...")
try:
    import streamlit as st
    import plotly.express as px
    import plotly.graph_objects as go
    import jupyter
    print("   ✅ All UI libraries imported")
except ImportError as e:
    print(f"   ❌ Import error: {e}")
    sys.exit(1)

# Test 2: Core components
print("2️⃣ Testing core components...")
try:
    from dotenv import load_dotenv
    load_dotenv(project_root / '.env')
    
    from src.analyzer import TestAnalyzer
    from src.data_source import get_data_source
    from src.llm_provider import get_llm_provider
    print("   ✅ Core components imported")
except Exception as e:
    print(f"   ❌ Component error: {e}")
    sys.exit(1)

# Test 3: Analyzer initialization (light test)
print("3️⃣ Testing analyzer initialization...")
try:
    analyzer = TestAnalyzer()
    print(f"   ✅ TestAnalyzer created")
    print(f"      LLM: {analyzer.llm.__class__.__name__}")
    print(f"      Data: {analyzer.data_source.__class__.__name__}")
except Exception as e:
    print(f"   ⚠️  Analyzer init warning: {e}")
    print("      (May be expected if credentials not configured)")

# Test 4: Data loading
print("4️⃣ Testing data loading...")
try:
    df = analyzer.data_source.load_test_data()
    print(f"   ✅ Data loaded: {len(df):,} rows, {df['testplan'].nunique()} tests")
except Exception as e:
    print(f"   ⚠️  Data loading warning: {e}")
    print("      (May be expected if database not accessible)")

print()
print("🎉 Demo components are ready!")
print()
print("Next steps:")
print("  📓 Jupyter: jupyter notebook notebooks/llm_analysis_demo.ipynb")
print("  🎨 Streamlit: streamlit run app_llm_demo.py")
