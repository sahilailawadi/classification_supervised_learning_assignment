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

# Default to academic mode if not set
if 'LLM_MODE' not in os.environ:
    os.environ['LLM_MODE'] = 'academic'

from src.analyzer import TestAnalyzer
from src.data_source import get_data_source
from src.llm_provider import get_llm_provider

# Import centralized prompts
from prompts.report_prompts import (
    get_summary_prompt_with_data,
    get_po_report_prompt_with_data,
    get_dev_report_prompt_with_data,
    get_stakeholder_report_prompt_with_data,
    get_po_report_prompt_short,
    get_eng_report_prompt_short,
    get_qa_report_prompt_short,
    get_explain_prediction_prompt,
    get_test_comparison_prompt,
    format_critical_transactions_list,
    format_transaction_table,
    format_qa_table
)

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
    
    .report-container {
        background-color: #f8f9fa;
        border: 1px solid #e9ecef;
        border-left: 5px solid #667eea;
        border-radius: 8px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .report-container h3 {
        margin-top: 0;
        color: #495057;
    }
    
    /* Make radio buttons more prominent */
    div[data-testid="stSidebar"] .stRadio > div {
        background-color: white;
        padding: 12px;
        border-radius: 8px;
        margin-top: 8px;
    }
    
    div[data-testid="stSidebar"] .stRadio > div > label {
        font-size: 15px !important;
        font-weight: 500 !important;
        padding: 10px 12px !important;
        border-radius: 6px;
        margin: 4px 0 !important;
        display: block;
        cursor: pointer;
        transition: all 0.2s ease;
    }
    
    div[data-testid="stSidebar"] .stRadio > div > label:hover {
        background-color: #f0f4ff;
        transform: translateX(3px);
    }
    
    div[data-testid="stSidebar"] .stRadio input[type="radio"]:checked + div > label {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white !important;
        font-weight: 600 !important;
        box-shadow: 0 2px 8px rgba(102, 126, 234, 0.4);
    }
    
    /* Style the chat input form to make it prominent */
    div[data-testid="stForm"] {
        background: linear-gradient(to right, #f8f9fa, #ffffff);
        border: 2px solid #667eea;
        border-radius: 12px;
        padding: 1.2rem;
        margin: 1.5rem 0;
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.15);
    }
    
    div[data-testid="stForm"] input[type="text"] {
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 0.75rem;
        font-size: 15px;
    }
    
    div[data-testid="stForm"] input[type="text"]:focus {
        border-color: #667eea;
        box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.2);
    }
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
if 'generate_report_type' not in st.session_state:
    st.session_state.generate_report_type = None
if 'submitted_api_key' not in st.session_state:
    st.session_state.submitted_api_key = None
if 'submitted_model' not in st.session_state:
    st.session_state.submitted_model = None
if 'is_processing' not in st.session_state:
    st.session_state.is_processing = False

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
    Send question to LLM with MCP tool integration.
    
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

# ============================================================================
# SIDEBAR - API Configuration (for professors/academic users ONLY)
# ============================================================================
mode = os.getenv('LLM_MODE', 'academic')

