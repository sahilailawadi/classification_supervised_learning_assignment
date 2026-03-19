#!/usr/bin/env python3
"""
Export anonymized test data for academic submission.

This script reads test runs from training_data.csv, anonymizes all
sensitive information, and exports to Excel format safe for sharing with
professors and GPT-4.

Usage:
    python scripts/export_anonymized_data.py [--num-tests 75] [--output academic_demo_data.xlsx]
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, Tuple

import pandas as pd

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent


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


def extract_from_csv(limit: int = 75) -> pd.DataFrame:
    """
    Extract diverse set of tests from training_data.csv.
    
    Retrieves a balanced mix of PASS/FAIL results from 2000-user tests.
    
    Args:
        limit: Maximum number of tests to extract
        
    Returns:
        DataFrame with test runs
    """
    csv_path = PROJECT_ROOT / "data_exports" / "training_data.csv"
    
    if not csv_path.exists():
        raise FileNotFoundError(f"training_data.csv not found at {csv_path}")
    
    print(f"📂 Loading from {csv_path.name}...")
    df = pd.read_csv(csv_path)
    
    # Filter to 2000-user tests only
    df = df[df['num_clients'] == 2000].copy()
    
    # Get unique testplans with their exit codes
    print(f"📊 Selecting {limit} diverse tests...")
    testplans = df.groupby(['testplan', 'exit_code']).first().reset_index()
    
    # Balance PASS/FAIL tests
    # exit_code 1 = PASS, exit_code 2/3/4 = FAIL
    pass_tests = testplans[testplans['exit_code'] == 1].sample(
        n=min(limit // 2, len(testplans[testplans['exit_code'] == 1])), 
        random_state=42
    )
    fail_tests = testplans[testplans['exit_code'].isin([2, 3, 4])].sample(
        n=min(limit // 2, len(testplans[testplans['exit_code'].isin([2, 3, 4])])), 
        random_state=42
    )
    
    selected_testplans = pd.concat([pass_tests, fail_tests])['testplan'].tolist()
    
    # Get all rows for selected testplans
    result = df[df['testplan'].isin(selected_testplans)].copy()
    
    print(f"✅ Selected {len(selected_testplans)} tests ({len(pass_tests)} PASS, {len(fail_tests)} FAIL)")
    print(f"   Total rows: {len(result)} (includes all transactions per test)")
    
    return result


def anonymize_testplan(testplan: str, index: int) -> str:
    """
    Convert real testplan ID to generic identifier.
    
    Examples:
        LoadTest_20230309T174858Z -> LoadTest_001
        EnduranceTest_20230310T090000Z -> EnduranceTest_002
    
    Args:
        testplan: Original testplan ID
        index: Sequential index for anonymized ID
        
    Returns:
        Anonymized testplan ID
    """
    # Try to extract test type from testplan name
    testplan_lower = testplan.lower()
    
    if 'load' in testplan_lower:
        prefix = 'LoadTest'
    elif 'endurance' in testplan_lower:
        prefix = 'EnduranceTest'
    elif 'spike' in testplan_lower:
        prefix = 'SpikeTest'
    elif 'stress' in testplan_lower:
        prefix = 'StressTest'
    elif 'soak' in testplan_lower:
        prefix = 'SoakTest'
    else:
        prefix = 'PerformanceTest'
    
    return f"{prefix}_{index:03d}"


def anonymize_version(version: str) -> str:
    """
    Convert real version to generic version.
    
    Examples:
        2.3.1-rc5 -> v1.0
        2.3.2 -> v1.1
        
    Uses hash-based mapping to maintain consistency.
    
    Args:
        version: Original version string
        
    Returns:
        Anonymized version string
    """
    if pd.isna(version) or version == '':
        return 'v0.0'
    
    # Simple hash-based mapping
    version_hash = abs(hash(str(version))) % 100
    major = version_hash // 10
    minor = version_hash % 10
    return f"v{major}.{minor}"


def create_transaction_mapping(df: pd.DataFrame) -> Dict[str, str]:
    """
    Create mapping of real transaction names to sanitized names.
    
    Categorizes transactions into groups for more realistic sanitized names:
    - API endpoints (/path/endpoint) -> API_001, API_002, etc.
    - Authentication paths (AuthPath_*) -> Auth_001, Auth_002, etc.
    - BAPIS operations (BAPIS_*) -> Service_001, Service_002, etc.
    - Callbacks (*Callback) -> Callback_001, Callback_002, etc.
    - Configuration endpoints -> Config_001, Config_002, etc.
    
    Args:
        df: DataFrame with 'transaction_name' column
        
    Returns:
        Dict mapping original names to sanitized names
    """
    unique_transactions = sorted(df['transaction_name'].unique())
    mapping = {}
    
    # Categorize transactions
    api_counter = 1
    auth_counter = 1
    service_counter = 1
    callback_counter = 1
    config_counter = 1
    other_counter = 1
    
    for original in unique_transactions:
        if original.startswith('/'):
            # API endpoint
            mapping[original] = f"API_{api_counter:03d}"
            api_counter += 1
        elif original.startswith('AuthPath_') or 'Auth' in original:
            # Authentication flow
            mapping[original] = f"Auth_{auth_counter:03d}"
            auth_counter += 1
        elif original.startswith('BAPIS_'):
            # Service operation
            mapping[original] = f"Service_{service_counter:03d}"
            service_counter += 1
        elif original.endswith('Callback'):
            # Callback endpoint
            mapping[original] = f"Callback_{callback_counter:03d}"
            callback_counter += 1
        elif 'configuration' in original.lower() or 'config' in original.lower():
            # Configuration endpoint
            mapping[original] = f"Config_{config_counter:03d}"
            config_counter += 1
        else:
            # Other
            mapping[original] = f"Transaction_{other_counter:03d}"
            other_counter += 1
    
    return mapping


def anonymize_text(text: str) -> str:
    """
    Remove sensitive information from free text fields.
    
    Sanitizes:
    - URLs and endpoints
    - IP addresses
    - Company-specific names
    - Service names
    - Internal system names
    
    Args:
        text: Original text
        
    Returns:
        Sanitized text
    """
    if pd.isna(text) or text == '':
        return text
    
    text = str(text)
    
    # Remove URLs
    text = re.sub(r'https?://[^\s]+', 'http://example.com', text)
    
    # Remove IP addresses
    text = re.sub(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', '10.0.0.1', text)
    
    # Remove Comcast-specific terms
    text = re.sub(r'Comcast|CMCSA|Xfinity|xfinity', '<Company>', text, flags=re.IGNORECASE)
    
    # Remove specific service names (add more as needed)
    text = re.sub(r'Phoenix|Hydra|Zeus|Athena|Apollo', '<Service>', text, flags=re.IGNORECASE)
    
    # Remove common internal system patterns
    text = re.sub(r'prod-\w+|staging-\w+|dev-\w+', '<Environment>', text, flags=re.IGNORECASE)
    
    return text


def anonymize_dataframe(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, str], Dict[str, str]]:
    """
    Anonymize all sensitive fields in dataframe.
    
    This is the main anonymization function that processes all columns
    and creates mapping files for reference.
    
    Args:
        df: Original dataframe with sensitive data
        
    Returns:
        Tuple of (anonymized_df, testplan_mapping, transaction_mapping)
    """
    print("\n🔒 Anonymizing sensitive data...")
    df = df.copy()
    testplan_mapping = {}
    
    # 1. Anonymize transaction names FIRST (most important for security)
    print("  - Anonymizing transaction names...")
    transaction_mapping = create_transaction_mapping(df)
    df['transaction_name'] = df['transaction_name'].map(transaction_mapping)
    print(f"    ✓ Anonymized {len(transaction_mapping)} unique transaction names")
    print(f"      API endpoints: {sum(1 for v in transaction_mapping.values() if v.startswith('API_'))}")
    print(f"      Auth flows: {sum(1 for v in transaction_mapping.values() if v.startswith('Auth_'))}")
    print(f"      Services: {sum(1 for v in transaction_mapping.values() if v.startswith('Service_'))}")
    print(f"      Callbacks: {sum(1 for v in transaction_mapping.values() if v.startswith('Callback_'))}")
    
    # 2. Anonymize testplan IDs
    print("  - Anonymizing testplan IDs...")
    unique_testplans = df['testplan'].unique()
    for i, original in enumerate(unique_testplans, 1):
        anonymized = anonymize_testplan(str(original), i)
        testplan_mapping[anonymized] = str(original)
        df.loc[df['testplan'] == original, 'testplan'] = anonymized
    print(f"    ✓ Anonymized {len(unique_testplans)} unique testplans")
    
    # 3. Anonymize build versions if column exists
    if 'build_version' in df.columns:
        print("  - Anonymizing build versions...")
        df['build_version'] = df['build_version'].apply(anonymize_version)
        print("    ✓ Build versions anonymized")
    
    # 3. Anonymize any text columns that might contain sensitive info
    text_columns = ['exit_reason', 'description', 'notes', 'comments', 'error_message']
    for col in text_columns:
        if col in df.columns:
            print(f"  - Sanitizing {col}...")
            df[col] = df[col].apply(anonymize_text)
            print(f"    ✓ {col} sanitized")
    
    # 4. Remove or anonymize timestamps (replace with sequential)
    if 'timestamp' in df.columns:
        print("  - Anonymizing timestamps...")
        # Replace with sequential timestamps starting 2024-01-01
        base_time = pd.Timestamp('2024-01-01 10:00:00')
        df['timestamp'] = [base_time + pd.Timedelta(hours=i) for i in range(len(df))]
        print("    ✓ Timestamps anonymized")
    
    # 5. Remove any columns that might contain sensitive identifiers
    sensitive_columns = ['user_id', 'username', 'email', 'hostname', 'server_id']
    for col in sensitive_columns:
        if col in df.columns:
            print(f"  - Removing sensitive column: {col}")
            df = df.drop(columns=[col])
    
    print("✅ Anonymization complete")
    return df, testplan_mapping, transaction_mapping


def create_metadata_sheet(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create metadata sheet with test descriptions.
    
    This provides context for the anonymized tests that can be safely
    shared with professors and used by GPT-4.
    
    Args:
        df: Anonymized dataframe
        
    Returns:
        Metadata dataframe
    """
    print("\n📝 Creating metadata sheet...")
    
    # Determine result based on exit_code or prediction column
    if 'exit_code' in df.columns:
        result_map = {0: 'PASS', 3: 'FAIL'}
        df['result'] = df['exit_code'].map(result_map).fillna('UNKNOWN')
    elif 'prediction' in df.columns:
        result_map = {0: 'FAIL', 1: 'PASS'}
        df['result'] = df['prediction'].map(result_map).fillna('UNKNOWN')
    else:
        df['result'] = 'UNKNOWN'
    
    # Create descriptive text for each test
    def create_description(row):
        result = row.get('result', 'UNKNOWN')
        num_txn = row.get('num_transactions', 'N/A')
        
        # Add some feature context if available
        issues = []
        if 'pct_txn_critical_p95' in row and row['pct_txn_critical_p95'] > 0:
            issues.append(f"{row['pct_txn_critical_p95']*100:.1f}% critical p95 transactions")
        if 'fail_ratio' in row and row['fail_ratio'] > 0.01:
            issues.append(f"{row['fail_ratio']*100:.1f}% failure ratio")
        if 'pct_deviation_throughput' in row and row['pct_deviation_throughput'] < -0.1:
            issues.append(f"{abs(row['pct_deviation_throughput'])*100:.0f}% throughput drop")
        
        base_desc = f"Performance test with {num_txn} transactions - {result}"
        if issues:
            base_desc += f". Issues: {'; '.join(issues)}"
        
        return base_desc
    
    metadata = pd.DataFrame({
        'testplan': df['testplan'],
        'result': df['result'],
        'description': df.apply(create_description, axis=1)
    })
    
    print(f"✅ Created metadata for {len(metadata)} tests")
    return metadata


