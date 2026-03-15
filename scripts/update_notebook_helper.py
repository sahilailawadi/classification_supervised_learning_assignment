#!/usr/bin/env python3
"""Update ask_about_test in notebook to use analyzer.get_test_context()"""

import json

# Read notebook
with open('notebooks/llm_analysis_demo.ipynb') as f:
    nb = json.load(f)

# Find the ask_about_test cell
for i, cell in enumerate(nb['cells']):
    if cell['cell_type'] == 'code':
        source = ''.join(cell['source'])
        if 'def ask_about_test' in source and 'Helper function to prevent hallucination' in source:
            # Replace with new implementation
            cell['source'] = [
                '# Helper function to prevent hallucination by fetching real test data\n',
                'def ask_about_test(test_id_or_index, question):\n',
                '    """\n',
                '    Ask a question about a specific test.\n',
                '    Fetches real test data to prevent LLM hallucination.\n',
                '    \n',
                '    Uses analyzer.get_test_context() for consistent behavior\n',
                '    across Streamlit UI and Jupyter notebook.\n',
                '    \n',
                '    Args:\n',
                '        test_id_or_index: Test index (0-713) or testplan ID string\n',
                '        question: Your question about the test\n',
                '    \n',
                '    Example:\n',
                '        ask_about_test(0, "What are the slowest transactions?")\n',
                '        ask_about_test("LoadTest_20260304T060726Z", "Why did this test fail?")\n',
                '    """\n',
                '    try:\n',
                '        # Get detailed test context with real data from analyzer\n',
                '        test_context = analyzer.get_test_context(test_id_or_index)\n',
                '        \n',
                '        # Build full prompt with test details\n',
                '        enriched_question = f"{test_context}\\n\\n---\\n\\n**Question:** {question}"\n',
                '        \n',
                '        # Use the regular ask function (which handles conversation history)\n',
                '        return ask_question(enriched_question, include_data_context=False)\n',
                '    \n',
                '    except Exception as e:\n',
                '        print(f"❌ Error: {e}")\n',
                '        return None\n',
                '\n',
                'print("✅ ask_about_test() helper loaded!")\n',
                'print("   Uses analyzer.get_test_context() - same implementation as Streamlit UI")\n'
            ]
            print(f"✅ Updated ask_about_test function in cell {i}")
            break
else:
    print("❌ ask_about_test cell not found")
    exit(1)

# Save notebook
with open('notebooks/llm_analysis_demo.ipynb', 'w') as f:
    json.dump(nb, f, indent=1)

print("✅ Notebook saved")
print("\n📝 The helper now uses:")
print("   analyzer.get_test_context(testplan_or_index)")
print("   - Consistent with Streamlit implementation")
print("   - Handles both test index and testplan ID")
print("   - Includes all transaction details")
