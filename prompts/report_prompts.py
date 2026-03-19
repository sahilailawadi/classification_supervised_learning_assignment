"""
Report generation prompts for performance test analysis.

This module centralizes all report prompt templates to:
- Eliminate duplication between Chat Analysis and Deep Dive pages
- Separate prompt engineering from UI logic
- Make prompts easier to maintain and version control
- Enable prompt testing and validation

Two strategies supported:
1. Data-rich prompts: Pre-fetch and embed actual test data (anti-hallucination)
2. MCP-delegated prompts: Short instructions, let MCP tools fetch data
"""


def get_summary_prompt_with_data(test_id, test_summary, baseline_summary, pred_result):
    """
    Summary report with embedded data.
    
    Args:
        test_id: Test identifier
        test_summary: Dict with test_df aggregated data
        baseline_summary: Dict from baseline_result['summary']
        pred_result: Dict from analyzer.predict_test()
    
    Returns:
        Formatted prompt string with actual data embedded
    """
    conf_pct = pred_result['confidence'] if pred_result['confidence'] >= 2 else pred_result['confidence'] * 100
    
    return f"""Analyze the most recent test run: {test_id}

ACTUAL TEST DATA:
- Test ID: {test_id}
- End Time: {test_summary['end_time']}
- Exit Code: {'PASS' if test_summary['exit_code'] == 1 else 'FAIL'}
- Classifier Prediction: {pred_result['prediction']} ({conf_pct:.1f}% confidence)
- Total Transactions: {int(test_summary['transaction_name'])}
- Average P95: {test_summary['perc_95']:.0f}ms
- Error Rate: {test_summary['error_percentage']:.2f}%
- Avg P95 Deviation from Baseline: {baseline_summary.get('avg_p95_deviation_pct', 0):.1f}%
- Critical Deviations (>50%): {baseline_summary.get('critical_deviations_count', 0)} transactions

Provide a concise summary with:
1. **Overall Assessment**: PASS/FAIL with confidence
2. **Key Metrics**: P95, error rate, baseline comparison
3. **Key Issues**: Critical deviations (if any)
4. **Release Readiness**: GO/NO-GO and why

Keep it brief - 4-5 sentences max."""


def get_po_report_prompt_with_data(test_id, test_summary, baseline_summary, critical_list, pred_result):
    """
    Product Owner sign-off report with embedded data.
    
    Args:
        test_id: Test identifier
        test_summary: Dict with test_df aggregated data
        baseline_summary: Dict from baseline_result['summary']
        critical_list: Formatted string with critical transactions
        pred_result: Dict from analyzer.predict_test()
    
    Returns:
        Formatted prompt string with actual data embedded
    """
    conf_pct = pred_result['confidence'] if pred_result['confidence'] >= 2 else pred_result['confidence'] * 100
    
    return f"""Generate a release sign-off report for test {test_id} for Product Owner review.

ACTUAL TEST DATA (DO NOT MODIFY):

Test Overview:
- Test ID: {test_id}
- End Time: {test_summary['end_time']}
- Result: {'PASS' if test_summary['exit_code'] == 1 else 'FAIL'}
- Classifier Prediction: {pred_result['prediction']} ({conf_pct:.1f}% confidence)
- Transactions Tested: {int(test_summary['transaction_name'])}
- Average P95: {test_summary['perc_95']:.0f}ms
- Error Rate: {test_summary['error_percentage']:.2f}%

Performance vs Baseline:
- Average P95 Deviation: {baseline_summary.get('avg_p95_deviation_pct', 0):.1f}%
- Critical Deviations (>50%): {baseline_summary.get('critical_deviations_count', 0)} transactions

Critical Transactions:
{critical_list if critical_list else 'None - all transactions within acceptable limits'}

Create a professional report with:

1. Executive Summary (2-3 sentences about overall performance)

2. Test Overview (use the EXACT data above - do not make up transaction names)

3. Performance Assessment:
   - Summarize performance vs baseline
   - Highlight any critical issues

4. Risk Assessment:
   - High/Medium/Low risk classification
   - Impact on users

5. **Release Recommendation** (bold):
   - **GO** / **NO-GO** / **GO WITH CAUTION**
   - Justification in 2-3 sentences

Format: Professional, concise, non-technical language suitable for stakeholder presentation."""


