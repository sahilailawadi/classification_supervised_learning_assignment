# MCP Server + RAG Implementation Plan
## Performance Test Intelligence Server

**Created:** March 15, 2026  
**Status:** Planning Phase  
**Timeline:** 2-3 weeks (5-8 hours implementation)  
**Goal:** Build production-ready MCP server with RAG for intelligent test analysis

---

## Executive Summary

Transform the current monolithic Python application into a **microservices-style architecture** where:
- PostgreSQL data access becomes an **MCP server** (reusable across tools)
- Test data is **semantically searchable** via RAG (vector embeddings)
- LLMs can **dynamically query** the database instead of loading all data upfront
- Any MCP-compatible client can access test intelligence (not just our Python app)

**Use Cases:**
1. "Find tests similar to this failure pattern"
2. "What changed between passing and failing tests?"
3. "Show me all auth-related performance issues"
4. "Which tests have gotten slower over time?"

---

## Current State Analysis

### What We Have Now

**Architecture:**
```
User → Streamlit/Jupyter → TestAnalyzer
                              ├─ PostgresDataSource (loads all 35k rows)
                              ├─ LLM Provider (OpenAI/Comcast Gateway)
                              └─ RandomForest Classifier
```

**Limitations:**
1. **Full data load**: Every query loads all 35,118 rows from database
2. **No semantic search**: Can't find "similar" failures without exact filters
3. **Monolithic**: Data access tightly coupled to Python app
4. **Static queries**: Pre-defined filters only (no dynamic exploration)
5. **No reusability**: Other tools can't access this intelligence
6. **Scalability**: Won't scale to 10k+ tests

**Strengths to Preserve:**
- ✅ Dual-mode architecture (academic/work)
- ✅ OAuth integration with SAT
- ✅ LLM provider abstraction
- ✅ Feature engineering pipeline
- ✅ Classifier predictions

---

## Target Architecture

### High-Level Design

```
┌─────────────────────────────────────────────────────────────────┐
│  Client Layer (Any MCP-compatible tool)                         │
│  ├─ Streamlit App (our current UI)                              │
│  ├─ Jupyter Notebooks (exploratory analysis)                    │
│  ├─ Claude Desktop / VS Code Copilot (direct queries)           │
│  └─ Future: Slack bots, CI/CD integrations, etc.                │
└────────────────────────┬────────────────────────────────────────┘
                         │ MCP Protocol (stdio/HTTP)
┌────────────────────────▼────────────────────────────────────────┐
│  MCP Server: Performance Test Intelligence Hub                  │
│                                                                  │
│  Tools Exposed:                                                 │
│  ├─ query_tests(filters, limit, sort)                          │
│  ├─ get_test_detail(testplan)                                  │
│  ├─ search_similar_tests(testplan, top_k)                      │
│  ├─ semantic_search(query, filters, top_k)                     │
│  ├─ compare_tests(test1, test2)                                │
│  ├─ get_test_trends(transaction, days)                         │
│  ├─ find_anomalies(date_range)                                 │
│  └─ explain_failure(testplan)                                  │
│                                                                  │
│  Resources:                                                      │
│  ├─ test://{testplan} - Individual test records                │
│  ├─ transaction://{name} - Transaction statistics              │
│  └─ trend://{metric}/{window} - Time series data               │
│                                                                  │
│  Prompts:                                                        │
│  ├─ analyze_test_failure - Template for failure analysis       │
│  ├─ compare_test_runs - Template for A/B comparison            │
│  └─ identify_root_cause - Root cause analysis guide            │
└────────────────────────┬────────────────────────────────────────┘
                         │
        ┌────────────────┴────────────────┐
        │                                  │
┌───────▼──────────┐            ┌─────────▼────────┐
│  PostgreSQL      │            │  Vector Store    │
│  (Source of      │            │  (RAG Layer)     │
│   Truth)         │            │                  │
│                  │            │  Embeddings:     │
│  Tables:         │◄───────────┤  - Test metadata │
│  - testrun       │  Sync      │  - Transactions  │
│  - test_summary  │            │  - Features      │
│  - baselines     │            │  - Outcomes      │
└──────────────────┘            │                  │
                                │  Tech:           │
                                │  - pgvector OR   │
                                │  - ChromaDB OR   │
                                │  - FAISS         │
                                └──────────────────┘
```

### Component Breakdown

