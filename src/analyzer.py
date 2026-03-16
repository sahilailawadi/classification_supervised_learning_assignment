"""
Test Analyzer Service - LLM-Augmented Performance Test Analysis.

Combines:
- Data sources (Excel/PostgreSQL) from Phase 2
- LLM providers (OpenAI/Work Gateway) from Phase 1
- Existing classifier predictions from predict.py
- Feature engineering from features.py

Provides intelligent analysis:
- "Why did this test fail?"
- "What changed between these two tests?"
- "Is this failure pattern normal?"
- "What should I investigate first?"

Usage:
    from src.analyzer import TestAnalyzer
    
    # Auto-detects mode from LLM_MODE
    analyzer = TestAnalyzer()
    
    # Analyze a test failure
    analysis = analyzer.analyze_test('LoadTest_001')
    print(analysis)
    
    # Compare two tests
    comparison = analyzer.compare_tests('LoadTest_001', 'LoadTest_002')
    print(comparison)
"""

import os
import json
from typing import Optional, Dict, List, Any
from pathlib import Path
import pandas as pd
import numpy as np
import joblib
from dotenv import load_dotenv

from src.llm_provider import get_llm_provider, BaseLLMProvider
from src.data_source import get_data_source, BaseDataSource

# MCP tools imported lazily to avoid circular dependency

# Load environment
load_dotenv()

# Model features (must match training)
MODEL_FEATURES = [
    "pct_txn_critical_p95",
    "pct_txn_degraded_p95",
    "max_pct_deviation_p95",
    "pct_txn_critical_avg_rt",
    "pct_txn_degraded_avg_rt",
    "max_pct_deviation_avg_rt",
    "pct_txn_critical_error",
    "pct_txn_degraded_error",
    "max_pct_deviation_error",
    "pct_txn_with_errors",
    "pct_txn_complete_failure",
    "max_error_percentage",
    "has_100pct_failure_txn",
    "throughput_per_user",
    "pct_deviation_throughput",
    "fail_ratio",
    "has_anomalous_transactions",
    "num_transactions",
    "test_type_encoded",
]


