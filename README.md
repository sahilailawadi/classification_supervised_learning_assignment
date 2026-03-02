# Performance Test Classification - Professor Deliverable

**INFO 629 Assignment - Supervised Learning Demonstration**

This package contains a trained Random Forest classifier that predicts Pass/Fail outcomes for Locust performance tests based on per-transaction metrics. No database connection or raw data required.

---

## What's Included

```
deliverable/
├── models/
│   ├── model.pkl           # Trained Random Forest (709 runs, 100% accuracy on sign-offs)
│   ├── scaler.pkl          # StandardScaler for 19 normalized features
│   └── baselines.pkl       # Per-transaction baseline medians
├── test_cases/
│   └── test_cases.json     # 3 representative test cases with features & labels
├── src/
│   └── predict.py          # Standalone prediction script
└── README.md     # This file
```

---

## Quick Start (No Installation Required)

### Option 1: Online Demo (Easiest - No Installation!)

**If deployed to Streamlit Cloud**, just click this URL:

```
https://ailawadia3.streamlit.app/
```

**Features:**
- 🎯 Select from 3 pre-computed test cases
- 📊 View features in a nice table with critical values highlighted
- 🤖 Click "Predict" button to see classification with confidence
- 📈 View feature importance and model metrics
- 🔧 **Manual Mode**: Enter custom feature values for "what-if" scenarios

### Option 2: Interactive UI (Local)

Launch the Streamlit web interface on your computer:

```bash
pip install streamlit
streamlit run app.py
```

Then open your browser to `http://localhost:8501`

**Features:**
- 🎯 Select from 3 pre-computed test cases
- 📊 View features in a nice table with critical values highlighted
- 🤖 Click "Predict" button to see classification with confidence
- 📈 View feature importance and model metrics
- 🔧 **Manual Mode**: Enter custom feature values for "what-if" scenarios

### Option 3: Command Line

If you have Python 3.11+ with scikit-learn, pandas, numpy, and joblib:

```bash
python3 -m src.predict
```

**Expected Output**: Predictions on 3 test cases (1 pass, 2 fails) with confidence scores and explanations.

---

## Setup Instructions

### Prerequisites

- Python 3.11 or higher
- pip (Python package manager)

### Installation

1. **Navigate to project directory:**

```bash
cd path/to/classification_supervised_learning_assignment
```

2. **Create virtual environment (recommended):**

```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. **Install dependencies:**

```bash
pip install -r requirements.txt
```

---

## Running the Demonstration

### Command

```bash
python3 -m src.predict
```

### Expected Output

```
=====================================================================
  PERFORMANCE TEST CLASSIFICATION — PREDICTIONS
======================================================================

──────────────────────────────────────────────────────────────────────
  Case 1: Clean Pass
  All transactions within baseline thresholds. Healthy test run.
  Source run: LoadTest_20251213T073644Z
──────────────────────────────────────────────────────────────────────

  Prediction:   PASS ✅  (confidence: 97.0%)
  Test Status:       PASS  [✓ Correct]
  Exit code:    1
  Reason:       All transactions within baseline thresholds

  Key Feature Values:
    Feature                                  Value
    ───────────────────────────────────────────────
    pct_txn_critical_p95                    0.0000
    pct_txn_degraded_p95                    0.0000
    max_pct_deviation_p95                   0.0202
    pct_txn_critical_avg_rt                 0.0000
    pct_txn_degraded_avg_rt                 0.0000
    max_pct_deviation_avg_rt                0.0000
    pct_txn_critical_error                  0.0000
    pct_txn_degraded_error                  0.0000
    max_pct_deviation_error                 0.0000
    pct_txn_with_errors                     0.0000
    pct_txn_complete_failure                0.0000
    max_error_percentage                    0.0000
    has_100pct_failure_txn                  0.0000
    throughput_per_user                     0.4421
    pct_deviation_throughput                1.1128 ⚠️
    fail_ratio                              0.0000
    has_anomalous_transactions              0.0000
    num_transactions                       54.0000
    test_type_encoded                       1.0000

──────────────────────────────────────────────────────────────────────
  Case 2: Response Time Failure
  Multiple transactions critical on p95 and avg RT. Exit code 3.
  Source run: LoadTest_20230309T174858Z