def get_dev_report_prompt_with_data(test_id, txn_table, baseline_summary, pred_result):
    """
    Engineering/Dev report with embedded transaction table.
    
    Args:
        test_id: Test identifier
        txn_table: Markdown table string with all transaction data
        baseline_summary: Dict from baseline_result['summary']
        pred_result: Dict from analyzer.predict_test()
    
    Returns:
        Formatted prompt string with actual data embedded
    """
    conf_pct = pred_result['confidence'] if pred_result['confidence'] >= 2 else pred_result['confidence'] * 100
    
    return f"""Generate a detailed engineering report for test {test_id} for Dev/QA teams.

Classifier Prediction: {pred_result['prediction']} ({conf_pct:.1f}% confidence)

ACTUAL BASELINE COMPARISON DATA (DO NOT MODIFY - USE EXACT TRANSACTION NAMES):

Test Type: {baseline_summary.get('test_type', 'N/A')}
Number of Clients: {baseline_summary.get('num_clients', 'N/A')}
Total Transactions: {baseline_summary.get('total_transactions', 'N/A')}
Transactions with Baseline: {baseline_summary.get('transactions_with_baseline', 'N/A')}

Classifier Features:
- Avg P95 Deviation: {baseline_summary.get('avg_p95_deviation_pct', 0):.1f}%
- Max P95 Deviation: {baseline_summary.get('max_p95_deviation_pct', 0):.1f}%
- Critical Transactions (>50%): {baseline_summary.get('pct_txn_critical_p95', 0):.1f}% ({baseline_summary.get('critical_deviations_count', 0)} txns)
- Degraded Transactions (20-50%): {baseline_summary.get('pct_txn_degraded_p95', 0):.1f}% ({baseline_summary.get('degraded_deviations_count', 0)} txns)

Transaction-level Performance Breakdown (ACTUAL DATA - DO NOT CHANGE TRANSACTION NAMES):
{txn_table}

Create a technical report with:

1. Classifier Analysis:
   - Prediction: {pred_result['prediction']} ({conf_pct:.1f}% confidence)
   - Summarize the classifier features above
   
2. Transaction-level Performance:
   - Include the EXACT table above (do not modify numbers or transaction names)
   - Highlight critical and degraded transactions
   
3. Critical Issues Analysis:
   - List transactions with >50% P95 degradation
   - Explain likely root causes
   
4. Action Items:
   - Specific debugging steps for worst performers
   - Code areas to investigate
   - Optimization recommendations

Format: Technical depth suitable for engineers. Use the ACTUAL data provided above - do not make up transaction names like Login, Search, Checkout."""


