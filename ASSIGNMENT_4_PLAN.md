# Assignment 2: LLM-Enhanced Performance Test Analyst

**Project:** Add LLM capabilities to Random Forest performance test classifier  
**Date:** March 12, 2026  
**Status:** Planning Complete, Ready for Implementation

---

## Executive Summary

Enhance the existing Random Forest classifier with LLM capabilities to provide natural language interface, intelligent explanations, and actionable recommendations. This transforms raw predictions into conversational insights while demonstrating all three LLM categories required by Assignment 2.

### Dual-Mode Architecture

**Academic Mode** (Professor Validation):
- **LLM:** OpenAI GPT-4 (best quality for grading)
- **Data:** Anonymized Excel file (`academic_demo_data.xlsx`)
- **Security:** Zero Comcast data exposure
- **Setup:** Professor only needs OpenAI API key + Excel file

**Work Mode** (Internal Comcast Use):
- **LLM:** Ollama + Llama 3 (local, no external API calls)
- **Data:** Live PostgreSQL database connection
- **Security:** Full privacy, data never leaves your machine
- **Setup:** Requires VPN + DB credentials + Ollama installation

---

## Assignment Requirements Coverage

### Category 1: Natural Language Understanding (LLM as Interface) ✅

**Use Cases:**
1. **Query Parser** - Convert natural language questions to structured queries
   - "Why did test X fail?" → Extract testplan ID, route to classifier
   - "Show me tests from last week" → Parse time range, query data source
   - "Compare build 2.3.0 vs 2.3.1" → Extract versions, run comparison

2. **Feature Translator** - Map user concepts to technical features
   - "Which tests had slow response times?" → Filter by `max_pct_deviation_p95` > threshold
   - "Show me tests with high errors" → Filter by `pct_txn_critical_error` > 0

**Demo:** Show query → intent parsing → structured action flow

### Category 2: LLM Task Execution ✅

**Use Cases:**
1. **Explanation Generation** - Transform classifier outputs into narratives
2. **Summarization** - Aggregate multiple test results
3. **Information Extraction** - Parse test metadata
4. **Recommendation Generation** - Suggest fixes based on failure patterns

**Demo:** Show classifier output → LLM explanation with recommendations

### Category 3: Pretraining Knowledge Application ✅

**Use Cases:**
1. **Domain Expertise** - Answer technical questions without provided context
   - "What causes high p95 latency in REST APIs?"
   - "How does connection pooling affect throughput?"

2. **Best Practices** - Recommend industry-standard solutions
3. **Feature Education** - Explain feature meanings and implications

**Demo:** Ask general questions without test context → LLM provides domain knowledge

---

## Implementation Roadmap

### Phase 0: Data Preparation (One-time Setup)

**Task:** Create `scripts/export_anonymized_data.py`

**Purpose:** Extract test data from PostgreSQL database and anonymize for academic submission

**Process:**
1. **Extract from Database**: Query 50-100 diverse test runs covering:
   - Mix of PASS/FAIL results
   - Different test types (load tests, endurance, spike)
   - Various failure patterns (p95 issues, error spikes, throughput drops)
   - Representative feature distributions

2. **Anonymize** all sensitive information:
   - `LoadTest_20230309T174858Z` → `LoadTest_001`
   - Version `2.3.1-rc5` → `v1.0`
   - Remove URLs, IPs, Comcast-specific terms
   - Replace timestamps with sequential dates

3. **Export to Excel** with two sheets:
   - `test_runs`: All 19 features + predictions (ready for classifier)
   - `metadata`: Test IDs and descriptions

4. **Store Mapping** locally (NOT in repo):
   - `local/.anonymization_map.json`: Maps anonymized → real IDs
   - Add `local/` to `.gitignore`

**Output:** `data_exports/academic_demo_data.xlsx` safe to submit to professor

