"""
MCP tool: query_tests

Query test runs with filters and sorting.
"""

from typing import Optional
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.data_source import get_data_source, BaseDataSource


def query_tests(
    limit: int = 10,
    exit_code: Optional[int] = None,
    sort_by: str = "end_time",
    ascending: bool = False,
    data_source: Optional[BaseDataSource] = None
) -> dict:
    """
    Query test runs with optional filtering and sorting.
    
    Args:
        limit: Maximum number of tests to return (default: 10)
        exit_code: Filter by exit code (1=PASS, 2+=FAIL)
        sort_by: Column to sort by (default: "end_time")
        ascending: Sort ascending if True, descending if False
        data_source: Optional data source (reuses connection if provided)
        
    Returns:
        Dict with 'tests' list and 'count'
        
    Example:
        # Get last 5 tests
        query_tests(limit=5, sort_by="end_time", ascending=False)
        
        # Get failed tests (reusing existing data source)
        query_tests(limit=10, exit_code=2, data_source=my_data_source)
    """
    # Get data source (automatically uses correct mode, or reuse if provided)
    if data_source is None:
        data_source = get_data_source()
    
    # Load full dataset (will use cached data if data source is reused)
    df = data_source.load_test_data()
    
    # Apply filters
    if exit_code is not None:
        df = df[df['exit_code'] == exit_code]
    
    # Group by testplan to get unique tests
    test_summary = df.groupby('testplan').agg({
        'end_time': 'first',
        'exit_code': 'first',
        'transaction_name': 'count',
        'perc_95': 'mean',
        'error_percentage': 'mean'
    }).rename(columns={'transaction_name': 'num_transactions'})
    
    # Sort
    if sort_by in test_summary.columns:
        test_summary = test_summary.sort_values(sort_by, ascending=ascending)
    
    # Limit
    test_summary = test_summary.head(limit)
    
    # Format response
    tests = []
    for testplan, row in test_summary.iterrows():
        tests.append({
            'testplan': testplan,
            'end_time': str(row['end_time']),
            'result': 'PASS' if row['exit_code'] == 1 else 'FAIL',
            'exit_code': int(row['exit_code']),
            'num_transactions': int(row['num_transactions']),
            'avg_p95': round(float(row['perc_95']), 2),
            'avg_error_pct': round(float(row['error_percentage']), 2)
        })
    
    return {
        'tests': tests,
        'count': len(tests),
        'total_in_dataset': df['testplan'].nunique()
    }
