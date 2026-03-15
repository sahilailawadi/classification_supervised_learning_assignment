#!/usr/bin/env python3
"""
Fix conversation context in Jupyter notebook

Updates the ask_question function to maintain proper conversation history
by sending previous messages to the LLM instead of just summarizing them.
"""

import json
from pathlib import Path

notebook_path = Path(__file__).parent.parent / "notebooks" / "llm_analysis_demo.ipynb"

# Read notebook
with open(notebook_path, 'r') as f:
    notebook = json.load(f)

# Find and update the ask_question cell
for cell in notebook['cells']:
    if cell['cell_type'] == 'code':
        source = ''.join(cell['source'])
        
        # Check if this is the ask_question function cell
        if 'def ask_question(question: str, include_data_context: bool = True):' in source:
            print(f"Found ask_question cell (id: {cell.get('id', 'unknown')})")
            
            # Replace the cell source with fixed version
            cell['source'] = [
                "# Conversation history\n",
                "conversation_history = []\n",
                "\n",
                "def ask_question(question: str, include_data_context: bool = True):\n",
                "    \"\"\"\n",
                "    Ask a question about test data and get LLM response.\n",
                "    \n",
                "    Args:\n",
                "        question: Your question in natural language\n",
                "        include_data_context: Whether to include dataset statistics\n",
                "    \"\"\"\n",
                "    # Build system prompt\n",
                "    system_prompt = \"\"\"You are an expert performance test analyst helping analyze test results.\n",
                "\n",
                "Answer questions about:\n",
                "- Test trends and patterns\n",
                "- Transaction performance\n",
                "- Failure analysis\n",
                "- Comparisons and anomalies\n",
                "\n",
                "Use the provided data context. Be concise but informative. Use bullet points.\n",
                "Maintain conversation context and reference previous questions when relevant.\"\"\"\n",
                "    \n",
                "    # Build dataset context\n",
                "    context_parts = []\n",
                "    \n",
                "    if include_data_context:\n",
                "        # Add dataset statistics\n",
                "        context_parts.append(f\"\"\"\n",
                "Dataset Context:\n",
                "- Total tests: {df['testplan'].nunique()}\n",
                "- Total transactions/rows: {len(df):,}\n",
                "- Unique transaction types: {df['transaction_name'].nunique()}\n",
                "- Pass/Fail distribution: {(df.groupby('exit_code')['testplan'].nunique().to_dict())}\n",
                "- Date range: {df['end_time'].min()} to {df['end_time'].max()}\n",
                "\n",
                "Available transactions:\n",
                "{', '.join(df['transaction_name'].unique()[:20])}\n",
                "{'...(and more)' if df['transaction_name'].nunique() > 20 else ''}\n",
                "\"\"\")\n",
                "    \n",
                "    # Build messages with conversation history\n",
                "    messages = [{\"role\": \"system\", \"content\": system_prompt}]\n",
                "    \n",
                "    # Add conversation history (last 5 exchanges to keep context manageable)\n",
                "    for prev_q, prev_a in conversation_history[-5:]:\n",
                "        messages.append({\"role\": \"user\", \"content\": prev_q})\n",
                "        messages.append({\"role\": \"assistant\", \"content\": prev_a})\n",
                "    \n",
                "    # Add current question with dataset context\n",
                "    current_prompt = \"\\n\".join(context_parts) + f\"\\n\\nQuestion: {question}\"\n",
                "    messages.append({\"role\": \"user\", \"content\": current_prompt})\n",
                "    \n",
                "    # Query LLM\n",
                "    print(f\"🤔 Question: {question}\")\n",
                "    print(\"   🤖 Thinking...\")\n",
                "    \n",
                "    response = llm.chat(\n",
                "        messages=messages,\n",
                "        temperature=0.7\n",
                "    )\n",
                "    \n",
                "    answer = response.content\n",
                "    \n",
                "    # Save to history\n",
                "    conversation_history.append((question, answer))\n",
                "    \n",
                "    # Display\n",
                "    print(f\"\\n💡 Answer:\")\n",
                "    print(answer)\n",
                "    print(f\"\\n   Tokens used: {response.tokens_used or 'N/A'}\")\n",
                "    print(f\"   Conversation depth: {len(conversation_history)} exchanges\")\n",
                "    print(\"-\" * 80)\n",
                "    \n",
                "    return answer\n",
                "\n",
                "# Example usage\n",
                "print(\"✅ Helper function loaded!\")\n",
                "print(\"\\nExample: ask_question('What are the most common transaction failures?')\")"
            ]
            
            print("✅ Cell updated!")
            break

# Write updated notebook
with open(notebook_path, 'w') as f:
    json.dump(notebook, f, indent=1)

print(f"✅ Notebook saved: {notebook_path}")
print("\nWhat changed:")
print("- Conversation history now sent as separate messages to LLM")
print("- Previous Q&A exchanges maintain context properly")
print("- Last 5 exchanges kept (prevents context overflow)")
print("- Added 'Conversation depth' to output")