def create_anonymized_baselines(transaction_mapping: Dict[str, str]) -> bool:
    """
    Create anonymized copy of baselines.pkl using transaction name mapping.
    
    This ensures the academic demo can use baseline comparisons without
    exposing actual transaction names.
    
    Args:
        transaction_mapping: Dict mapping original names to sanitized names
        
    Returns:
        True if successful, False otherwise
    """
    import joblib
    
    print("\n🗃️  Creating anonymized baselines...")
    
    baseline_path = PROJECT_ROOT / "models" / "baselines.pkl"
    output_path = PROJECT_ROOT / "models" / "baselines_anonymized.pkl"
    
    if not baseline_path.exists():
        print(f"  ⚠️  baselines.pkl not found at {baseline_path}")
        print("     Run training first: python -m src.train")
        return False
    
    try:
        # Load original baselines
        baselines = joblib.load(baseline_path)
        print(f"  📂 Loaded baselines: {baselines.shape} rows")
        print(f"     Original transactions: {baselines['transaction_name'].nunique()}")
        
        # Apply transaction name mapping
        baselines_anon = baselines.copy()
        baselines_anon['transaction_name'] = baselines_anon['transaction_name'].map(transaction_mapping)
        
        # Check for unmapped transactions
        unmapped = baselines_anon['transaction_name'].isna().sum()
        if unmapped > 0:
            print(f"  ⚠️  Warning: {unmapped} baseline rows have unmapped transaction names")
            print("     These will be dropped")
            baselines_anon = baselines_anon.dropna(subset=['transaction_name'])
        
        # Save anonymized baselines
        joblib.dump(baselines_anon, output_path)
        print(f"  ✅ Anonymized baselines saved: {output_path.name}")
        print(f"     Sanitized transactions: {baselines_anon['transaction_name'].nunique()}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Failed to create anonymized baselines: {e}")
        return False


