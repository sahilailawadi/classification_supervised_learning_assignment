"""
LLM-Augmented Test Analysis - Interactive Streamlit Demo

Run with: streamlit run app_llm_demo.py
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import sys
import os
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import components
from dotenv import load_dotenv
load_dotenv(project_root / '.env')

from src.analyzer import TestAnalyzer
from src.data_source import get_data_source
from src.llm_provider import get_llm_provider

# Page config
st.set_page_config(
    page_title="LLM Test Analysis",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {font-size: 2.5rem; font-weight: bold; margin-bottom: 0;}
    .sub-header {font-size: 1.2rem; color: #666; margin-top: 0;}
    .metric-card {background: #f0f2f6; padding: 1rem; border-radius: 0.5rem; margin: 0.5rem 0;}
    .success-text {color: #28a745;}
    .fail-text {color: #dc3545;}
    .stChatMessage {background: #f8f9fa; border-radius: 0.5rem; padding: 1rem;}
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'analyzer' not in st.session_state:
    st.session_state.analyzer = None
if 'df' not in st.session_state:
    st.session_state.df = None
if 'conversation_history' not in st.session_state:
    st.session_state.conversation_history = []
if 'current_test' not in st.session_state:
    st.session_state.current_test = None
if 'pending_question' not in st.session_state:
    st.session_state.pending_question = None
if 'test_chat_history' not in st.session_state:
    st.session_state.test_chat_history = {}  # {test_id: [(question, answer), ...]}

def initialize_system():
    """Initialize TestAnalyzer and load data"""
    if st.session_state.analyzer is None:
        with st.spinner("🔧 Initializing LLM Test Analyzer..."):
            try:
                st.session_state.analyzer = TestAnalyzer()
                st.session_state.df = st.session_state.analyzer.data_source.load_test_data()
                return True
            except Exception as e:
                st.error(f"❌ Initialization failed: {e}")
                return False
    return True

def ask_llm_question(question: str, context: str = ""):
    """
    Send question to LLM with MCP Phase 2 tool integration.
    
    NOW USES: analyzer.ask() which automatically calls MCP tools as needed!
    - "What are the last 5 tests?" → auto-calls query_tests
    - "Show failed tests" → auto-calls query_tests(exit_code=2)
    - General questions → provides dataset overview
    """
    analyzer = st.session_state.analyzer
    conversation_history = st.session_state.conversation_history
    
    # Create status container for detailed progress
    status_container = st.empty()
    
    try:
        # Show initial status
        with status_container:
            with st.status("🤖 Processing your question...", expanded=True) as status:
                st.write("🔍 Analyzing question to determine data needs...")
                
                # Use unified ask() method with MCP tool integration
                # If context provided, pass it; otherwise let ask() handle it
                result = analyzer.ask(
                    question,
                    data_context=context if context else None,
                    conversation_history=conversation_history
                )
                
                # Show what tools were used
                tools_used = result.get('tools_used', [])
                if tools_used:
                    st.write(f"✅ Used MCP tools: {', '.join(tools_used)}")
                    st.write("💡 Reused existing database connection (no new connection overhead)")
                else:
                    st.write("✅ Used dataset overview (no tool calls needed)")
                
                status.update(label="✅ Analysis complete!", state="complete")
        
        # Clear status after completion
        status_container.empty()
        
        # Extract tools used for display
        tools_info = f"\n\n*🔧 Tools: {', '.join(tools_used)}*" if tools_used else ""
        
        return result['answer'] + tools_info, result['tokens_used']
    except Exception as e:
        status_container.empty()
        return f"❌ Error: {e}", 0

def ask_about_test(testplan_or_index, question: str):
    """
    Ask a question about a specific test with real data (prevents hallucination).
    
    Args:
        testplan_or_index: Test index (0-N) or testplan ID string
        question: Your question about the test
        
    Returns:
        Tuple of (answer, tokens_used)
    """
    analyzer = st.session_state.analyzer
    conversation_history = st.session_state.conversation_history
    
    try:
        # Use unified ask() method
        result = analyzer.ask(
            question,
            about_test=testplan_or_index,
            conversation_history=conversation_history
        )
        return result['answer'], result['tokens_used']
    except Exception as e:
        return f"❌ Error: {e}", 0

def ask_with_data(data_context: str, question: str):
    """
    Ask LLM to interpret any data (pandas results, aggregations, etc.).
    
    Args:
        data_context: Formatted data (DataFrame.to_string(), custom text, etc.)
        question: Your question about the data
        
    Returns:
        Tuple of (answer, tokens_used)
    """
    analyzer = st.session_state.analyzer
    conversation_history = st.session_state.conversation_history
    
    try:
        # Use unified ask() method
        result = analyzer.ask(
            question,
            data_context=data_context,
            conversation_history=conversation_history
        )
        return result['answer'], result['tokens_used']
    except Exception as e:
        return f"❌ Error: {e}", 0

# Initialize system ONCE before sidebar (prevents reload on navigation)
if not initialize_system():
    st.error("System initialization failed")
    st.stop()

# Sidebar
with st.sidebar:
    st.markdown("### ⚙️ Configuration")
    
    mode = os.getenv('LLM_MODE', 'academic')
    st.info(f"**Mode:** {mode.upper()}")
    
    if st.button("🔄 Reload System"):
        st.session_state.analyzer = None
        st.session_state.df = None
        st.session_state.conversation_history = []
        st.rerun()
    
    st.markdown("---")
    st.markdown("### 📊 Quick Stats")
    
    # Use cached data (already initialized above)
    df = st.session_state.df
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Tests", df['testplan'].nunique())
        st.metric("Transactions", df['transaction_name'].nunique())
    with col2:
        pass_count = df[df['exit_code'] == 1]['testplan'].nunique()
        fail_count = df[df['exit_code'] != 1]['testplan'].nunique()
        st.metric("PASS", pass_count)
        st.metric("FAIL", fail_count)
    
    st.markdown("---")
    st.markdown("### 🎯 Navigation")
    page = st.radio(
        "Choose a view:",
        ["💬 Chat Analysis", "📈 Test Overview", "🔍 Deep Dive", "⚖️ Compare Tests"],
        label_visibility="collapsed"
    )

# Main content (already checked initialization above)

st.markdown('<p class="main-header">🤖 LLM-Augmented Test Analysis</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Ask questions in natural language • MCP Enabled: Auto data fetching with tool routing</p>', unsafe_allow_html=True)

# ============================================================================
# PAGE: Chat Analysis
# ============================================================================
if page == "💬 Chat Analysis":
    st.markdown("### 💬 Ask Questions About Your Tests")
    st.markdown("**MCP Enabled:** Ask naturally and tools fetch data automatically!")
    st.markdown("Try: *'What are the last 5 test runs?'*, *'Show me failed tests'*, *'Compare LoadTest_001 and LoadTest_002'*")
    
    # Chat history
    chat_container = st.container()
    
    with chat_container:
        for i, (question, answer) in enumerate(st.session_state.conversation_history):
            with st.chat_message("user"):
                st.write(question)
            with st.chat_message("assistant"):
                st.markdown(answer)
    
    # Handle pending question from quick buttons
    if st.session_state.pending_question:
        question = st.session_state.pending_question
        st.session_state.pending_question = None
        
        # Add user message
        with st.chat_message("user"):
            st.write(question)
        
        # Get LLM response with detailed status
        with st.chat_message("assistant"):
            answer, tokens = ask_llm_question(question)
            st.markdown(answer)
            st.caption(f"💭 *Tokens used: {tokens}*")
        
        # Save to history
        st.session_state.conversation_history.append((question, answer))
    
    # Question input
    question = st.chat_input("Ask a question about your test data...")
    
    if question:
        # Add user message
        with st.chat_message("user"):
            st.write(question)
        
        # Get LLM response with detailed status
        with st.chat_message("assistant"):
            answer, tokens = ask_llm_question(question)
            st.markdown(answer)
            st.caption(f"💭 *Tokens used: {tokens}*")
        
        # Save to history
        st.session_state.conversation_history.append((question, answer))
    
    # Quick questions
    st.markdown("---")
    st.markdown("**💡 Quick Questions (with MCP auto-tool routing):**")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("📋 Last 5 tests?"):
            st.session_state.pending_question = "What are the last 5 test runs?"
            st.rerun()
    
    with col2:
        if st.button("❌ Failed tests?"):
            st.session_state.pending_question = "Show me all failed tests"
            st.rerun()
    
    with col3:
        if st.button("📊 Pass rate?"):
            st.session_state.pending_question = "What is the overall pass rate?"
            st.rerun()
    
    with col4:
        if st.button("🔍 Summarize last test"):
            # Pre-fetch actual data to prevent hallucination
            analyzer = st.session_state.analyzer
            tests = analyzer.data_source.list_tests(limit=1)
            if tests:
                latest_test = tests[0]
                
                # Get prediction
                pred_result = analyzer.predict_test(latest_test)
                conf_pct = pred_result['confidence'] if pred_result['confidence'] >= 2 else pred_result['confidence'] * 100
                
                # Get test details
                test_df = analyzer.data_source.get_test_by_id(latest_test)
                test_summary = test_df.groupby('testplan').agg({
                    'perc_95': 'mean',
                    'error_percentage': 'mean',
                    'transaction_name': 'count',
                    'end_time': 'first',
                    'exit_code': 'first'
                }).iloc[0]
                
                # Get baseline comparison
                from mcp_server.tools.baseline import get_baseline_comparison
                baseline_result = get_baseline_comparison(latest_test, analyzer=analyzer)
                
                if 'error' not in baseline_result:
                    baseline_summary = baseline_result['summary']
                else:
                    baseline_summary = {}
                
                summary_question = f"""Analyze the most recent test run: {latest_test}

