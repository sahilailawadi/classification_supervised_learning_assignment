"""
features.py — Feature engineering for performance test classification.

Takes the raw extracted DataFrame (one row per transaction per run) and produces
model-ready features (one row per test run) with normalized % deviation metrics.

Pipeline:
    1. Derive test_type from build_version
    2. Compute per-transaction baselines from passing training runs
    3. Compute % deviation features per transaction
    4. Aggregate to per-run feature vectors
    5. Create binary label

Usage:
    from src.features import build_features, compute_baselines
"""

import re
import numpy as np
import pandas as pd
import joblib


# ---------------------------------------------------------------------------
# 1. Test type classification (from build_version)
# ---------------------------------------------------------------------------

def derive_test_type(build_version: str) -> str:
    """
    Classify a test run by its build_version naming pattern.

    Returns:
        'endurance'    — Chat_Endurance_*
        'load_test'    — Chat_LoadTest_*, Chat_Loadtest_*, Chat Web App Deploy_*,
                         Chat - Function - CD_*
        'experimental' — BAPIS_*, Mercury_DB_*, db_test* (should already be excluded)
        'unknown'      — anything else
    """
    if not build_version or pd.isna(build_version):
        return "load_test"  # default: treat empty build_version as load_test

    bv = str(build_version).strip()

    if re.match(r"(?i)chat[_ ]endurance", bv):
        return "endurance"
    elif re.match(r"(?i)(chat[_ ]load|chat web app deploy|chat - function)", bv):
        return "load_test"
    elif re.match(r"(?i)(bapis|mercury_db|db_test)", bv):
        return "experimental"
    else:
        return "load_test"  # default for unrecognized patterns


def add_test_type(df: pd.DataFrame) -> pd.DataFrame:
    """Add test_type column derived from build_version."""
    df = df.copy()
    df["test_type"] = df["build_version"].apply(derive_test_type)
    return df


# ---------------------------------------------------------------------------
# 2. Baseline computation
# ---------------------------------------------------------------------------

