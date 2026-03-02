"""
extract.py — Data extraction from Postgres for performance test classification.

Connects to the Locust performance test database, runs the primary JOIN query
(test_summary ⟕ testrun), applies exclusion filters, and returns a clean DataFrame.
Also provides a validation query to check class distribution before training.

Usage:
    # As a module
    from src.extract import extract_training_data, run_validation_query

    # As a standalone script
    python -m src.extract --validate   # Run validation query only
    python -m src.extract --extract    # Extract and save to CSV
"""

import os
import sys
import argparse
from urllib.parse import quote_plus
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Database connection
# ---------------------------------------------------------------------------

def get_db_engine():
    """Create a SQLAlchemy engine from .env credentials."""
    load_dotenv()

    required_vars = ["DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD"]
    missing = [v for v in required_vars if not os.getenv(v)]
    if missing:
        raise EnvironmentError(
            f"Missing required environment variables: {', '.join(missing)}. "
            f"Copy .env.example to .env and fill in your Postgres credentials."
        )

    # URL-encode credentials to handle special characters like @ in password
    user = quote_plus(os.getenv('DB_USER'))
    password = quote_plus(os.getenv('DB_PASSWORD'))
    host = os.getenv('DB_HOST')
    port = os.getenv('DB_PORT')
    dbname = os.getenv('DB_NAME')
    
    url = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
    return create_engine(url)


# ---------------------------------------------------------------------------
# Exclusion filters (applied in SQL WHERE clause)
# ---------------------------------------------------------------------------

EXCLUSION_WHERE = """
    tr.exit_code IS NOT NULL
    AND tr.exit_code != 0              -- exclude incomplete runs
    AND COALESCE(tr.rps_avg, 0) > 0    -- exclude zero-traffic runs
    AND tr.num_clients = 2000          -- REQUIREMENT: only 2000-user tests
    AND COALESCE(tr.build_version, '') NOT LIKE 'BAPIS%%'
    AND COALESCE(tr.build_version, '') NOT LIKE 'Mercury_DB%%'
    AND COALESCE(tr.build_version, '') NOT LIKE 'db_test%%'
"""


# ---------------------------------------------------------------------------
# Primary extraction query
# ---------------------------------------------------------------------------

PRIMARY_QUERY = f"""
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
WHERE {EXCLUSION_WHERE}
ORDER BY tr.end_time DESC, ts.testplan, ts.name
"""


# ---------------------------------------------------------------------------
# Validation queries
# ---------------------------------------------------------------------------

VALIDATION_CLASS_DIST = f"""
SELECT
    tr.exit_code,
    COUNT(DISTINCT tr.testplan) AS run_count
FROM testrun tr
WHERE {EXCLUSION_WHERE}
GROUP BY tr.exit_code
ORDER BY tr.exit_code
"""

VALIDATION_COVERAGE = f"""
SELECT
    COUNT(DISTINCT tr.testplan) AS total_usable_runs,
    COUNT(DISTINCT CASE
        WHEN ts.testplan IS NOT NULL THEN tr.testplan
    END) AS runs_with_summary
FROM testrun tr
LEFT JOIN test_summary ts
    ON ts.testplan = tr.testplan
WHERE {EXCLUSION_WHERE}
"""

VALIDATION_TEST_TYPES = f"""
SELECT
    tr.build_version,
    tr.num_clients,
    tr.exit_code,
    tr.rps_avg,
    tr.resp_time_avg,
    tr.fail_ratio,
    tr.requests
FROM testrun tr
WHERE {EXCLUSION_WHERE}
ORDER BY tr.end_time DESC
LIMIT 50
"""