**Validation Checklist:**
- [ ] No real testplan IDs in Excel
- [ ] No Comcast-specific terms in free text
- [ ] No internal URLs or endpoints
- [ ] Build versions are generic
- [ ] Timestamps don't reveal launch dates
- [ ] Excel opens correctly and data looks reasonable
- [ ] Professor can load Excel with pandas/openpyxl without errors

---

### Phase 1: Foundation (Week 1)

**Goal:** Basic LLM integration with single-test analysis in both modes

#### Tasks

1. **Dual Environment Setup**
   - Install Ollama: `curl -fsSL https://ollama.com/install.sh | sh`
   - Pull llama3 model: `ollama pull llama3:8b`
   - Install libraries: `pip install openai ollama openpyxl python-dotenv`
   - Create `.env` with `OPENAI_API_KEY` and `LLM_MODE=academic` or `work`

2. **Abstract LLM Interface** - Create `src/llm_provider.py`
   - Base class: `LLMProvider(ABC)`
   - Implementation: `OpenAIProvider` (GPT-4)
   - Implementation: `OllamaProvider` (Llama 3)
   - Factory: `get_llm_provider()` based on config

3. **Abstract Data Source** - Create `src/data_source.py`
   - Base class: `DataSource(ABC)`
   - Implementation: `ExcelSource` (anonymized Excel)
   - Implementation: `DatabaseSource` (PostgreSQL)
   - Factory: `get_data_source()` based on config

4. **Core LLM Module** - Create `src/llm_assistant.py`
   - Class: `PerformanceTestAssistant`
   - Uses abstract LLM provider and data source
   - Methods: `parse_intent()`, `generate_explanation()`

5. **Prompt Templates** - Create `src/prompts.py`
   - Intent parsing prompts
   - Explanation generation prompts
   - Recommendation prompts
   - Separate versions for GPT-4 vs Llama3

6. **Enhanced Prediction** - Modify `src/predict.py`
   - Add `predict_with_context()` function
   - Returns structured output with feature flags and formatted summaries

7. **CLI Demo** - Create `src/llm_demo.py`
   - Add `--mode academic|work` argument
   - Test single test analysis

8. **Unit Tests** - Create `tests/test_llm_assistant.py`
   - Test both configurations
   - Mock LLM responses

**Verification:**
- Work mode: `python -m src.llm_demo --mode work --testplan LoadTest_20230309T174858Z`
- Academic mode: `python -m src.llm_demo --mode academic --testplan LoadTest_001`

---

### Phase 2: Interactive Interface (Week 2)

**Goal:** Natural language query interface with conversation support

#### Tasks

9. **Intent Parser Enhancement**
   - Support multiple query types: single_test_analysis, comparative_analysis, feature_explanation, general_question
   - Extract parameters: testplan IDs, date ranges, feature names

10. **Database Queries** - Implement in `src/data_source.py`
    - `DatabaseSource.query_recent_tests()`
    - `DatabaseSource.query_tests_by_date_range()`
    - Connects to PostgreSQL via existing `src/extract.py`

11. **Excel Queries** - Implement in `src/data_source.py`
    - `ExcelSource` loads from `academic_demo_data.xlsx`
    - Same query interface as DatabaseSource

12. **Context Management** - Create `src/context.py`
    - Class: `ConversationContext`
    - Manages conversation state
    - Stores history for context awareness

13. **Streamlit Chat UI** - Create `app_llm.py`
    - Mode selector in sidebar
    - Chat interface with message history
    - Example queries
    - Display classifier results + LLM explanations

14. **Multi-Test Analysis**
    - Implement `compare_tests()` method
    - Works with both data sources
    - Trend identification

**Verification:**
- Streamlit app: `streamlit run app_llm.py`
- Academic mode: Uses anonymized Excel data + GPT-4
- Work mode: Uses live PostgreSQL + Ollama

---

### Phase 3: Advanced Features (Week 3)

**Goal:** Comparative analysis, recommendations, and knowledge Q&A

#### Tasks

15. **Comparative Analysis**
    - Complete implementation with trend detection
    - Identify improving/degrading/stable patterns
    - Highlight regressions

