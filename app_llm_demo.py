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
    
    col1, col2, col3 = st.columns(3)
    
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
    
    col1, col2 = st.columns([3, 1])
    with col1:
        selected_test = st.selectbox(
            "Select a test:",
            tests,
            index=0 if st.session_state.current_test is None else tests.index(st.session_state.current_test) if st.session_state.current_test in tests else 0
        )
    
    with col2:
        analyze_button = st.button("🔍 Analyze", type="primary")
    
    # Only analyze on button click (removed automatic analysis on selection change)
    if analyze_button:
        st.session_state.current_test = selected_test
        
        with st.spinner("🤖 Analyzing test..."):
            # Get prediction
            pred_result = analyzer.predict_test(selected_test)
            
            # Get LLM analysis
            analysis = analyzer.analyze_test(selected_test, include_transactions=True)
            
            # Display results
            st.markdown("---")
            
            # Prediction metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Prediction", pred_result['prediction'])
            with col2:
                st.metric("Confidence", f"{pred_result['confidence']:.1f}%")
            with col3:
                actual = pred_result.get('actual_result', 'N/A')
                st.metric("Actual Result", actual)
            with col4:
                match = "✅" if pred_result['prediction'] == actual else "❌"
                st.metric("Match", match)
            
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
                st.dataframe(test_data[['transaction_name', 'perc_95', 'error_percentage', 
                                        'avg_response_time', 'min_response', 'max_response']], 
                            use_container_width=True)

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
                        st.metric("Confidence", f"{pred1['confidence']:.1f}%")
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
                        st.metric("Confidence", f"{pred2['confidence']:.1f}%")
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