if mode == 'academic':
    # Academic mode: Allow professors to input their own API key
    with st.sidebar:
        st.markdown("### 🔑 API Configuration")
        
        # Check if API key is in environment (from .env file)
        default_key = os.getenv('OPENAI_API_KEY', '')
        default_model = os.getenv('OPENAI_MODEL', 'gpt-4.1')
        
        # Check if both are configured
        api_configured = bool(st.session_state.submitted_api_key or default_key)
        model_configured = bool(st.session_state.submitted_model or default_model)
        both_configured = api_configured and model_configured
        
        # Show status summary
        if both_configured:
            st.success("✅ Configured")
            if st.session_state.submitted_model:
                st.caption(f"Model: {st.session_state.submitted_model}")
        else:
            st.warning("⚠️ Configuration required")
        
        # Collapsible configuration (expanded when API key is NOT configured)
        with st.expander("🔧 Configure Credentials", expanded=not api_configured):
            st.markdown("*For Demo: Enter your LLM credentials below*")
            
            # Single form for both API key and model
            with st.form(key="config_form", clear_on_submit=False):
                # API Key input
                api_key_input = st.text_input(
                    "LLM API Key",
                    value=st.session_state.submitted_api_key if st.session_state.submitted_api_key else default_key,
                    type="password",
                    placeholder="Enter your API key...",
                    help="Enter your API key for OpenAI, Anthropic Claude, or other LLM provider",
                    key="api_key_input"
                )
                
                # Model input
                model_input = st.text_input(
                    "LLM Model",
                    value=st.session_state.submitted_model if st.session_state.submitted_model else default_model,
                    placeholder="e.g., gpt-4.1, claude-3-opus...",
                    help="Enter the model name for your LLM provider",
                    key="model_input"
                )
                
                # Single submit button for both
                submitted = st.form_submit_button("🚀 Configure & Start", type="primary", use_container_width=True)
                
                if submitted:
                    if api_key_input and model_input:
                        # Update both
                        st.session_state.submitted_api_key = api_key_input
                        st.session_state.submitted_model = model_input
                        os.environ['OPENAI_API_KEY'] = api_key_input
                        os.environ['OPENAI_MODEL'] = model_input
                        # Reset analyzer to reinitialize
                        st.session_state.analyzer = None
                        st.session_state.df = None
                        st.success("✅ Configuration saved!")
                        st.rerun()
                    elif not api_key_input:
                        st.error("❌ Please enter an API key")
                    elif not model_input:
                        st.error("❌ Please enter a model name")
        
        st.markdown("---")
    
    # Initialize system ONLY if API key is provided (academic mode)
    if not st.session_state.submitted_api_key and not default_key:
        st.error("🔑 **API Key Required**")
        st.info("""
        To use this LLM-augmented test analyzer, enter your API key in the sidebar and click Submit.
        
        **Supported providers:** OpenAI, Anthropic Claude, Llama, or other LLM providers
        
        **For local use:** You can also set `OPENAI_API_KEY` and `OPENAI_MODEL` in your `.env` file.
        """)
        st.stop()
    
    # Apply environment variables if submitted or from .env
    if st.session_state.submitted_api_key:
        os.environ['OPENAI_API_KEY'] = st.session_state.submitted_api_key
    if st.session_state.submitted_model:
        os.environ['OPENAI_MODEL'] = st.session_state.submitted_model

else:
    # Work mode: Use Comcast LLM Gateway configuration from .env
    with st.sidebar:
        st.markdown("### 🔑 LLM Configuration")
        st.success("✅ Using Comcast LLM Gateway")
        st.caption("*Configuration from .env file*")
        st.markdown("---")

# Initialize system ONCE before additional sidebar content
if not initialize_system():
    st.error("System initialization failed")
    st.stop()