16. **Recommendation Engine**
    - Pattern-based recommendations
    - Specific troubleshooting steps
    - Link to documentation/tools

17. **Knowledge Q&A**
    - Add `answer_question()` method
    - Uses LLM pretraining for feature definitions
    - Provides best practices
    - Explains performance concepts

18. **Academic Submission Package**
    - Create `README_ACADEMIC.md` for professor
    - Package: Excel file + app code + setup instructions
    - GPT-4 setup guide
    - Example queries

**Verification:**
- All three LLM categories demonstrable in academic mode
- Professor can run with only Excel file + OpenAI API key

---

### Phase 4: Polish & Documentation (Week 4)

**Goal:** Production-ready demo with comprehensive documentation

#### Tasks

19. **Error Handling & Resilience**
    - Add retry logic for API failures
    - Implement graceful degradation
    - Add fallback responses
    - Timeout management for Ollama

20. **Performance Optimization**
    - Add response streaming for long outputs
    - Optimize prompt lengths
    - Batch API calls where possible
    - Consider caching for identical queries

21. **Comprehensive Documentation**
    - `README_LLM.md`: Setup for both modes, architecture diagrams, configuration guide
    - `README_ACADEMIC.md`: Simplified for professor (academic mode only)
    - `PROMPT_ENGINEERING.md`: Document all prompt templates with versioning

22. **Testing & Validation**
    - Integration tests: `tests/test_llm_integration.py` for both modes
    - Manual test scenarios: `test_cases/llm_test_scenarios.md`
    - Quality validation on 10+ test cases

**Verification:**
- Full test suite passes for both modes
- Documentation complete
- Both demos ready (work-internal + academic-submission)

---

## File Structure

### Existing Files (to modify)

- `src/predict.py` - Add `predict_with_context()` function
- `src/features.py` - Reference for feature definitions
- `src/extract.py` - Reuse database connection in `DatabaseSource`
- `data_exports/training_data.csv` - Original training data (709 runs)
- `test_cases/test_cases.json` - Sample predictions
- `app.py` - Reference for Streamlit structure
- `requirements.txt` - Add `openai>=1.0.0`, `ollama>=0.1.0`, `openpyxl>=3.1.0`, `python-dotenv>=1.0.0`

### New Files to Create

**Phase 0:**
- `scripts/export_anonymized_data.py` - Export and anonymization script
- `data_exports/academic_demo_data.xlsx` - Anonymized test data
- `local/.anonymization_map.json` - Mapping (gitignored)

**Phase 1:**
- `.env` - Configuration file
- `src/llm_provider.py` - Abstract LLM interface
- `src/data_source.py` - Abstract data source interface
- `src/llm_assistant.py` - Core LLM integration
- `src/prompts.py` - Prompt templates
- `src/llm_demo.py` - CLI demo script
- `tests/test_llm_assistant.py` - Unit tests

**Phase 2:**
- `src/context.py` - Conversation context management
- `app_llm.py` - Streamlit chat interface

**Phase 3-4:**
- `README_LLM.md` - Complete documentation
- `README_ACADEMIC.md` - Professor-facing documentation
- `PROMPT_ENGINEERING.md` - Prompt documentation
- `tests/test_llm_integration.py` - Integration tests
- `test_cases/llm_test_scenarios.md` - Manual test scenarios

---

## Technical Specifications

### Configuration

**Environment Variables (`.env`):**
```bash
# LLM Configuration
LLM_MODE=academic           # or 'work'
OPENAI_API_KEY=sk-...       # Required for academic mode

# Data Configuration (inferred from LLM_MODE)
# academic mode → Excel source
# work mode → Database source

# Database (work mode only)
DB_HOST=localhost
DB_PORT=5432
DB_NAME=performance_tests
DB_USER=your_user
DB_PASSWORD=your_password
```

### LLM Provider Interface