ACTUAL TEST DATA:
- Test ID: {latest_test}
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
                
                st.session_state.pending_question = summary_question
            else:
                st.session_state.pending_question = "No tests found in database."
            st.rerun()
    
    # Report generation
    st.markdown("---")
    st.markdown("**📄 Generate Reports (Last Test):**")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📝 PO Sign-Off Report"):
            # Pre-fetch actual data to prevent hallucination
            analyzer = st.session_state.analyzer
            tests = analyzer.data_source.list_tests(limit=1)
            if tests:
                latest_test = tests[0]
                
                # Get baseline comparison with ACTUAL data
                from mcp_server.tools.baseline import get_baseline_comparison
                baseline_result = get_baseline_comparison(latest_test, analyzer=analyzer)
                
                # Get prediction
                pred_result = analyzer.predict_test(latest_test)
                conf_pct = pred_result['confidence'] if pred_result['confidence'] >= 2 else pred_result['confidence'] * 100
                
                # Get test details
                test_df = analyzer.data_source.get_test_by_id(latest_test)
                test_summary = test_df.groupby('testplan').agg({
                    'perc_95': 'mean',
                    'error_percentage': 'mean',
                    'transaction_name': 'count',
                    'end_time': 'first',
                    'exit_code': 'first'
                }).iloc[0]
                
                if 'error' not in baseline_result:
                    baseline_summary = baseline_result['summary']
                    
                    # Format critical issues
                    critical_txns = [t for t in baseline_result['transactions'] 
                                   if t['has_baseline'] and t['deviation']['p95_pct'] > 50]
                    critical_list = "\\n".join([f"- {t['name']}: {t['actual']['p95']:.0f}ms vs {t['baseline']['p95']:.0f}ms baseline ({t['deviation']['p95_pct']:+.1f}%)" 
                                              for t in sorted(critical_txns, key=lambda x: x['deviation']['p95_pct'], reverse=True)[:5]])
                else:
                    baseline_summary = {}
                    critical_list = "No baseline data available"
                
                report_question = f"""Generate a release sign-off report for test {latest_test} for Product Owner review.

ACTUAL TEST DATA (DO NOT MODIFY):

Test Overview:
- Test ID: {latest_test}
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
                
                st.session_state.pending_question = report_question
            else:
                st.session_state.pending_question = "No tests found in database."
            st.rerun()
    
    with col2:
        if st.button("🔬 Dev/QA Report"):
            # Pre-fetch actual data to prevent hallucination
            analyzer = st.session_state.analyzer
            tests = analyzer.data_source.list_tests(limit=1)
            if tests:
                latest_test = tests[0]
                
                # Get baseline comparison with ACTUAL data
                from mcp_server.tools.baseline import get_baseline_comparison
                baseline_result = get_baseline_comparison(latest_test, analyzer=analyzer)
                
                # Get prediction
                pred_result = analyzer.predict_test(latest_test)
                conf_pct = pred_result['confidence'] if pred_result['confidence'] >= 2 else pred_result['confidence'] * 100
                
                # Format transaction data into table
                if 'error' not in baseline_result:
                    txn_table = "\\n| Transaction | Actual P95 | Baseline P95 | Δ% | Actual Avg RT | Baseline Avg RT | Δ% | Error% | Status |\\n"
                    txn_table += "|------------|-----------|-------------|-----|--------------|----------------|-----|---------|--------|\\n"
                    
                    for txn in baseline_result['transactions']:
                        if txn['has_baseline']:
                            status = "⚠️ CRITICAL" if txn['deviation']['p95_pct'] > 50 else "⚠️ DEGRADED" if txn['deviation']['p95_pct'] > 20 else "✅ PASS"
                            txn_table += f"| {txn['name']} | {txn['actual']['p95']:.0f}ms | {txn['baseline']['p95']:.0f}ms | {txn['deviation']['p95_pct']:+.1f}% | {txn['actual']['avg_rt']:.0f}ms | {txn['baseline']['avg_rt']:.0f}ms | {txn['deviation']['avg_rt_pct']:+.1f}% | {txn['actual']['error_pct']:.1f}% | {status} |\\n"
                    
                    baseline_summary = baseline_result['summary']
                else:
                    txn_table = "No baseline data available"
                    baseline_summary = {}
                
                report_question = f"""Generate a detailed engineering report for test {latest_test} for Dev/QA teams.

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
                
                st.session_state.pending_question = report_question
            else:
                st.session_state.pending_question = "No tests found in database."
            st.rerun()
    
    with col3:
        if st.button("📊 Stakeholder Summary"):
            # Pre-fetch actual data to prevent hallucination
            analyzer = st.session_state.analyzer
            tests = analyzer.data_source.list_tests(limit=1)
            if tests:
                latest_test = tests[0]
                
                # Get baseline comparison with ACTUAL data
                from mcp_server.tools.baseline import get_baseline_comparison
                baseline_result = get_baseline_comparison(latest_test, analyzer=analyzer)
                
                # Get prediction
                pred_result = analyzer.predict_test(latest_test)
                conf_pct = pred_result['confidence'] if pred_result['confidence'] >= 2 else pred_result['confidence'] * 100
                
                # Get test details
                test_df = analyzer.data_source.get_test_by_id(latest_test)
                
                if 'error' not in baseline_result:
                    summary = baseline_result['summary']
                    
                    # Format quality metrics table (top 5 by deviation)
                    txns_sorted = sorted([t for t in baseline_result['transactions'] if t['has_baseline']], 
                                       key=lambda x: x['deviation']['p95_pct'], reverse=True)[:5]
                    qa_table = "\\n| Transaction | P95 | Baseline P95 | Δ% | Status |\\n"
                    qa_table += "|------------|-----|-------------|-----|--------|\\n"
                    for txn in txns_sorted:
                        status = "❌ CRITICAL" if txn['deviation']['p95_pct'] > 50 else "⚠️ WARN" if txn['deviation']['p95_pct'] > 20 else "✅ PASS"
                        qa_table += f"| {txn['name']} | {txn['actual']['p95']:.0f}ms | {txn['baseline']['p95']:.0f}ms | {txn['deviation']['p95_pct']:+.1f}% | {status} |\\n"
                else:
                    summary = {}
                    qa_table = "No baseline data available"
                
                report_question = f"""Generate a stakeholder summary for test {latest_test}.

ACTUAL TEST DATA (DO NOT MODIFY - USE EXACT TRANSACTION NAMES):

Test Summary:
- Test ID: {latest_test}
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
                
                st.session_state.pending_question = report_question
            else:
                st.session_state.pending_question = "No tests found in database."
            st.rerun()

# ============================================================================
# PAGE: Test Overview
# ============================================================================
elif page == "📈 Test Overview":
    df = st.session_state.df
    
    st.markdown("### 📈 Test Dataset Overview")
    
    # Metrics row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Tests", df['testplan'].nunique())
    with col2:
        pass_pct = (df[df['exit_code'] == 1]['testplan'].nunique() / df['testplan'].nunique()) * 100
        st.metric("Pass Rate", f"{pass_pct:.1f}%")
    with col3:
        avg_p95 = df['perc_95'].mean()
        st.metric("Avg P95", f"{avg_p95:.0f}ms")
    with col4:
        avg_error = df['error_percentage'].mean()
        st.metric("Avg Error%", f"{avg_error:.2f}%")
    
    st.markdown("---")
    
    # Charts
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Pass/Fail Distribution")
        result_counts = df.groupby('exit_code')['testplan'].nunique()
        result_labels = {1: 'PASS', 2: 'FAIL', 3: 'FAIL', 4: 'FAIL'}
        result_df = pd.DataFrame({
            'Result': [result_labels.get(code, 'UNKNOWN') for code in result_counts.index],
            'Count': result_counts.values
        })
        fig = px.pie(result_df, values='Count', names='Result', 
                     color='Result', color_discrete_map={'PASS': '#28a745', 'FAIL': '#dc3545'})
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("#### Top 10 Slowest Transactions")
        top_slow = df.groupby('transaction_name')['perc_95'].mean().sort_values(ascending=False).head(10)
        fig = px.bar(x=top_slow.values, y=top_slow.index, orientation='h',
                     labels={'x': 'P95 Response Time (ms)', 'y': 'Transaction'})
        st.plotly_chart(fig, use_container_width=True)
    
    # Performance over time
    st.markdown("#### Performance Trends")
    df['date'] = pd.to_datetime(df['end_time'], utc=True).dt.date
    daily_stats = df.groupby('date').agg({
        'perc_95': 'mean',
        'error_percentage': 'mean',
        'testplan': 'nunique'
    }).reset_index()
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=daily_stats['date'], y=daily_stats['perc_95'],
                             mode='lines+markers', name='Avg P95'))
    fig.update_layout(xaxis_title='Date', yaxis_title='P95 (ms)', hovermode='x')
    st.plotly_chart(fig, use_container_width=True)
    
    # Transaction table
    st.markdown("#### Transaction Summary")
    trans_summary = df.groupby('transaction_name').agg({
        'perc_95': 'mean',
        'error_percentage': 'mean',
        'avg_response_time': 'mean',
        'testplan': 'count'
    }).round(2)
    trans_summary.columns = ['Avg P95', 'Avg Error%', 'Avg Response', 'Count']
    trans_summary = trans_summary.sort_values('Avg P95', ascending=False)
    st.dataframe(trans_summary, use_container_width=True)
    
    # Ask about the data
    st.markdown("---")
    st.markdown("**💡 Ask about this data:**")
    if st.button("🔍 Analyze these trends"):
        summary = f"""
