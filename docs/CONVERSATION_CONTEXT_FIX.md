# Conversation Context Fix

## Problem

When asking follow-up questions in the Streamlit app or Jupyter notebook, the LLM would lose context from previous questions. For example:

```
User: "What are the slowest transactions?"
LLM: "Here are the top 5 slowest transactions..."

User: "Why are they slow?"
LLM: "I don't have information about what 'they' refers to" ❌
```

## Root Cause

Both implementations were:
1. ✅ **Saving** conversation history to a list
2. ❌ **Not sending** that history to the LLM

The LLM only received the current question, so it had no memory of previous exchanges.

## Solution

Updated both implementations to send conversation history as proper message format:

**Before:**
```python
# Only send current question
response = llm.chat(
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": current_question}
    ]
)
```

**After:**
```python
# Build messages with conversation history
messages = [{"role": "system", "content": system_prompt}]

# Add previous Q&A (last 5 exchanges)
for prev_q, prev_a in conversation_history[-5:]:
    messages.append({"role": "user", "content": prev_q})
    messages.append({"role": "assistant", "content": prev_a})

# Add current question
messages.append({"role": "user", "content": current_question})

response = llm.chat(messages=messages)
```

## What Changed

### Streamlit App ([app_llm_demo.py](app_llm_demo.py))
- Updated `ask_llm_question()` function
- Now sends last 5 Q&A exchanges with each new question
- LLM can reference previous questions and answers

### Jupyter Notebook ([notebooks/llm_analysis_demo.ipynb](notebooks/llm_analysis_demo.ipynb))
- Updated `ask_question()` function in cell 3
- Same conversation history approach
- Added "Conversation depth" counter to output

## Testing

**Test conversation flow:**
```python
# Question 1
ask_question("What are the top 5 slowest transactions?")
# → Returns: /auth/login, /api/checkout, etc.

# Question 2 (follows up)
ask_question("Why is the first one slow?")
# → Now understands "first one" = /auth/login ✅

# Question 3 (follows up again)
ask_question("Are there any patterns in when it happens?")
# → Understands context from both previous questions ✅
```

## Benefits

✅ **Natural conversations** - Can use pronouns like "it", "they", "the first one"  
✅ **Follow-up questions** - "Why?", "Show me more", "What about X?"  
✅ **Context accumulation** - Each answer builds on previous knowledge  
✅ **Memory efficient** - Only keep last 5 exchanges (prevents token overflow)  

## Technical Details

- **History limit**: 5 exchanges (10 messages)
- **Token impact**: ~500-2000 tokens per request (manageable)
- **Conversation reset**: Clearing history removes context
- **Persistence**: History lost on app restart (by design)

## Example Conversation

```
User: "What patterns do you see in failed tests?"
LLM: "Failed tests show high P95 response times, especially in /auth/login (avg 2000ms) 
      and increased error rates in checkout flow (5-10%)."

User: "Are those two issues related?"
LLM: "Yes, likely related. The auth delays cascade to checkout because users must be
      authenticated before accessing cart. The 2000ms auth delay + network overhead 
      likely causes checkout timeouts."

User: "What would you recommend investigating first?"
LLM: "Start with the auth service. Since it's upstream and affects all subsequent requests,
      fixing /auth/login performance should improve checkout success rates as well."
```

## Files Modified

- `app_llm_demo.py` - Streamlit chat interface
- `notebooks/llm_analysis_demo.ipynb` - Jupyter Q&A helper
- `scripts/fix_notebook_context.py` - Automated notebook updater

## Verification

Run these to verify the fix:

**Streamlit:**
```bash
streamlit run app_llm_demo.py
# Go to Chat page, ask 2-3 related questions
```

**Jupyter:**
```bash
jupyter notebook notebooks/llm_analysis_demo.ipynb
# Run cells, use ask_question() with follow-ups
```

---

**Issue:** Conversation context not maintained between questions  
**Status:** ✅ Fixed  
**Affects:** Both Streamlit and Jupyter demos  
**Committed:** [commit hash]
