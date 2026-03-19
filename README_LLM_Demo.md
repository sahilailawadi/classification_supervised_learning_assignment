# LLM-Augmented Performance Test Analysis — Academic Demo

**INFO 629 Assignment — LLM Integration with Supervised Learning**

This project extends the base Random Forest classifier from Assignment 3 with LLM-powered analysis. The application integrates LLM-powered natural language analysis through an MCP server with four specialized tools (query, detail, compare, baseline), enabling users to ask questions about test results and receive AI-generated insights grounded in real data. The LLM serves two key roles: (1) **Natural Language Interface** — translating user questions into structured tool calls, and (2) **Task Execution** — performing report generation, performance interpretation, test comparison, and metric summarization, all with anti-hallucination safeguards that pre-fetch real data before analysis.

---

## What's Included (LLM Features)

```
A3_Code/
├── app_llm_demo.py              # ⭐ Streamlit UI with LLM chat interface
├── src/
│   ├── analyzer.py              # TestAnalyzer — combines data + LLM + classifier
│   ├── data_source.py           # Dual-mode data source (Excel / PostgreSQL)
│   ├── llm_provider.py          # Dual-mode LLM provider (OpenAI / Work Gateway)
│   ├── features.py              # Feature engineering (19 features)
│   ├── train.py                 # Training pipeline
│   └── predict.py               # Standalone prediction
├── prompts/
│   └── report_prompts.py        # Centralized prompt templates for reports
├── mcp_server/                  # MCP tool server (4 tools)
│   ├── server.py                # MCP server entry point
│   └── tools/
│       ├── query.py             # query_tests — list/filter tests
│       ├── detail.py            # get_test_detail — single test details
│       ├── compare.py           # compare_tests — side-by-side comparison
│       └── baseline.py          # get_baseline_comparison — vs classifier baselines
├── data_exports/
│   └── academic_demo_data.xlsx  # ⭐ Anonymized dataset (no DB required)
├── models/
│   ├── model.pkl                # Trained Random Forest classifier
│   ├── scaler.pkl               # Feature scaler
│   └── baselines.pkl            # Per-transaction baseline medians
├── notebooks/
│   ├── llm_analysis_demo.ipynb  # ⭐ Jupyter version of LLM features
│   ├── predict_demo.ipynb       # Quick classifier demo (no LLM needed)
│   ├── evaluation.ipynb         # Full training pipeline & evaluation
│   └── eda.ipynb                # Exploratory data analysis
├── .env.example                 # Environment variable template
└── requirements.txt             # Python dependencies
```

---

## Quick Start (No Installation Required!)

### Option 1: Streamlit UI (Easiest — Just Click!)

**If deployed to Streamlit Cloud**, access it here:

```
https://ailawadia3-llm-demo.streamlit.app/
```
*(Note: If not yet deployed, skip to Option 3 to run locally)*

**What you can try:**
- 💬 **Chat Analysis** — Ask "What are the last 5 test runs?" or "Show me all failed tests"  
  **Value:** Take the model for a drive — chat naturally and get analysis, or try pre-configured prompts to see MCP tool integration
- 📊 **Generate Reports** — Click report buttons to see PO sign-off, dev analysis, stakeholder summary  
  **Value:** Experience automated report generation with real data embedded to prevent hallucination
- 🔍 **Deep Dive** — Select any test and get LLM-powered analysis with baseline comparisons  
  **Value:** Get an engineer's view of test results with LLM insights, then ask follow-up questions in chat
- 🤖 **Classifier Predictions** — View ML model's PASS/FAIL prediction with confidence scores  
  **Value:** See how the Random Forest classifier makes decisions — view all 19 features it used
- 🆚 **Compare Tests** — Side-by-side comparison of a passing vs failing test  
  **Value:** Understand what separates good runs from bad — LLM explains the key differences

---

### Option 2: Jupyter Notebook via Binder (No Installation!)

Click to open the LLM analysis notebook in your browser:

[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/sahilailawadi/classification_supervised_learning_assignment/HEAD?labpath=notebooks%2Fllm_analysis_demo.ipynb) **← Click to launch**

