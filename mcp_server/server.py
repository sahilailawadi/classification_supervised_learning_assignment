#!/usr/bin/env python3
"""
MCP Server for Performance Test Analysis

Entry point for the MCP server. Exposes tools for querying and analyzing test data.
Works with both CSV (academic mode) and PostgreSQL (work mode) data sources.

Usage:
    python -m mcp_server.server
    
    Or with MCP Inspector:
    npx @modelcontextprotocol/inspector python -m mcp_server.server
"""

import asyncio
import sys
from pathlib import Path

#Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from mcp.server import Server
from mcp.types import Tool, TextContent
import mcp.server.stdio

from mcp_server.tools.query import query_tests
from mcp_server.tools.detail import get_test_detail
from mcp_server.tools.compare import compare_tests
from mcp_server.config import SERVER_NAME, SERVER_VERSION, MODE


# Create server instance
app = Server(SERVER_NAME)


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available MCP tools"""
    return [
        Tool(
            name="query_tests",
            description="Query test runs with optional filtering and sorting. Get last N tests, failed tests, etc.",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of tests to return",
                        "default": 10
                    },
                    "exit_code": {
                        "type": "integer",
                        "description": "Filter by exit code (1=PASS, 2+=FAIL)",
                        "enum": [1, 2, 3, 4]
                    },
                    "sort_by": {
                        "type": "string",
                        "description": "Column to sort by",
                        "enum": ["end_time", "exit_code", "num_transactions", "perc_95", "error_percentage"],
                        "default": "end_time"
                    },
                    "ascending": {
                        "type": "boolean",
                        "description": "Sort ascending (True) or descending (False)",
                        "default": False
                    }
                }
            }
        ),
        Tool(
            name="get_test_detail",
            description="Get comprehensive details about a specific test including all transactions, metrics, and classifier predictions",
            inputSchema={
                "type": "object",
                "properties": {
                    "testplan": {
                        "type": "string",
                        "description": "Test plan identifier"
                    }
                },
                "required": ["testplan"]
            }
        ),
        Tool(
            name="compare_tests",
            description="Compare two test runs side-by-side to identify performance differences and changes",
            inputSchema={
                "type": "object",
                "properties": {
                    "testplan1": {
                        "type": "string",
                        "description": "First test identifier"
                    },
                    "testplan2": {
                        "type": "string",
                        "description": "Second test identifier"
                    }
                },
                "required": ["testplan1", "testplan2"]
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls"""
    
    try:
        if name == "query_tests":
            result = query_tests(
                limit=arguments.get('limit', 10),
                exit_code=arguments.get('exit_code'),
                sort_by=arguments.get('sort_by', 'end_time'),
                ascending=arguments.get('ascending', False)
            )
        
        elif name == "get_test_detail":
            result = get_test_detail(arguments['testplan'])
        
        elif name == "compare_tests":
            result = compare_tests(arguments['testplan1'], arguments['testplan2'])
        
        else:
            result = {'error': f'Unknown tool: {name}'}
        
        # Format response
        import json
        return [TextContent(
            type="text",
            text=json.dumps(result, indent=2)
        )]
    
    except Exception as e:
        return [TextContent(
            type="text",
            text=json.dumps({'error': str(e)}, indent=2)
        )]


async def main():
    """Run the MCP server"""
    print(f"🚀 Starting {SERVER_NAME} v{SERVER_VERSION}", file=sys.stderr)
    print(f"   Mode: {MODE}", file=sys.stderr)
    print(f"   Ready for MCP connections", file=sys.stderr)
    
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
