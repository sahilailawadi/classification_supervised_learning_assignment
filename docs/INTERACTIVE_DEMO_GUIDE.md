# LLM Interactive Demo Guide

This guide covers the **interactive** LLM demos for conversational test analysis. These complement the automated demos in `scripts/demo_analyzer.py`.

## 🎯 Two Interactive Demo Options

### 1. **Jupyter Notebook** - For Exploration
**File:** `notebooks/llm_analysis_demo.ipynb`

**Best for:**
- Data exploration and ad-hoc queries
- Following your analysis flow
- Combining pandas + visualizations + LLM
- Academic presentations

**How to use:**
```bash
# Start Jupyter
jupyter notebook notebooks/llm_analysis_demo.ipynb

# OR use VS Code
# Just open the .ipynb file in VS Code
```

**Features:**
- ✅ Run cells sequentially or jump around
- ✅ Conversation history maintained 
- ✅ Ask follow-up questions
- ✅ Mix code, data, charts, and LLM Q&A
- ✅ Export your analysis

**Example questions:**
```python
ask_question("What are the top 5 slowest transactions?")
ask_question("How is /auth/login performing?")
ask_question("Show me patterns in failed tests")
ask_question("Why did LoadTest_20230309T174858Z fail?")
```

### 2. **Streamlit App** - For Interactive UI
**File:** `app_llm_demo.py`

**Best for:**
- Live demos to your professor
- Interactive presentations
- Non-technical stakeholders
- Polish and visual appeal

**How to run:**
```bash
streamlit run app_llm_demo.py
```

**Features:**
- ✅ Chat interface (like ChatGPT)
- ✅ Visual dashboards and charts
- ✅ Test overview with metrics
- ✅ Deep dive into specific tests
- ✅ Side-by-side test comparisons
- ✅ No coding required (UI-based)

**Pages:**
1. **💬 Chat Analysis** - Ask questions in natural language
2. **📈 Test Overview** - See trends, charts, distributions
3. **🔍 Deep Dive** - Analyze single test in detail
4. **⚖️ Compare Tests** - Side-by-side comparison

## 🚀 Quick Start

### Prerequisites
```bash
# Make sure environment is set up
source .venv/bin/activate
pip install -r requirements.txt

# Configure .env file
cp .env.example .env
# Edit .env with your credentials
```

### Jupyter Demo
```bash
# Option 1: Command line
jupyter notebook notebooks/llm_analysis_demo.ipynb

# Option 2: VS Code
# Just open the file and run cells with Shift+Enter
```

### Streamlit Demo
```bash
# Run the app
streamlit run app_llm_demo.py

# Open browser to http://localhost:8501
# Start asking questions!
```

## 💬 Example Conversations

### Jupyter Notebook Examples

**Question 1: Transaction performance**
```python
ask_question("What are the top 5 slowest transactions by P95 response time?")
```
Expected output: LLM analyzes data and returns ranked list with insights.

**Question 2: Failure analysis**
```python
ask_question("What patterns do you see in failed tests?")
```
Expected output: LLM identifies common characteristics of failures.

**Question 3: Specific transaction**
```python
ask_question("How is transaction /auth/login trending over time?")
```
Expected output: LLM analyzes trends for that specific transaction.

**Question 4: Follow-up**
```python
ask_question("Why might that transaction be slow?")
```
Expected output: LLM uses conversation history to provide context-aware answer.

### Streamlit App Examples

**Chat Page:**
- User: "What are the slowest transactions?"
- LLM: [Analyzes top 10 transactions with P95 times and insights]

- User: "Why is /auth/login so slow?"
- LLM: [Provides hypotheses about authentication bottlenecks]

- User: "Show me trends"
- LLM: [Analyzes trends button generates trend analysis]

**Deep Dive Page:**
1. Select test from dropdown
2. Click "Analyze"
3. Get comprehensive analysis with:
   - Prediction + confidence
   - LLM insights
   - Feature values
   - Transaction breakdown

**Compare Page:**
1. Select two tests (e.g., one PASS, one FAIL)
2. Click "Compare"
3. Get side-by-side analysis highlighting differences

## 🎓 For Your Professor

### Why This Approach?

**Conversational vs Automated:**
- ❌ Automated demo: Pre-scripted, limited flexibility
- ✅ Interactive demo: Ask ANY question, explore freely

**Demonstrates:**
1. **LLM Intelligence** - Answers varied questions, not just templates
2. **Context Awareness** - Maintains conversation history
3. **Data Integration** - Combines ML predictions + raw data + LLM insights
4. **Practical Value** - Real engineers would USE this