VALIDATION_MISSING_SUMMARY = f"""
SELECT
    tr.testplan,
    tr.end_time,
    tr.exit_code,
    tr.num_clients,
    tr.build_version,
    tr.rps_avg,
    tr.requests
FROM testrun tr
LEFT JOIN test_summary ts
    ON ts.testplan = tr.testplan
WHERE {EXCLUSION_WHERE}
    AND ts.testplan IS NULL
ORDER BY tr.end_time DESC
"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_training_data(engine=None):
    """
    Extract the full training dataset from the database.

    Returns:
        pd.DataFrame with one row per transaction per test run,
        including testrun metadata (exit_code, num_clients, etc.)
    """
    if engine is None:
        engine = get_db_engine()

    print("Extracting training data from database...")
    df = pd.read_sql(PRIMARY_QUERY, engine)
    print(f"  Extracted {len(df):,} rows "
          f"({df['testplan'].nunique():,} distinct runs)")

    # Exclude the SignalR_Analysis meta-row (always perc_95=0, not a real transaction)
    before = len(df)
    df = df[df["transaction_name"] != "SignalR_Analysis"]
    excluded = before - len(df)
    if excluded > 0:
        print(f"  Excluded {excluded:,} SignalR_Analysis meta-rows")

    # Basic sanity checks
    _print_summary(df)
    return df


def run_validation_query(engine=None):
    """
    Run validation queries to check data quality before training.
    Prints class distribution, coverage, and sample of recent test types.
    """
    if engine is None:
        engine = get_db_engine()

    print("=" * 60)
    print("VALIDATION: Class Distribution (exit_code)")
    print("=" * 60)
    df_dist = pd.read_sql(VALIDATION_CLASS_DIST, engine)
    print(df_dist.to_string(index=False))
    total_runs = df_dist["run_count"].sum()
    for _, row in df_dist.iterrows():
        pct = row["run_count"] / total_runs * 100
        label = {1: "Pass", 2: "Fail(TPS)", 3: "Fail(RT)", 4: "Fail(FailRatio)"}
        print(f"  exit_code={int(row['exit_code'])}: "
              f"{row['run_count']} runs ({pct:.1f}%) — {label.get(int(row['exit_code']), '?')}")
    print(f"  TOTAL usable runs: {total_runs}")

    print()
    print("=" * 60)
    print("VALIDATION: test_summary Coverage")
    print("=" * 60)
    df_cov = pd.read_sql(VALIDATION_COVERAGE, engine)
    print(df_cov.to_string(index=False))
    total = df_cov["total_usable_runs"].iloc[0]
    with_summary = df_cov["runs_with_summary"].iloc[0]
    without = total - with_summary
    print(f"  {with_summary}/{total} runs have test_summary data "
          f"({without} runs missing → cannot use for per-txn features)")

    print()
    print("=" * 60)
    print("VALIDATION: Runs Missing test_summary Data")
    print("=" * 60)
    df_missing = pd.read_sql(VALIDATION_MISSING_SUMMARY, engine)
    print(f"Found {len(df_missing)} runs without test_summary data:")
    print(df_missing.to_string(index=False))

    print()
    print("=" * 60)
    print("VALIDATION: Recent 50 Runs (test type inspection)")
    print("=" * 60)
    df_types = pd.read_sql(VALIDATION_TEST_TYPES, engine)
    print(df_types.to_string(index=False))

    return {
        "class_distribution": df_dist,
        "coverage": df_cov,
        "recent_runs": df_types,
        "missing_summary": df_missing,
    }


def check_testplan_join(engine, testplan):
    """
    Diagnostic: check why a specific testplan isn't joining with test_summary.
    """
    print(f"\n{'='*60}")
    print(f"DIAGNOSTIC: Checking testplan {testplan}")
    print(f"{'='*60}\n")
    
    # Check testrun
    query_tr = f"""
    SELECT id, testplan, exit_code, num_clients, build_version, rps_avg, end_time
    FROM testrun
    WHERE testplan = '{testplan}'
    """
    df_tr = pd.read_sql(query_tr, engine)
    print("testrun records:")
    print(df_tr.to_string(index=False))
    
    # Check test_summary
    query_ts = f"""
    SELECT DISTINCT testplan, run_id
    FROM test_summary
    WHERE testplan = '{testplan}'
    LIMIT 5
    """
    df_ts = pd.read_sql(query_ts, engine)
    print(f"\ntest_summary records (showing distinct testplan, run_id):")
    print(df_ts.to_string(index=False))
    
    # Check JOIN
    query_join = f"""
    SELECT 
        tr.testplan,
        tr.id AS testrun_id,
        ts.run_id AS test_summary_run_id,
        COUNT(*) AS matching_rows
    FROM testrun tr
    LEFT JOIN test_summary ts
        ON ts.testplan = tr.testplan
    WHERE tr.testplan = '{testplan}'
    GROUP BY tr.testplan, tr.id, ts.run_id
    """
    df_join = pd.read_sql(query_join, engine)
    print(f"\nJOIN result (testrun.id vs test_summary.run_id):")
    print(df_join.to_string(index=False))
    
    if df_ts['run_id'].iloc[0] != df_tr['id'].iloc[0] if len(df_ts) > 0 and len(df_tr) > 0 else False:
        print(f"\n⚠️  MISMATCH DETECTED:")
        print(f"   testrun.id = {df_tr['id'].iloc[0]}")
        print(f"   test_summary.run_id = {df_ts['run_id'].iloc[0]}")
        print(f"   These don't match, so the JOIN fails!")


def _print_summary(df):
    """Print a quick summary of the extracted data."""
    n_runs = df["testplan"].nunique()
    n_txns = df["transaction_name"].nunique()
    n_pass = df[df["exit_code"] == 1]["testplan"].nunique()
    n_fail = df[df["exit_code"] != 1]["testplan"].nunique()
    print(f"\n  Summary:")
    print(f"    Total rows:          {len(df):,}")
    print(f"    Distinct runs:       {n_runs:,}")
    print(f"    Distinct txn names:  {n_txns:,}")
    print(f"    Pass (exit_code=1):  {n_pass:,} runs")
    print(f"    Fail (exit_code≠1):  {n_fail:,} runs")
    print(f"    Pass/Fail ratio:     {n_pass/max(n_fail,1):.1f}:1")
    print(f"    Avg txns per run:    {len(df)/max(n_runs,1):.0f}")
    print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Extract performance test data from Postgres"
    )
    parser.add_argument(
        "--validate", action="store_true",
        help="Run validation queries only (class distribution, coverage)"
    )
    parser.add_argument(
        "--extract", action="store_true",
        help="Extract full training data and save to data_exports/"
    )
    parser.add_argument(
        "--check-testplan", type=str, default=None,
        help="Check JOIN diagnostic for a specific testplan"
    )
    args = parser.parse_args()

    if not args.validate and not args.extract and not args.check_testplan:
        parser.print_help()
        sys.exit(1)

    engine = get_db_engine()

    if args.check_testplan:
        check_testplan_join(engine, args.check_testplan)

    if args.validate:
        run_validation_query(engine)

    if args.extract:
        df = extract_training_data(engine)
        os.makedirs("data_exports", exist_ok=True)
        out_path = "data_exports/training_data.csv"
        df.to_csv(out_path, index=False)
        print(f"Saved to {out_path}")


if __name__ == "__main__":
    main()