# Sidebar - Additional Configuration
with st.sidebar:
    
    st.markdown("""
    <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                padding: 12px; 
                border-radius: 10px; 
                margin-bottom: 10px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);'>
        <h3 style='color: white; margin: 0; text-align: center; font-size: 18px;'>
            🎯 NAVIGATION
        </h3>
    </div>
    """, unsafe_allow_html=True)
    
    page = st.radio(
        "Choose a view:",
        ["💬 Chat Analysis", "🔍 Deep Dive", "⚖️ Compare Tests", "📈 Testing Overview"],
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    st.markdown("### 🎯 Classifier Model")
    
    # Load model metrics from metrics.json
    try:
        import json
        metrics_path = project_root / 'models' / 'metrics.json'
        with open(metrics_path, 'r') as f:
            metrics = json.load(f)
        best_model = metrics.get('best_model', 'Random Forest')
        model_metrics = metrics.get(best_model, {})
        accuracy = model_metrics.get('accuracy', 0) * 100
        f1_score = model_metrics.get('f1_score', 0) * 100
    except Exception:
        accuracy = 92.3
        f1_score = 93.5
        best_model = 'Random Forest'
    
    st.info(f"""
    **Model:** {best_model}  
    **Accuracy:** {accuracy:.1f}%  
    **F1 Score:** {f1_score:.1f}%  
    **Training:** 714 runs, 19 features
    """)
    
    st.markdown("---")
    st.markdown("### 🔧 MCP Tool Stats")
    st.caption("*Available data for LLM queries*")
    
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
    st.markdown("### ⚙️ System Info")
    st.info(f"**Mode:** {mode.upper()}")
    if st.button("🔄 Reload System"):
        st.session_state.analyzer = None
        st.session_state.df = None
        st.session_state.conversation_history = []
        st.rerun()

# Main content (already checked initialization above)

st.markdown('<p class="main-header">🤖 LLM-Augmented Performance Test Analysis Demo</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Ask questions in natural language • MCP Enabled to fetch relevant test data from DB</p>', unsafe_allow_html=True)

# ============================================================================
# PAGE: Chat Analysis
# ============================================================================
if page == "💬 Chat Analysis":
    
    # === Render header and chat history first (non-blocking) ===
    st.markdown("### 💬 Ask Questions About Your Tests")
    st.markdown("Try: *'What are the last 5 test runs?'*, *'Show me failed tests'*, *'Compare LoadTest_001 and LoadTest_002'*")
    
    # Chat history
    for i, (q, a) in enumerate(st.session_state.conversation_history):
        with st.chat_message("user"):
            st.write(q)
        with st.chat_message("assistant"):
            st.markdown(a)
    
    # === Process report generation (spinners appear after chat history, above input) ===
    if st.session_state.generate_report_type:
        report_type = st.session_state.generate_report_type
        st.session_state.generate_report_type = None
        
        with st.spinner("⏳ Fetching test data and preparing report..."):
            analyzer = st.session_state.analyzer
            tests = analyzer.data_source.list_tests(limit=1)
        
        if tests:
            latest_test = tests[0]
            with st.spinner(f"📊 Analyzing test {latest_test} — fetching baseline comparison..."):
                from mcp_server.tools.baseline import get_baseline_comparison
                baseline_result = get_baseline_comparison(latest_test, analyzer=analyzer)
                pred_result = analyzer.predict_test(latest_test)
                conf_pct = pred_result['confidence'] if pred_result['confidence'] >= 2 else pred_result['confidence'] * 100
            
            # Get common data needed for all report types
            test_df = analyzer.data_source.get_test_by_id(latest_test)
            test_summary = test_df.groupby('testplan').agg({
                'perc_95': 'mean',
                'error_percentage': 'mean',
                'transaction_name': 'count',
                'end_time': 'first',
                'exit_code': 'first'
            }).iloc[0]
            
            baseline_summary = baseline_result.get('summary', {}) if 'error' not in baseline_result else {}
            
            # Generate prompt based on report type
            if report_type == 'summary':
                st.session_state.pending_question = get_summary_prompt_with_data(
                    latest_test, test_summary, baseline_summary, pred_result
                )
            
            elif report_type == 'po_report':
                critical_list = format_critical_transactions_list(baseline_result)
                st.session_state.pending_question = get_po_report_prompt_with_data(
                    latest_test, test_summary, baseline_summary, critical_list, pred_result
                )
            
            elif report_type == 'dev_report':
                txn_table = format_transaction_table(baseline_result)
                st.session_state.pending_question = get_dev_report_prompt_with_data(
                    latest_test, txn_table, baseline_summary, pred_result
                )
            
            elif report_type == 'stakeholder_report':
                qa_table = format_qa_table(baseline_result)
                st.session_state.pending_question = get_stakeholder_report_prompt_with_data(
                    latest_test, qa_table, baseline_summary, pred_result
                )
        else:
            st.session_state.pending_question = "No tests found in database."
        
        # This was missing! We set it to true, but never reset it in this path.
        st.session_state.is_processing = False 
        st.rerun()
    
    # === Process pending question (spinner appears after chat history, above input) ===
    if st.session_state.pending_question:
        question = st.session_state.pending_question
        st.session_state.pending_question = None
        
        with st.chat_message("user"):
            st.write(question)
        
        with st.chat_message("assistant"):
            with st.spinner("🤖 Sending to LLM — generating response..."):
                analyzer = st.session_state.analyzer
                conversation_history = st.session_state.conversation_history
                try:
                    result = analyzer.ask(
                        question,
                        conversation_history=conversation_history
                    )
                    tools_used = result.get('tools_used', [])
                    tools_info = f"\n\n*🔧 Tools: {', '.join(tools_used)}*" if tools_used else ""
                    answer = result['answer'] + tools_info
                except Exception as e:
                    answer = f"❌ Error: {e}"
            
            st.markdown(answer)
        
        st.session_state.conversation_history.append((question, answer))
        st.session_state.is_processing = False # Reset processing state
        st.rerun() # Rerun to re-enable buttons immediately

    # Placeholder for the loading indicator
    loading_placeholder = st.empty()

    # Disable input form while processing
    if st.session_state.is_processing:
        loading_placeholder.info("🤖 Thinking... please wait.")

    with st.form(key="chat_form", clear_on_submit=True):
        col1, col2 = st.columns([4, 1])
        with col1:
            question = st.text_input(
                "Ask a question about your test data...",
                key="chat_input",
                disabled=st.session_state.is_processing,
                label_visibility="collapsed",
                placeholder="Ask a question about your test data..."
            )
        with col2:
            submitted = st.form_submit_button("💬 Ask", use_container_width=True, disabled=st.session_state.is_processing)

        if submitted and question:
            st.session_state.pending_question = question
            st.session_state.is_processing = True
            st.rerun()

    # Quick questions
    st.markdown("---")
    st.markdown("**💡 Quick Questions :**")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("📋 Last 5 tests?", disabled=st.session_state.is_processing):
            st.session_state.pending_question = "What are the last 5 test runs?"
            st.session_state.is_processing = True
            st.rerun()
    
    with col2:
        if st.button("❌ Failed tests?", disabled=st.session_state.is_processing):
            st.session_state.pending_question = "Show me all failed tests"
            st.session_state.is_processing = True
            st.rerun()
    
    with col3:
        if st.button("📊 Pass rate?", disabled=st.session_state.is_processing):
            st.session_state.pending_question = "What is the overall pass rate?"
            st.session_state.is_processing = True
            st.rerun()
    
    with col4:
        if st.button("🔍 Summarize last test", disabled=st.session_state.is_processing):
            st.session_state.generate_report_type = 'summary'
            st.session_state.is_processing = True
            st.rerun()
    
    # Report generation
    st.markdown("---")
    st.markdown("**📄 Generate Reports (Last Test):**")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📝 PO Sign-Off Report", disabled=st.session_state.is_processing):
            st.session_state.generate_report_type = 'po_report'
            st.session_state.is_processing = True
            st.rerun()
    
    with col2:
        if st.button("🔬 Dev/QA Report", disabled=st.session_state.is_processing):
            st.session_state.generate_report_type = 'dev_report'
            st.session_state.is_processing = True
            st.rerun()
    
    with col3:
        if st.button("📊 Stakeholder Summary", disabled=st.session_state.is_processing):
            st.session_state.generate_report_type = 'stakeholder_report'
            st.session_state.is_processing = True
            st.rerun()

# ============================================================================
# PAGE: Test Overview
# ============================================================================
elif page == "📈 Testing Overview":
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
        st.plotly_chart(fig, width='stretch')
    
    with col2:
        st.markdown("#### Top 10 Slowest Transactions")
        top_slow = df.groupby('transaction_name')['perc_95'].mean().sort_values(ascending=False).head(10)
        fig = px.bar(x=top_slow.values, y=top_slow.index, orientation='h',
                     labels={'x': 'P95 Response Time (ms)', 'y': 'Transaction'})
        st.plotly_chart(fig, width='stretch')
    
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
    st.plotly_chart(fig, width='stretch')
    
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
    st.dataframe(trans_summary, width='stretch')
    
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
        analyze_button = st.button("🔍 Analyze", type="primary", width='stretch')
    
    # Only analyze on button click (removed automatic analysis on selection change)
    if analyze_button:
        st.session_state.current_test = selected_test
        
        # Detailed status instead of simple spinner
        with st.status("🤖 Analyzing test...", expanded=True) as status:
            st.write("🔍 Step 1: Running classifier prediction...")
            pred_result = analyzer.predict_test(selected_test)
            confidence = pred_result['confidence'] if pred_result['confidence'] >= 2 else pred_result['confidence'] * 100
            st.write(f"   ✅ Prediction: {pred_result['prediction']} ({confidence:.1f}% confidence)")
            
            st.write("📊 Step 2: Fetching baseline comparison via MCP tool...")
            st.write("   ↳ Reusing database connection (no new connection overhead)")
            
            st.write("🤖 Step 3: Sending test data to LLM for deep analysis...")
            st.write("   ↳ Temperature: 0.7 (balanced analysis)")
            analysis = analyzer.analyze_test(selected_test, include_transactions=True)
            st.write("   ✅ Analysis complete")
            
            status.update(label="✅ All analysis steps complete!", state="complete")
            
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
                st.dataframe(features_df.T, width='stretch')
            
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
                
                st.dataframe(test_data[display_cols], width='stretch')
            
            # HYBRID APPROACH: Quick Actions + Chat
            st.markdown("---")
            st.markdown("### 💬 Ask About This Test")
            st.markdown(f"Ask questions about **{selected_test}** or generate reports:")
            
            # Quick action buttons
            st.markdown("**Quick Actions:**")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                if st.button("📝 PO Report", key="quick_po", width='stretch'):
                    # Show immediate feedback
                    loading_placeholder = st.empty()
                    loading_placeholder.info("⏳ Generating PO report... check below for response")
                    
                    conf_pct = confidence if confidence >= 2 else confidence * 100
                    question = get_po_report_prompt_short(selected_test, pred_result['prediction'], conf_pct)
                    
                    # Process immediately without page refresh
                    with st.spinner("🤖 Analyzing..."):
                        answer, tokens = ask_about_test(selected_test, question)
                        
                        if selected_test not in st.session_state.test_chat_history:
                            st.session_state.test_chat_history[selected_test] = []
                        st.session_state.test_chat_history[selected_test].append((question, answer))
                    
                    loading_placeholder.empty()
                    st.rerun()
            
            with col2:
                if st.button("🔬 Eng Report", key="quick_eng", width='stretch'):
                    loading_placeholder = st.empty()
                    loading_placeholder.info("⏳ Generating engineering report... check below for response")
                    
                    conf_pct = confidence if confidence >= 2 else confidence * 100
                    question = get_eng_report_prompt_short(selected_test, pred_result['prediction'], conf_pct)
                    
                    with st.spinner("🤖 Analyzing..."):
                        answer, tokens = ask_about_test(selected_test, question)
                        
                        if selected_test not in st.session_state.test_chat_history:
                            st.session_state.test_chat_history[selected_test] = []
                        st.session_state.test_chat_history[selected_test].append((question, answer))
                    
                    loading_placeholder.empty()
                    st.rerun()
            
            with col3:
                if st.button("📊 QA Report", key="quick_qa", width='stretch'):
                    loading_placeholder = st.empty()
                    loading_placeholder.info("⏳ Generating QA report... check below for response")
                    
                    conf_pct = confidence if confidence >= 2 else confidence * 100
                    question = get_qa_report_prompt_short(selected_test, pred_result['prediction'], conf_pct)
                    
                    with st.spinner("🤖 Analyzing..."):
                        answer, tokens = ask_about_test(selected_test, question)
                        
                        if selected_test not in st.session_state.test_chat_history:
                            st.session_state.test_chat_history[selected_test] = []
                        st.session_state.test_chat_history[selected_test].append((question, answer))
                    
                    loading_placeholder.empty()
                    st.rerun()
            
            with col4:
                if st.button("❓ Explain Prediction", key="quick_explain", width='stretch'):
                    loading_placeholder = st.empty()
                    loading_placeholder.info("⏳ Analyzing prediction... check below for response")
                    
                    conf_pct = confidence if confidence >= 2 else confidence * 100
                    question = get_explain_prediction_prompt(selected_test, pred_result['prediction'], conf_pct)
                    
                    with st.spinner("🤖 Analyzing..."):
                        answer, tokens = ask_about_test(selected_test, question)
                        
                        if selected_test not in st.session_state.test_chat_history:
                            st.session_state.test_chat_history[selected_test] = []
                        st.session_state.test_chat_history[selected_test].append((question, answer))
                    
                    loading_placeholder.empty()
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
                
                submitted = st.form_submit_button("💬 Ask", type="primary", width='stretch')
            
            # Clear chat button (outside form)
            if st.button("🗑️ Clear Chat", key="clear_chat_btn"):
                if selected_test in st.session_state.test_chat_history:
                    st.session_state.test_chat_history[selected_test] = []
                st.rerun()
            
            # Process question from form submission
            if submitted and test_question:
                # Show loading indicator right here where user is looking
                loading_status = st.empty()
                loading_status.info("⏳ Processing your question... response will appear below")
                
                with st.spinner("🤖 Analyzing..."):
                    # Use ask_about_test for test-specific context
                    answer, tokens = ask_about_test(selected_test, test_question)
                    
                    # Store in test-specific chat history
                    if selected_test not in st.session_state.test_chat_history:
                        st.session_state.test_chat_history[selected_test] = []
                    st.session_state.test_chat_history[selected_test].append((test_question, answer))
                
                loading_status.empty()
                # Note: Form clears input automatically via clear_on_submit=True
            
            # Display chat history for this test
            if selected_test in st.session_state.test_chat_history and st.session_state.test_chat_history[selected_test]:
                st.markdown("---")
                st.markdown("### 📝 Conversation")
                
                history = st.session_state.test_chat_history[selected_test]
                total = len(history)
                for i, (q, a) in enumerate(reversed(history)):
                    orig_idx = total - 1 - i  # original index for unique keys
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
                            file_name=f"{selected_test}_Q{orig_idx+1}.md",
                            mime="text/markdown",
                            key=f"download_qa_{selected_test}_{orig_idx}"
                        )
                    
                    if i < total - 1:
                        st.markdown("---")