#### 1. MCP Server Core
**Responsibility:** Expose test data and intelligence via MCP protocol

**Technology Stack:**
- **Framework:** `mcp` Python package (official SDK)
- **Transport:** stdio (local) + HTTP/SSE (remote)
- **Auth:** OAuth2 bearer tokens (Comcast SAT integration)
- **Config:** Environment-based (academic/work modes)

**Key Features:**
- Tool registration and discovery
- Request validation
- Rate limiting
- Logging and observability
- Error handling

#### 2. Vector Store (RAG Layer)
**Responsibility:** Enable semantic search over test data

**Embeddings Strategy:**
```python
# What to embed for each test:
test_vector = embed({
    "testplan": "LoadTest_20260304T060726Z",
    "description": "2000 users, build v2.8.14",
    "outcome": "FAIL",
    "exit_code": 2,
    "error_summary": "P95 > 2000ms on /auth/login",
    "key_transactions": ["/auth/login", "/api/checkout"],
    "features": {
        "fail_ratio": 0.023,
        "max_pct_deviation_p95": 0.85,
        ...
    },
    "root_cause_hints": "Authentication service slow"
})
```

**Technology Options:**

**Option A: pgvector (Recommended for work)**
- ✅ Native PostgreSQL extension
- ✅ Data stays in same database
- ✅ ACID guarantees
- ✅ Simple architecture
- ❌ Requires PostgreSQL >= 11 with extension

**Option B: ChromaDB (Recommended for academic)**
- ✅ Easy local setup
- ✅ Built-in embedding functions
- ✅ Good for demos
- ❌ Separate storage layer

**Option C: FAISS (Fallback)**
- ✅ Fast in-memory search
- ✅ No dependencies
- ❌ Need to persist separately
- ❌ Not distributed

**Recommendation:** pgvector for work mode, ChromaDB for academic mode

#### 3. Embedding Model
**Responsibility:** Convert test data to vectors

**Options:**

**For Academic Mode:**
- `text-embedding-3-small` (OpenAI) - $0.02/1M tokens, 1536 dims
- `text-embedding-3-large` (OpenAI) - Better quality, 3072 dims
- Local: `sentence-transformers/all-MiniLM-L6-v2` (free)

**For Work Mode:**
- Check if Comcast LLM Gateway supports embeddings API
- Fallback: Local model (no data leaves network)
- Option: Azure OpenAI (if approved)

**Recommendation:** Start with OpenAI for academic, evaluate Comcast options for work

#### 4. MCP Tools Design

**Tool 1: query_tests**
```typescript
{
  name: "query_tests",
  description: "Query performance tests with filters",
  inputSchema: {
    type: "object",
    properties: {
      date_from: { type: "string", format: "date" },
      date_to: { type: "string", format: "date" },
      exit_code: { type: "integer", enum: [1, 2, 3, 4] },
      build_version: { type: "string" },
      transaction_name: { type: "string" },
      limit: { type: "integer", default: 50, maximum: 1000 },
      sort_by: { type: "string", enum: ["date", "testplan", "exit_code"] }
    }
  }
}
```

**Tool 2: semantic_search**
```typescript
{
  name: "semantic_search",
  description: "Semantic search for similar test scenarios",
  inputSchema: {
    type: "object",
    properties: {
      query: {
        type: "string",
        description: "Natural language query (e.g., 'auth failures')"
      },
      filters: {
        type: "object",
        description: "Optional filters (exit_code, date_range)"
      },
      top_k: { type: "integer, default: 10, maximum: 50 }
    },
    required: ["query"]
  }
}
```

**Tool 3: explain_failure**
```typescript
{
  name: "explain_failure",
  description: "Get AI analysis of why a test failed",
  inputSchema: {
    type: "object",
    properties: {
      testplan: { type: "string", pattern: "^LoadTest_.*Z$" },
      include_similar: { type: "boolean", default: true },
      use_classifier: { type: "boolean", default: true }
    },
    required: ["testplan"]
  }
}
```

**Tool 4: compare_tests**
```typescript
{
  name: "compare_tests",
  description: "Compare two test runs to identify differences",
  inputSchema: {
    type: "object",
    properties: {
      test1: { type: "string" },
      test2: { type: "string" },
      focus: {
        type: "string",
        enum: ["all", "performance", "errors", "features"],
        default: "all"
      }
    },
    required: ["test1", "test2"]
  }
}
```

