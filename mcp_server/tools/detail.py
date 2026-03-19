"""
MCP tool: get_test_detail

Get detailed information about a specific test.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.analyzer import TestAnalyzer
from typing import Optional


def get_test_detail(testplan: str, analyzer: Optional[TestAnalyzer] = None) -> dict:
    """
    Get comprehensive details about a specific test.
    
    Args:
        testplan: Test plan identifier
        analyzer: Optional analyzer instance (reuses connection if provided)
        
    Returns:
        Dict with test details, transactions, and predictions
        
    Example:
        get_test_detail("LoadTest_20260304T060726Z")
        
        # Reuse existing analyzer to avoid new connection
        get_test_detail("LoadTest_20260304T060726Z", analyzer=my_analyzer)
    """
    # Initialize analyzer (uses correct mode automatically, or reuse if provided)
    if analyzer is None:
        analyzer = TestAnalyzer()
    
    # Get test context with all transaction details
    context = analyzer.get_test_context(testplan)
    
    # Get classifier prediction
    try:
        prediction = analyzer.predict_test(testplan)
    except Exception as e:
        prediction = {'error': str(e)}
    
    # Get raw data
    df_raw = analyzer.data_source.get_test_by_id(testplan)
    
    if len(df_raw) == 0:
        return {'error': f'Test {testplan} not found'}
    
    # Build response
    test_info = df_raw.iloc[0]
    
    # Get transaction summaries
    transactions = []
    for _, txn in df_raw.iterrows():
        transactions.append({
            'name': txn['transaction_name'],
            'p95': round(float(txn['perc_95']), 2),
            'avg_response_time': round(float(txn['avg_response_time']), 2),
            'error_percentage': round(float(txn['error_percentage']), 2),
            'requests': int(txn.get('txn_requests', 0))
        })
    
    return {
        'testplan': testplan,
        'end_time': str(test_info['end_time']),
        'exit_code': int(test_info['exit_code']),
        'result': 'PASS' if test_info['exit_code'] == 1 else 'FAIL',
        'num_transactions': len(transactions),
        'transactions': transactions,
        'prediction': prediction,
        'formatted_context': context  # Full markdown context for LLM
    }
