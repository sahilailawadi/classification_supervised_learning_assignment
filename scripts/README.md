# Scripts Directory

This directory contains utility scripts for the LLM integration project.

## export_anonymized_data.py

**Purpose:** Read test data from training_data.csv and anonymize for academic submission.

**Usage:**
```bash
# Basic usage (exports 75 tests)
python scripts/export_anonymized_data.py

# Custom number of tests
python scripts/export_anonymized_data.py --num-tests 100

# Custom output filename
python scripts/export_anonymized_data.py --output my_data.xlsx

# Skip validation (not recommended)
python scripts/export_anonymized_data.py --skip-validation
```

**Output:**
- `data_exports/academic_demo_data.xlsx` - Anonymized test data with two sheets:
  - `test_runs`: All features + predictions (ready for classifier)
  - `metadata`: Test IDs and descriptions
- `local/.anonymization_map.json` - Mapping file (⚠️ DO NOT COMMIT)

**Anonymization Process:**
1. Testplan IDs: `LoadTest_20230309T174858Z` → `LoadTest_001`
2. Build versions: `2.3.1-rc5` → `v1.0`
3. URLs: Removed or replaced with `http://example.com`
4. IPs: Replaced with `10.0.0.1`
5. Company terms: Replaced with `<Company>`
6. Service names: Replaced with `<Service>`
7. Timestamps: Sequential from 2024-01-01

**Validation:**
The script automatically validates:
- No real testplan IDs (containing timestamps)
- No real URLs
- No company-specific terms
- Mapping file is not empty

**Troubleshooting:**

If you see validation errors:
1. Review the specific error messages
2. Manually inspect the output Excel file
3. Check for any Comcast-specific information
4. Re-run with additional anonymization rules as needed

**Data Source:**
- Reads from: `data_exports/training_data.csv`
- Filters to: 2000-user tests only  
- Balances: 50/50 PASS (exit_code=1) vs FAIL (exit_code=2,3,4)
- Preserves: All transaction-level metrics

**Security Notes:**
- The mapping file (`local/.anonymization_map.json`) contains real testplan IDs
- This file is gitignored and should NEVER be committed
- The Excel file is safe to share with professors and GPT-4
- Always manually verify the Excel file before submission