**What you can try:**
- Run `ask_question("What are the last 5 test runs?")` — MCP-powered queries  
  **Value:** See the code that routes questions to MCP tools — inspect prompts, modify questions, trace execution
- Run `ask_about_test(0, "What are the slowest transactions?")` — Test-specific analysis  
  **Value:** Observe anti-hallucination in action — real test data fetched before LLM sees the question
- Run `generate_report("summary")` — All 4 report types (Summary, PO, Dev, Stakeholder)  
  **Value:** Inspect how reports embed actual transaction names and metrics to prevent fabrication
- Run baseline comparison cells — See per-transaction P95 deviations  
  **Value:** Understand how the classifier uses baselines for feature engineering
- Run classifier prediction cells — View features + confidence  
  **Value:** See exactly what the Random Forest model sees — all 19 normalized features

**Note:** Binder may take 1-2 minutes to build the environment on first launch. You'll need to add your OpenAI API key in the setup cell.

---

### Option 3: Local Installation (Full Control)

Clone and run on your machine for full control and persistent configuration.

#### Prerequisites

- Python 3.10+
- An OpenAI API key ([get one here](https://platform.openai.com/api-keys))

#### 1. Clone & Install

```bash
git clone https://github.com/sahilailawadi/classification_supervised_learning_assignment.git
cd classification_supervised_learning_assignment

python -m venv .venv
source .venv/bin/activate   # macOS/Linux
# .venv\Scripts\activate    # Windows

pip install -r requirements.txt
```

#### 2. Configure Environment

Copy the example and add your OpenAI key:

```bash
cp .env.example .env
```

Edit `.env`:

```env
# Mode — use 'academic' for OpenAI + Excel data
LLM_MODE=academic

# OpenAI API credentials
OPENAI_API_KEY=sk-your-openai-api-key-here
OPENAI_MODEL=gpt-4-turbo-preview
```

That's it — no database needed. Academic mode reads from `data_exports/academic_demo_data.xlsx`.

#### 3. Run the Streamlit App

```bash
streamlit run app_llm_demo.py
```

Opens in your browser at `http://localhost:8501`.

**Or run the Jupyter notebook locally:**

```bash
cd notebooks
jupyter notebook llm_analysis_demo.ipynb
```

**Value:** Explore the full system implementation — inspect code, modify MCP tools, experiment with prompts, and extend features. Best for deep technical dive or building on top of this project.

---

## Features

### 💬 Chat Analysis

Ask questions in natural language. MCP tools automatically fetch real data from the Excel dataset before sending to the LLM — preventing hallucination.

**Examples:**
- "What are the last 5 test runs?"
- "Show me all failed tests"
- "What is the overall pass rate?"
- "Which transactions have the highest error rates?"

### 📊 Report Generation

Generate 4 report types, each pre-loaded with real test data and baseline comparisons:

| Report | Audience | Content |
|--------|----------|---------|
| **Summary** | Quick review | PASS/FAIL assessment, key metrics, GO/NO-GO |
| **PO Report** | Product Owner | Executive summary, risk assessment, release recommendation |
| **Dev Report** | Engineering | Transaction-level data table, critical issues, action items |
| **Stakeholder Report** | Business | High-level summary, why classifier marked PASS/FAIL |

### 🔍 Deep Dive

Select any test and get:
- Full LLM analysis with transaction-level breakdown
- Classifier prediction with confidence score
- Follow-up questions with conversation context

### 📈 Baseline Comparison

Compare any test against the classifier's baseline data:
- Per-transaction P95 deviation from median of passing runs
- Critical (>50%) and degraded (20-50%) transaction counts
- Same baseline data the ML classifier uses for feature engineering

### 🆚 Compare Tests

Select two tests (e.g., a PASS and a FAIL) and get an LLM-generated comparison of their performance differences.

### 🤖 Classifier Prediction

View the Random Forest classifier's PASS/FAIL prediction with:
- Confidence score (percentage)
- All 19 feature values the classifier used
- Actual vs predicted result comparison

---

## Anti-Hallucination Design

Every LLM interaction is grounded in actual data:

1. **Reports** pre-fetch real test metrics, baseline deviations, and classifier predictions before sending to the LLM
2. **Chat queries** route through MCP tools that query the actual dataset
3. **Deep Dive** fetches full test context (transactions, response times, error rates) before LLM analysis
4. Prompts include instructions like "DO NOT MODIFY — USE EXACT TRANSACTION NAMES" to prevent fabrication

---

## Jupyter Notebook Features

**Quick access:** See [Quick Start → Option 2](#option-2-jupyter-notebook-via-binder-no-installation) for Binder (browser-based, no install) or [Option 3](#option-3-local-installation-full-control) for local Jupyter.

**Available functions in the notebook:**
```python
# MCP-powered natural language queries
ask_question("What are the last 5 test runs?")
ask_question("Show me all failed tests")

# Test-specific analysis with anti-hallucination
ask_about_test(0, "What are the slowest transactions?")
ask_about_test("LoadTest_20260304T060726Z", "Why did this fail?")

# Pandas + LLM interpretation
ask_with_data(df.describe(), "What patterns do you see?")

# Report generation (all 4 types)
generate_report("summary")           # Quick PASS/FAIL assessment
generate_report("po_report")          # Product Owner sign-off
generate_report("dev_report")         # Engineering deep dive
generate_report("stakeholder_report") # Business summary
```

**Additional cells:**
- Baseline comparison — Per-transaction P95 deviations
- Classifier prediction — View all 19 features + confidence
- Visualizations — Charts with LLM interpretation

---

## Architecture

```
User Question
     │
     ▼
┌─────────────────┐
│  TestAnalyzer    │ ← Central service
│  (src/analyzer)  │
├─────────────────┤
│ .ask()           │ ← Unified entry point
│ .analyze_test()  │
│ .compare_tests() │
│ .predict_test()  │
└────┬────┬────┬──┘
     │    │    │
     ▼    ▼    ▼
   Data  LLM  Classifier
  Source Provider (model.pkl)
     │    │
     ▼    ▼
  Excel  OpenAI     ← Academic mode
  (.xlsx) (GPT-4)
```

**MCP Tools** (called automatically by `analyzer.ask()`):
- `query_tests` — list/filter tests by exit code, sort order
- `get_test_detail` — full transaction data for a specific test
- `compare_tests` — side-by-side comparison of two tests
- `get_baseline_comparison` — deviation from classifier baselines

---

## MCP Server (Optional)

The MCP server can also be used standalone with Claude Desktop:

```bash
# Test the MCP server directly
python -m mcp_server.server

# Or use the MCP Inspector
npx @modelcontextprotocol/inspector python -m mcp_server.server
```

Claude Desktop config (`claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "perf-test-analyzer": {
      "command": "python",
      "args": ["-m", "mcp_server.server"],
      "cwd": "/path/to/A3_Code",
      "env": {
        "LLM_MODE": "academic",
        "OPENAI_API_KEY": "sk-..."
      }
    }
  }
}
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `FileNotFoundError: model.pkl` | Run from project root, not `notebooks/`. Or run `python -m src.train --from-csv data_exports/training_data.csv` |
| `openai.AuthenticationError` | Check `OPENAI_API_KEY` in `.env` |
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` |
| LLM makes up transaction names | This shouldn't happen — reports pre-fetch real data. If it does, check that `.env` has `LLM_MODE=academic` |
| Notebook can't find modules | Make sure to run cell 1 first (changes directory to project root) |

---

## Data Source

Academic mode uses `data_exports/academic_demo_data.xlsx` — an anonymized Excel file containing performance test data with:
- Multiple test runs with PASS/FAIL outcomes
- Per-transaction metrics: P95 response time, error percentage, throughput
- No database connection required

The same data flows through the classifier, MCP tools, and LLM prompts.

---

## Related Files

- [README.md](README.md) — Base classifier documentation (Assignment 3)
- [STREAMLIT_GUIDE.md](STREAMLIT_GUIDE.md) — Streamlit deployment guide
- [mcp_server/README.md](mcp_server/README.md) — MCP server documentation