**Tool 5: get_test_trends**
```typescript
{
  name: "get_test_trends",
  description: "Get performance trends for a transaction",
  inputSchema: {
    type: "object",
    properties: {
      transaction_name: { type: "string" },
      metric: {
        type: "string",
        enum: ["p95", "avg", "error_rate", "throughput"]
      },
      days: { type: "integer", default: 30 }
    },
    required: ["transaction_name", "metric"]
  }
}
```

---

## Implementation Phases

### Phase 0: Prerequisites & Setup (1 hour)

**Tasks:**
1. Install MCP SDK: `pip install mcp`
2. Choose vector store (pgvector vs ChromaDB)
3. Set up embedding provider credentials
4. Create MCP server project structure

**Deliverables:**
- [ ] `mcp_server/` directory created
- [ ] Dependencies in `requirements-mcp.txt`
- [ ] `.env` updated with embedding API keys
- [ ] Development MCP config file

**File Structure:**
```
mcp_server/
├── __init__.py
├── server.py              # Main MCP server entry point
├── config.py              # Configuration management
├── tools/
│   ├── __init__.py
│   ├── query.py           # query_tests tool
│   ├── semantic.py        # semantic_search tool
│   ├── explain.py         # explain_failure tool
│   ├── compare.py         # compare_tests tool
│   └── trends.py          # get_test_trends tool
├── resources/
│   ├── __init__.py
│   └── test_resource.py   # test:// resource handler
├── rag/
│   ├── __init__.py
│   ├── embedder.py        # Embedding generation
│   ├── vector_store.py    # Vector DB abstraction
│   ├── indexer.py         # Batch indexing
│   └── retriever.py       # Similarity search
└── utils/
    ├── __init__.py
    ├── database.py        # PostgreSQL connection pool
    ├── cache.py           # Redis/in-memory cache
    └── auth.py            # OAuth token management
```

---

### Phase 1: MCP Server Foundation (2-3 hours)

**Goal:** Create basic MCP server that exposes PostgreSQL queries

**Step 1.1: Server Bootstrap**
```python
# mcp_server/server.py
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

app = Server("performance-test-intelligence")

@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="query_tests",
            description="Query performance tests with filters",
            inputSchema={ ... }
        ),
        # ... other tools
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "query_tests":
        return await query_tests(**arguments)
    # ... dispatch other tools

if __name__ == "__main__":
    stdio_server(app)
```

**Step 1.2: Database Connection**
```python
# mcp_server/utils/database.py
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool
import os

class DatabaseManager:
    def __init__(self):
        self.engine = create_engine(
            self._get_connection_string(),
            poolclass=QueuePool,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True
        )
    
    def _get_connection_string(self):
        if os.getenv('LLM_MODE') == 'work':
            return os.getenv('DATABASE_URL')
        else:
            # Academic mode: use local SQLite or sample data
            return "sqlite:///data/academic_tests.db"
    
    def query_tests(self, filters):
        # Use existing extract.py logic
        pass
```

**Step 1.3: First Tool - query_tests**
```python
# mcp_server/tools/query.py
from typing import Optional
import pandas as pd

async def query_tests(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    exit_code: Optional[int] = None,
    limit: int = 50
) -> dict:
    """Query tests with filters"""
    
    # Build SQL query
    query = """
        SELECT DISTINCT testplan, exit_code, build_version, end_time
        FROM testrun
        WHERE 1=1
    """
    params = {}
    
    if date_from:
        query += " AND end_time >= :date_from"
        params['date_from'] = date_from
    
    if exit_code:
        query += " AND exit_code = :exit_code"
        params['exit_code'] = exit_code
    
    query += " ORDER BY end_time DESC LIMIT :limit"
    params['limit'] = limit
    
    # Execute and return
    df = db.execute(query, params)
    
    return {
        "tests": df.to_dict('records'),
        "count": len(df),
        "filters_applied": {k: v for k, v in params.items() if v}
    }
```

**Testing Phase 1:**
```bash
# Start MCP server
python -m mcp_server.server

# Test with MCP Inspector (official tool)
npx @modelcontextprotocol/inspector python -m mcp_server.server

# Or use in Claude Desktop:
# Add to claude_desktop_config.json:
{
  "mcpServers": {
    "perf-tests": {
      "command": "python",
      "args": ["-m", "mcp_server.server"],
      "env": {
        "LLM_MODE": "work"
      }
    }
  }
}
```