Transaction Summary (Top 10):
{trans_summary.head(10).to_string()}

Daily Performance:
{daily_stats.tail(7).to_string()}
"""
        with st.spinner("🤖 Analyzing..."):
            answer, tokens = ask_llm_question(
                "What insights can you provide from this data? What should I investigate?",
                context=summary
            )
            st.markdown(answer)
            st.caption(f"💭 *Tokens used: {tokens}*")

# ============================================================================
# PAGE: Deep Dive
# ============================================================================
elif page == "🔍 Deep Dive":
    analyzer = st.session_state.analyzer
    df = st.session_state.df
    
    st.markdown("### 🔍 Deep Dive: Single Test Analysis")
    
    # Test selector
    tests = analyzer.data_source.list_tests(limit=50)
    
    col1, col2 = st.columns([5, 1])
    with col1:
        selected_test = st.selectbox(
            "Select a test:",
            tests,
            index=0 if st.session_state.current_test is None else tests.index(st.session_state.current_test) if st.session_state.current_test in tests else 0
        )
    
    with col2:
        st.write("")  # Add spacing to align button with selectbox
        st.write("")  # 
        analyze_button = st.button("🔍 Analyze", type="primary", use_container_width=True)
    
    # Only analyze on button click (removed automatic analysis on selection change)
    if analyze_button:
        st.session_state.current_test = selected_test
        
        with st.spinner("🤖 Analyzing test..."):
            # Get prediction
            pred_result = analyzer.predict_test(selected_test)
            
            # Get LLM analysis
            analysis = analyzer.analyze_test(selected_test, include_transactions=True)
            
            # Store in session state for persistence across reruns
            st.session_state.current_analysis = {
                'test_id': selected_test,
                'prediction': pred_result,
                'analysis': analysis
            }
    
    # Display analysis if it exists in session state and matches selected test
    if 'current_analysis' in st.session_state and st.session_state.current_analysis:
        analysis_data = st.session_state.current_analysis
        
        # Only display if analysis matches currently selected test
        if analysis_data['test_id'] == selected_test:
            pred_result = analysis_data['prediction']
            analysis = analysis_data['analysis']
            
            # Display results
            st.markdown("---")
            
            # Prediction metrics (ENHANCED - more prominent)
            st.markdown("### 🎯 Classifier Prediction")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                pred_class = pred_result['prediction']
                st.metric(
                    "Prediction", 
                    pred_class
                )
                if pred_class == "PASS":
                    st.success("✅ Ready")
                else:
                    st.warning("⚠️ Review Needed")
            with col2:
                confidence = pred_result['confidence']
                # Handle confidence as decimal (0-1) or percentage (0-100)
                if confidence < 2:  # If it's a decimal, convert to percentage
                    confidence = confidence * 100
                
                conf_level = "High" if confidence > 80 else "Moderate" if confidence > 60 else "Low"
                st.metric(
                    "Confidence", 
                    f"{confidence:.1f}%"
                )
                if confidence > 80:
                    st.success(f"✅ {conf_level}")
                elif confidence > 60:
                    st.info(f"ℹ️ {conf_level}")
                else:
                    st.warning(f"⚠️ {conf_level}")
            with col3:
                actual = pred_result.get('actual_result', 'N/A')
                st.metric("Actual Result", actual)
            with col4:
                if actual != 'N/A':
                    match = "✅ Correct" if pred_result['prediction'] == actual else "❌ Mismatch"
                else:
                    match = "⏳ Pending"
                st.metric("Validation", match)
            
            # Show prediction interpretation
            if pred_result['prediction'] == "PASS":
                st.success("✅ **Classifier Assessment:** Test meets quality thresholds for release")
            else:
                st.error("⚠️ **Classifier Assessment:** Test shows quality concerns - review recommended")
            
            st.markdown("---")
            
            # LLM Analysis
            st.markdown("### 🤖 LLM Analysis")
            st.markdown(analysis)
            
            # Show features
            with st.expander("📊 Feature Values"):
                features_df = pd.DataFrame([pred_result['features']])
                st.dataframe(features_df.T, use_container_width=True)
            
            # Show transaction data
            test_data = df[df['testplan'] == selected_test].sort_values('perc_95', ascending=False)
            with st.expander(f"📋 Transaction Data ({len(test_data)} rows)"):
                # Select columns that exist in the dataframe
                available_cols = ['transaction_name', 'perc_95', 'error_percentage', 'avg_response_time']
                optional_cols = ['min_response', 'max_response', 'total_count', 'pass_count', 'fail_count']
                
                # Add optional columns if they exist
                display_cols = available_cols.copy()
                for col in optional_cols:
                    if col in test_data.columns:
                        display_cols.append(col)
                
                st.dataframe(test_data[display_cols], use_container_width=True)
            
            # HYBRID APPROACH: Quick Actions + Chat
            st.markdown("---")
            st.markdown("### 💬 Ask About This Test")
            st.markdown(f"Ask questions about **{selected_test}** or generate reports:")
            
            # Quick action buttons
            st.markdown("**Quick Actions:**")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                if st.button("📝 PO Report", key="quick_po", use_container_width=True):
                    conf_pct = confidence if confidence >= 2 else confidence * 100
                    question = f"Generate a release sign-off report for test {selected_test} for Product Owner. Include: executive summary, test overview with classifier prediction ({pred_result['prediction']}, {conf_pct:.1f}% confidence), performance vs baseline, critical issues, and bold **Release Recommendation** (GO/NO-GO/WITH CAUTION)."
                    
                    # Process immediately without page refresh
                    with st.spinner("🤖 Analyzing..."):
                        answer, tokens = ask_about_test(selected_test, question)
                        
                        if selected_test not in st.session_state.test_chat_history:
                            st.session_state.test_chat_history[selected_test] = []
                        st.session_state.test_chat_history[selected_test].append((question, answer))
                    st.rerun()
            
            with col2:
                if st.button("🔬 Eng Report", key="quick_eng", use_container_width=True):
                    conf_pct = confidence if confidence >= 2 else confidence * 100
                    question = f"Generate a detailed engineering report for test {selected_test}. Include: classifier analysis ({pred_result['prediction']}, {conf_pct:.1f}% confidence), complete transaction-level breakdown with baseline comparisons showing ALL transactions with actual data, critical issues (>50% degradation), and actionable debugging steps."
                    
                    with st.spinner("🤖 Analyzing..."):
                        answer, tokens = ask_about_test(selected_test, question)
                        
                        if selected_test not in st.session_state.test_chat_history:
                            st.session_state.test_chat_history[selected_test] = []
                        st.session_state.test_chat_history[selected_test].append((question, answer))
                    st.rerun()
            
            with col3:
                if st.button("📊 QA Report", key="quick_qa", use_container_width=True):
                    conf_pct = confidence if confidence >= 2 else confidence * 100
                    question = f"Generate a QA report for test {selected_test}. Include: test summary with classifier prediction ({pred_result['prediction']}, {conf_pct:.1f}% confidence), quality metrics vs baseline with transaction table, pass/fail analysis, and bold **Sign-Off Status** (ready/needs retest/blocked)."
                    
                    with st.spinner("🤖 Analyzing..."):
                        answer, tokens = ask_about_test(selected_test, question)
                        
                        if selected_test not in st.session_state.test_chat_history:
                            st.session_state.test_chat_history[selected_test] = []
                        st.session_state.test_chat_history[selected_test].append((question, answer))
                    st.rerun()
            
            with col4:
                if st.button("❓ Explain Prediction", key="quick_explain", use_container_width=True):
                    conf_pct = confidence if confidence >= 2 else confidence * 100
                    question = f"Explain why the classifier predicted {pred_result['prediction']} for test {selected_test} with {conf_pct:.1f}% confidence. What were the key factors? Which transactions influenced this decision?"
                    
                    with st.spinner("🤖 Analyzing..."):
                        answer, tokens = ask_about_test(selected_test, question)
                        
                        if selected_test not in st.session_state.test_chat_history:
                            st.session_state.test_chat_history[selected_test] = []
                        st.session_state.test_chat_history[selected_test].append((question, answer))
                    st.rerun()
            
            # Chat input using form to handle submission properly
            st.markdown("**Or ask a custom question:**")
            with st.form(key=f"chat_form_{selected_test}", clear_on_submit=True):
                test_question = st.text_input(
                    "Type your question...",
                    placeholder="e.g., 'What are the top 3 performance risks?', 'Is /negotiate endpoint acceptable?'",
                    key="test_question_input",
                    label_visibility="collapsed"
                )
                
                submitted = st.form_submit_button("💬 Ask", type="primary", use_container_width=True)
            
            # Clear chat button (outside form)
            if st.button("🗑️ Clear Chat", key="clear_chat_btn"):
                if selected_test in st.session_state.test_chat_history:
                    st.session_state.test_chat_history[selected_test] = []
                st.rerun()
            
            # Process question from form submission
            if submitted and test_question:
                with st.spinner("🤖 Analyzing..."):
                    # Use ask_about_test for test-specific context
                    answer, tokens = ask_about_test(selected_test, test_question)
                    
                    # Store in test-specific chat history
                    if selected_test not in st.session_state.test_chat_history:
                        st.session_state.test_chat_history[selected_test] = []
                    st.session_state.test_chat_history[selected_test].append((test_question, answer))
                    
                # Note: Form clears input automatically via clear_on_submit=True
            
            # Display chat history for this test
            if selected_test in st.session_state.test_chat_history and st.session_state.test_chat_history[selected_test]:
                st.markdown("---")
                st.markdown("### 📝 Conversation")
                
                for i, (q, a) in enumerate(st.session_state.test_chat_history[selected_test]):
                    # Question
                    st.markdown(f"**👤 You:** {q}")
                    
                    # Answer
                    with st.container():
                        st.markdown(f"**🤖 Answer:**")
                        st.markdown(a)
                        
                        # Download button for this answer
                        st.download_button(
                            "📥 Download as Markdown",
                            f"# Question\n{q}\n\n# Answer\n{a}",
                            file_name=f"{selected_test}_Q{i+1}.md",
                            mime="text/markdown",
                            key=f"download_qa_{selected_test}_{i}"
                        )
                    
                    if i < len(st.session_state.test_chat_history[selected_test]) - 1:
                        st.markdown("---")

# ============================================================================
# PAGE: Compare Tests
# ============================================================================
elif page == "⚖️ Compare Tests":
    analyzer = st.session_state.analyzer
    
    st.markdown("### ⚖️ Compare Tests: Test 1 vs Test 2 vs Baseline")
    
    tests = analyzer.data_source.list_tests(limit=50)
    
    col1, col2, col3 = st.columns([3, 3, 1])
    
    with col1:
        test1 = st.selectbox("Test 1:", tests, index=0, key="test1")
    
    with col2:
        test2 = st.selectbox("Test 2:", tests, index=1 if len(tests) > 1 else 0, key="test2")
    
    with col3:
        include_baseline = st.checkbox("Include Baseline", value=True)
    
    if st.button("⚖️ Compare All", type="primary"):
        if test1 == test2:
            st.warning("⚠️ Please select two different tests")
        else:
            with st.spinner("🤖 Performing three-way comparison..."):
                st.markdown("---")
                
                # Section 1: Test 1 vs Test 2
                st.markdown("### 🔄 Test 1 vs Test 2")
                comparison = analyzer.compare_tests(test1, test2)
                st.markdown(comparison)
                
                if include_baseline:
                    # Section 2: Test 1 vs Baseline
                    st.markdown("---")
                    st.markdown(f"### 📈 Test 1 ({test1}) vs Baseline")
                    result1 = analyzer.ask(
                        f"Compare {test1} with baseline. Focus on key deviations and classifier features.",
                        conversation_history=st.session_state.conversation_history
                    )
                    st.markdown(result1['answer'])
                    
                    # Section 3: Test 2 vs Baseline
                    st.markdown("---")
                    st.markdown(f"### 📈 Test 2 ({test2}) vs Baseline")
                    result2 = analyzer.ask(
                        f"Compare {test2} with baseline. Focus on key deviations and classifier features.",
                        conversation_history=st.session_state.conversation_history
                    )
                    st.markdown(result2['answer'])
                
                # Section 4: Three-way Prediction Comparison
                st.markdown("---")
                st.markdown("### 📊 Predictions")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown(f"**Test 1: {test1}**")
                    pred1 = analyzer.predict_test(test1)
                    subcol1, subcol2, subcol3 = st.columns(3)
                    with subcol1:
                        st.metric("Prediction", pred1['prediction'])
                    with subcol2:
                        conf1 = pred1['confidence'] if pred1['confidence'] >= 2 else pred1['confidence'] * 100
                        st.metric("Confidence", f"{conf1:.1f}%")
                    with subcol3:
                        actual1 = pred1.get('actual_result', 'N/A')
                        match1 = "✅" if pred1['prediction'] == actual1 else "❌"
                        st.metric("Actual", f"{actual1} {match1}")
                
                with col2:
                    st.markdown(f"**Test 2: {test2}**")
                    pred2 = analyzer.predict_test(test2)
                    subcol1, subcol2, subcol3 = st.columns(3)
                    with subcol1:
                        st.metric("Prediction", pred2['prediction'])
                    with subcol2:
                        conf2 = pred2['confidence'] if pred2['confidence'] >= 2 else pred2['confidence'] * 100
                        st.metric("Confidence", f"{conf2:.1f}%")
                    with subcol3:
                        actual2 = pred2.get('actual_result', 'N/A')
                        match2 = "✅" if pred2['prediction'] == actual2 else "❌"
                        st.metric("Actual", f"{actual2} {match2}")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; padding: 1rem;'>
    <small>LLM-Augmented Test Analysis | Mode: {mode} | Powered by TestAnalyzer</small>
</div>
""".format(mode=os.getenv('LLM_MODE', 'academic').upper()), unsafe_allow_html=True)