### Demo Flow Suggestion

**For Professor (15-min demo):**

1. **Start with Streamlit** (5 min)
   - Show Test Overview page
   - Ask 2-3 questions in Chat page
   - Deep dive on one interesting test
   - Compare PASS vs FAIL test

2. **Switch to Jupyter** (5 min)
   - Show how you can combine pandas analysis
   - Create visualization
   - Ask LLM to interpret it
   - Show conversation history

3. **Technical Deep Dive** (5 min)
   - Show code in `src/analyzer.py`
   - Explain dual-mode (academic/work)
   - Show OAuth flow (if work mode)
   - Discuss architecture

### Key Points to Highlight

✅ **Dual-mode architecture** - Works with academic data OR production database
✅ **OAuth integration** - Enterprise-ready with Comcast gateway
✅ **Context building** - Intelligent prompts with features + transaction data
✅ **Conversation memory** - Follow-up questions work naturally
✅ **ML + LLM fusion** - Classifier prediction + LLM interpretation
✅ **Production-ready** - 714 real tests, not toy data

## 📊 Sample Questions by Category

### Performance Analysis
- "What are the slowest transactions?"
- "Show me P95 trends over time"
- "Which transactions have high variance?"

### Failure Investigation
- "Why did LoadTest_X fail?"
- "What's common in failed tests?"
- "Are there any anomalies?"

### Comparison
- "How does test A compare to test B?"
- "What's different about today vs yesterday?"
- "PASS vs FAIL characteristics?"

### Trends
- "Is performance improving?"
- "Any degradation over time?"
- "How is transaction X trending?"

### Root Cause
- "What might cause these slow response times?"
- "Why are errors increasing?"
- "What should I investigate next?"

## 🔧 Customization

### Adding Custom Questions

**Jupyter:**
```python
# Add a new cell anywhere
ask_question("Your custom question here")
```

**Streamlit:**
```python
# Edit app_llm_demo.py
# Find "Quick Questions" section
# Add your button:
if st.button("Your Question"):
    st.session_state.conversation_history.append((
        "Your question text",
        "⏳ Processing..."
    ))
    st.rerun()
```

### Adjusting LLM Parameters

**Temperature (creativity):**
```python
# In ask_question() or ask_llm_question()
response = llm.chat(
    messages=[...],
    temperature=0.7  # 0=focused, 1=creative
)
```

**Context depth:**
```python
# Include more conversation history
for i, (q, a) in enumerate(conversation_history[-5:]):  # Last 5 vs 3
```

## 🐛 Troubleshooting

### "Module not found" errors
```bash
# Make sure you're in virtual environment
source .venv/bin/activate

# Reinstall if needed
pip install -r requirements.txt
```

### Jupyter not finding modules
```python
# Add to first cell:
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd().parent))
```

### Streamlit port already in use
```bash
# Use different port
streamlit run app_llm_demo.py --server.port 8502
```

### LLM errors

**Academic mode:**
- Check `OPENAI_API_KEY` in `.env`
- Verify model name: use `gpt-4` or `gpt-4-turbo` (not `gpt-4-turbo-preview`)

**Work mode:**
- Check SAT credentials (`SAT_CLIENT_ID`, `SAT_CLIENT_SECRET`)
- Verify VPN connection
- Check token expiration

## 📋 Requirements

**Additional for demos:**
- `jupyter>=1.0.0` - For notebook
- `streamlit>=1.31.0` - For web UI
- `plotly>=5.18.0` - For interactive charts
- `matplotlib>=3.8.0` - For static charts
- `seaborn>=0.13.0` - For statistical plots

**Install:**
```bash
pip install jupyter streamlit plotly matplotlib seaborn
```

## 🎯 Next Steps

1. **Test both demos** - Run through them once before showing professor
2. **Prepare questions** - Have 5-10 interesting questions ready
3. **Check data** - Make sure you have test data loaded
4. **Practice flow** - 5 min Streamlit → 5 min Jupyter → 5 min code review
5. **Export examples** - Save some good Q&A exchanges to show

## 📚 Related Files

- `scripts/demo_analyzer.py` - Original automated demo (still useful!)
- `src/analyzer.py` - Core TestAnalyzer class
- `src/llm_provider.py` - LLM abstraction
- `src/data_source.py` - Data loading
- `docs/LLM_IMPLEMENTATION_SUMMARY.md` - Complete implementation docs

---

**Questions?** Check the main docs or ask in the Streamlit chat! 😊