```python
# src/llm_provider.py
from abc import ABC, abstractmethod

class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    def chat(self, messages: list, temperature: float = 0.7) -> str:
        """Send chat completion request."""
        pass

class OpenAIProvider(LLMProvider):
    """OpenAI GPT-4 provider for academic mode."""
    
    def __init__(self, api_key: str):
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key)
        self.model = "gpt-4"
    
    def chat(self, messages: list, temperature: float = 0.7) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature
        )
        return response.choices[0].message.content

class OllamaProvider(LLMProvider):
    """Ollama provider for work mode (local inference)."""
    
    def __init__(self, model: str = "llama3:8b"):
        import ollama
        self.model = model
        self.client = ollama
    
    def chat(self, messages: list, temperature: float = 0.7) -> str:
        response = self.client.chat(
            model=self.model,
            messages=messages,
            options={'temperature': temperature}
        )
        return response['message']['content']

def get_llm_provider() -> LLMProvider:
    """Factory function to get provider based on config."""
    import os
    mode = os.getenv('LLM_MODE', 'academic')
    
    if mode == 'academic':
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY required for academic mode")
        return OpenAIProvider(api_key)
    else:
        return OllamaProvider()
```

### Data Source Interface

```python
# src/data_source.py
from abc import ABC, abstractmethod
import pandas as pd

class DataSource(ABC):
    """Abstract base class for data sources."""
    
    @abstractmethod
    def get_test(self, testplan: str) -> dict:
        """Get single test by testplan ID."""
        pass
    
    @abstractmethod
    def query_recent_tests(self, limit: int = 10) -> pd.DataFrame:
        """Query recent tests."""
        pass

class ExcelSource(DataSource):
    """Excel file source for academic mode (anonymized data)."""
    
    def __init__(self):
        from pathlib import Path
        
        project_root = Path(__file__).parent.parent
        excel_path = project_root / "data_exports" / "academic_demo_data.xlsx"
        
        if excel_path.exists():
            self.df = pd.read_excel(excel_path, sheet_name='test_runs')
            self.metadata = pd.read_excel(excel_path, sheet_name='metadata')
        else:
            # Fallback to training CSV
            self.df = pd.read_csv(project_root / "data_exports" / "training_data.csv")
            self.metadata = None
    
    def get_test(self, testplan: str) -> dict:
        row = self.df[self.df['testplan'] == testplan]
        if row.empty:
            return {}
        return row.iloc[0].to_dict()
    
    def query_recent_tests(self, limit: int = 10) -> pd.DataFrame:
        return self.df.tail(limit)

class DatabaseSource(DataSource):
    """Database source for work mode."""
    
    def __init__(self):
        from src.extract import get_connection
        self.conn = get_connection()
    
    def get_test(self, testplan: str) -> dict:
        query = "SELECT * FROM testrun WHERE testplan = %s"
        df = pd.read_sql(query, self.conn, params=(testplan,))
        if df.empty:
            return {}
        return df.iloc[0].to_dict()
    
    def query_recent_tests(self, limit: int = 10) -> pd.DataFrame:
        query = """
        SELECT * FROM testrun 
        ORDER BY testplan DESC
        LIMIT %s
        """
        return pd.read_sql(query, self.conn, params=(limit,))

def get_data_source() -> DataSource:
    """Factory function to get data source based on config."""
    import os
    mode = os.getenv('LLM_MODE', 'academic')
    
    if mode == 'academic':
        return ExcelSource()
    else:
        return DatabaseSource()
```

### Prompt Templates