**Deliverables:**
- [ ] MCP server runs without errors
- [ ] `query_tests` tool callable via MCP Inspector
- [ ] Returns test data from PostgreSQL
- [ ] Handles filters correctly

---

### Phase 2: RAG Implementation (3-4 hours)

**Goal:** Add semantic search capability using vector embeddings

**Step 2.1: Embedding Generator**
```python
# mcp_server/rag/embedder.py
from openai import OpenAI
import hashlib
import pickle
from pathlib import Path

class TestEmbedder:
    def __init__(self):
        self.client = OpenAI()  # Or Comcast gateway
        self.cache_dir = Path("mcp_server/.cache/embeddings")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def embed_test(self, test_data: dict) -> list[float]:
        """Generate embedding for a test"""
        
        # Create semantic representation
        text = self._create_embedding_text(test_data)
        
        # Check cache
        cache_key = hashlib.md5(text.encode()).hexdigest()
        cache_file = self.cache_dir / f"{cache_key}.pkl"
        
        if cache_file.exists():
            with open(cache_file, 'rb') as f:
                return pickle.load(f)
        
        # Generate embedding
        response = self.client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        
        embedding = response.data[0].embedding
        
        # Cache it
        with open(cache_file, 'wb') as f:
            pickle.dump(embedding, f)
        
        return embedding
    
    def _create_embedding_text(self, test_data: dict) -> str:
        """Convert test data to text for embedding"""
        
        # Include key information
        parts = [
            f"Test: {test_data['testplan']}",
            f"Result: {'PASS' if test_data['exit_code'] == 1 else 'FAIL'}",
            f"Version: {test_data.get('build_version', 'unknown')}",
        ]
        
        # Add transaction information
        if 'transactions' in test_data:
            slow_txns = [
                t['name'] for t in test_data['transactions']
                if t.get('perc_95', 0) > 2000
            ]
            if slow_txns:
                parts.append(f"Slow transactions: {', '.join(slow_txns)}")
        
        # Add feature highlights
        if 'features' in test_data:
            f = test_data['features']
            if f.get('fail_ratio', 0) > 0.01:
                parts.append(f"High error rate: {f['fail_ratio']:.1%}")
            if f.get('pct_txn_critical_p95', 0) > 0:
                parts.append(f"Critical P95 issues: {f['pct_txn_critical_p95']:.1%}")
        
        return " | ".join(parts)
```

**Step 2.2: Vector Store Integration**

**Option A: pgvector (Work Mode)**
```python
# mcp_server/rag/vector_store.py
from pgvector.sqlalchemy import Vector
from sqlalchemy import create_engine, Column, String, Integer
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class TestEmbedding(Base):
    __tablename__ = 'test_embeddings'
    
    testplan = Column(String, primary_key=True)
    embedding = Column(Vector(1536))  # text-embedding-3-small dimension
    exit_code = Column(Integer)
    metadata = Column(JSON)
    indexed_at = Column(DateTime, default=datetime.utcnow)

class PgVectorStore:
    def __init__(self, connection_string):
        self.engine = create_engine(connection_string)
        Base.metadata.create_all(self.engine)
    
    def upsert_embedding(self, testplan, embedding, metadata):
        with self.engine.begin() as conn:
            conn.execute(
                TestEmbedding.__table__.insert().values(
                    testplan=testplan,
                    embedding=embedding,
                    metadata=metadata
                ).on_conflict_do_update(
                    index_elements=['testplan'],
                    set_={'embedding': embedding, 'metadata': metadata}
                )
            )
    
    def search_similar(self, query_embedding, top_k=10, filters=None):
        with self.engine.connect() as conn:
            # Cosine similarity search
            stmt = select(
                TestEmbedding.testplan,
                TestEmbedding.metadata,
                TestEmbedding.embedding.cosine_distance(query_embedding).label('distance')
            ).order_by('distance').limit(top_k)
            
            if filters:
                if 'exit_code' in filters:
                    stmt = stmt.where(TestEmbedding.exit_code == filters['exit_code'])
            
            results = conn.execute(stmt).fetchall()
            
            return [
                {
                    'testplan': r.testplan,
                    'metadata': r.metadata,
                    'similarity': 1 - r.distance
                }
                for r in results
            ]
```