def compute_baselines(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute per-transaction baselines from PASSING runs only.

    Baselines are grouped by (test_type, num_clients, transaction_name) and
    computed as the MEDIAN of each metric across passing runs (exit_code == 1).

    Args:
        df: Raw extracted DataFrame with test_type column already added.
            Must contain ONLY training data (not test set).

    Returns:
        DataFrame with columns:
            test_type, num_clients, transaction_name,
            baseline_median_p95, baseline_median_avg_rt,
            baseline_median_error_pct, baseline_median_throughput_per_user
    """
    passing = df[df["exit_code"] == 1].copy()

    if len(passing) == 0:
        raise ValueError("No passing runs (exit_code=1) found in training data. "
                         "Cannot compute baselines.")

    # Per-transaction baselines
    txn_baselines = (
        passing
        .groupby(["test_type", "num_clients", "transaction_name"])
        .agg(
            baseline_median_p95=("perc_95", "median"),
            baseline_median_avg_rt=("avg_response_time", "median"),
            baseline_median_error_pct=("error_percentage", "median"),
            baseline_count=("perc_95", "count"),  # how many runs contributed
        )
        .reset_index()
    )

    # Per-run throughput baseline (run-level, not per-transaction)
    # Compute throughput_per_user for each passing run, then median per group
    run_level = (
        passing
        .drop_duplicates(subset=["testplan"])
        [["testplan", "test_type", "num_clients", "rps_avg"]]
        .copy()
    )
    run_level["throughput_per_user"] = run_level["rps_avg"] / run_level["num_clients"]

    throughput_baselines = (
        run_level
        .groupby(["test_type", "num_clients"])
        .agg(baseline_median_throughput_per_user=("throughput_per_user", "median"))
        .reset_index()
    )

    # Merge throughput baseline into transaction baselines
    txn_baselines = txn_baselines.merge(
        throughput_baselines, on=["test_type", "num_clients"], how="left"
    )

    print(f"  Computed baselines for {len(txn_baselines):,} "
          f"(test_type, num_clients, transaction) groups")
    print(f"  From {passing['testplan'].nunique():,} passing runs")

    return txn_baselines


# ---------------------------------------------------------------------------
# 3. Per-transaction % deviation features
# ---------------------------------------------------------------------------

def _pct_deviation(actual, baseline):
    """
    Compute percentage deviation: (actual - baseline) / baseline.

    Returns 0.0 if baseline is 0 or NaN (cannot compute deviation).
    """
    if baseline is None or pd.isna(baseline) or baseline == 0:
        return 0.0
    return (actual - baseline) / baseline


def add_deviation_features(df: pd.DataFrame, baselines: pd.DataFrame) -> pd.DataFrame:
    """
    Merge baselines and compute % deviation columns per transaction row.

    Adds columns:
        pct_deviation_p95, pct_deviation_avg_rt, pct_deviation_error_pct
    """
    # Make copies to avoid modifying original DataFrames
    df = df.copy()
    baselines = baselines.copy()
    
    # Convert dtypes to ensure compatibility before merge
    # (baselines may have StringDtype from pickle, db queries return object)
    # Convert test_type and transaction_name to string
    df["test_type"] = df["test_type"].astype(str)
    df["transaction_name"] = df["transaction_name"].astype(str)
    baselines["test_type"] = baselines["test_type"].astype(str)
    baselines["transaction_name"] = baselines["transaction_name"].astype(str)
    
    # Ensure num_clients is numeric (not string) for both
    df["num_clients"] = pd.to_numeric(df["num_clients"], errors='coerce')
    baselines["num_clients"] = pd.to_numeric(baselines["num_clients"], errors='coerce')
    
    df = df.merge(
        baselines,
        on=["test_type", "num_clients", "transaction_name"],
        how="left"
    )

    # Flag transactions with no baseline (only appear in failing runs)
    df["has_baseline"] = df["baseline_median_p95"].notna()

    # Compute deviations (vectorized)
    df["pct_deviation_p95"] = df.apply(
        lambda r: _pct_deviation(r["perc_95"], r["baseline_median_p95"]), axis=1
    )
    df["pct_deviation_avg_rt"] = df.apply(
        lambda r: _pct_deviation(r["avg_response_time"], r["baseline_median_avg_rt"]), axis=1
    )
    df["pct_deviation_error_pct"] = df.apply(
        lambda r: _pct_deviation(r["error_percentage"], r["baseline_median_error_pct"]), axis=1
    )

    return df


# ---------------------------------------------------------------------------
# 4. Aggregate to per-run feature vectors
# ---------------------------------------------------------------------------

# Threshold constants (from copilot-instructions.md §8)
DEGRADED_THRESHOLD = 0.05   # 5% above baseline
CRITICAL_THRESHOLD = 0.10   # 10% above baseline


def _classify_deviation(pct_dev):
    """Classify a deviation as good/degraded/critical."""
    if pct_dev > CRITICAL_THRESHOLD:
        return "critical"
    elif pct_dev > DEGRADED_THRESHOLD:
        return "degraded"
    else:
        return "good"


def aggregate_to_run_level(df: pd.DataFrame, baselines: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate per-transaction rows into one feature vector per test run.

    Args:
        df: DataFrame with deviation features (output of add_deviation_features).
        baselines: Baselines DataFrame (for throughput baseline lookup).

    Returns:
        DataFrame with one row per run, containing:
            - Proportion of transactions in each health band per dimension
            - Max deviation per dimension
            - Throughput per user + its deviation
            - fail_ratio, has_anomalous_transactions, num_transactions
            - test_type, num_clients, label_pass_fail
    """
    runs = []

    for (testplan,), group in df.groupby(["testplan"]):
        row = {"testplan": testplan}

        # --- Run-level metadata (same for all txns in this run) ---
        first = group.iloc[0]
        row["exit_code"] = first["exit_code"]
        row["num_clients"] = first["num_clients"]
        row["rps_avg"] = first["rps_avg"]
        row["fail_ratio"] = first["fail_ratio"]
        row["build_version"] = first["build_version"]
        row["test_type"] = first["test_type"]
        row["total_requests"] = first["total_requests"]

        # --- Label ---
        row["label_pass_fail"] = 1 if first["exit_code"] == 1 else 0

        # --- Throughput per user ---
        row["throughput_per_user"] = (
            first["rps_avg"] / first["num_clients"]
            if first["num_clients"] > 0 else 0
        )

        # Get throughput baseline for this test_type + num_clients
        tp_baseline = baselines[
            (baselines["test_type"] == first["test_type"]) &
            (baselines["num_clients"] == first["num_clients"])
        ]["baseline_median_throughput_per_user"]

        if len(tp_baseline) > 0 and tp_baseline.iloc[0] > 0:
            row["pct_deviation_throughput"] = _pct_deviation(
                row["throughput_per_user"], tp_baseline.iloc[0]
            )
        else:
            row["pct_deviation_throughput"] = 0.0

        # --- Per-transaction aggregation (only rows with baselines) ---
        with_baseline = group[group["has_baseline"]]
        n_txns = len(with_baseline)
        row["num_transactions"] = len(group)
        row["num_transactions_with_baseline"] = n_txns

        if n_txns > 0:
            # P95 dimension
            p95_devs = with_baseline["pct_deviation_p95"]
            row["pct_txn_critical_p95"] = (p95_devs > CRITICAL_THRESHOLD).sum() / n_txns
            row["pct_txn_degraded_p95"] = (
                (p95_devs > DEGRADED_THRESHOLD) & (p95_devs <= CRITICAL_THRESHOLD)
            ).sum() / n_txns
            row["max_pct_deviation_p95"] = p95_devs.max()

            # Avg RT dimension
            rt_devs = with_baseline["pct_deviation_avg_rt"]
            row["pct_txn_critical_avg_rt"] = (rt_devs > CRITICAL_THRESHOLD).sum() / n_txns
            row["pct_txn_degraded_avg_rt"] = (
                (rt_devs > DEGRADED_THRESHOLD) & (rt_devs <= CRITICAL_THRESHOLD)
            ).sum() / n_txns
            row["max_pct_deviation_avg_rt"] = rt_devs.max()

            # Error percentage dimension
            err_devs = with_baseline["pct_deviation_error_pct"]
            row["pct_txn_critical_error"] = (err_devs > CRITICAL_THRESHOLD).sum() / n_txns
            row["pct_txn_degraded_error"] = (
                (err_devs > DEGRADED_THRESHOLD) & (err_devs <= CRITICAL_THRESHOLD)
            ).sum() / n_txns
            row["max_pct_deviation_error"] = err_devs.max()
        else:
            # No baseline data — set to 0
            for prefix in ["p95", "avg_rt", "error"]:
                row[f"pct_txn_critical_{prefix}"] = 0.0
                row[f"pct_txn_degraded_{prefix}"] = 0.0
                row[f"max_pct_deviation_{prefix}"] = 0.0

        # --- Anomalous transactions (those without a baseline) ---
        without_baseline = group[~group["has_baseline"]]
        row["has_anomalous_transactions"] = 1 if len(without_baseline) > 0 else 0
        row["num_anomalous_transactions"] = len(without_baseline)

        # --- Test type encoded ---
        row["test_type_encoded"] = 1 if first["test_type"] == "endurance" else 0

        runs.append(row)

    run_df = pd.DataFrame(runs)
    print(f"  Aggregated to {len(run_df):,} run-level feature vectors")
    print(f"    Pass: {(run_df['label_pass_fail'] == 1).sum():,}  "
          f"Fail: {(run_df['label_pass_fail'] == 0).sum():,}")

    return run_df


# ---------------------------------------------------------------------------
# 5. Feature list (columns used by the model)
# ---------------------------------------------------------------------------

# These are the columns fed to the classifier — no absolute values, all ratios
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
    "throughput_per_user",
    "pct_deviation_throughput",
    "fail_ratio",
    "has_anomalous_transactions",
    "num_transactions",
    "test_type_encoded",
]


