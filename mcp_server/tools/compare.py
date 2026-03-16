"""
MCP tool: compare_tests

Compare two test runs side-by-side.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.analyzer import TestAnalyzer
from typing import Optional


def compare_tests(testplan1: str, testplan2: str, analyzer: Optional[TestAnalyzer] = None) -> dict:
    """
    Compare two test runs side-by-side.
    
    Args:
        testplan1: First test identifier
        testplan2: Second test identifier
        analyzer: Optional analyzer instance (reuses connection if provided)
        
    Returns:
        Dict with comparison data including deltas
        
    Example:
        compare_tests("LoadTest_001", "LoadTest_002")
        
        # Reuse existing analyzer to avoid new connection
        compare_tests("LoadTest_001", "LoadTest_002", analyzer=my_analyzer)
    """
    # Initialize analyzer (or reuse if provided)
    if analyzer is None:
        analyzer = TestAnalyzer()
    
    # Get predictions for both tests
    try:
        pred1 = analyzer.predict_test(testplan1)
        pred2 = analyzer.predict_test(testplan2)
    except Exception as e:
        return {'error': str(e)}
    
    # Get raw data
    df1 = analyzer.data_source.get_test_by_id(testplan1)
    df2 = analyzer.data_source.get_test_by_id(testplan2)
    
    if len(df1) == 0 or len(df2) == 0:
        return {'error': 'One or both tests not found'}
    
    # Calculate key differences
    test1_info = df1.iloc[0]
    test2_info = df2.iloc[0]
    
    # Aggregate transaction metrics
    avg_p95_1 = df1['perc_95'].mean()
    avg_p95_2 = df2['perc_95'].mean()
    
    avg_error_1 = df1['error_percentage'].mean()
    avg_error_2 = df2['error_percentage'].mean()
    
    return {
        'testplan1': testplan1,
        'testplan2': testplan2,
        'test1': {
            'result': 'PASS' if test1_info['exit_code'] == 1 else 'FAIL',
            'exit_code': int(test1_info['exit_code']),
            'num_transactions': len(df1),
            'avg_p95': round(float(avg_p95_1), 2),
            'avg_error_pct': round(float(avg_error_1), 2),
            'prediction': pred1.get('prediction'),
            'confidence': pred1.get('confidence')
        },
        'test2': {
            'result': 'PASS' if test2_info['exit_code'] == 1 else 'FAIL',
            'exit_code': int(test2_info['exit_code']),
            'num_transactions': len(df2),
            'avg_p95': round(float(avg_p95_2), 2),
            'avg_error_pct': round(float(avg_error_2), 2),
            'prediction': pred2.get('prediction'),
            'confidence': pred2.get('confidence')
        },
        'differences': {
            'result_changed': (test1_info['exit_code'] == 1) != (test2_info['exit_code'] == 1),
            'p95_delta': round(float(avg_p95_2 - avg_p95_1), 2),
            'p95_pct_change': round(float((avg_p95_2 - avg_p95_1) / avg_p95_1 * 100), 2) if avg_p95_1 > 0 else None,
            'error_delta': round(float(avg_error_2 - avg_error_1), 2),
            'transaction_count_delta': len(df2) - len(df1)
        }
    }