**Option B: ChromaDB (Academic Mode)**
```python
# mcp_server/rag/vector_store.py
import chromadb
from chromadb.config import Settings

class ChromaVectorStore:
    def __init__(self, persist_dir="mcp_server/.chroma_db"):
        self.client = chromadb.Client(Settings(
            persist_directory=persist_dir,
            anonymized_telemetry=False
        ))
        self.collection = self.client.get_or_create_collection(
            name="performance_tests",
            metadata={"hnsw:space": "cosine"}
        )
    
    def upsert_embedding(self, testplan, embedding, metadata):
        self.collection.upsert(
            ids=[testplan],
            embeddings=[embedding],
            metadatas=[metadata]
        )
    
    def search_similar(self, query_embedding, top_k=10, filters=None):
        where = filters if filters else None
        
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where
        )
        
        return [
            {
                'testplan': results['ids'][0][i],
                'metadata': results['metadatas'][0][i],
                'similarity': 1 - results['distances'][0][i]
            }
            for i in range(len(results['ids'][0]))
        ]
```

**Step 2.3: Batch Indexing Script**
```python
# mcp_server/rag/indexer.py
import asyncio
from tqdm import tqdm

async def index_all_tests():
    """Index all tests in the database"""
    
    db = DatabaseManager()
    embedder = TestEmbedder()
    vector_store = get_vector_store()  # Factory based on mode
    
    # Get all tests
    tests = db.query_tests(limit=10000)
    
    print(f"Indexing {len(tests)} tests...")
    
    for test in tqdm(tests):
        # Get full test details
        test_data = db.get_test_detail(test['testplan'])
        
        # Generate embedding
        embedding = embedder.embed_test(test_data)
        
        # Store in vector DB
        vector_store.upsert_embedding(
            testplan=test['testplan'],
            embedding=embedding,
            metadata={
                'exit_code': test['exit_code'],
                'build_version': test['build_version'],
                'end_time': test['end_time'].isoformat(),
                'num_transactions': test_data.get('num_transactions', 0)
            }
        )
    
    print("✅ Indexing complete!")

if __name__ == "__main__":
    asyncio.run(index_all_tests())
```

**Step 2.4: Semantic Search Tool**
```python
# mcp_server/tools/semantic.py

async def semantic_search(
    query: str,
    filters: Optional[dict] = None,
    top_k: int = 10
) -> dict:
    """Search for tests using natural language"""
    
    embedder = TestEmbedder()
    vector_store = get_vector_store()
    
    # Embed the query
    query_embedding = embedder.embed_text(query)
    
    # Search vector store
    results = vector_store.search_similar(
        query_embedding=query_embedding,
        top_k=top_k,
        filters=filters
    )
    
    # Enrich with details
    enriched_results = []
    for result in results:
        test_detail = await get_test_detail(result['testplan'])
        enriched_results.append({
            **test_detail,
            'similarity_score': result['similarity'],
            'relevance': 'high' if result['similarity'] > 0.8 else 'medium'
        })
    
    return {
        'query': query,
        'results': enriched_results,
        'count': len(enriched_results)
    }
```

**Testing Phase 2:**
```python
# Test semantic search
await semantic_search("authentication failures with high P95")
# Should return tests with auth issues and high response times

await semantic_search("sudden throughput drops", filters={'exit_code': 2})
# Should return failed tests with throughput problems
```

**Deliverables:**
- [ ] Embeddings generated for all tests
- [ ] Vector store populated
- [ ] `semantic_search` tool works
- [ ] Returns relevant tests for queries
- [ ] Sub-second query response time

---

### Phase 3: Advanced Tools (2 hours)

**Goal:** Implement remaining MCP tools

**Tool: explain_failure**
```python
# mcp_server/tools/explain.py

async def explain_failure(
    testplan: str,
    include_similar: bool = True,
    use_classifier: bool = True
) -> dict:
    """Comprehensive failure analysis"""
    
    # Get test details
    test_data = await get_test_detail(testplan)
    
    if test_data['exit_code'] == 1:
        return {"error": "Test passed, no failure to explain"}
    
    analysis = {
        "testplan": testplan,
        "exit_code": test_data['exit_code'],
        "analysis": {}
    }
    
    # Classifier prediction
    if use_classifier:
        from src.analyzer import TestAnalyzer
        analyzer = TestAnalyzer()
        prediction = analyzer.predict_test(testplan)
        analysis['classifier_prediction'] = prediction
    
    # Find similar failures
    if include_similar:
        similar = await semantic_search(
            f"failures like {testplan}",
            filters={'exit_code': test_data['exit_code']},
            top_k=5
        )
        analysis['similar_failures'] = similar['results']
    
    # LLM analysis
    llm_analysis = await generate_failure_analysis(test_data, analysis)
    analysis['llm_insights'] = llm_analysis
    
    return analysis
```