──────────────────────────────────────────────────────────────────────

  Prediction:   FAIL ❌  (confidence: 75.5%)
  Test Status:       FAIL  [✓ Correct]
  Exit code:    3
  Reason:       p95 critical on 33/54 txns (worst: +112316%); 
                avg RT critical on 33/54 txns (worst: +25694%)

  Key Feature Values:
    Feature                                  Value
    ───────────────────────────────────────────────
    pct_txn_critical_p95                    0.6111 ⚠️
    pct_txn_degraded_p95                    0.0741
    max_pct_deviation_p95                1123.1564 ⚠️
    pct_txn_critical_avg_rt                 0.6111 ⚠️
    pct_txn_degraded_avg_rt                 0.0185
    max_pct_deviation_avg_rt              256.9356 ⚠️
    pct_txn_critical_error                  0.0185
    pct_txn_degraded_error                  0.0000
    max_pct_deviation_error                29.9252 ⚠️
    pct_txn_with_errors                     0.1852 ⚠️
    pct_txn_complete_failure                0.1481 ⚠️
    max_error_percentage                  100.0000 ⚠️
    has_100pct_failure_txn                  1.0000 ⚠️
    throughput_per_user                     0.2134
    pct_deviation_throughput               -0.0457
    fail_ratio                              0.0011
    has_anomalous_transactions              0.0000
    num_transactions                       54.0000
    test_type_encoded                       0.0000

──────────────────────────────────────────────────────────────────────
  Case 3: Throughput / Error Failure
  High failure ratio and/or low throughput. Degraded or critical.
  Source run: LoadTest_20251008T203436Z
──────────────────────────────────────────────────────────────────────

  Prediction:   FAIL ❌  (confidence: 99.0%)
  Test Status:       FAIL  [✓ Correct]
  Exit code:    2
  Reason:       p95 critical on 23/62 txns (worst: +1206%); 
                avg RT critical on 36/62 txns (worst: +876%); 
                throughput_per_user 40% below baseline; 
                fail_ratio=0.3764 (>1%)

  Key Feature Values:
    Feature                                  Value
    ───────────────────────────────────────────────
    pct_txn_critical_p95                    0.3710 ⚠️
    pct_txn_degraded_p95                    0.0161
    max_pct_deviation_p95                  12.0573 ⚠️
    pct_txn_critical_avg_rt                 0.5806 ⚠️
    pct_txn_degraded_avg_rt                 0.0484
    max_pct_deviation_avg_rt                8.7628 ⚠️
    pct_txn_critical_error                  0.3548 ⚠️
    pct_txn_degraded_error                  0.0000
    max_pct_deviation_error                 0.0000
    pct_txn_with_errors                     0.3548 ⚠️
    pct_txn_complete_failure                0.0000
    max_error_percentage                   37.6400 ⚠️
    has_100pct_failure_txn                  0.0000
    throughput_per_user                     0.1336
    pct_deviation_throughput               -0.4023 ⚠️
    fail_ratio                              0.3764 ⚠️
    has_anomalous_transactions              0.0000
    num_transactions                       62.0000
    test_type_encoded                       0.0000

======================================================================
  3 test cases evaluated
