# MCP Server - Performance Test Analysis

MCP (Model Context Protocol) server for querying and analyzing performance test data.

**Status**: ✅ Phase 1 Complete (Basic Tools - No RAG)

## Features

- **Works with CSV (academic mode)** and **PostgreSQL (work mode)**
- Three core tools for test analysis:
  - `query_tests` - Query test runs with filtering
  - `get_test_detail` - Get comprehensive test details
  - `compare_tests` - Compare two test runs

## Installation

```bash
# Install MCP SDK
pip install mcp

# Or install all requirements
pip install -r requirements.txt
```

## Usage

### Running the MCP Server

```bash
# Run directly
python -m mcp_server.server

# Test with MCP Inspector
npx @modelcontextprotocol/inspector python -m mcp_server.server
```

### Available Tools

#### 1. query_tests
Query test runs with optional filtering and sorting.

**Parameters:**
- `limit` (int): Maximum tests to return (default: 10)
- `exit_code` (int): Filter by exit code (1=PASS, 2+=FAIL)
- `sort_by` (str): Column to sort by (default: "end_time")
- `ascending` (bool): Sort order (default: False)

**Example:**
```json
{
  "limit": 5,
  "sort_by": "end_time",
  "ascending": false
}
```

**Use Cases:**
- "What are the last 5 test runs?" → `query_tests(limit=5)`
- "Show me failed tests" → `query_tests(exit_code=2)`

#### 2. get_test_detail
Get comprehensive details about a specific test.

**Parameters:**
- `testplan` (str): Test plan identifier

**Example:**
```json
{
  "testplan": "LoadTest_20260304T060726Z"
}
```

**Returns:**
- Test metadata
- All transactions with P95, avg RT, error rates
- Classifier prediction
- Formatted context for LLM

#### 3. compare_tests
Compare two test runs side-by-side.

**Parameters:**
- `testplan1` (str): First test identifier
- `testplan2` (str): Second test identifier

**Example:**
```json
{
  "testplan1": "LoadTest_001",
  "testplan2": "LoadTest_002"
}
```

**Returns:**
- Side-by-side metrics
- Performance deltas
- Result changes

## Configuration

The server automatically detects mode from `LLM_MODE` environment variable:
- `academic` - Uses CSV files from `data_exports/training_data.csv`
- `work` - Uses PostgreSQL database

No configuration changes needed!

## Testing

```bash
# Test individual tools
python3 mcp_server/test_tools.py

# Quick verification
python3 -c "from mcp_server.tools.query import query_tests; print(query_tests(limit=1))"
```

## Architecture

```
mcp_server/
├── __init__.py
├── __main__.py          # Module entry point
├── server.py            # MCP server (registers tools)
├── config.py            # Configuration
├── tools/
│   ├── __init__.py
│   ├── query.py         # query_tests tool
│   ├── detail.py        # get_test_detail tool
│   └── compare.py       # compare_tests tool
└── test_tools.py        # Tool tests
```

## Integration with Claude Desktop

Add to `~/.config/claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "perf-test-analyzer": {
      "command": "python",
      "args": ["-m", "mcp_server.server"],
      "cwd": "/path/to/A3_Code",
      "env": {
        "LLM_MODE": "academic"
      }
    }
  }
}
```

## What This Solves

**Before MCP:**
```python
# Manual pandas query + LLM call
last_5 = df.groupby('testplan').agg(...).head(5)
result = analyzer.ask("What are these?", data_context=last_5.to_string())
```

**With MCP (Phase 3):**
```
User: "What are the last 5 test runs?"
LLM: [autonomously calls query_tests(limit=5)]
LLM: [interprets real data, no hallucination]
```

## Next Steps

- **Phase 2 (RAG)**: Add semantic search with embeddings
- **Phase 3 (Pure MCP)**: Full LLM autonomy with tool chaining

## Troubleshooting

**Server won't start:**
- Check `pip install mcp` completed successfully
- Verify `.env` file exists with `LLM_MODE` set

**No data returned:**
- Verify `data_exports/training_data.csv` exists (academic mode)
- Check database connection (work mode)

**Tools load slowly:**
- TestAnalyzer initializes classifier on first use
- Subsequent calls are faster

## License

Same as parent project.
