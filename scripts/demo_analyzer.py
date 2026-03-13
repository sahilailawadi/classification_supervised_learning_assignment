#!/usr/bin/env python3
"""
Demo script for LLM-Augmented Test Analysis.

Demonstrates:
1. Single test analysis with LLM insights
2. Test comparison between PASS and FAIL
3. Integration of classifier + LLM

Usage:
    # Analyze a specific test
    python scripts/demo_analyzer.py --test LoadTest_001
    
    # Compare two tests
    python scripts/demo_analyzer.py --compare LoadTest_001 LoadTest_002
    
    # Run demo with sample tests
    python scripts/demo_analyzer.py --demo
"""

import argparse
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load environment
load_dotenv(PROJECT_ROOT / '.env')

from src.analyzer import TestAnalyzer


def demo_single_analysis(analyzer: TestAnalyzer, testplan: str):
    """Demo single test analysis."""
    print("\n" + "="*70)
    print("DEMO: Single Test Analysis")
    print("="*70 + "\n")
    
    try:
        # Run analysis
        analysis = analyzer.analyze_test(testplan, include_transactions=True)
        
        print(analysis)
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


def demo_comparison(analyzer: TestAnalyzer, test1: str, test2: str):
    """Demo test comparison."""
    print("\n" + "="*70)
    print("DEMO: Test Comparison")
    print("="*70 + "\n")
    
    try:
        # Run comparison
        comparison = analyzer.compare_tests(test1, test2)
        
        print(comparison)
        
    except Exception as e:
        print(f"❌ Comparison failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


def run_demo(analyzer: TestAnalyzer):
    """Run automated demo with sample tests."""
    print("\n" + "="*70)
    print("🎬 LLM-AUGMENTED TEST ANALYSIS DEMO")
    print("="*70 + "\n")
    
    # Get available tests
    tests = analyzer.data_source.list_tests(limit=10)
    
    if len(tests) < 2:
        print("❌ Not enough tests available for demo")
        return False
    
    print(f"📊 Available tests: {len(tests)}")
    print(f"   Samples: {tests[:5]}\n")
    
    # Find a PASS and a FAIL test
    pass_test = None
    fail_test = None
    
    for test in tests[:20]:  # Check first 20 tests
        try:
            result = analyzer.predict_test(test)
            if result['actual_result'] == 'PASS' and pass_test is None:
                pass_test = test
            elif result['actual_result'] == 'FAIL' and fail_test is None:
                fail_test = test
            
            if pass_test and fail_test:
                break
        except Exception as e:
            print(f"   ⚠️  Skipping {test}: {e}")
            continue
    
    # Demo 1: Analyze a FAIL test
    if fail_test:
        print("\n" + "▶"*35)
        print("DEMO 1: Analyzing a FAILED test")
        print("▶"*35 + "\n")
        
        success = demo_single_analysis(analyzer, fail_test)
        if not success:
            return False
    else:
        print("⚠️  No FAIL test found for Demo 1")
    
    # Demo 2: Compare PASS vs FAIL
    if pass_test and fail_test:
        print("\n" + "▶"*35)
        print("DEMO 2: Comparing PASS vs FAIL test")
        print("▶"*35 + "\n")
        
        success = demo_comparison(analyzer, pass_test, fail_test)
        if not success:
            return False
    else:
        print("⚠️  Not enough tests for Demo 2")
    
    print("\n" + "="*70)
    print("✅ DEMO COMPLETE")
    print("="*70 + "\n")
    
    return True


def main():
    parser = argparse.ArgumentParser(
        description="LLM-Augmented Test Analysis Demo"
    )
    parser.add_argument(
        '--test',
        help='Analyze a specific test'
    )
    parser.add_argument(
        '--compare',
        nargs=2,
        metavar=('TEST1', 'TEST2'),
        help='Compare two tests'
    )
    parser.add_argument(
        '--demo',
        action='store_true',
        help='Run automated demo'
    )
    parser.add_argument(
        '--mode',
        choices=['academic', 'work'],
        help='Override LLM_MODE'
    )
    
    args = parser.parse_args()
    
    # Initialize analyzer
    try:
        analyzer = TestAnalyzer(mode=args.mode)
    except Exception as e:
        print(f"❌ Failed to initialize TestAnalyzer: {e}")
        print("\n💡 Make sure:")
        print("   1. You have a trained model: python -m src.train")
        print("   2. LLM credentials are configured in .env")
        print("   3. Data source is available (Excel or PostgreSQL)")
        return 1
    
    # Run requested action
    if args.test:
        success = demo_single_analysis(analyzer, args.test)
    elif args.compare:
        success = demo_comparison(analyzer, args.compare[0], args.compare[1])
    elif args.demo:
        success = run_demo(analyzer)
    else:
        print("❌ No action specified. Use --demo, --test, or --compare")
        print("   Run with --help for usage information")
        return 1
    
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