======================================================================
```

---

## Interpreting the Results

### Test Case Descriptions

**Case 1: Clean Pass (97% confidence)**
- All 54 transactions performed within or better than baseline thresholds
- Zero critical transactions, zero failures
- Throughput was 111% above baseline (exceptional performance)
- **Model learned**: Healthy test = all metrics near zero

**Case 2: Response Time Failure (73% confidence)**
- 61% of transactions (33/54) had p95 >10% above baseline
- Worst transaction was **1,123x slower** than baseline (+112,316%)
- Low confidence because fail_ratio was only 0.1% (requests didn't actually fail)
- **Model learned**: Extreme p95 deviations predict failure even with low error rates

**Case 3: Throughput/Error Failure (98% confidence)**
- Multiple failure signals: 37% critical p95, 58% critical avg_rt
- **37.6% of requests FAILED** (catastrophic)
- Throughput 40% below baseline (system couldn't handle load)
- **Model learned**: Combined signals (slow + errors + low throughput) = high confidence failure

### Feature Interpretation Guide

| Feature | Meaning | Example Value | Interpretation |
|---------|---------|---------------|----------------|
| `pct_txn_critical_p95` | % of transactions with p95 >10% above baseline | 0.6111 | 61% of transactions critically slow |
| `max_pct_deviation_p95` | Worst p95 deviation as ratio | 1123.1564 | Worst transaction 1,124x slower (baseline × 1124) |
| `pct_txn_critical_avg_rt` | % of transactions with avg RT >10% above baseline | 0.5806 | 58% of transactions critically slow on average |
| `pct_txn_with_errors` | % of transactions with any errors (>0%) | 0.1852 | 18.5% of transactions had at least 1 failed request |
| `pct_txn_complete_failure` | % of transactions with 100% failure rate | 0.1481 | 14.8% of transactions had all requests fail (catastrophic) |
| `max_error_percentage` | Worst absolute error rate across all transactions | 100.0 | At least 1 transaction had 100% of its requests fail |
| `has_100pct_failure_txn` | Binary flag for catastrophic failure | 1.0 | 1 if any transaction had 100% failure, else 0 |
| `fail_ratio` | Proportion of failed requests (global) | 0.3764 | 37.6% of all requests failed |
| `pct_deviation_throughput` | Throughput deviation from baseline | -0.4023 | 40% below expected throughput |
| `throughput_per_user` | Requests/second per user | 0.1336 | Each of 2000 users did 0.13 req/sec |
| `test_type_encoded` | Test type | 0.0 | 0=load_test, 1=endurance, 2=experimental |

**⚠️ Symbols** flag features exceeding critical thresholds (help identify problem areas).

### Confidence Levels

- **>95%**: High confidence (multiple aligned failure signals)
- **70-95%**: Medium confidence (some ambiguity or conflicting signals)
- **<70%**: Low confidence (model uncertain)

---

## Model Architecture & Methodology

### Training Data

- **Source**: 709 Locust performance test runs from production database
- **Constraint**: Only 2000-user tests (consistent load level)
- **Features**: 43,000+ per-transaction rows aggregated to 19 run-level features
- **Split**: 80% train (567 runs), 20% test (142 runs), stratified by pass/fail
- **Class Distribution**: 57.6% pass (exit_code=1), 42.4% fail (exit_code=2,3,4)

### Feature Engineering

**Per-Transaction Baselines:**
- Computed from **median** of passing runs (exit_code=1)
- Grouped by: (test_type, num_clients, transaction_name)
- Example: `/negotiate` transaction in 2000-user load_test has baseline_p95=156ms
- Each transaction compared to its own baseline (not global average)

**Deviation Calculation:**
```python
pct_deviation_p95 = (actual_p95 - baseline_p95) / baseline_p95