**Tool: compare_tests**
```python
# mcp_server/tools/compare.py

async def compare_tests(
    test1: str,
    test2: str,
    focus: str = "all"
) -> dict:
    """Compare two tests side-by-side"""
    
    # Get both tests
    data1 = await get_test_detail(test1)
    data2 = await get_test_detail(test2)
    
    comparison = {
        "test1": test1,
        "test2": test2,
        "differences": {}
    }
    
    # Outcome difference
    comparison['differences']['outcome'] = {
        'test1': 'PASS' if data1['exit_code'] == 1 else 'FAIL',
        'test2': 'PASS' if data2['exit_code'] == 1 else 'FAIL'
    }
    
    # Feature differences
    if focus in ['all', 'features']:
        from src.features import build_features
        f1 = build_features(data1['raw_data'])[0].iloc[0].to_dict()
        f2 = build_features(data2['raw_data'])[0].iloc[0].to_dict()
        
        significant_diffs = [
            {
                'feature': k,
                'test1': f1[k],
                'test2': f2[k],
                'delta': f2[k] - f1[k],
                'pct_change': ((f2[k] - f1[k]) / f1[k] * 100) if f1[k] != 0 else None
            }
            for k in f1.keys()
            if abs(f2[k] - f1[k]) > 0.01  # Significant difference threshold
        ]
        
        comparison['differences']['features'] = significant_diffs
    
    # Transaction-level comparison
    if focus in ['all', 'performance']:
        comparison['differences']['transactions'] = compare_transactions(
            data1['transactions'],
            data2['transactions']
        )
    
    return comparison
```

**Tool: get_test_trends**
```python
# mcp_server/tools/trends.py

async def get_test_trends(
    transaction_name: str,
    metric: str = "p95",
    days: int = 30
) -> dict:
    """Get performance trends over time"""
    
    # Query historical data
    query = """
        SELECT 
            DATE(end_time) as date,
            AVG(perc_95) as avg_p95,
            MAX(perc_95) as max_p95,
            AVG(error_percentage) as avg_error_rate
        FROM test_summary ts
        JOIN testrun tr ON ts.testplan = tr.testplan
        WHERE ts.transaction_name = :txn
          AND tr.end_time >= NOW() - INTERVAL :days DAY
        GROUP BY DATE(end_time)
        ORDER BY date
    """
    
    df = await db.query(query, {'txn': transaction_name, 'days': days})
    
    # Calculate trend
    import numpy as np
    x = np.arange(len(df))
    y = df[f'avg_{metric}'].values
    slope = np.polyfit(x, y, 1)[0]
    
    trend = {
        'transaction': transaction_name,
        'metric': metric,
        'period_days': days,
        'data_points': df.to_dict('records'),
        'trend': 'improving' if slope < 0 else 'degrading',
        'slope': float(slope),
        'current_value': float(y[-1]) if len(y) > 0 else None,
        'period_start_value': float(y[0]) if len(y) > 0 else None
    }
    
    return trend
```

**Deliverables:**
- [ ] All 5+ tools implemented
- [ ] Each tool tested individually
- [ ] Error handling robust
- [ ] Performance acceptable (<2s per call)

---

### Phase 4: Integration & Polish (1-2 hours)

**Goal:** Connect MCP server to existing apps, add auth, optimize

**Step 4.1: Update Streamlit to use MCP**
```python
# app_llm_demo.py - Update to use MCP client

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

class MCPTestAnalyzer:
    """Wrapper that uses MCP server instead of direct DB access"""
    
    def __init__(self):
        # Start MCP server as subprocess
        server_params = StdioServerParameters(
            command="python",
            args=["-m", "mcp_server.server"],
            env={"LLM_MODE": os.getenv("LLM_MODE")}
        )
        
        self.session = stdio_client(server_params)
        self.session.__enter__()
    
    async def analyze_test(self, testplan: str):
        # Call MCP tool
        result = await self.session.call_tool(
            "explain_failure",
            {"testplan": testplan, "include_similar": True}
        )
        return result
    
    async def search_tests(self, query: str):
        result = await self.session.call_tool(
            "semantic_search",
            {"query": query, "top_k": 10}
        )
        return result
```