def get_stakeholder_report_prompt_with_data(test_id, qa_table, summary, pred_result):
    """
    Stakeholder summary report with embedded data.
    
    Args:
        test_id: Test identifier
        qa_table: Markdown table string with top 5 transactions
        summary: Dict from baseline_result['summary']
        pred_result: Dict from analyzer.predict_test()
    
    Returns:
        Formatted prompt string with actual data embedded
    """
    conf_pct = pred_result['confidence'] if pred_result['confidence'] >= 2 else pred_result['confidence'] * 100
    
    return f"""Generate a stakeholder summary for test {test_id}.

ACTUAL TEST DATA (DO NOT MODIFY - USE EXACT TRANSACTION NAMES):

Test Summary:
- Test ID: {test_id}
- Classifier: {pred_result['prediction']} ({conf_pct:.1f}% confidence)
- Total Transactions: {summary.get('total_transactions', 'N/A')}
- Transactions with Baseline: {summary.get('transactions_with_baseline', 'N/A')}

Quality Metrics:
- Avg P95 Deviation: {summary.get('avg_p95_deviation_pct', 0):.1f}%
- Max P95 Deviation: {summary.get('max_p95_deviation_pct', 0):.1f}%
- Critical Transactions: {summary.get('critical_deviations_count', 0)}
- Degraded Transactions: {summary.get('degraded_deviations_count', 0)}

Top 5 Transactions by Performance (ACTUAL DATA):
{qa_table}

Create a stakeholder summary with:

1. Test Summary:
   - Use the data above
   - Classifier confidence interpretation

2. Transaction Highlights:
   - Include the EXACT table above (do not make up transaction names)
   - Pass/Fail breakdown
   
3. Why Classifier Marked as {pred_result['prediction']}:
   - Explain based on actual metrics
   - Reference specific transactions from the table above

4. **Release Recommendation** (bold):
   - Ready for release / Needs review / Blocked
   - Brief justification

Format: Brief, business-focused. Use ACTUAL transaction names from the data above."""


# ============================================================================
# MCP-Delegated Prompts (Short versions for Deep Dive)
# ============================================================================

def get_po_report_prompt_short(test_id, prediction, confidence):
    """
    Short PO report prompt - delegates data fetching to MCP tools.
    
    Args:
        test_id: Test identifier
        prediction: Classifier prediction (PASS/FAIL)
        confidence: Confidence percentage
    
    Returns:
        Short instruction prompt
    """
    return f"""Generate a release sign-off report for test {test_id} for Product Owner. Include: executive summary, test overview with classifier prediction ({prediction}, {confidence:.1f}% confidence), performance vs baseline, critical issues, and bold **Release Recommendation** (GO/NO-GO/WITH CAUTION)."""


def get_eng_report_prompt_short(test_id, prediction, confidence):
    """
    Short engineering report prompt - delegates data fetching to MCP tools.
    
    Args:
        test_id: Test identifier
        prediction: Classifier prediction (PASS/FAIL)
        confidence: Confidence percentage
    
    Returns:
        Short instruction prompt
    """
    return f"""Generate a detailed engineering report for test {test_id}. Include: classifier analysis ({prediction}, {confidence:.1f}% confidence), complete transaction-level breakdown with baseline comparisons showing ALL transactions with actual data, critical issues (>50% degradation), and actionable debugging steps."""


def get_qa_report_prompt_short(test_id, prediction, confidence):
    """
    Short QA report prompt - delegates data fetching to MCP tools.
    
    Args:
        test_id: Test identifier
        prediction: Classifier prediction (PASS/FAIL)
        confidence: Confidence percentage
    
    Returns:
        Short instruction prompt
    """
    return f"""Generate a comprehensive QA report for test {test_id}.

Include:
1. Test Summary: Classifier prediction ({prediction}, {confidence:.1f}% confidence)
2. Baseline Comparison Summary: Overall deviation metrics
3. **COMPLETE Transaction Performance Table**: Show ALL transactions with baseline comparison (P95, Avg RT, Error Rate, deviations). Do not abbreviate or use "..." - include every transaction.
4. Critical Issues: Detailed analysis of transactions with >50% deviation
5. Action Items: Specific debugging recommendations
6. **QA Sign-Off Status**: Bold assessment (READY / NEEDS RETEST / BLOCKED)

The transaction table must be complete - do not omit any transactions."""


def get_explain_prediction_prompt(test_id, prediction, confidence):
    """
    Prompt to explain classifier's prediction decision.
    
    Args:
        test_id: Test identifier
        prediction: Classifier prediction (PASS/FAIL)
        confidence: Confidence percentage
    
    Returns:
        Explanation prompt
    """
    return f"""Explain why the classifier predicted {prediction} for test {test_id} with {confidence:.1f}% confidence. What were the key factors? Which transactions influenced this decision?"""