# Example:
# actual_p95 = 312ms, baseline_p95 = 156ms
# pct_deviation_p95 = (312 - 156) / 156 = 1.0 (100% above baseline)
```

**Thresholds:**
- **Degraded**: 5-10% above baseline
- **Critical**: >10% above baseline

**Aggregation to Run-Level:**
- `pct_txn_critical_p95` = count(transactions with p95 >10% above) / total_transactions
- `max_pct_deviation_p95` = max(pct_deviation_p95 across all transactions)
- Similar for avg_rt, error_rate

**All 19 Features:**

**Response Time Features (6):**
1. `pct_txn_critical_p95` - % txns with critical p95 deviation (>10% above baseline)
2. `pct_txn_degraded_p95` - % txns with degraded p95 deviation (5-10% above baseline)
3. `max_pct_deviation_p95` - Worst p95 deviation across all transactions
4. `pct_txn_critical_avg_rt` - % txns with critical avg RT deviation (>10% above baseline)
5. `pct_txn_degraded_avg_rt` - % txns with degraded avg RT deviation (5-10% above baseline)
6. `max_pct_deviation_avg_rt` - Worst avg RT deviation across all transactions

**Error Features (7):**
7. `pct_txn_critical_error` - % txns with critical error rate deviation (>10% above baseline)
8. `pct_txn_degraded_error` - % txns with degraded error rate deviation (5-10% above baseline)
9. `max_pct_deviation_error` - Worst error rate deviation across all transactions
10. `pct_txn_with_errors` - % of transactions with any errors (>0% failure rate)
11. `pct_txn_complete_failure` - % of transactions with 100% failure rate (catastrophic)
12. `max_error_percentage` - Worst absolute error rate across all transactions (0-100)
13. `has_100pct_failure_txn` - Binary flag: 1 if any transaction had 100% failure, else 0

**Throughput/Global Features (6):**
14. `throughput_per_user` - Requests per second per user
15. `pct_deviation_throughput` - Throughput deviation from baseline
16. `fail_ratio` - Proportion of failed requests globally (0.0-1.0)
17. `has_anomalous_transactions` - Binary flag for txns without baseline
18. `num_transactions` - Count of unique transactions in the test
19. `test_type_encoded` - Test type: 0=load_test, 1=endurance, 2=experimental

### Models Evaluated

| Model | Balanced Accuracy | F1 Score | ROC-AUC |
|-------|-------------------|----------|---------|
| **Random Forest** (selected) | **98.5%** | **98.2%** | **0.995** |
| Decision Tree | 96.3% | 95.8% | 0.963 |
| SVM (RBF kernel) | 94.7% | 93.9% | 0.947 |

**Why Random Forest?**
- Best balanced accuracy (handles class imbalance)
- High precision and recall (fewer false alarms)
- `class_weight='balanced'` ensures minority class attention

### Performance Metrics

**Test Set (142 unseen runs):**
- Accuracy: 97.2%
- Balanced Accuracy: 96.8%
- Precision: 96.5% (few false positives)
- Recall: 95.7% (catches most failures)
- F1 Score: 96.1%

**Production Validation (11 real sign-off tests from 2022-2025):**
- Accuracy: **100.0%**
- True Positives: 9 (Pass→Pass)
- True Negatives: 2 (Fail→Fail)
- False Positives: 0
- False Negatives: 0

**Key Insight**: Model learned that **high p95 deviations alone don't cause failure** if `fail_ratio ≈ 0`. Many production sign-offs had 60-85% of transactions critically slow but still passed because requests didn't actually fail.

---

## Implementation Details

### Why These 3 Test Cases?

**Case Selection Algorithm** (from `train.py`):
1. **Case 1**: Passing run with **lowest max_pct_deviation_p95** (cleanest pass)
2. **Case 2**: exit_code=3 run with **highest max_pct_deviation_p95** (worst response time failure)
3. **Case 3**: exit_code=2 or 4 run with **highest fail_ratio** (worst throughput/error failure)

This ensures diversity across failure modes.

### Data Flow

```
Raw Database (testrun + test_summary)
        ↓
Extract 709 runs (num_clients=2000, exit_code≠0, rps_avg>0)
        ↓
Compute baselines per (test_type, num_clients, txn_name) from passing runs
        ↓
Calculate per-transaction % deviations (p95, avg_rt, error_pct)
        ↓
Aggregate to 15 run-level features
        ↓
StandardScaler normalization
        ↓
Random Forest training (class_weight='balanced')
        ↓
Export model.pkl, scaler.pkl, baselines.pkl, test_cases.json
```

### Baseline Computation Example

**Transaction**: `/negotiate` in 2000-user load_test

**Baseline calculation:**
```python
# Filter to passing runs with this transaction
passing_runs = df[(df['exit_code'] == 1) & 
                  (df['test_type'] == 'load_test') & 
                  (df['num_clients'] == 2000) &
                  (df['transaction_name'] == '/negotiate')]

# Compute median of p95 from these runs
baseline_p95 = passing_runs['perc_95'].median()  # e.g., 156ms
```

**Deviation for new test:**
```python
actual_p95 = 312  # Current test's /negotiate p95
pct_deviation = (actual_p95 - baseline_p95) / baseline_p95  # = 1.0 (100% above)