# ---------------------------------------------------------------------------
# 6. Full pipeline
# ---------------------------------------------------------------------------

def build_features(
    df_raw: pd.DataFrame,
    baselines: pd.DataFrame = None,
    is_training: bool = True,
    baselines_path: str = "models/baselines.pkl",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Full feature engineering pipeline.

    Args:
        df_raw: Raw extracted DataFrame from extract.py
        baselines: Pre-computed baselines (if None, computed from df_raw)
        is_training: If True, compute baselines from this data;
                     if False, load from baselines_path
        baselines_path: Path to save/load baselines

    Returns:
        (run_level_df, baselines_df)
    """
    print("\n=== Feature Engineering Pipeline ===\n")

    # Step 1: Add test_type
    print("Step 1: Deriving test_type from build_version...")
    df = add_test_type(df_raw)
    test_type_counts = df.drop_duplicates("testplan")["test_type"].value_counts()
    for tt, count in test_type_counts.items():
        print(f"  {tt}: {count} runs")

    # Exclude experimental (should already be excluded by SQL, but double-check)
    before = df["testplan"].nunique()
    df = df[df["test_type"] != "experimental"]
    after = df["testplan"].nunique()
    if before != after:
        print(f"  Excluded {before - after} experimental runs")

    # Step 2: Baselines
    if is_training:
        print("\nStep 2: Computing baselines from passing training runs...")
        baselines = compute_baselines(df)
        joblib.dump(baselines, baselines_path)
        print(f"  Saved baselines to {baselines_path}")
    else:
        if baselines is None:
            print(f"\nStep 2: Loading baselines from {baselines_path}...")
            baselines = joblib.load(baselines_path)
            print(f"  Loaded {len(baselines):,} baseline groups")

    # Step 3: Per-transaction deviations
    print("\nStep 3: Computing per-transaction % deviations...")
    df = add_deviation_features(df, baselines)
    n_no_baseline = (~df["has_baseline"]).sum()
    if n_no_baseline > 0:
        print(f"  {n_no_baseline:,} transaction rows have no baseline "
              f"(appear only in failing runs)")

    # Step 4: Aggregate to run level
    print("\nStep 4: Aggregating to per-run feature vectors...")
    run_df = aggregate_to_run_level(df, baselines)

    return run_df, baselines


def generate_reason(row: pd.Series, df_txn: pd.DataFrame = None) -> str:
    """
    Generate a human-readable reason string for a prediction.

    Args:
        row: A single run-level feature row
        df_txn: Optional per-transaction DataFrame for detailed breakdown

    Returns:
        Reason string like "Fail — p95 critical on 12/55 txns, throughput 40% below baseline"
    """
    reasons = []

    # P95
    if row.get("pct_txn_critical_p95", 0) > 0:
        n_crit = int(row["pct_txn_critical_p95"] * row.get("num_transactions_with_baseline", row.get("num_transactions", 55)))
        total = int(row.get("num_transactions_with_baseline", row.get("num_transactions", 55)))
        max_dev = row.get("max_pct_deviation_p95", 0) * 100
        reasons.append(f"p95 critical on {n_crit}/{total} txns (worst: +{max_dev:.0f}%)")

    # Avg RT
    if row.get("pct_txn_critical_avg_rt", 0) > 0:
        n_crit = int(row["pct_txn_critical_avg_rt"] * row.get("num_transactions_with_baseline", row.get("num_transactions", 55)))
        total = int(row.get("num_transactions_with_baseline", row.get("num_transactions", 55)))
        max_dev = row.get("max_pct_deviation_avg_rt", 0) * 100
        reasons.append(f"avg RT critical on {n_crit}/{total} txns (worst: +{max_dev:.0f}%)")

    # Error
    if row.get("pct_txn_critical_error", 0) > 0:
        n_crit = int(row["pct_txn_critical_error"] * row.get("num_transactions_with_baseline", row.get("num_transactions", 55)))
        total = int(row.get("num_transactions_with_baseline", row.get("num_transactions", 55)))
        reasons.append(f"error rate critical on {n_crit}/{total} txns")

    # Throughput
    if row.get("pct_deviation_throughput", 0) < -DEGRADED_THRESHOLD:
        dev = abs(row["pct_deviation_throughput"]) * 100
        reasons.append(f"throughput_per_user {dev:.0f}% below baseline")

    # Fail ratio
    if row.get("fail_ratio", 0) > 0.01:
        reasons.append(f"fail_ratio={row['fail_ratio']:.4f} (>1%)")

    # Anomalous transactions
    if row.get("has_anomalous_transactions", 0) == 1:
        n = row.get("num_anomalous_transactions", 0)
        reasons.append(f"{int(n)} anomalous txns (no baseline)")

    if not reasons:
        return "Pass — all transactions within baseline thresholds"

    return "Fail — " + "; ".join(reasons)