# ============================================================================
# Helper Functions
# ============================================================================

def format_critical_transactions_list(baseline_result, top_n=5):
    """
    Format critical transactions into a bulleted list.
    
    Args:
        baseline_result: Dict from get_baseline_comparison()
        top_n: Number of transactions to include
    
    Returns:
        Formatted string with critical transactions or "No baseline data available"
    """
    if 'error' in baseline_result:
        return "No baseline data available"
    
    critical_txns = [t for t in baseline_result['transactions'] 
                    if t['has_baseline'] and t['deviation']['p95_pct'] > 50]
    
    if not critical_txns:
        return ""
    
    sorted_txns = sorted(critical_txns, key=lambda x: x['deviation']['p95_pct'], reverse=True)[:top_n]
    
    return "\n".join([
        f"- {t['name']}: {t['actual']['p95']:.0f}ms vs {t['baseline']['p95']:.0f}ms baseline ({t['deviation']['p95_pct']:+.1f}%)"
        for t in sorted_txns
    ])


def format_transaction_table(baseline_result):
    """
    Format transaction data into a markdown table.
    
    Args:
        baseline_result: Dict from get_baseline_comparison()
    
    Returns:
        Markdown table string or "No baseline data available"
    """
    if 'error' in baseline_result:
        return "No baseline data available"
    
    table = "\n| Transaction | Actual P95 | Baseline P95 | Δ% | Actual Avg RT | Baseline Avg RT | Δ% | Error% | Status |\n"
    table += "|------------|-----------|-------------|-----|--------------|----------------|-----|---------|--------|\n"
    
    for txn in baseline_result['transactions']:
        if txn['has_baseline']:
            status = "⚠️ CRITICAL" if txn['deviation']['p95_pct'] > 50 else "⚠️ DEGRADED" if txn['deviation']['p95_pct'] > 20 else "✅ PASS"
            table += f"| {txn['name']} | {txn['actual']['p95']:.0f}ms | {txn['baseline']['p95']:.0f}ms | {txn['deviation']['p95_pct']:+.1f}% | {txn['actual']['avg_rt']:.0f}ms | {txn['baseline']['avg_rt']:.0f}ms | {txn['deviation']['avg_rt_pct']:+.1f}% | {txn['actual']['error_pct']:.1f}% | {status} |\n"
    
    return table


def format_qa_table(baseline_result, top_n=5):
    """
    Format top N transactions for QA/stakeholder reports.
    
    Args:
        baseline_result: Dict from get_baseline_comparison()
        top_n: Number of transactions to include
    
    Returns:
        Markdown table string or "No baseline data available"
    """
    if 'error' in baseline_result:
        return "No baseline data available"
    
    txns_sorted = sorted([t for t in baseline_result['transactions'] if t['has_baseline']], 
                        key=lambda x: x['deviation']['p95_pct'], reverse=True)[:top_n]
    
    table = "\n| Transaction | P95 | Baseline P95 | Δ% | Status |\n"
    table += "|------------|-----|-------------|-----|--------|\n"
    
    for txn in txns_sorted:
        status = "❌ CRITICAL" if txn['deviation']['p95_pct'] > 50 else "⚠️ WARN" if txn['deviation']['p95_pct'] > 20 else "✅ PASS"
        table += f"| {txn['name']} | {txn['actual']['p95']:.0f}ms | {txn['baseline']['p95']:.0f}ms | {txn['deviation']['p95_pct']:+.1f}% | {status} |\n"
    
    return table