```python
# src/prompts.py

# Intent Parsing
INTENT_PARSER_SYSTEM = """
You are an intent parser for a performance testing analysis system.
Extract the task type and parameters from user queries.

Task types:
- single_test_analysis: Analyze one specific test
- comparative_analysis: Compare multiple tests
- feature_explanation: Explain what a feature means
- troubleshooting: Diagnose issues
- general_question: Answer general performance testing questions

Always respond in valid JSON format.
"""

INTENT_PARSER_USER = """
Parse this query: "{user_query}"

Return JSON:
{{
    "task": "<task_type>",
    "parameters": {{<extracted parameters>}},
    "confidence": <0.0-1.0>
}}
"""

# Explanation Generation (GPT-4 version)
EXPLANATION_SYSTEM_GPT4 = """
You are a senior performance testing engineer providing analysis.

Guidelines:
- Be clear and concise
- Explain technical terms when first used
- Focus on root causes, not symptoms
- Use analogies for complex concepts
- Be authoritative but approachable
"""

EXPLANATION_USER = """
Analyze this performance test result:

Testplan: {testplan}
Prediction: {prediction} (Confidence: {confidence:.1%})
Exit Code: {exit_code}

Critical Metrics:
{critical_features}

Task: Explain why this test {prediction_verb} in 2-3 paragraphs.
Focus on the primary root cause and key contributing factors.
"""

# Explanation Generation (Llama3 version - more structured)
EXPLANATION_SYSTEM_LLAMA3 = """
You are a performance testing expert. Your task is to analyze test results.

Structure your response:
1. Primary failure cause
2. Contributing factors
3. Impact assessment

Keep explanations clear and specific.
"""

# Recommendation Generation
RECOMMENDATION_SYSTEM = """
You are a DevOps troubleshooting expert.

Based on test failure patterns, provide specific, actionable troubleshooting steps.
"""

RECOMMENDATION_USER = """
Test failure pattern:
- fail_ratio: {fail_ratio:.2%}
- Throughput deviation: {throughput_deviation:.1%}
- Critical p95 transactions: {pct_critical:.0%}

Provide 3-5 specific troubleshooting steps, ordered by likelihood of fixing the issue.
Include specific commands or tools where applicable.
"""

def get_explanation_prompt(provider: str) -> str:
    """Get explanation system prompt based on provider."""
    if provider == 'openai':
        return EXPLANATION_SYSTEM_GPT4
    else:
        return EXPLANATION_SYSTEM_LLAMA3
```

---

## Testing Strategy

### Automated Tests

#### Unit Tests (`tests/test_llm_assistant.py`)

```python
def test_intent_parse_single_test():
    """Test parsing single test query."""
    assistant = PerformanceTestAssistant(mode='academic')
    query = "Why did LoadTest_001 fail?"
    intent = assistant.parse_intent(query)
    
    assert intent['task'] == 'single_test_analysis'
    assert 'LoadTest_001' in intent['parameters']['testplan']

def test_explanation_generation():
    """Test generating explanation from classifier output."""
    assistant = PerformanceTestAssistant(mode='academic')
    prediction = {
        'testplan': 'LoadTest_001',
        'prediction': 'FAIL',
        'confidence': 0.755,
        'features': {'pct_txn_critical_p95': 0.6111}
    }
    explanation = assistant.generate_explanation(prediction)
    
    assert len(explanation) > 100
    assert 'fail' in explanation.lower()
```

#### Integration Tests (`tests/test_llm_integration.py`)

```python
def test_end_to_end_academic_mode():
    """Test full workflow in academic mode."""
    os.environ['LLM_MODE'] = 'academic'
    
    query = "Why did LoadTest_001 fail?"
    intent = parse_intent(query)
    prediction = predict_with_context(intent['parameters']['testplan'])
    explanation = generate_explanation(prediction)
    
    assert prediction['prediction'] == 'FAIL'
    assert len(explanation) > 200

def test_end_to_end_work_mode():
    """Test full workflow in work mode."""
    os.environ['LLM_MODE'] = 'work'
    
    # Test with real testplan from database
    query = "Why did LoadTest_20230309T174858Z fail?"
    # ... rest of test
```

### Manual Test Scenarios

Create `test_cases/llm_test_scenarios.md`:

