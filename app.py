"""
Streamlit UI for Performance Test Classification Demo
INFO 629 Assignment - Supervised Learning

Run: streamlit run app.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import json
import joblib
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# Page config
st.set_page_config(
    page_title="Performance Test Classifier",
    page_icon="🎯",
    layout="wide"
)

# Constants
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
    # NEW: Per-transaction error metrics (detect catastrophic failures)
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

FEATURE_DESCRIPTIONS = {
    "pct_txn_critical_p95": "% transactions with p95 >10% above baseline",
    "pct_txn_degraded_p95": "% transactions with p95 5-10% above baseline",
    "max_pct_deviation_p95": "Worst p95 deviation (ratio)",
    "pct_txn_critical_avg_rt": "% transactions with avg RT >10% above baseline",
    "pct_txn_degraded_avg_rt": "% transactions with avg RT 5-10% above baseline",
    "max_pct_deviation_avg_rt": "Worst avg RT deviation (ratio)",
    "pct_txn_critical_error": "% transactions with error rate >10% above baseline",
    "pct_txn_degraded_error": "% transactions with error rate 5-10% above baseline",
    "max_pct_deviation_error": "Worst error rate deviation (ratio)",
    # NEW: Per-transaction error features
    "pct_txn_with_errors": "% transactions with any errors (>0%)",
    "pct_txn_complete_failure": "% transactions with 100% failure (catastrophic)",
    "max_error_percentage": "Worst absolute error rate across transactions (0-100)",
    "has_100pct_failure_txn": "1 if any transaction had 100% failure",
    "throughput_per_user": "Requests per second per user",
    "pct_deviation_throughput": "Throughput deviation from baseline (negative = worse)",
    "fail_ratio": "Proportion of failed requests (0.0-1.0)",
    "has_anomalous_transactions": "1 if any transactions have no baseline",
    "num_transactions": "Count of unique transactions",
    "test_type_encoded": "0=load_test, 1=endurance, 2=experimental",
}


@st.cache_resource
def load_model():
    """Load trained model and scaler."""
    model = joblib.load("models/model.pkl")
    scaler = joblib.load("models/scaler.pkl")
    return model, scaler


@st.cache_data
def load_test_cases():
    """Load test cases from JSON."""
    with open("test_cases/test_cases.json", "r") as f:
        return json.load(f)


def predict(model, scaler, features_dict):
    """Make prediction on feature dict."""
    X = np.array([features_dict[f] for f in MODEL_FEATURES]).reshape(1, -1)
    X_scaled = scaler.transform(X)
    prediction = model.predict(X_scaled)[0]
    
    try:
        proba = model.predict_proba(X_scaled)[0]
        confidence = max(proba) * 100
        proba_pass = proba[1] * 100
        proba_fail = proba[0] * 100
    except AttributeError:
        confidence = None
        proba_pass = None
        proba_fail = None
    
    return prediction, confidence, proba_pass, proba_fail


def get_feature_importance(model):
    """Get feature importance from model."""
    if hasattr(model, 'feature_importances_'):
        importance = model.feature_importances_
        return pd.DataFrame({
            'Feature': MODEL_FEATURES,
            'Importance': importance
        }).sort_values('Importance', ascending=False)
    return None


def plot_feature_importance(importance_df):
    """Plot feature importance bar chart."""
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.barplot(data=importance_df.head(10), x='Importance', y='Feature', palette='viridis', ax=ax)
    ax.set_title('Top 10 Most Important Features')
    ax.set_xlabel('Importance')
    return fig


def main():
    # Header
    st.title("🎯 Performance Test Classification Demo")
    st.markdown("**INFO 629 Assignment - Supervised Learning**")
    st.markdown("---")
    
    # Load model and test cases
    try:
        model, scaler = load_model()
        test_cases = load_test_cases()
    except FileNotFoundError as e:
        st.error(f"Error loading model or test cases: {e}")
        st.info("Make sure models/model.pkl, models/scaler.pkl, and test_cases/test_cases.json exist.")
        return
    
    # Sidebar
    st.sidebar.header("🔍 Select Test Case")
    
    # Mode selection
    mode = st.sidebar.radio(
        "Mode",
        ["Pre-computed Test Cases", "Manual Feature Input"],
        help="Choose pre-computed cases or enter custom features"
    )
    
    if mode == "Pre-computed Test Cases":
        # Test case selection
        case_names = [case['case_name'] for case in test_cases]
        selected_case_name = st.sidebar.selectbox(
            "Test Case",
            case_names,
            help="Select one of the 3 representative test cases"
        )
        
        # Get selected case
        selected_case = next(c for c in test_cases if c['case_name'] == selected_case_name)
        
        # Display case info
        st.sidebar.markdown("---")
        st.sidebar.markdown("**Test Information:**")
        st.sidebar.markdown(f"**Testplan:** `{selected_case['testplan']}`")
        st.sidebar.markdown(f"**Description:** {selected_case['description']}")
        st.sidebar.markdown(f"**Exit Code:** {selected_case['exit_code']}")
        
        features = selected_case['features']
        test_status_label = selected_case.get('test_status_label', selected_case.get('actual_label'))  # Support old key
        
    else:
        # Manual feature input
        st.sidebar.markdown("Enter custom feature values:")
        features = {}
        for feature in MODEL_FEATURES:
            default_val = 0.0
            features[feature] = st.sidebar.number_input(
                feature,
                value=default_val,
                format="%.4f",
                help=FEATURE_DESCRIPTIONS.get(feature, "")
            )
        test_status_label = None
    
    # Main content - Two columns
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("📊 Feature Values")
        
        # Create feature dataframe
        feature_df = pd.DataFrame([
            {
                "Feature": f,
                "Value": features[f],
                "Description": FEATURE_DESCRIPTIONS.get(f, "")
            }
            for f in MODEL_FEATURES
        ])
        
        # Highlight critical values
        def highlight_critical(row):
            feature = row['Feature']
            value = row['Value']
            
            # Define critical conditions
            is_critical = False
            if feature.startswith('pct_txn_critical') and value > 0:
                is_critical = True
            elif feature.startswith('max_pct_deviation') and value > 0.10:
                is_critical = True
            elif feature == 'fail_ratio' and value > 0.01:
                is_critical = True
            elif feature == 'has_anomalous_transactions' and value > 0:
                is_critical = True
            elif feature == 'pct_deviation_throughput' and value < -0.10:
                # Only highlight NEGATIVE deviation (below baseline)
                is_critical = True
            
            if is_critical:
                return ['background-color: #ffcccc'] * len(row)
            return [''] * len(row)
        
        styled_df = feature_df.style.apply(highlight_critical, axis=1)
        st.dataframe(styled_df, use_container_width=True, height=600)
        
        st.caption("⚠️ Red-highlighted rows indicate features exceeding critical thresholds")
    
    with col2:
        st.header("🤖 Prediction")
        
        # Predict button
        if st.button("🔮 Predict", type="primary", use_container_width=True):
            prediction, confidence, proba_pass, proba_fail = predict(model, scaler, features)
            
            # Display prediction
            if prediction == 1:
                st.success("### ✅ PASS")
            else:
                st.error("### ❌ FAIL")
            
            if confidence is not None:
                st.metric("Confidence", f"{confidence:.1f}%")
                
                # Probability bars
                st.markdown("**Class Probabilities:**")
                st.progress(proba_pass / 100, text=f"Pass: {proba_pass:.1f}%")
                st.progress(proba_fail / 100, text=f"Fail: {proba_fail:.1f}%")
            
            # Test status comparison (from exit code)
            if test_status_label is not None:
                st.markdown("---")
                st.markdown("**Test Status (Exit Code):**")
                if test_status_label == 1:
                    st.success("PASS (exit_code=1)")
                else:
                    st.error("FAIL (exit_code≠1)")
                
                # Alignment check
                if prediction == test_status_label:
                    st.success("✓ Model prediction matches automated test status")
                else:
                    st.warning("✗ Model prediction differs from automated test status")
            
            # Reason (if available)
            if mode == "Pre-computed Test Cases":
                st.markdown("---")
                st.markdown("**Reason:**")
                st.info(selected_case['reason'])
        
        # Feature importance
        st.markdown("---")
        st.header("📈 Feature Importance")
        
        importance_df = get_feature_importance(model)
        if importance_df is not None:
            st.dataframe(
                importance_df.head(5).style.format({'Importance': '{:.4f}'}),
                use_container_width=True,
                hide_index=True
            )
            
            with st.expander("View Full Feature Importance Chart"):
                fig = plot_feature_importance(importance_df)
                st.pyplot(fig)
    
    # Bottom section - Model info
    st.markdown("---")
    st.header("ℹ️ About This Model")
    
    info_col1, info_col2, info_col3 = st.columns(3)
    
    with info_col1:
        st.metric("Training Data", "709 runs")
        st.caption("2000-user tests from 2022-2026")
    
    with info_col2:
        st.metric("Test Accuracy", "97.2%")
        st.caption("On 142 unseen test runs")
    
    with info_col3:
        st.metric("Sign-off Accuracy", "100%")
        st.caption("On 11 production sign-off tests")
    
    with st.expander("📚 Model Methodology"):
        st.markdown("""
        **Approach:**
        - **Per-transaction baselines:** Each transaction compared to its own median from passing runs
        - **Normalized features:** All features are ratios/percentages (application-agnostic)
        - **Dynamic baselines:** Grouped by (test_type, num_clients, transaction_name)
        - **Model:** Random Forest with 200 estimators, max_depth=15, class_weight='balanced'
        
        **Key Insight:**
        The model learned that high p95 deviations alone don't cause failure if `fail_ratio ≈ 0`. 
        Many production tests had 60-85% of transactions critically slow but still passed because 
        requests didn't actually fail.
        
        **Failure Indicators:**
        - Multiple problems (slow + errors + low throughput) signal clear failure
        - `fail_ratio > 0.01` (>1% failures) is a strong failure signal
        - `pct_deviation_throughput < -0.10` (>10% below baseline) indicates capacity issues
        """)


if __name__ == "__main__":
    main()
