"""
MCP tool: get_baseline_comparison

Compare a test against the classifier's actual baseline data.
"""

import sys
from pathlib import Path
import pandas as pd
import joblib
from typing import Optional

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.analyzer import TestAnalyzer


def get_baseline_comparison(testplan: str, analyzer: Optional[TestAnalyzer] = None) -> dict:
    """
    Compare a test against the classifier's actual baseline data.
    
    Shows the baseline values used by the classifier for feature engineering.
    Baselines are medians from passing runs grouped by (test_type, num_clients, transaction_name).
    
    Args:
        testplan: Test plan identifier
        analyzer: Optional analyzer instance (reuses connection if provided)
        
    Returns:
        Dict with test data, baseline data, and deviations
        
    Example:
        get_baseline_comparison("LoadTest_20260304T060726Z")
    """
    # Initialize analyzer (or reuse if provided)
    if analyzer is None:
        analyzer = TestAnalyzer()
    
    # Load baselines used by classifier
    baseline_path = project_root / "models" / "baselines.pkl"
    if not baseline_path.exists():
        return {
            'error': 'Baselines not found. Run training first to generate baselines.pkl',
            'testplan': testplan
        }
    
    baselines = joblib.load(baseline_path)
    
    # Get test data
    df_test = analyzer.data_source.get_test_by_id(testplan)
    
    if len(df_test) == 0:
        return {'error': f'Test {testplan} not found'}
    
    # Extract test metadata
    test_info = df_test.iloc[0]
    test_type = test_info.get('test_type', 'unknown')
    num_clients = test_info.get('num_clients', 0)
    exit_code = test_info['exit_code']
    
    # Merge with baselines
    df_merged = df_test.copy()
    df_merged = df_merged.merge(
        baselines,
        on=['test_type', 'num_clients', 'transaction_name'],
        how='left'
    )
    
    # Build transaction comparison list
    transactions = []
    for _, row in df_merged.iterrows():
        has_baseline = pd.notna(row.get('baseline_median_p95'))
        
        txn_data = {
            'name': row['transaction_name'],
            'actual': {
                'p95': float(row['perc_95']),
                'avg_rt': float(row['avg_response_time']),
                'error_pct': float(row['error_percentage'])
            },
            'has_baseline': has_baseline
        }
        
        if has_baseline:
            txn_data['baseline'] = {
                'p95': float(row['baseline_median_p95']),
                'avg_rt': float(row['baseline_median_avg_rt']),
                'error_pct': float(row['baseline_median_error_pct'])
            }
            txn_data['deviation'] = {
                'p95_pct': ((row['perc_95'] - row['baseline_median_p95']) / 
                           row['baseline_median_p95'] * 100) if row['baseline_median_p95'] > 0 else 0,
                'avg_rt_pct': ((row['avg_response_time'] - row['baseline_median_avg_rt']) / 
                              row['baseline_median_avg_rt'] * 100) if row['baseline_median_avg_rt'] > 0 else 0,
                'error_delta': row['error_percentage'] - row['baseline_median_error_pct']
            }
        else:
            txn_data['baseline'] = None
            txn_data['deviation'] = None
            txn_data['note'] = 'No baseline (transaction only appears in failing runs)'
        
        transactions.append(txn_data)
    
    # Compute summary statistics
    with_baseline = [t for t in transactions if t['has_baseline']]
    
    summary = {
        'test_type': test_type,
        'num_clients': int(num_clients),
        'result': 'PASS' if exit_code == 1 else 'FAIL',
        'total_transactions': len(transactions),
        'transactions_with_baseline': len(with_baseline),
        'transactions_without_baseline': len(transactions) - len(with_baseline)
    }
    
    if with_baseline:
        summary['avg_p95_deviation_pct'] = sum(t['deviation']['p95_pct'] for t in with_baseline) / len(with_baseline)
        summary['max_p95_deviation_pct'] = max(t['deviation']['p95_pct'] for t in with_baseline)
        summary['critical_deviations'] = len([t for t in with_baseline if t['deviation']['p95_pct'] > 50])
    
    return {
        'testplan': testplan,
        'summary': summary,
        'transactions': transactions,
        'baseline_source': 'models/baselines.pkl (medians from passing runs)',
        'baseline_grouping': f'test_type={test_type}, num_clients={num_clients}'
    }