```markdown
# LLM Assistant Test Scenarios

## Academic Mode Tests

### Scenario 1: Single Test Analysis
**Mode:** Academic
**Query:** "Why did LoadTest_001 fail?"
**Expected:** Detailed explanation with specific metric values
**Success Criteria:**
- Mentions specific features from test data
- Identifies root cause
- Provides 3+ recommendations

### Scenario 2: Comparative Analysis
**Mode:** Academic
**Query:** "Compare LoadTest_001 vs LoadTest_002"
**Expected:** Side-by-side comparison with trends
**Success Criteria:**
- Compares metrics across tests
- Identifies biggest differences
- Recommends investigation areas

### Scenario 3: Feature Explanation
**Mode:** Academic
**Query:** "What is pct_deviation_throughput?"
**Expected:** Clear definition
**Success Criteria:**
- Accurate definition
- Explains impact on test results
- Provides example values

## Work Mode Tests

### Scenario 4: Recent Tests Query
**Mode:** Work
**Query:** "Show me the last 5 test runs from database"
**Expected:** List of 5 most recent tests
**Success Criteria:**
- Queries database successfully
- Returns formatted results
- Includes timestamps

### Scenario 5: Database Comparative
**Mode:** Work
**Query:** "Compare tests from last week"
**Expected:** Summary of recent test trends
**Success Criteria:**
- Queries database by date range
- Identifies trends
- Highlights anomalies
```

### Quality Validation

**Metrics:**
1. **Explanation Quality:** 10 test cases rated 4+/5 on clarity and accuracy
2. **Intent Parsing Accuracy:** >90% correct extraction on 20 sample queries
3. **Response Latency:** 
   - Academic mode (GPT-4): <5 seconds
   - Work mode (Ollama): <10 seconds

---

## Decisions & Trade-offs

### 1. Dual Configuration Strategy

**Decision:** Support two configurations via environment variables

**Rationale:**
- Best quality for grading (GPT-4) while keeping production data secure (Ollama + DB)
- Professor can validate full functionality without database access
- Excel format is portable and easy to inspect

**Trade-offs:**
- Slightly more complex implementation (abstract interfaces)
- Need to maintain two code paths
- **Benefit:** Clean separation of concerns, production-ready architecture

### 2. LLM Provider Choice

**Academic Mode: OpenAI GPT-4**
- Pro: Best quality, impressive for grading
- Pro: Well-documented API, reliable
- Con: Costs ~$0.03-0.08 per query
- Con: Requires external API (but okay for academic use)

**Work Mode: Ollama Llama 3**
- Pro: Zero API costs, unlimited queries
- Pro: Full data privacy, no external calls
- Pro: Comcast-approved (no data leaves machine)
- Con: Requires local GPU (8GB VRAM minimum)
- Con: Slower inference than GPT-4

### 3. Data Anonymization Approach

**Decision:** One-time export with comprehensive anonymization script

**Rationale:**
- Maintains data quality while ensuring privacy
- Mapping file allows correlation if needed
- Excel is portable and version-controllable

**Anonymization Rules:**
- Testplan IDs: Sequential generic IDs
- Versions: Generic semantic versions
- Timestamps: Sequential from 2024-01-01
- Free text: Regex-based sanitization
- URLs/IPs: Removed or genericized

### 4. Architecture Pattern

**Decision:** Hybrid ML + LLM, not pure LLM prediction

**Rationale:**
- Existing classifier achieves 97% accuracy
- LLM adds interface and explanation, not prediction
- More reliable than pure LLM approach

**Benefit:** Leverages proven ML while adding LLM value

### 5. Prompt Engineering Strategy

**GPT-4 Prompts:**
- More natural language, conversational
- Longer and more detailed
- Target quality: 4.5+/5.0

**Llama3 Prompts:**
- More structured with clear instructions
- Use few-shot examples
- Keep concise (8K context limit)
- Target quality: 3.5+/5.0

---

## Risk Mitigation

### Technical Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Ollama slow inference | High | Set timeout warnings, use streaming, optimize prompts |
| GPT-4 API costs | Medium | Cache identical queries, optimize prompt lengths |
| Anonymization incomplete | Critical | Comprehensive validation checklist, manual review |
| Database connection failures | Medium | Graceful fallback, clear error messages |
| LLM hallucinations | Medium | Ground responses in classifier outputs, validate facts |

