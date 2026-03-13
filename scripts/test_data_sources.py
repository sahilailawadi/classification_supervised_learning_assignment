#!/usr/bin/env python3
"""
Test data sources to verify configuration and connectivity.

Usage:
    # Test academic mode (Excel)
    python scripts/test_data_sources.py --mode academic
    
    # Test work mode (PostgreSQL)
    python scripts/test_data_sources.py --mode work
    
    # Test both modes
    python scripts/test_data_sources.py --mode both
"""

import argparse
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load environment variables
load_dotenv(PROJECT_ROOT / '.env')

from src.data_source import get_data_source, ExcelDataSource, PostgresDataSource


def test_data_source(mode: str) -> bool:
    """
    Test a specific data source.
    
    Args:
        mode: "academic" or "work"
        
    Returns:
        True if test passed, False otherwise
    """
    print("\n" + "="*60)
    print(f"Testing {mode.upper()} mode")
    print("="*60)
    
    try:
        # Create data source
        ds = get_data_source(mode=mode)
        print(f"✅ Data source created: {ds.__class__.__name__}")
        
        # Test list_tests
        print("\n🔍 Testing list_tests()...")
        tests = ds.list_tests(limit=5)
        print(f"✅ Found tests: {tests}")
        
        if not tests:
            print("❌ No tests available")
            return False
        
        # Test load_test_data
        print("\n📊 Testing load_test_data()...")
        df = ds.load_test_data()
        print(f"✅ Loaded data: {len(df)} rows, {df['testplan'].nunique()} unique tests")
        print(f"   Columns: {list(df.columns[:10])}{'...' if len(df.columns) > 10 else ''}")
        
        # Verify expected columns
        expected_cols = ['testplan', 'transaction_name', 'exit_code', 'num_clients']
        missing_cols = [col for col in expected_cols if col not in df.columns]
        if missing_cols:
            print(f"⚠️  Missing expected columns: {missing_cols}")
        else:
            print(f"✅ All expected columns present")
        
        # Test get_test_by_id
        print(f"\n🎯 Testing get_test_by_id('{tests[0]}')...")
        test_df = ds.get_test_by_id(tests[0])
        print(f"✅ Retrieved test: {len(test_df)} transactions")
        print(f"   Sample transaction: {test_df['transaction_name'].iloc[0] if len(test_df) > 0 else 'N/A'}")
        
        # Data quality checks
        print("\n🔍 Data quality checks:")
        print(f"   Exit codes: {sorted(df['exit_code'].unique())}")
        print(f"   User counts: {sorted(df['num_clients'].unique())}")
        print(f"   Date range: {df['end_time'].min() if 'end_time' in df.columns else 'N/A'} to {df['end_time'].max() if 'end_time' in df.columns else 'N/A'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Test data source connectivity and functionality"
    )
    parser.add_argument(
        '--mode',
        choices=['academic', 'work', 'both'],
        default='both',
        help='Which mode to test (default: both)'
    )
    
    args = parser.parse_args()
    
    print("="*60)
    print("🧪 DATA SOURCE TEST SUITE")
    print("="*60)
    
    # Check environment configuration
    print("\n📋 Environment Configuration:")
    print(f"   LLM_MODE: {os.getenv('LLM_MODE', 'not set (defaults to academic)')}")
    
    # Check academic mode prerequisites
    project_root = Path(__file__).parent.parent
    excel_path = project_root / 'data_exports' / 'academic_demo_data.xlsx'
    print(f"   Academic Excel: {'✅ exists' if excel_path.exists() else '❌ not found'}")
    
    # Check work mode prerequisites
    db_vars = ['DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_USER', 'DB_PASSWORD']
    db_configured = all(os.getenv(var) for var in db_vars)
    print(f"   PostgreSQL DB: {'✅ configured' if db_configured else '❌ not configured'}")
    
    # Run tests
    results = {}
    
    if args.mode == 'both':
        modes = ['academic', 'work']
    else:
        modes = [args.mode]
    
    for mode in modes:
        results[mode] = test_data_source(mode)
    
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
        print("\n⚠️  Some tests failed. Check configuration:")
        print("\n💡 Configuration hints:")
        print("   ACADEMIC mode: Run 'python scripts/export_anonymized_data.py'")
        print("   WORK mode: Verify .env has DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD")
        return 1


if __name__ == '__main__':
    sys.exit(main())
