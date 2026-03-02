"""
predict.py — Standalone prediction script (professor deliverable).

Loads the exported trained model, scaler, and baselines, then runs 3 test cases
demonstrating pass/fail classification with structured reasons. No database
connection or training data required.

Usage:
    python -m src.predict
    python -m src.predict --test-cases test_cases/test_cases.json
    python -m src.predict --testplan LoadTest_20260227T060941Z
"""

import os
import sys
import json
import argparse
import numpy as np
import pandas as pd
import joblib

# Feature list must match training (from features.py)
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

# Threshold constants (must match training)
DEGRADED_THRESHOLD = 0.05
CRITICAL_THRESHOLD = 0.10


def load_artifacts(models_dir: str = "models"):
    """Load the trained model and scaler."""
    model_path = os.path.join(models_dir, "model.pkl")
    scaler_path = os.path.join(models_dir, "scaler.pkl")

    if not os.path.exists(model_path):
        raise FileNotFoundError(
            f"Model not found at {model_path}. Run 'python -m src.train' first."
        )
    if not os.path.exists(scaler_path):
        raise FileNotFoundError(
            f"Scaler not found at {scaler_path}. Run 'python -m src.train' first."
        )

    model = joblib.load(model_path)
    scaler = joblib.load(scaler_path)

    print(f"  Loaded model from {model_path}")
    print(f"  Loaded scaler from {scaler_path}")

    return model, scaler


def load_test_cases(path: str = "test_cases/test_cases.json") -> list[dict]:
    """Load test cases from JSON file."""
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Test cases not found at {path}. Run 'python -m src.train' first."
        )

    with open(path) as f:
        cases = json.load(f)

    print(f"  Loaded {len(cases)} test cases from {path}")
    return cases


def predict_testplan(model, scaler, testplan: str):
    """
    Query a specific testplan from the database, build features, and predict.
    """
    try:
        from src.extract import get_db_engine, extract_training_data
        from src.features import build_features
    except ImportError as e:
        print(f"Error: Database modules not available: {e}")
        print("Make sure src.extract and src.features are accessible.")
        sys.exit(1)
    
    print(f"\n{'='*60}")
    print(f"PREDICTING TESTPLAN: {testplan}")
    print(f"{'='*60}\n")
    
    # Query database
    engine = get_db_engine()
    query = f"""
    SELECT
        ts.testplan,
        ts.run_id,
        ts.name              AS transaction_name,
        ts.request_type,
        ts.requests          AS txn_requests,
        ts.failed            AS txn_failed,
        ts.error_percentage,
        ts.avg_response_time,
        ts.min_response_time,
        ts.max_response_time,
        ts.median_response_time,
        ts.perc_95,
        ts.perc_99,
        tr.exit_code,
        tr.num_clients,
        tr.rps_avg,
        tr.resp_time_avg,
        tr.fail_ratio,
        tr.build_version,
        tr.requests          AS total_requests,
        tr.end_time
    FROM test_summary ts
    JOIN testrun tr
        ON ts.testplan = tr.testplan
    WHERE ts.testplan = '{testplan}'
    ORDER BY ts.name
    """
    
    df_raw = pd.read_sql(query, engine)
    
    if len(df_raw) == 0:
        print(f"❌ No data found for testplan: {testplan}")
        print("   Check that the testplan exists in the database.")
        sys.exit(1)
    
    print(f"✓ Found {len(df_raw)} transaction rows for this testplan")
    print(f"  Exit Code: {df_raw['exit_code'].iloc[0]}")
    print(f"  Build Version: {df_raw['build_version'].iloc[0]}")
    print(f"  Num Clients: {df_raw['num_clients'].iloc[0]}")
    print(f"  End Time: {df_raw['end_time'].iloc[0]}\n")
    
    # Build features
    df_features, _ = build_features(df_raw, is_training=False)
    
    if len(df_features) == 0:
        print("❌ Feature engineering failed (no data after aggregation)")
        sys.exit(1)
    
    # Extract features
    X = df_features[MODEL_FEATURES].values
    X_scaled = scaler.transform(X)
    
    # Predict
    prediction = model.predict(X_scaled)[0]
    label = "PASS ✓" if prediction == 1 else "FAIL ✗"
    
    try:
        proba = model.predict_proba(X_scaled)[0]
        confidence = max(proba) * 100
        print(f"PREDICTION: {label} (confidence: {confidence:.1f}%)\n")
    except AttributeError:
        print(f"PREDICTION: {label}\n")
    
    # Generate reason
    features_dict = df_features[MODEL_FEATURES].iloc[0].to_dict()
    reason = generate_reason(features_dict)
    
    print(f"ACTUAL LABEL: {'PASS ✓' if df_raw['exit_code'].iloc[0] == 1 else 'FAIL ✗'}")
    print(f"  (exit_code={df_raw['exit_code'].iloc[0]})\n")
    
    print("REASON:")
    print(reason)
    print()
    
    print("KEY FEATURES:")
    for feat, val in features_dict.items():
        flag = "⚠️ " if (
            (feat.startswith("pct_txn_critical") and val > 0) or
            (feat.startswith("max_pct_deviation") and val > CRITICAL_THRESHOLD) or
            (feat == "fail_ratio" and val > 0.01) or
            (feat == "has_anomalous_transactions" and val > 0)
        ) else ""
        print(f"  {flag}{feat}: {val:.4f}")
    print()