def validate_anonymization(df: pd.DataFrame, mapping: Dict[str, str]) -> bool:
    """
    Validate that anonymization was successful.
    
    Checks for common patterns that indicate sensitive data might remain.
    
    Args:
        df: Anonymized dataframe
        mapping: Mapping dictionary
        
    Returns:
        True if validation passes, False otherwise
    """
    print("\n🔍 Validating anonymization...")
    
    issues = []
    
    # Check 1: No real testplan IDs (they contain timestamps)
    testplan_pattern = r'\d{8}T\d{6}'
    if df['testplan'].astype(str).str.contains(testplan_pattern, regex=True).any():
        issues.append("❌ Real testplan IDs detected (contain timestamps)")
    else:
        print("  ✓ No real testplan IDs detected")
    
    # Check 2: No real URLs in text columns
    url_pattern = r'https?://(?!example\.com)[^\s]+'
    text_cols = df.select_dtypes(include=['object']).columns
    for col in text_cols:
        if df[col].astype(str).str.contains(url_pattern, regex=True, na=False).any():
            issues.append(f"❌ Real URLs detected in column: {col}")
    if not issues or 'Real URLs' not in str(issues):
        print("  ✓ No real URLs detected")
    
    # Check 3: No company-specific terms in text columns
    company_pattern = r'Comcast|CMCSA|Xfinity'
    for col in text_cols:
        if df[col].astype(str).str.contains(company_pattern, regex=True, na=False, flags=re.IGNORECASE).any():
            issues.append(f"❌ Company terms detected in column: {col}")
    if not issues or 'Company terms' not in str(issues):
        print("  ✓ No company-specific terms detected")
    
    # Check 4: Mapping is not empty
    if not mapping:
        issues.append("❌ Mapping dictionary is empty")
    else:
        print(f"  ✓ Mapping contains {len(mapping)} entries")
    
    if issues:
        print("\n⚠️  Validation issues found:")
        for issue in issues:
            print(f"    {issue}")
        return False
    else:
        print("✅ All validation checks passed")
        return True