def get_test_comparison_prompt(test1_id, test2_id, df_test1, df_test2):
    """
    Comprehensive test-to-test comparison with focused transaction data.
    
    Compares key transactions between two tests to identify:
    - Overall performance winner
    - Common transactions that regressed/improved
    - Transaction-specific differences
    - Anomalies and patterns
    
    Args:
        test1_id: First test identifier
        test2_id: Second test identifier  
        df_test1: DataFrame with all transactions from test 1
        df_test2: DataFrame with all transactions from test 2
    
    Returns:
        Formatted prompt string with focused comparison data
    """
    # Summary statistics
    test1_summary = {
        'exit_code': df_test1['exit_code'].iloc[0],
        'result': 'PASS' if df_test1['exit_code'].iloc[0] == 1 else 'FAIL',
        'transactions': len(df_test1),
        'avg_p95': df_test1['perc_95'].mean(),
        'max_p95': df_test1['perc_95'].max(),
        'avg_rt': df_test1['avg_response_time'].mean(),
        'max_rt': df_test1['avg_response_time'].max(),
        'avg_error': df_test1['error_percentage'].mean(),
        'max_error': df_test1['error_percentage'].max()
    }
    
    test2_summary = {
        'exit_code': df_test2['exit_code'].iloc[0],
        'result': 'PASS' if df_test2['exit_code'].iloc[0] == 1 else 'FAIL',
        'transactions': len(df_test2),
        'avg_p95': df_test2['perc_95'].mean(),
        'max_p95': df_test2['perc_95'].max(),
        'avg_rt': df_test2['avg_response_time'].mean(),
        'max_rt': df_test2['avg_response_time'].max(),
        'avg_error': df_test2['error_percentage'].mean(),
        'max_error': df_test2['error_percentage'].max()
    }
    
    # Get focused transaction sets (not ALL - optimize for token limit)
    # 1. Top 10 slowest from each test
    test1_top10 = df_test1.nlargest(10, 'perc_95')[['transaction_name', 'perc_95', 'avg_response_time', 'error_percentage']]
    test2_top10 = df_test2.nlargest(10, 'perc_95')[['transaction_name', 'perc_95', 'avg_response_time', 'error_percentage']]
    
    # 2. Merge common transactions to show side-by-side comparison
    merged = df_test1[['transaction_name', 'perc_95', 'avg_response_time', 'error_percentage']].merge(
        df_test2[['transaction_name', 'perc_95', 'avg_response_time', 'error_percentage']],
        on='transaction_name',
        suffixes=('_test1', '_test2'),
        how='inner'
    )
    
    # Calculate changes for common transactions
    if len(merged) > 0:
        merged['p95_delta'] = merged['perc_95_test2'] - merged['perc_95_test1']
        merged['p95_pct_change'] = (merged['p95_delta'] / merged['perc_95_test1'] * 100).fillna(0)
        merged['rt_delta'] = merged['avg_response_time_test2'] - merged['avg_response_time_test1']
        merged['error_delta'] = merged['error_percentage_test2'] - merged['error_percentage_test1']
        
        # Get biggest regressions and improvements
        biggest_regressions = merged.nlargest(5, 'p95_pct_change')[['transaction_name', 'perc_95_test1', 'perc_95_test2', 'p95_pct_change']]
        biggest_improvements = merged.nsmallest(5, 'p95_pct_change')[['transaction_name', 'perc_95_test1', 'perc_95_test2', 'p95_pct_change']]
        
        # Overall statistics for common transactions
        common_stats = {
            'count': len(merged),
            'avg_p95_change': merged['p95_pct_change'].mean(),
            'regressions': (merged['p95_pct_change'] > 10).sum(),
            'improvements': (merged['p95_pct_change'] < -10).sum(),
            'stable': ((merged['p95_pct_change'] >= -10) & (merged['p95_pct_change'] <= 10)).sum()
        }
    else:
        biggest_regressions = None
        biggest_improvements = None
        common_stats = {'count': 0}
    
    # Calculate deltas
    p95_delta = test2_summary['avg_p95'] - test1_summary['avg_p95']
    p95_pct_change = (p95_delta / test1_summary['avg_p95'] * 100) if test1_summary['avg_p95'] > 0 else 0
    
    rt_delta = test2_summary['avg_rt'] - test1_summary['avg_rt']
    rt_pct_change = (rt_delta / test1_summary['avg_rt'] * 100) if test1_summary['avg_rt'] > 0 else 0
    
    error_delta = test2_summary['avg_error'] - test1_summary['avg_error']
    
    # Build compact, focused prompt
    prompt = f"""# Test Comparison: {test1_id} vs {test2_id}

## Summary Statistics

### Test 1 ({test1_id}):
- **Result**: {test1_summary['result']} (exit_code={test1_summary['exit_code']})
- **Transactions**: {test1_summary['transactions']}
- **Avg P95**: {test1_summary['avg_p95']:.2f} ms (Max: {test1_summary['max_p95']:.2f} ms)
- **Avg Response Time**: {test1_summary['avg_rt']:.2f} ms (Max: {test1_summary['max_rt']:.2f} ms)
- **Avg Error Rate**: {test1_summary['avg_error']:.2f}% (Max: {test1_summary['max_error']:.2f}%)

### Test 2 ({test2_id}):
- **Result**: {test2_summary['result']} (exit_code={test2_summary['exit_code']})
- **Transactions**: {test2_summary['transactions']}
- **Avg P95**: {test2_summary['avg_p95']:.2f} ms (Max: {test2_summary['max_p95']:.2f} ms)
- **Avg Response Time**: {test2_summary['avg_rt']:.2f} ms (Max: {test2_summary['max_rt']:.2f} ms)
- **Avg Error Rate**: {test2_summary['avg_error']:.2f}% (Max: {test2_summary['max_error']:.2f}%)

### Key Differences:
- **P95 Change**: {p95_delta:+.2f} ms ({p95_pct_change:+.1f}%)
- **Avg RT Change**: {rt_delta:+.2f} ms ({rt_pct_change:+.1f}%)
- **Error Rate Change**: {error_delta:+.2f}%
- **Result Change**: {'❌ Changed' if test1_summary['result'] != test2_summary['result'] else '✅ Same'}

## Top 10 Slowest Transactions by P95

### Test 1 Top 10:
{test1_top10.to_string(index=False)}

### Test 2 Top 10:
{test2_top10.to_string(index=False)}
"""

    # Add common transaction analysis if available
    if common_stats['count'] > 0:
        prompt += f"""
## Common Transactions Analysis ({common_stats['count']} shared)

### Performance Distribution:
- **Regressions** (>10% slower): {common_stats['regressions']} transactions
- **Improvements** (>10% faster): {common_stats['improvements']} transactions
- **Stable** (±10%): {common_stats['stable']} transactions
- **Average P95 Change**: {common_stats['avg_p95_change']:+.1f}%

### Top 5 Biggest Regressions:
{biggest_regressions.to_string(index=False)}

### Top 5 Biggest Improvements:
{biggest_improvements.to_string(index=False)}
"""
    else:
        prompt += f"""
## Common Transactions Analysis
No common transactions found between tests (different test scenarios or transaction names changed).
"""

    prompt += """
## Analysis Instructions

Provide a detailed comparison focusing on:

1. **Overall Performance Winner**: Which test performed better and why? Consider P95, Avg RT, and Error Rate.

2. **Transaction-Level Patterns**: 
   - Are the regressions/improvements isolated to specific transactions or system-wide?
   - Do the top 10 slowest transactions overlap between tests?
   - Are there transaction categories (API, Auth, Service) showing consistent patterns?

3. **Root Cause Hypotheses**: What might explain the performance differences?

4. **Actionable Recommendations**: What should be investigated or fixed?

**Note**: Analysis based on top performers and common transaction changes. Full transaction set has {test1_summary['transactions']} (Test 1) and {test2_summary['transactions']} (Test 2) transactions."""

    return prompt