def generate_reason(features: dict) -> str:
    """
    Generate a human-readable reason from feature values.

    Mirrors the logic in features.py but works from a dict of features.
    """
    reasons = []

    n_txns = features.get("num_transactions", 55)

    # P95
    pct_crit_p95 = features.get("pct_txn_critical_p95", 0)
    if pct_crit_p95 > 0:
        n_crit = int(pct_crit_p95 * n_txns)
        max_dev = features.get("max_pct_deviation_p95", 0) * 100
        reasons.append(f"p95 critical on {n_crit}/{int(n_txns)} txns (worst: +{max_dev:.0f}%)")

    # Avg RT
    pct_crit_rt = features.get("pct_txn_critical_avg_rt", 0)
    if pct_crit_rt > 0:
        n_crit = int(pct_crit_rt * n_txns)
        max_dev = features.get("max_pct_deviation_avg_rt", 0) * 100
        reasons.append(f"avg RT critical on {n_crit}/{int(n_txns)} txns (worst: +{max_dev:.0f}%)")

    # Error
    pct_crit_err = features.get("pct_txn_critical_error", 0)
    if pct_crit_err > 0:
        n_crit = int(pct_crit_err * n_txns)
        reasons.append(f"error rate critical on {n_crit}/{int(n_txns)} txns")

    # Throughput
    if features.get("pct_deviation_throughput", 0) < -DEGRADED_THRESHOLD:
        dev = abs(features["pct_deviation_throughput"]) * 100
        reasons.append(f"throughput_per_user {dev:.0f}% below baseline")

    # Fail ratio
    if features.get("fail_ratio", 0) > 0.01:
        reasons.append(f"fail_ratio={features['fail_ratio']:.4f} (>1%)")

    # Anomalous transactions
    if features.get("has_anomalous_transactions", 0) == 1:
        reasons.append("anomalous transactions detected (no baseline)")

    if not reasons:
        return "All transactions within baseline thresholds"

    return "; ".join(reasons)


def predict_and_explain(model, scaler, cases: list[dict]):
    """
    Run predictions on test cases and print results.
    """
    print("\n" + "=" * 70)
    print("  PERFORMANCE TEST CLASSIFICATION — PREDICTIONS")
    print("=" * 70)

    for i, case in enumerate(cases):
        print(f"\n{'─'*70}")
        print(f"  {case.get('case_name', f'Test Case {i+1}')}")
        print(f"  {case.get('description', '')}")
        if case.get("testplan"):
            print(f"  Source run: {case['testplan']}")
        print(f"{'─'*70}")

        # Build feature vector
        features = case["features"]
        X = pd.DataFrame([features])[MODEL_FEATURES]
        X_scaled = pd.DataFrame(
            scaler.transform(X), columns=MODEL_FEATURES
        )

        # Predict
        prediction = model.predict(X_scaled)[0]
        label = "PASS ✅" if prediction == 1 else "FAIL ❌"

        # Probability (if available)
        proba_str = ""
        if hasattr(model, "predict_proba"):
            proba = model.predict_proba(X_scaled)[0]
            proba_str = f"  (confidence: {max(proba)*100:.1f}%)"

        print(f"\n  Prediction:   {label}{proba_str}")

        # Test status label (if available)
        if "test_status_label" in case:
            test_status = "PASS" if case["test_status_label"] == 1 else "FAIL"
            match = "✓ Match" if prediction == case["test_status_label"] else "✗ MISMATCH"
            print(f"  Test Status:  {test_status}  [{match}]")

        if "exit_code" in case:
            print(f"  Exit code:    {case['exit_code']}")

        # Reason
        reason = generate_reason(features)
        print(f"  Reason:       {reason}")

        # Key features
        print(f"\n  Key Feature Values:")
        print(f"    {'Feature':<35s} {'Value':>10s}")
        print(f"    {'─'*47}")
        for feat in MODEL_FEATURES:
            val = features.get(feat, 0)
            # Highlight critical values
            flag = ""
            if "critical" in feat and val > 0:
                flag = " ⚠️"
            elif "deviation" in feat and abs(val) > CRITICAL_THRESHOLD:
                flag = " ⚠️"
            elif feat == "fail_ratio" and val > 0.01:
                flag = " ⚠️"
            print(f"    {feat:<35s} {val:>10.4f}{flag}")

    print(f"\n{'='*70}")
    print(f"  {len(cases)} test cases evaluated")
    print(f"{'='*70}\n")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Run predictions on test cases using the trained model"
    )
    parser.add_argument(
        "--test-cases", type=str, default="test_cases/test_cases.json",
        help="Path to test cases JSON file"
    )
    parser.add_argument(
        "--models-dir", type=str, default="models",
        help="Directory containing model.pkl and scaler.pkl"
    )
    parser.add_argument(
        "--testplan", type=str, default=None,
        help="Predict a specific testplan from the database"
    )
    args = parser.parse_args()

    model, scaler = load_artifacts(args.models_dir)
    
    if args.testplan:
        predict_testplan(model, scaler, args.testplan)
    else:
        cases = load_test_cases(args.test_cases)
        predict_and_explain(model, scaler, cases)


if __name__ == "__main__":
    main()
