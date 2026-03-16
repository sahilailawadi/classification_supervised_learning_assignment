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
    
    # Derive test_type from build_version (same logic as features.py)
    def derive_test_type(build_version):
        if pd.isna(build_version) or build_version == '':
            return 'unknown'
        bv_lower = str(build_version).lower()
        if 'load' in bv_lower:
            return 'load_test'
        elif 'stress' in bv_lower:
            return 'stress_test'
        elif 'soak' in bv_lower:
            return 'soak_test'
        else:
            return 'load_test'  # default
    
    df_test['test_type'] = df_test['build_version'].apply(derive_test_type)
    
    # Extract test metadata
    test_info = df_test.iloc[0]
    test_type = test_info['test_type']
    num_clients = test_info.get('num_clients', 0)
    exit_code = test_info['exit_code']
    
    # Ensure data types match for merge
    df_test["test_type"] = df_test["test_type"].astype(str)
    df_test["transaction_name"] = df_test["transaction_name"].astype(str)
    df_test["num_clients"] = pd.to_numeric(df_test["num_clients"], errors='coerce')
    
    baselines["test_type"] = baselines["test_type"].astype(str)
    baselines["transaction_name"] = baselines["transaction_name"].astype(str)
    baselines["num_clients"] = pd.to_numeric(baselines["num_clients"], errors='coerce')
    
    # Merge with baselines
    df_merged = df_test.copy()
    df_merged = df_merged.merge(
        baselines,
        on=['test_type', 'num_clients', 'transaction_name'],
        how='left'
    )
    
    # Build transaction comparison list with ALL baseline fields
    transactions = []
    for _, row in df_merged.iterrows():
        has_baseline = pd.notna(row.get('baseline_median_p95'))
        
        # Actual values - include ALL available metrics
        txn_data = {
            'name': row['transaction_name'],
            'actual': {
                'p95': float(row['perc_95']),
                'avg_rt': float(row['avg_response_time']),
                'min_rt': float(row.get('min_response', 0)),
                'max_rt': float(row.get('max_response', 0)),
                'error_pct': float(row['error_percentage']),
                'total_count': int(row.get('total_count', 0)),
                'pass_count': int(row.get('pass_count', 0)),
                'fail_count': int(row.get('fail_count', 0))
            },
            'has_baseline': has_baseline
        }
        
        if has_baseline:
            # Baseline values - include ALL baseline fields
            txn_data['baseline'] = {
                'p95': float(row['baseline_median_p95']),
                'avg_rt': float(row['baseline_median_avg_rt']),
                'error_pct': float(row['baseline_median_error_pct']),
                'throughput_per_user': float(row.get('baseline_median_throughput_per_user', 0))
            }
            
            # Deviations for ALL metrics
            txn_data['deviation'] = {
                'p95_pct': ((row['perc_95'] - row['baseline_median_p95']) / 
                           row['baseline_median_p95'] * 100) if row['baseline_median_p95'] > 0 else 0,
                'avg_rt_pct': ((row['avg_response_time'] - row['baseline_median_avg_rt']) / 
                              row['baseline_median_avg_rt'] * 100) if row['baseline_median_avg_rt'] > 0 else 0,
                'error_delta': row['error_percentage'] - row['baseline_median_error_pct'],
                'p95_absolute': row['perc_95'] - row['baseline_median_p95'],
                'avg_rt_absolute': row['avg_response_time'] - row['baseline_median_avg_rt']
            }
        else:
            txn_data['baseline'] = None
            txn_data['deviation'] = None
            txn_data['note'] = 'No baseline (transaction only appears in failing runs)'
        
        transactions.append(txn_data)
    
    # Compute summary statistics AND classifier-style features
    with_baseline = [t for t in transactions if t['has_baseline']]
    
    summary = {
        'test_type': test_type,
        'num_clients': int(num_clients),
        'result': 'PASS' if exit_code == 1 else 'FAIL',
        'total_transactions': len(transactions),
        'transactions_with_baseline': len(with_baseline),
        'transactions_without_baseline': len(transactions) - len(with_baseline)
    }
    
    # Classifier-style features (mimics what the model sees)
    if with_baseline:
        deviations = [t['deviation'] for t in with_baseline]
        
        # P95 deviation features
        summary['avg_p95_deviation_pct'] = sum(d['p95_pct'] for d in deviations) / len(deviations)
        summary['max_p95_deviation_pct'] = max(d['p95_pct'] for d in deviations)
        summary['min_p95_deviation_pct'] = min(d['p95_pct'] for d in deviations)
        
        # Avg RT deviation features
        summary['avg_avgrt_deviation_pct'] = sum(d['avg_rt_pct'] for d in deviations) / len(deviations)
        summary['max_avgrt_deviation_pct'] = max(d['avg_rt_pct'] for d in deviations)
        
        # Error deviation
        summary['avg_error_delta'] = sum(d['error_delta'] for d in deviations) / len(deviations)
        summary['max_error_delta'] = max(d['error_delta'] for d in deviations)
        
        # Classifier thresholds (same as in features.py)
        summary['pct_txn_critical_p95'] = (len([d for d in deviations if d['p95_pct'] > 50]) / len(with_baseline) * 100)
        summary['pct_txn_degraded_p95'] = (len([d for d in deviations if 20 < d['p95_pct'] <= 50]) / len(with_baseline) * 100)
        summary['pct_txn_critical_avgrt'] = (len([d for d in deviations if d['avg_rt_pct'] > 50]) / len(with_baseline) * 100)
        summary['pct_txn_degraded_avgrt'] = (len([d for d in deviations if 20 < d['avg_rt_pct'] <= 50]) / len(with_baseline) * 100)
        
        summary['critical_deviations_count'] = len([d for d in deviations if d['p95_pct'] > 50])
        summary['degraded_deviations_count'] = len([d for d in deviations if 20 < d['p95_pct'] <= 50])
    
    return {
        'testplan': testplan,
        'summary': summary,
        'transactions': transactions,
        'baseline_source': 'models/baselines.pkl (medians from passing runs)',
        'baseline_grouping': f'test_type={test_type}, num_clients={num_clients}',
        'available_fields': {
            'per_transaction': ['p95', 'avg_rt', 'min_rt', 'max_rt', 'error_pct', 'total_count', 'pass_count', 'fail_count'],
            'baseline_fields': ['p95', 'avg_rt', 'error_pct', 'throughput_per_user'],
            'deviation_fields': ['p95_pct', 'avg_rt_pct', 'error_delta', 'p95_absolute', 'avg_rt_absolute']
        }
    }
