#!/usr/bin/env python3
"""Quick test for sklearn warning fix"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.analyzer import TestAnalyzer

print("Testing prediction with warning fix...")
a = TestAnalyzer()
result = a.predict_test('LoadTest_001')
print(f"\n✅ Prediction: {result['prediction']}")
print(f"   Confidence: {result['confidence']:.1%}")
print(f"   Actual: {result['actual_result']}")
print("\n✓ If you don't see UserWarning above, the fix worked!")
