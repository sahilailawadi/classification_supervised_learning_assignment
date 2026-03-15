#!/usr/bin/env python3
"""Add ask_about_test helper function to Jupyter notebook"""

import json

# Read notebook
with open('notebooks/llm_analysis_demo.ipynb') as f:
    nb = json.load(f)

# Find ask_question cell
ask_q_idx = None
for i, cell in enumerate(nb['cells']):
    if cell['cell_type'] == 'code':
        source = ''.join(cell['source'])
        if 'def ask_question' in source and 'conversation_history' in source:
            ask_q_idx = i
            print(f'Found ask_question cell at index {i}')
            break

if ask_q_idx is None:
    print('Error: ask_question cell not found')
    exit(1)

# Create new cell with ask_about_test helper
helper_cell = {
    'cell_type': 'code',
    'execution_count': None,
    'metadata': {},
    'outputs': [],
    'source': [
        '# Helper function to prevent hallucination by fetching real test data\n',
        'def ask_about_test(test_id_or_index, question):\n',
        '    """\n',
        '    Ask a question about a specific test.\n',
        '    Fetches real test data to prevent LLM hallucination.\n',
        '    \n',
        '    Args:\n',
        '        test_id_or_index: Test index (0-713) or testplan ID string\n',
        '        question: Your question about the test\n',
        '    \n',
        '    Example:\n',
        '        ask_about_test(0, "What are the slowest transactions?")\n',
        '        ask_about_test("LoadTest_20260304T060726Z", "Why did this test fail?")\n',
        '    """\n',
        '    # Get testplan ID\n',
        '    if isinstance(test_id_or_index, int):\n',
        '        testplan = df.iloc[test_id_or_index]["testplan"]\n',
        '    else:\n',
        '        testplan = test_id_or_index\n',
        '    \n',
        '    # Fetch real test data\n',
        '    test_data = df[df["testplan"] == testplan]\n',
        '    \n',
        '    if len(test_data) == 0:\n',
        '        return f"Test {testplan} not found in dataset"\n',
        '    \n',
        '    # Get test metadata\n',
        '    test_info = test_data.iloc[0]\n',
        '    \n',
        '    # Build context with real transaction data\n',
        '    context_parts = [\n',
        '        f"Test Plan: {testplan}",\n',
        '        f"Exit Code: {test_info[\'exit_code\']}",\n',
        '        f"Result: {\'PASS\' if test_info[\'exit_code\'] == 1 else \'FAIL\'}",\n',
        '        f"Duration: {test_info.get(\'duration_sec\', \'N/A\')} seconds",\n',
        '        "",\n',
        '        "Transaction Performance (sorted by P95):",\n',
        '    ]\n',
        '    \n',
        '    # Get all transactions for this test, sorted by P95\n',
        '    transactions = df[df["testplan"] == testplan].copy()\n',
        '    transactions = transactions.sort_values("perc_95", ascending=False)\n',
        '    \n',
        '    for idx, txn in transactions.iterrows():\n',
        '        context_parts.append(\n',
        '            f"  - {txn[\'transaction_name\']}: "\n',
        '            f"P95={txn[\'perc_95\']}ms, "\n',
        '            f"Avg={txn[\'avg_response_time\']}ms, "\n',
        '            f"Errors={txn[\'error_percentage\']}%"\n',
        '        )\n',
        '    \n',
        '    full_context = "\\n".join(context_parts)\n',
        '    \n',
        '    # Ask LLM with real data\n',
        '    enriched_question = f"{full_context}\\n\\nQuestion: {question}"\n',
        '    \n',
        '    return ask_question(enriched_question)\n'
    ]
}

# Insert after ask_question cell
nb['cells'].insert(ask_q_idx + 1, helper_cell)

# Save notebook
with open('notebooks/llm_analysis_demo.ipynb', 'w') as f:
    json.dump(nb, f, indent=1)

print('✅ Added ask_about_test helper function')
print(f'   Cell inserted at position {ask_q_idx + 1}')
print('\n📝 Usage examples:')
print('   ask_about_test(0, "What are the slowest transactions?")')
print('   ask_about_test("LoadTest_20260304T060726Z", "Why did this fail?")')