**Step 4.2: Add Authentication**
```python
# mcp_server/utils/auth.py

class MCPAuthMiddleware:
    """Validate OAuth tokens for MCP requests"""
    
    def __init__(self, sat_url: str):
        self.sat_url = sat_url
        self.token_cache = {}
    
    async def validate_token(self, token: str) -> bool:
        # Check cache
        if token in self.token_cache:
            expiry = self.token_cache[token]
            if expiry > time.time():
                return True
        
        # Validate with SAT
        response = requests.post(
            f"{self.sat_url}/validate",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        if response.status_code == 200:
            # Cache for 50 minutes (tokens valid for 1 hour)
            self.token_cache[token] = time.time() + 3000
            return True
        
        return False
```

**Step 4.3: Add Caching Layer**
```python
# mcp_server/utils/cache.py

from functools import wraps
import hashlib
import json

class ToolCache:
    """Cache expensive tool calls"""
    
    def __init__(self, ttl_seconds=300):
        self.cache = {}
        self.ttl = ttl_seconds
    
    def cached_tool(self, func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Create cache key
            cache_key = hashlib.md5(
                json.dumps((func.__name__, args, kwargs), sort_keys=True).encode()
            ).hexdigest()
            
            # Check cache
            if cache_key in self.cache:
                result, timestamp = self.cache[cache_key]
                if time.time() - timestamp < self.ttl:
                    return result
            
            # Call function
            result = await func(*args, **kwargs)
            
            # Cache result
            self.cache[cache_key] = (result, time.time())
            
            return result
        
        return wrapper
```

**Step 4.4: Observability**
```python
# mcp_server/server.py - Add logging

import structlog

logger = structlog.get_logger()

@app.call_tool()
async def call_tool(name: str, arguments: dict):
    logger.info("tool_called", tool=name, args=arguments)
    
    start_time = time.time()
    try:
        result = await dispatch_tool(name, arguments)
        duration = time.time() - start_time
        
        logger.info("tool_completed", tool=name, duration=duration)
        return result
    
    except Exception as e:
        duration = time.time() - start_time
        logger.error("tool_failed", tool=name, error=str(e), duration=duration)
        raise
```

**Deliverables:**
- [ ] MCP server accessible from Streamlit
- [ ] Authentication working
- [ ] Caching reduces repeated queries
- [ ] Logs available for debugging
- [ ] Performance metrics tracked

---

## Testing Strategy

### Unit Tests
```python
# tests/test_mcp_tools.py

import pytest
from mcp_server.tools import query_tests, semantic_search

@pytest.mark.asyncio
async def test_query_tests_basic():
    result = await query_tests(limit=10)
    assert 'tests' in result
    assert len(result['tests']) <= 10

@pytest.mark.asyncio
async def test_semantic_search_relevance():
    result = await semantic_search("authentication failures")
    
    # Should return results
    assert result['count'] > 0
    
    # Results should be relevant
    for test in result['results']:
        assert 'auth' in test['testplan'].lower() or \
               'authentication' in str(test).lower()
```

### Integration Tests
```python
# tests/test_mcp_integration.py

async def test_end_to_end_failure_analysis():
    """Test full workflow: query → semantic search → explain"""
    
    # 1. Find recent failures
    failures = await query_tests(exit_code=2, limit=5)
    assert len(failures['tests']) > 0
    
    # 2. Pick one and explain
    testplan = failures['tests'][0]['testplan']
    explanation = await explain_failure(testplan)
    
    # 3. Should include similar failures
    assert 'similar_failures' in explanation
    assert len(explanation['similar_failures']) > 0
    
    # 4. Should have LLM insights
    assert 'llm_insights' in explanation
    assert len(explanation['llm_insights']) > 100  # Some substantial text
```

### Performance Benchmarks
```python
# tests/benchmark_mcp.py

async def benchmark_tools():
    """Measure tool performance"""
    
    benchmarks = {}
    
    # Benchmark semantic search
    start = time.time()
    await semantic_search("test", top_k=10)
    benchmarks['semantic_search_10'] = time.time() - start
    
    # Benchmark explain_failure
    start = time.time()
    await explain_failure("LoadTest_20260304T060726Z")
    benchmarks['explain_failure'] = time.time() - start
    
    # Assertions
    assert benchmarks['semantic_search_10'] < 1.0, "Semantic search too slow"
    assert benchmarks['explain_failure'] < 3.0, "Explain failure too slow"
    
    print(json.dumps(benchmarks, indent=2))
```

