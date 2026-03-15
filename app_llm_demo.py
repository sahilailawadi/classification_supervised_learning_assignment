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
    """Send question to LLM and get response with conversation history"""
    analyzer = st.session_state.analyzer
    df = st.session_state.df
    conversation_history = st.session_state.conversation_history
    
    # Build context
    system_prompt = """You are an expert performance test analyst. 
    
Answer questions about test results, trends, and patterns. Be concise but informative.
Use bullet points and highlight key insights. Format numbers clearly.
Maintain conversation context and reference previous questions when relevant."""

    context_parts = [
        f"Dataset: {df['testplan'].nunique()} tests, {len(df):,} transactions",
        f"Transactions types: {df['transaction_name'].nunique()}",
        f"Date range: {df['end_time'].min()} to {df['end_time'].max()}"
    ]
    
    if context:
        context_parts.append(f"\nAdditional context:\n{context}")
    
    # Build messages with conversation history
    messages = [{"role": "system", "content": system_prompt}]
    
    # Add conversation history (last 5 exchanges to keep context manageable)
    for prev_q, prev_a in conversation_history[-5:]:
        messages.append({"role": "user", "content": prev_q})
        messages.append({"role": "assistant", "content": prev_a})
    
    # Add current question with dataset context
    current_prompt = "\n".join(context_parts) + f"\n\nQuestion: {question}"
    messages.append({"role": "user", "content": current_prompt})
    
    # Query LLM
    try:
        response = analyzer.llm.chat(
            messages=messages,
            temperature=0.7
        )
        return response.content, response.tokens_used
    except Exception as e:
        return f"❌ Error: {e}", 0

def ask_about_test(testplan_or_index, question: str):
    """
    Ask a question about a specific test with real data (prevents hallucination).
    
    Args:
        testplan_or_index: Test index (0-N) or testplan ID string
        question: Your question about the test
        
    Returns:
        Tuple of (answer, tokens_used)
        
    Example:
        answer, tokens = ask_about_test(0, "What are the slowest transactions?")
        answer, tokens = ask_about_test("LoadTest_20260304T060726Z", "Why did this fail?")
    """
    analyzer = st.session_state.analyzer
    
    try:
        # Get detailed test context with real data
        test_context = analyzer.get_test_context(testplan_or_index)
        
        # Build full prompt with test details
        full_question = f"{test_context}\n\n---\n\n**Question:** {question}"
        
        # Use the regular ask function with conversation history
        return ask_llm_question(full_question, context="")
    
    except Exception as e:
        return f"❌ Error: {e}", 0

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
    
    if initialize_system():
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
    else:
        page = None
        st.error("System initialization failed")

# Main content
if not initialize_system():
    st.stop()

st.markdown('<p class="main-header">🤖 LLM-Augmented Test Analysis</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Ask questions about your performance tests in natural language</p>', unsafe_allow_html=True)

# ============================================================================
# PAGE: Chat Analysis
# ============================================================================
if page == "💬 Chat Analysis":
    st.markdown("### 💬 Ask Questions About Your Tests")
    st.markdown("Ask anything: *'What are the slowest transactions?'*, *'Why did LoadTest_X fail?'*, *'Show trends'*")
    
    # Chat history
    chat_container = st.container()
    
    with chat_container:
        for i, (question, answer) in enumerate(st.session_state.conversation_history):
            with st.chat_message("user"):
                st.write(question)
            with st.chat_message("assistant"):
                st.markdown(answer)
    
    # Question input
    question = st.chat_input("Ask a question about your test data...")
    
    if question:
        # Add user message
        with st.chat_message("user"):
            st.write(question)
        
        # Get LLM response
        with st.chat_message("assistant"):
            with st.spinner("🤔 Thinking..."):
                answer, tokens = ask_llm_question(question)
                st.markdown(answer)
                st.caption(f"💭 *Tokens used: {tokens}*")
        
        # Save to history
        st.session_state.conversation_history.append((question, answer))
    
    # Quick questions
    st.markdown("---")
    st.markdown("**💡 Quick Questions:**")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🐌 Slowest transactions?"):
            st.session_state.conversation_history.append((
                "What are the top 5 slowest transactions?",
                "⏳ Processing..."
            ))
            st.rerun()
    
    with col2:
        if st.button("❌ Common failures?"):
            st.session_state.conversation_history.append((
                "What patterns do you see in failed tests?",
                "⏳ Processing..."
            ))
            st.rerun()
    
    with col3:
        if st.button("📊 Performance trends?"):
            st.session_state.conversation_history.append((
                "Are there any performance trends over time?",
                "⏳ Processing..."
            ))
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
    df['date'] = pd.to_datetime(df['end_time']).dt.date
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
    
    if analyze_button or (selected_test and selected_test != st.session_state.current_test):
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
    
    st.markdown("### ⚖️ Compare Two Tests")
    
    tests = analyzer.data_source.list_tests(limit=50)
    
    col1, col2 = st.columns(2)
    
    with col1:
        test1 = st.selectbox("Test 1:", tests, index=0, key="test1")
    
    with col2:
        test2 = st.selectbox("Test 2:", tests, index=1 if len(tests) > 1 else 0, key="test2")
    
    if st.button("⚖️ Compare", type="primary"):
        if test1 == test2:
            st.warning("⚠️ Please select two different tests")
        else:
            with st.spinner("🤖 Comparing tests..."):
                comparison = analyzer.compare_tests(test1, test2)
                
                st.markdown("---")
                st.markdown("### 🤖 Comparison Analysis")
                st.markdown(comparison)
                
                # Side-by-side predictions
                st.markdown("---")
                st.markdown("### 📊 Predictions")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown(f"**{test1}**")
                    pred1 = analyzer.predict_test(test1)
                    st.metric("Prediction", pred1['prediction'])
                    st.metric("Confidence", f"{pred1['confidence']:.1f}%")
                
                with col2:
                    st.markdown(f"**{test2}**")
                    pred2 = analyzer.predict_test(test2)
                    st.metric("Prediction", pred2['prediction'])
                    st.metric("Confidence", f"{pred2['confidence']:.1f}%")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; padding: 1rem;'>
    <small>LLM-Augmented Test Analysis | Mode: {mode} | Powered by TestAnalyzer</small>
</div>
""".format(mode=os.getenv('LLM_MODE', 'academic').upper()), unsafe_allow_html=True)