class TestAnalyzer:
    """
    Intelligent test analysis service using LLM augmentation.
    
    Automatically adapts to academic or work mode based on LLM_MODE env var.
    """
    
    def __init__(
        self,
        mode: Optional[str] = None,
        models_dir: str = "models"
    ):
        """
        Initialize test analyzer.
        
        Args:
            mode: Override mode ('academic' or 'work')
            models_dir: Directory containing trained model artifacts
        """
        self.mode = mode or os.getenv('LLM_MODE', 'academic')
        self.models_dir = Path(models_dir)
        
        # Load components
        print(f"🔧 Initializing TestAnalyzer in {self.mode.upper()} mode...")
        
        # Load LLM provider
        self.llm = get_llm_provider(mode=self.mode)
        print(f"   ✅ LLM: {self.llm.__class__.__name__}")
        
        # Load data source
        self.data_source = get_data_source(mode=self.mode)
        print(f"   ✅ Data: {self.data_source.__class__.__name__}")
        
        # Load classifier artifacts
        self._load_artifacts()
        print(f"   ✅ Classifier: {self.model.__class__.__name__}")
        
        print("✅ TestAnalyzer ready\n")
    
    def _load_artifacts(self):
        """Load trained model and scaler."""
        model_path = self.models_dir / "model.pkl"
        scaler_path = self.models_dir / "scaler.pkl"
        
        if not model_path.exists():
            raise FileNotFoundError(
                f"Model not found at {model_path}. Run 'python -m src.train' first."
            )
        if not scaler_path.exists():
            raise FileNotFoundError(
                f"Scaler not found at {scaler_path}. Run 'python -m src.train' first."
            )
        
        self.model = joblib.load(model_path)
        self.scaler = joblib.load(scaler_path)
    
    def predict_test(self, testplan: str) -> Dict[str, Any]:
        """
        Get classifier prediction for a test.
        
        Args:
            testplan: Test identifier
            
        Returns:
            Dict with prediction, confidence, features, actual_result
        """
        # Get test data
        df_raw = self.data_source.get_test_by_id(testplan)
        
        if len(df_raw) == 0:
            raise ValueError(f"No data found for test: {testplan}")
        
        # Build features (import here to avoid circular dependency)
        from src.features import build_features
        
        df_features, _ = build_features(df_raw, is_training=False)
        
        if len(df_features) == 0:
            raise ValueError(f"Feature engineering failed for test: {testplan}")
        
        # Extract and scale features (convert back to DataFrame to preserve column names)
        X = df_features[MODEL_FEATURES]
        X_scaled = self.scaler.transform(X)
        X_scaled_df = pd.DataFrame(X_scaled, columns=MODEL_FEATURES, index=X.index)
        
        # Predict
        prediction = self.model.predict(X_scaled_df)[0]
        
        # Get confidence if available
        confidence = None
        if hasattr(self.model, 'predict_proba'):
            proba = self.model.predict_proba(X_scaled_df)[0]
            confidence = float(max(proba))
        
        # Extract features as dict
        features = df_features[MODEL_FEATURES].iloc[0].to_dict()
        
        # Get actual result
        actual_exit_code = df_raw['exit_code'].iloc[0]
        actual_result = "PASS" if actual_exit_code == 1 else "FAIL"
        
        return {
            'testplan': testplan,
            'prediction': "PASS" if prediction == 1 else "FAIL",
            'prediction_code': int(prediction),
            'confidence': confidence,
            'features': features,
            'actual_result': actual_result,
            'actual_exit_code': int(actual_exit_code),
            'num_transactions': len(df_raw),
            'transactions': df_raw['transaction_name'].unique().tolist()
        }
    
    def analyze_test(
        self,
        testplan: str,
        include_transactions: bool = True
    ) -> str:
        """
        Perform deep analysis of a test using LLM.
        
        Args:
            testplan: Test identifier
            include_transactions: Whether to include transaction details
            
        Returns:
            Markdown-formatted analysis from LLM
        """
        print(f"🔍 Analyzing test: {testplan}")
        
        # Get prediction
        result = self.predict_test(testplan)
        
        # Get raw data for context
        df_raw = self.data_source.get_test_by_id(testplan)
        
        # Build context for LLM
        context = self._build_test_context(result, df_raw, include_transactions)
        
        # Create LLM prompt
        system_prompt = """You are an expert performance test analyst. Analyze test results and provide actionable insights.

Focus on:
1. Why the test passed or failed
2. Key performance indicators and deviations
3. Specific transactions with issues
4. Root cause hypotheses
5. Actionable next steps

Be concise but thorough. Use bullet points and highlight critical issues."""
        
        user_prompt = f"""Analyze this performance test result:

{context}

Provide a comprehensive analysis covering:
- Overall verdict and confidence
- Key findings (what stands out?)
- Problem areas (if any)
- Root cause analysis
- Recommended actions

Format your response in clear sections with markdown."""
        
        # Get LLM analysis
        print("   🤖 Querying LLM for analysis...")
        response = self.llm.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7
        )
        
        print(f"   ✅ Analysis complete ({response.tokens_used or '?'} tokens)\n")
        
        return response.content
    
    def compare_tests(
        self,
        testplan1: str,
        testplan2: str
    ) -> str:
        """
        Compare two tests using LLM to identify differences.
        
        Args:
            testplan1: First test identifier
            testplan2: Second test identifier
            
        Returns:
            Markdown-formatted comparison from LLM
        """
        print(f"🔍 Comparing tests:")
        print(f"   Test 1: {testplan1}")
        print(f"   Test 2: {testplan2}")
        
        # Get predictions for both
        result1 = self.predict_test(testplan1)
        result2 = self.predict_test(testplan2)
        
        # Get raw data
        df1 = self.data_source.get_test_by_id(testplan1)
        df2 = self.data_source.get_test_by_id(testplan2)
        
        # Build comparison context
        context = self._build_comparison_context(result1, result2, df1, df2)
        
        # Create LLM prompt
        system_prompt = """You are an expert performance test analyst comparing two test runs.

Identify:
1. Key differences in outcomes and metrics
2. Performance improvements or degradations
3. Pattern changes
4. Possible causes of differences
5. Which test is better and why"""
        
        user_prompt = f"""Compare these two performance tests:

{context}

Provide a detailed comparison covering:
- Outcome comparison (PASS/FAIL)
- Performance metric differences
- Transaction-level changes
- Possible explanations for differences
- Recommendations based on comparison

Use tables and bullet points for clarity."""
        
        # Get LLM comparison
        print("   🤖 Querying LLM for comparison...")
        response = self.llm.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7
        )
        
        print(f"   ✅ Comparison complete ({response.tokens_used or '?'} tokens)\n")
        
        return response.content
    
    def _build_test_context(
        self,
        result: Dict[str, Any],
        df_raw: pd.DataFrame,
        include_transactions: bool
    ) -> str:
        """Build context string for LLM analysis."""
        lines = []
        
        # Test summary
        lines.append(f"## Test: {result['testplan']}")
        lines.append(f"- **Prediction**: {result['prediction']} (confidence: {result['confidence']*100:.1f}%)" if result['confidence'] else f"- **Prediction**: {result['prediction']}")
        lines.append(f"- **Actual Result**: {result['actual_result']} (exit_code: {result['actual_exit_code']})")
        lines.append(f"- **Transactions**: {result['num_transactions']}")
        
        # Build version and user count
        if 'build_version' in df_raw.columns:
            lines.append(f"- **Build**: {df_raw['build_version'].iloc[0]}")
        if 'num_clients' in df_raw.columns:
            lines.append(f"- **Users**: {df_raw['num_clients'].iloc[0]}")
        
        # Key features
        lines.append("\n## Key Performance Indicators")
        features = result['features']
        
        # Highlight critical metrics
        critical_features = {
            'max_pct_deviation_p95': 'Max P95 Deviation',
            'max_pct_deviation_avg_rt': 'Max Avg RT Deviation',
            'max_pct_deviation_error': 'Max Error Deviation',
            'fail_ratio': 'Overall Fail Ratio',
            'max_error_percentage': 'Max Error %',
            'pct_txn_critical_p95': '% Critical Txns (P95)',
            'pct_txn_with_errors': '% Txns With Errors',
            'throughput_per_user': 'Throughput/User',
        }
        
        for feat_key, feat_name in critical_features.items():
            if feat_key in features:
                value = features[feat_key]
                lines.append(f"- **{feat_name}**: {value:.4f}")
        
        # Transaction details
        if include_transactions and len(df_raw) > 0:
            lines.append("\n## Transaction Details")
            lines.append("| Transaction | Error % | P95 (ms) | Avg RT (ms) | Requests |")
            lines.append("|------------|---------|----------|-------------|----------|")
            
            # Group by transaction
            txn_summary = df_raw.groupby('transaction_name').agg({
                'error_percentage': 'mean',
                'perc_95': 'mean',
                'avg_response_time': 'mean',
                'txn_requests': 'sum'
            }).round(2)
            
            for txn, row in txn_summary.iterrows():
                lines.append(
                    f"| {txn} | {row['error_percentage']:.2f}% | "
                    f"{row['perc_95']:.0f} | {row['avg_response_time']:.0f} | "
                    f"{int(row['txn_requests'])} |"
                )
        
        return "\n".join(lines)
    
    def _build_comparison_context(
        self,
        result1: Dict,
        result2: Dict,
        df1: pd.DataFrame,
        df2: pd.DataFrame
    ) -> str:
        """Build context string for LLM comparison."""
        lines = []
        
        # Test summaries
        lines.append(f"## Test 1: {result1['testplan']}")
        lines.append(f"- **Result**: {result1['prediction']} (actual: {result1['actual_result']})")
        lines.append(f"- **Transactions**: {result1['num_transactions']}")
        
        lines.append(f"\n## Test 2: {result2['testplan']}")
        lines.append(f"- **Result**: {result2['prediction']} (actual: {result2['actual_result']})")
        lines.append(f"- **Transactions**: {result2['num_transactions']}")
        
        # Feature comparison
        lines.append("\n## Feature Comparison")
        lines.append("| Metric | Test 1 | Test 2 | Difference |")
        lines.append("|--------|--------|--------|------------|")
        
        key_features = [
            'max_pct_deviation_p95',
            'fail_ratio',
            'max_error_percentage',
            'throughput_per_user'
        ]
        
        for feat in key_features:
            if feat in result1['features'] and feat in result2['features']:
                val1 = result1['features'][feat]
                val2 = result2['features'][feat]
                diff = val2 - val1
                diff_str = f"+{diff:.4f}" if diff > 0 else f"{diff:.4f}"
                lines.append(f"| {feat} | {val1:.4f} | {val2:.4f} | {diff_str} |")
        
        return "\n".join(lines)
    
    def get_test_context(
        self,
        testplan_or_index,
        sort_by: str = "perc_95"
    ) -> str:
        """
        Get detailed test context for LLM queries (prevents hallucination).
        
        This method fetches real transaction data and formats it for LLM consumption.
        Use this when asking specific questions about a test to ensure the LLM
        has access to actual data rather than making up answers.
        
        Args:
            testplan_or_index: Test index (int) or testplan ID (str)
            sort_by: Column to sort transactions by (default: "perc_95")
            
        Returns:
            Formatted string with test details and all transactions
            
        Example:
            # By index
            context = analyzer.get_test_context(0)
            
            # By testplan ID
            context = analyzer.get_test_context("LoadTest_20260304T060726Z")
            
            # Then use in LLM query
            response = analyzer.llm.chat(messages=[
                {"role": "user", "content": f"{context}\\n\\nQuestion: What are the slowest transactions?"}
            ])
        """
        # Load full dataset if not already loaded
        df = self.data_source.load_test_data()
        
        # Get testplan ID
        if isinstance(testplan_or_index, int):
            # User provided index - get testplan from dataframe
            unique_tests = df['testplan'].unique()
            if testplan_or_index < 0 or testplan_or_index >= len(unique_tests):
                raise ValueError(
                    f"Test index {testplan_or_index} out of range. "
                    f"Valid range: 0-{len(unique_tests)-1}"
                )
            testplan = unique_tests[testplan_or_index]
        else:
            testplan = testplan_or_index
        
        # Fetch real test data
        test_data = df[df["testplan"] == testplan]
        
        if len(test_data) == 0:
            raise ValueError(f"Test '{testplan}' not found in dataset")
        
        # Get test metadata
        test_info = test_data.iloc[0]
        
        # Build context with real transaction data
        lines = []
        
        # Test header
        lines.append(f"# Test Details: {testplan}")
        lines.append("")
        
        # Metadata
        lines.append("## Test Metadata")
        lines.append(f"- **Test Plan**: {testplan}")
        lines.append(f"- **Exit Code**: {test_info['exit_code']}")
        lines.append(f"- **Result**: {'PASS' if test_info['exit_code'] == 1 else 'FAIL'}")
        
        # Optional fields
        if 'duration_sec' in test_data.columns:
            duration = test_info.get('duration_sec', 'N/A')
            lines.append(f"- **Duration**: {duration} seconds")
        
        if 'build_version' in test_data.columns:
            lines.append(f"- **Build Version**: {test_info['build_version']}")
        
        if 'num_clients' in test_data.columns:
            lines.append(f"- **Virtual Users**: {test_info['num_clients']}")
        
        if 'end_time' in test_data.columns:
            lines.append(f"- **Timestamp**: {test_info['end_time']}")
        
        lines.append("")
        
        # Transaction performance
        lines.append("## Transaction Performance")
        lines.append("")
        lines.append("Transactions sorted by P95 response time (highest first):")
        lines.append("")
        
        # Sort transactions by specified column
        transactions = test_data.sort_values(by=sort_by, ascending=False)
        
        # Format each transaction
        for idx, txn in transactions.iterrows():
            txn_name = txn['transaction_name']
            p95 = txn['perc_95']
            avg_rt = txn['avg_response_time']
            error_pct = txn['error_percentage']
            
            # Highlight problematic transactions
            status = ""
            if error_pct > 0:
                status = " ⚠️ HAS ERRORS"
            elif p95 > 5000:  # >5 seconds
                status = " 🐌 SLOW"
            
            lines.append(
                f"**{txn_name}**{status}\n"
                f"  - P95: {p95:.2f} ms\n"
                f"  - Average: {avg_rt:.2f} ms\n"
                f"  - Error Rate: {error_pct:.2f}%\n"
            )
        
        lines.append("")
        lines.append("---")
        lines.append("*This data includes ALL transactions from the actual test run.*")
        
        return "\n".join(lines)
    
    def ask(
        self,
        question: str,
        about_test=None,
        data_context=None,
        conversation_history: Optional[List[tuple]] = None
    ) -> Dict[str, Any]:
        """
        Universal method to ask LLM questions about test data.
        
        NOW WITH MCP TOOL INTEGRATION (Phase 2):
        - Automatically routes questions to appropriate MCP tools
        - Fetches real data instead of providing generic statistics
        - Supports natural language queries like "last 5 tests", "failed tests"
        
        This is the main interface - handles all query types in one method:
        - Specific test questions (provide about_test)
        - Custom data questions (provide data_context)  
        - Natural language queries (LLM + MCP tools fetch data automatically)
        
        Args:
            question: Your question in natural language
            about_test: Optional test ID/index for test-specific questions
            data_context: Optional pre-formatted data (DataFrame.to_string(), etc.)
            conversation_history: Optional list of (question, answer) tuples
            
        Returns:
            Dict with 'answer' (str), 'tokens_used' (int or None), and 'tools_used' (list)
            
        Examples:
            # Ask about specific test (backward compatible)
            result = analyzer.ask("What are the slowest transactions?", about_test=0)
            
            # Natural language queries (NEW - uses MCP tools automatically)
            result = analyzer.ask("What are the last 5 test runs?")
            result = analyzer.ask("Show me all failed tests")
            result = analyzer.ask("Compare LoadTest_001 and LoadTest_002")
            
            # General question
            result = analyzer.ask("What's the overall pass rate?")
        """
        # Backward compatibility: explicit about_test or data_context
        if about_test is not None:
            context = self.get_test_context(about_test)
            response = self.ask_about_data(context, question, conversation_history)
            response['tools_used'] = []
            return response
            
        elif data_context is not None:
            response = self.ask_about_data(data_context, question, conversation_history)
            response['tools_used'] = []
            return response
        
        # NEW: Intelligent routing with MCP tools
        print(f"🤔 Analyzing question: '{question[:80]}{'...' if len(question) > 80 else ''}'")
        
        # Step 1: Use LLM to determine which tools to call
        tool_selection = self._determine_tools_needed(question)
        
        # Step 2: Execute the appropriate MCP tools
        tool_results = []
        for tool_call in tool_selection['tools']:
            print(f"   🔧 Calling {tool_call['name']}({tool_call['params']})")
            result = self._execute_mcp_tool(tool_call['name'], tool_call['params'])
            tool_results.append({
                'tool': tool_call['name'],
                'params': tool_call['params'],
                'result': result
            })
        
        # Step 3: Format tool results as context for LLM
        context = self._format_tool_results(tool_results, question)
        
        # Step 4: Ask LLM with the fetched data
        response = self.ask_about_data(context, question, conversation_history)
        response['tools_used'] = [t['tool'] for t in tool_results]
        
        return response
    
    def _determine_tools_needed(self, question: str) -> Dict[str, Any]:
        """
        Use LLM to analyze the question and determine which MCP tools to call.
        
        Returns dict with 'tools' list containing tool name and parameters.
        """
        system_prompt = """You are a query planner for a performance test analysis system.
Analyze the user's question and determine which tools to call to fetch the necessary data.

Available tools:
1. query_tests(limit, exit_code, sort_by, ascending)
   - Get list of test runs
   - Use for: "last N tests", "recent tests", "failed tests", "show me tests"
   - Parameters:
     * limit: number of tests (default 10)
     * exit_code: filter by result (1=PASS, 2=FAIL, omit for all)
     * sort_by: "end_time" (most recent), "perc_95" (slowest), etc.
     * ascending: false for most recent/slowest first

2. get_test_detail(testplan)
   - Get comprehensive details about one test
   - Use for: questions about a specific test (id mentioned)
   - Parameters:
     * testplan: the test identifier

3. compare_tests(testplan1, testplan2)
   - Compare two tests side-by-side
   - Use for: "compare", "difference between", "what changed"
   - Parameters:
     * testplan1: first test id
     * testplan2: second test id

Respond with JSON:
{
  "reasoning": "brief explanation of tool selection",
  "tools": [
    {"name": "tool_name", "params": {...}}
  ]
}

If the question needs data but you can't extract specific test IDs, use query_tests to list tests first.
If it's a general statistics question (pass rate, total tests), return empty tools list."""

        user_prompt = f"""Question: {question}

Which tools should be called to answer this question?"""

        response = self.llm.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1
        )
        
        # Parse JSON response
        try:
            result = json.loads(response.content)
            print(f"   💡 Tool plan: {result['reasoning']}")
            return result
        except json.JSONDecodeError:
            print(f"   ⚠️  Failed to parse tool selection, using fallback")
            # Fallback: query recent tests
            return {
                'reasoning': 'Fallback - showing recent tests',
                'tools': [{'name': 'query_tests', 'params': {'limit': 5}}]
            }
    
    def _execute_mcp_tool(self, tool_name: str, params: Dict[str, Any]) -> Any:
        """Execute an MCP tool with given parameters."""
        # Lazy import to avoid circular dependency
        from mcp_server.tools.query import query_tests
        from mcp_server.tools.detail import get_test_detail
        from mcp_server.tools.compare import compare_tests
        
        if tool_name == 'query_tests':
            return query_tests(
                limit=params.get('limit', 10),
                exit_code=params.get('exit_code'),
                sort_by=params.get('sort_by', 'end_time'),
                ascending=params.get('ascending', False)
            )
        elif tool_name == 'get_test_detail':
            return get_test_detail(params['testplan'])
        elif tool_name == 'compare_tests':
            return compare_tests(params['testplan1'], params['testplan2'])
        else:
            raise ValueError(f"Unknown tool: {tool_name}")
    
    def _format_tool_results(self, tool_results: List[Dict], question: str) -> str:
        """Format MCP tool results into context string for LLM."""
        if not tool_results:
            # No tools used - provide general dataset overview
            df = self.data_source.load_test_data()
            return f"""Dataset Overview:
- Total tests: {df['testplan'].nunique()}
- Total transactions/rows: {len(df):,}
- Date range: {df['end_time'].min()} to {df['end_time'].max()}
- Pass/Fail: {df[df['exit_code']==1]['testplan'].nunique()} pass, {df[df['exit_code']!=1]['testplan'].nunique()} fail"""
        
        context_parts = [f"Query: {question}\n", "Data retrieved:\n"]
        
        for tr in tool_results:
            context_parts.append(f"\n=== {tr['tool']}({tr['params']}) ===\n")
            
            if tr['tool'] == 'query_tests':
                result = tr['result']
                context_parts.append(f"Found {result['count']} tests (total: {result['total_in_dataset']})\n")
                for i, test in enumerate(result['tests'], 1):
                    context_parts.append(
                        f"{i}. {test['testplan']}: "
                        f"P95={test['avg_p95']:.0f}ms, "
                        f"Errors={test['avg_error_pct']:.1f}%, "
                        f"Txns={test['num_transactions']}, "
                        f"Result={test['result']} "
                        f"({test['end_time']})\n"
                    )
            
            elif tr['tool'] == 'get_test_detail':
                result = tr['result']
                # Use the formatted_context from the tool
                if 'formatted_context' in result:
                    context_parts.append(result['formatted_context'])
                else:
                    context_parts.append(json.dumps(result, indent=2))
            
            elif tr['tool'] == 'compare_tests':
                result = tr['result']
                diff = result['differences']
                context_parts.append(
                    f"Test 1: {result['test1']['testplan']}\n"
                    f"  P95: {result['test1']['p95_ms']:.0f}ms, Prediction: {result['test1']['prediction']}\n"
                    f"Test 2: {result['test2']['testplan']}\n"
                    f"  P95: {result['test2']['p95_ms']:.0f}ms, Prediction: {result['test2']['prediction']}\n"
                    f"Differences:\n"
                    f"  P95 delta: {diff['p95_delta']:+.0f}ms ({diff['p95_pct_change']:+.1%})\n"
                    f"  Error delta: {diff['error_delta']:+.1f}%\n"
                )
        
        return ''.join(context_parts)
    
    def ask_about_data(
        self,
        data_context: str,
        question: str,
        conversation_history: Optional[List[tuple]] = None
    ) -> Dict[str, Any]:
        """
        Ask LLM a question with provided data context.
        
        This is a general-purpose method for querying the LLM with any data.
        Use this when you have pandas query results, aggregations, or custom
        data that you want the LLM to interpret or answer questions about.
        
        Args:
            data_context: Formatted data (can include pandas output, tables, stats)
            question: Your question about the data
            conversation_history: Optional list of (question, answer) tuples for context
            
        Returns:
            Dict with 'answer' (str) and 'tokens_used' (int or None)
            
        Example:
            # Get last 3 tests
            df = analyzer.data_source.load_test_data()
            last_3 = df.groupby('testplan').agg({
                'end_time': 'first',
                'exit_code': 'first'
            }).sort_values('end_time', ascending=False).head(3)
            
            # Ask LLM about them
            result = analyzer.ask_about_data(
                data_context=f"Last 3 test runs:\\n{last_3.to_string()}",
                question="What patterns do you see in these tests?"
            )
            print(result['answer'])
        """
        # Build system prompt
        system_prompt = """You are an expert performance test analyst.

Answer questions about the provided test data. Be concise but informative.
Use bullet points for clarity. Highlight key insights and patterns.
When data is provided, reference specific values and trends from that data."""
        
        # Build messages array
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history if provided (last 5 exchanges)
        if conversation_history:
            for prev_q, prev_a in conversation_history[-5:]:
                messages.append({"role": "user", "content": prev_q})
                messages.append({"role": "assistant", "content": prev_a})
        
        # Add current question with data context
        full_prompt = f"{data_context}\n\n---\n\n**Question:** {question}"
        messages.append({"role": "user", "content": full_prompt})
        
        # Query LLM
        response = self.llm.chat(
            messages=messages,
            temperature=0.7
        )
        
        return {
            'answer': response.content,
            'tokens_used': response.tokens_used
        }