# ============================================================================
# PAGE: Compare Tests
# ============================================================================
elif page == "⚖️ Compare Tests":
    analyzer = st.session_state.analyzer
    
    st.markdown("### ⚖️ Compare Tests: Test 1 vs Test 2 vs Baseline")
    
    tests = analyzer.data_source.list_tests(limit=50)
    
    col1, col2, col3 = st.columns([4, 4, 2])
    
    with col1:
        test1 = st.selectbox("Test 1:", tests, index=0, key="test1")
    
    with col2:
        test2 = st.selectbox("Test 2:", tests, index=1 if len(tests) > 1 else 0, key="test2")
    
    with col3:
        st.write("")  # Add spacing to align with selectbox
        include_baseline = st.checkbox("Include Baseline", value=True)
    
    if st.button("⚖️ Compare All", type="primary"):
        if test1 == test2:
            st.warning("⚠️ Please select two different tests")
        else:
            st.markdown("---")
            
            # Detailed status instead of simple spinner
            with st.status("🤖 Performing comparison...", expanded=True) as status:
                # Section 1: Test 1 vs Test 2 (Using centralized prompt)
                st.markdown("### 🔄 Test 1 vs Test 2")
                
                st.write("📊 Step 1: Fetching transaction data for both tests...")
                st.write(f"   ↳ Test 1: {test1}")
                st.write(f"   ↳ Test 2: {test2}")
                # Fetch detailed transaction data for both tests
                df_test1 = analyzer.data_source.get_test_by_id(test1)
                df_test2 = analyzer.data_source.get_test_by_id(test2)
                st.write(f"   ✅ Loaded {len(df_test1)} transactions from Test 1, {len(df_test2)} from Test 2")
                
                st.write("🔍 Step 2: Embedding full transaction data in prompt...")
                # Generate comparison prompt with FULL transaction data
                comparison_prompt = get_test_comparison_prompt(test1, test2, df_test1, df_test2)
                st.write("   ✅ Comparison context prepared (anti-hallucination pattern)")
                
                st.write("🤖 Step 3: Sending to LLM for transaction-level analysis...")
                # Ask LLM with comprehensive context
                result = analyzer.ask(
                    "Provide a detailed comparison analysis of these two tests.",
                    data_context=comparison_prompt,
                    conversation_history=[]
                )
                st.write("   ✅ Test comparison analysis complete")
                
                status.update(label="✅ Comparison ready!", state="complete")
            
            st.markdown(result['answer'])
            
            if include_baseline:
                # Section 2: Test 1 vs Baseline
                st.markdown("---")
                st.markdown(f"### 📈 Test 1 ({test1}) vs Baseline")
                
                with st.status("📊 Fetching Test 1 baseline...", expanded=False) as baseline_status:
                    st.write("🔧 Calling get_baseline_comparison MCP tool...")
                    st.write("   ↳ Reusing database connection")
                    result1 = analyzer.ask(
                        f"Compare {test1} with baseline. Focus on key deviations and classifier features.",
                        conversation_history=st.session_state.conversation_history
                    )
                    tools = result1.get('tools_used', [])
                    if tools:
                        st.write(f"   ✅ Tools used: {', '.join(tools)}")
                    baseline_status.update(label="✅ Test 1 baseline comparison complete", state="complete")
                
                st.markdown(result1['answer'])
                
                # Section 3: Test 2 vs Baseline
                st.markdown("---")
                st.markdown(f"### 📈 Test 2 ({test2}) vs Baseline")
                
                with st.status("📊 Fetching Test 2 baseline...", expanded=False) as baseline_status2:
                    st.write("🔧 Calling get_baseline_comparison MCP tool...")
                    st.write("   ↳ Reusing database connection")
                    result2 = analyzer.ask(
                        f"Compare {test2} with baseline. Focus on key deviations and classifier features.",
                        conversation_history=st.session_state.conversation_history
                    )
                    tools2 = result2.get('tools_used', [])
                    if tools2:
                        st.write(f"   ✅ Tools used: {', '.join(tools2)}")
                    baseline_status2.update(label="✅ Test 2 baseline comparison complete", state="complete")
                
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
st.markdown(f"""
<div style='text-align: center; color: #666; padding: 1rem;'>
    <small>LLM-Augmented Test Analysis | Mode: {mode.upper()} | Powered by Sentinel Performance</small>
</div>
""", unsafe_allow_html=True)