### Academic Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Professor can't run demo | High | Simple setup guide, pre-validate Excel file, test on clean machine |
| Data privacy violation | Critical | Thorough anonymization, no real data in Excel |
| LLM quality insufficient | Medium | Use GPT-4 for academic mode, validate on 10+ examples |

---

## Success Criteria

### Minimum Viable Product (MVP)

- [ ] Both modes (academic + work) functional
- [ ] Single test analysis with explanation works
- [ ] CLI demo operational
- [ ] 5+ test cases passing
- [ ] Basic documentation complete

### Full Feature Set

- [ ] Natural language query parsing
- [ ] Multi-test comparative analysis
- [ ] Recommendation generation
- [ ] General knowledge Q&A
- [ ] Streamlit chat interface
- [ ] Comprehensive test coverage (>80%)
- [ ] All 3 LLM categories demonstrable

### Production Ready (for work extension)

- [ ] Error handling and retry logic
- [ ] Performance optimization
- [ ] Multiple LLM provider support validated
- [ ] Security review (API key handling)
- [ ] User acceptance testing at Comcast

---

## Timeline Estimate

**Phase 0 (Data Prep):** 2-4 hours
- Export script: 1 hour
- Data validation: 1 hour
- Excel testing: 1 hour

**Phase 1 (Foundation):** 12-16 hours
- Provider abstractions: 3 hours
- Data source abstractions: 3 hours
- Core LLM module: 4 hours
- Prompts and CLI: 3 hours
- Testing: 3 hours

**Phase 2 (Interface):** 10-14 hours
- Intent parser: 3 hours
- Context management: 2 hours
- Streamlit UI: 4 hours
- Integration: 3 hours
- Testing: 2 hours

**Phase 3 (Advanced):** 8-12 hours
- Comparative analysis: 3 hours
- Recommendations: 3 hours
- Knowledge Q&A: 2 hours
- Academic package: 2 hours
- Testing: 2 hours

**Phase 4 (Polish):** 8-10 hours
- Error handling: 3 hours
- Documentation: 4 hours
- Final testing: 3 hours

**Total Estimate:** 40-56 hours (1-1.5 weeks full-time)

---

## Next Steps

### Immediate Actions

1. **Review Plan:** Confirm approach with Q (your operator)
2. **Setup Environment:**
   ```bash
   # Install Ollama (if not done)
   curl -fsSL https://ollama.com/install.sh | sh
   ollama pull llama3:8b
   
   # Install Python dependencies
   pip install openai ollama openpyxl python-dotenv
   
   # Get OpenAI API key
   # Visit: https://platform.openai.com/api-keys
   ```

3. **Create Feature Branch:**
   ```bash
   git checkout -b feature/llm-integration
   ```

4. **Start with Phase 0:**
   ```bash
   # Create export script
   mkdir -p scripts
   touch scripts/export_anonymized_data.py
   
   # Add local/ to .gitignore
   echo "local/" >> .gitignore
   ```

### Questions to Resolve

1. **OpenAI API Access:** Do you have an API key or budget for GPT-4 usage?
2. **Database Access:** Do you have VPN + credentials for work mode testing?
3. **Timeline:** What's the assignment deadline?
4. **Deliverable Preference:** Jupyter notebook, video demo, or live presentation?

---

## Resources

### Documentation
- OpenAI API: https://platform.openai.com/docs
- Ollama: https://ollama.ai/
- Llama 3: https://ai.meta.com/llama/

### Related Files
- [AGENTS.md](AGENTS.md) - Coding agent instructions
- [README.md](README.md) - Project overview
- [assignment_1.md](assignment_1.md) - Previous assignment context

### Contact
- **Q (Operator):** Senior engineer guidance
- **Course Instructor:** Assignment requirement clarifications

---

**Document Status:** ✅ Planning Complete, Ready for Implementation  
**Last Updated:** March 12, 2026  
**Next Review:** After Phase 1 completion