# Flag as critical if >10% above baseline
is_critical = (pct_deviation > 0.10)  # True
```

### Why Normalized Features?

**Application-Agnostic Design:**
- No absolute values (e.g., "p95 must be <200ms")
- All features are ratios/percentages relative to baseline
- Allows model to generalize across:
  - Different applications (Chat vs Analytics vs File Transfer)
  - Different endpoints (fast vs slow transactions)
  - Different load levels (with per-num_clients baselines)

**Example**: A `/health` endpoint with baseline_p95=10ms deviating to 15ms (50% above) is treated the same as `/heavy-report` with baseline_p95=5000ms deviating to 7500ms (50% above).

---

## Technical Specifications

**Language**: Python 3.11+

**Key Libraries**:
- `scikit-learn==1.4.0` - Random Forest, StandardScaler, train_test_split, metrics
- `pandas==2.1.0` - Data manipulation
- `numpy==1.26.0` - Numerical operations
- `joblib==1.3.0` - Model serialization

**Model Hyperparameters**:
```python
RandomForestClassifier(
    n_estimators=200,
    max_depth=15,
    class_weight='balanced',
    random_state=42
)
```

**Feature Scaling**: StandardScaler (mean=0, std=1)

**Train/Test Split**: 80/20 stratified by label

---

## Limitations & Future Work

**Current Limitations:**
1. **Training data constraint**: Only 2000-user tests (709 runs)
   - To generalize across user counts, need more diverse training data
2. **Binary classification**: Pass/Fail only
   - Could extend to multi-class (exit_code=1,2,3,4 separately)
3. **Static baselines**: Computed once during training
   - Could implement dynamic baseline updates as more passing runs accumulate
4. **⚠️ Error feature bug**: Error deviations always return 0 when baseline ≈ 0%
   - Impact: Model cannot detect per-transaction error rates
   - Example: LoadTest_20230309T174858Z had 8 transactions with 100% failure, but `pct_txn_critical_error = 0.0`
   - Fix documented in FINETUNING.md
5. **⚠️ Global fail_ratio masks per-transaction failures**: 
   - High-volume transactions with low errors mask 100% failures on low-volume transactions
   - Example: 8 SignalR transactions with 100% failure showed `fail_ratio = 0.1%` globally
   - Should add `has_100pct_failure_txn` feature for catastrophic failure detection

**Future Enhancements:**
1. **Fix error features** (Phase 2a - see FINETUNING.md Step 0)
   - Use absolute error when baseline ≈ 0
   - Add per-transaction error metrics (detect 100% failures)
2. **Production label training** (Phase 2b - see FINETUNING.md Steps 1-5)
   - Train on actual release decisions from `release_runs` table
   - Learn when humans override automated criteria
3. Multi-class classification (Pass, Fail-TPS, Fail-RT, Fail-Error)
4. Confidence calibration (ensure 95% confidence truly means 95% accuracy)
5. SHAP values for per-transaction explainability
6. Real-time prediction API (integrate with CI/CD)
7. Anomaly detection for novel transaction patterns

---

## FAQ

**Q: Why no raw data?**
A: Assignment requirement states "send only the classifier and a few testing cases." The 700GB Postgres database contains proprietary production performance data.

**Q: Can I add my own test cases?**
A: Yes! Edit `test_cases/test_cases.json` with your own features array (must have all 15 features). Then run `python3 -m src.predict --test-cases test_cases/test_cases.json`.

**Q: What if I want to see training code?**
A: Full source code is in `src/` directory:
- `extract.py` - Database queries (requires .env credentials)
- `features.py` - Baseline computation & feature engineering
- `train.py` - Model training & evaluation
- `predict.py` - Prediction (works standalone)

**Q: How long did training take?**
A: ~30 seconds on MacBook Pro M1 (709 runs, 3 models, cross-validation, evaluation)

**Q: Why Random Forest over Neural Network?**
A: Interpretability - can inspect feature importance, requires less data, no GPU needed, comparable accuracy for tabular data.

---

## Acknowledgments

This supervised learning demonstration was developed for Drexel University INFO 629 using real production Locust performance test data from a large-scale web application spanning 2022-2026.

**Assignment Objective**: Demonstrate supervised learning on real-world data without sharing proprietary raw data.

**Result**: Trained classifier achieves 100% accuracy on 11 production sign-off decisions, packaged as standalone demo requiring no database access.

---

## Contact

For questions about this demonstration or methodology, contact the project author through Drexel University INFO 629 course channels.