---

## Deployment

### Local Development
```bash
# Run MCP server locally
python -m mcp_server.server

# Test with MCP Inspector
npx @modelcontextprotocol/inspector python -m mcp_server.server
```

### Claude Desktop Integration
```json
// ~/.config/claude/claude_desktop_config.json
{
  "mcpServers": {
    "perf-tests": {
      "command": "python",
      "args": ["-m", "mcp_server.server"],
      "env": {
        "LLM_MODE": "work",
        "DATABASE_URL": "postgresql://...",
        "OPENAI_API_KEY": "..."
      }
    }
  }
}
```

### Production Deployment (Future)
```yaml
# docker-compose.yml
version: '3.8'
services:
  mcp-server:
    build: .
    ports:
      - "8080:8080"
    environment:
      - LLM_MODE=work
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
    depends_on:
      - postgres
      - redis
  
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      - POSTGRES_PASSWORD=${DB_PASSWORD}
  
  redis:
    image: redis:7-alpine
```

---

## Success Metrics

### Functional
- [ ] All 5+ MCP tools working
- [ ] Semantic search returns relevant results (>80% precision)
- [ ] End-to-end workflows complete successfully
- [ ] Works in both academic and work modes

### Performance
- [ ] Query tools: <500ms
- [ ] Semantic search: <1s for top-10
- [ ] Explain failure: <3s (includes LLM call)
- [ ] Batch indexing: <5min for 714 tests

### Quality
- [ ] Test coverage >80%
- [ ] No runtime errors in normal usage
- [ ] Graceful degradation when services unavailable
- [ ] Clear error messages

---

## Next Steps After Implementation

### Short-term Enhancements
1. **Add more tools:**
   - `find_anomalies` - Statistical anomaly detection
   - `suggest_actions` - Actionable recommendations
   - `export_report` - Generate PDF/HTML reports

2. **Improve RAG quality:**
   - Fine-tune embedding strategy
   - Add metadata filters
   - Implement re-ranking
   - Use hybrid search (keyword + semantic)

3. **Better caching:**
   - Redis for distributed cache
   - Cache vector search results
   - Precompute common queries

### Long-term Vision
1. **Real-time indexing:** Index tests as they complete (webhook)
2. **Multi-tenancy:** Support multiple teams/projects
3. **GraphQL API:** Alternative to MCP for web frontends
4. **Alerting:** Proactive notifications for anomalies
5. **CI/CD integration:** Auto-analyze test results in pipelines

---

## Resources & References

### MCP Documentation
- Official docs: https://modelcontextprotocol.io/
- Python SDK: https://github.com/modelcontextprotocol/python-sdk
- Examples: https://github.com/modelcontextprotocol/servers

### RAG & Embeddings
- OpenAI Embeddings: https://platform.openai.com/docs/guides/embeddings
- pgvector: https://github.com/pgvector/pgvector
- ChromaDB: https://docs.trychroma.com/
- Sentence Transformers: https://www.sbert.net/

### Related Projects
- LangChain MCP support: Coming soon
- AutoGPT MCP integration: In progress
- VS Code Copilot MCP: Experimental

---

## Timeline Estimate

| Phase | Tasks | Time | Dependencies |
|-------|-------|------|--------------|
| Phase 0 | Setup & prerequisites | 1 hour | None |
| Phase 1 | MCP server foundation | 2-3 hours | Phase 0 |
| Phase 2 | RAG implementation | 3-4 hours | Phase 1 |
| Phase 3 | Advanced tools | 2 hours | Phase 2 |
| Phase 4 | Integration & polish | 1-2 hours | Phase 3 |
| **Total** | **End-to-end** | **9-12 hours** | **~2 weeks calendar time** |

---

## Contact & Support

**Implementation Lead:** GitHub Copilot  
**Created:** March 15, 2026  
**Next Review:** When ready to begin implementation

**Ready to start?** Just say:
- "Let's implement Phase 0" - Begin setup
- "Start with Phase 1" - Jump to MCP server
- "Show me Phase 2 first" - Start with RAG
- "I need help with X" - Get specific guidance

---

**END OF PLAN**