def main():
    """Main export function."""
    parser = argparse.ArgumentParser(
        description='Export and anonymize test data for academic submission'
    )
    parser.add_argument(
        '--num-tests',
        type=int,
        default=75,
        help='Number of tests to export (default: 75)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='academic_demo_data.xlsx',
        help='Output Excel filename (default: academic_demo_data.xlsx)'
    )
    parser.add_argument(
        '--skip-validation',
        action='store_true',
        help='Skip validation checks (not recommended)'
    )
    
    args = parser.parse_args()
    
    OUTPUT_FILE = PROJECT_ROOT / "data_exports" / args.output
    TESTPLAN_MAPPING_FILE = PROJECT_ROOT / "local" / ".testplan_anonymization_map.json"
    TRANSACTION_MAPPING_FILE = PROJECT_ROOT / "local" / ".transaction_anonymization_map.json"
    
    print("=" * 60)
    print("📦 ACADEMIC DATA EXPORT & ANONYMIZATION")
    print("=" * 60)
    
    try:
        # Step 1: Extract from CSV
        df = extract_from_csv(args.num_tests)
        
        # Step 2: Add test_type column (required for baseline matching)
        print("\n🏷️  Adding test_type column...")
        df = add_test_type(df)
        test_type_counts = df['test_type'].value_counts().to_dict()
        print(f"  ✅ Test types: {test_type_counts}")
        
        # Step 3: Anonymize
        df_anon, testplan_mapping, transaction_mapping = anonymize_dataframe(df)
        
        # Step 4: Create metadata
        metadata = create_metadata_sheet(df_anon)
        
        # Step 5: Create anonymized baselines
        baselines_success = create_anonymized_baselines(transaction_mapping)
        if not baselines_success:
            print("\n⚠️  Baseline anonymization failed - continuing with data export")
        
        # Step 6: Validate (optional)
        if not args.skip_validation:
            if not validate_anonymization(df_anon, testplan_mapping):
                print("\n⚠️  Validation failed. Review and fix issues before proceeding.")
                response = input("Continue anyway? (yes/no): ").strip().lower()
                if response != 'yes':
                    print("❌ Export cancelled")
                    return 1
        
        # Step 7: Save to Excel
        print(f"\n💾 Saving to Excel: {OUTPUT_FILE}")
        OUTPUT_FILE.parent.mkdir(exist_ok=True, parents=True)
        
        with pd.ExcelWriter(OUTPUT_FILE, engine='openpyxl') as writer:
            df_anon.to_excel(writer, sheet_name='test_runs', index=False)
            metadata.to_excel(writer, sheet_name='metadata', index=False)
        
        print(f"✅ Excel file saved: {OUTPUT_FILE}")
        print(f"   📋 Sheet 1: test_runs ({len(df_anon)} rows)")
        print(f"   📋 Sheet 2: metadata ({len(metadata)} rows)")
        
        # Step 8: Save mappings
        print(f"\n🗺️  Saving anonymization mappings:")
        TESTPLAN_MAPPING_FILE.parent.mkdir(exist_ok=True, parents=True)
        
        with open(TESTPLAN_MAPPING_FILE, 'w') as f:
            json.dump(testplan_mapping, f, indent=2)
        print(f"   ✅ Testplan mapping: {TESTPLAN_MAPPING_FILE.name}")
        
        with open(TRANSACTION_MAPPING_FILE, 'w') as f:
            # Invert mapping for easier lookup (sanitized -> original)
            inverted_txn_mapping = {v: k for k, v in transaction_mapping.items()}
            json.dump(inverted_txn_mapping, f, indent=2)
        print(f"   ✅ Transaction mapping: {TRANSACTION_MAPPING_FILE.name}")
        print(f"   ⚠️  DO NOT COMMIT THESE FILES - ALREADY IN .gitignore")
        
        # Summary
        print("\n" + "=" * 60)
        print("✨ EXPORT COMPLETE")
        print("=" * 60)
        print(f"📁 Academic Excel:        {OUTPUT_FILE}")
        print(f"🗺️  Testplan mapping:      {TESTPLAN_MAPPING_FILE}")
        print(f"🗺️  Transaction mapping:   {TRANSACTION_MAPPING_FILE}")
        if baselines_success:
            print(f"🗃️  Anonymized baselines:  models/baselines_anonymized.pkl")
        print(f"📊 Tests exported:        {len(df_anon)}")
        print(f"🔐 Transaction names:     {len(transaction_mapping)} sanitized")
        print(f"    - API endpoints:      {sum(1 for v in transaction_mapping.values() if v.startswith('API_'))}")
        print(f"    - Auth flows:         {sum(1 for v in transaction_mapping.values() if v.startswith('Auth_'))}")
        print(f"    - Services:           {sum(1 for v in transaction_mapping.values() if v.startswith('Service_'))}")
        print(f"🔒 Security:              All transaction names sanitized")
        print("\n📌 NEXT STEPS:")
        print("   1. Open Excel file and verify anonymization")
        print("   2. Confirm no internal API structure is visible")
        print("   3. Transaction names should be generic (API_001, Auth_001, etc.)")
        print("   4. Test with: python -m src.predict --test-file data_exports/academic_demo_data.xlsx")
        print("   5. Do NOT commit local/*.json mapping files")
        print("=" * 60)
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Export failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
