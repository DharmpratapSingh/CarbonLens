# How to Resolve API Naming Issues - Complete Guide

## Quick Summary

**Problem**: Parameter name mismatches between LLM, HTTP Bridge, and MCP Server
**Solution**: Standardize all layers to use `key_column` and `value_column`
**Status**: ✅ RESOLVED

---

## Step-by-Step Resolution

### Step 1: Identify the Problem
The issue manifests as API errors when temporal queries fail:
```
Error: "Invalid MCP response: Unable to parse JSON"
Detail: "'key_column' is a required property"
```

### Step 2: Check MCP Server Schema (Source of Truth)
The **MCP server defines the correct parameter names**:

**File**: `src/mcp_server_stdio.py` (lines 2063-2070)
```python
"metrics.yoy": {
    ...
    "properties": {
        "key_column": {"type": "string", "description": "Column to group by..."},
        "value_column": {"type": "string", "default": "emissions_tonnes"},
        ...
    },
    "required": ["file_id", "key_column"]
}
```

**Take-away**: MCP Server expects `key_column` and `value_column`

### Step 3: Fix the LLM System Prompt
The LLM must be taught the correct parameter names.

**File**: `src/run_llm.py` (around line 146-155)

**Fix**:
```python
# BEFORE (❌ WRONG):
4. metrics.yoy:
   {"tool":"metrics.yoy","args":{
     "file_id":"transport-country-year",
     "key_col":"country_name",        # ❌ WRONG
     "value_col":"emissions_tonnes",  # ❌ WRONG
     ...
   }}

# AFTER (✅ CORRECT):
4. metrics.yoy:
   {"tool":"metrics.yoy","args":{
     "file_id":"transport-country-year",
     "key_column":"country_name",     # ✅ CORRECT
     "value_column":"emissions_tonnes",  # ✅ CORRECT
     ...
   }}
```

### Step 4: Fix the HTTP Bridge Request Model
The HTTP bridge validates incoming requests and must use the same parameter names.

**File**: `src/mcp_http_bridge.py` (around line 508-515)

**Fix**:
```python
# BEFORE (❌ WRONG):
class YoYMetricsRequest(BaseModel):
    file_id: str
    key_col: str        # ❌ WRONG
    value_col: str      # ❌ WRONG
    ...

# AFTER (✅ CORRECT):
class YoYMetricsRequest(BaseModel):
    file_id: str
    key_column: str     # ✅ CORRECT
    value_column: str   # ✅ CORRECT
    ...
```

### Step 5: Restart Services
After making changes, restart the HTTP bridge to reload the new request model:

```bash
pkill -9 -f "mcp_http_bridge"
sleep 2
python src/mcp_http_bridge.py > mcp_bridge.log 2>&1 &
sleep 3
curl http://localhost:8010/health  # Should return "healthy"
```

### Step 6: Verify the Fix
Test the metrics.yoy endpoint with the new parameter names:

```bash
python -c "
import requests

payload = {
    'file_id': 'transport-country-year',
    'key_column': 'country_name',      # ✅ CORRECT
    'value_column': 'emissions_tonnes',  # ✅ CORRECT
    'base_year': 2020,
    'compare_year': 2023,
    'top_n': 5,
    'direction': 'drop'
}

response = requests.post('http://localhost:8010/metrics/yoy', json=payload)
print(f'Status: {response.status_code}')
if response.status_code == 200:
    print('✅ SUCCESS!')
else:
    print(f'❌ Error: {response.text}')
"
```

Expected output:
```
Status: 200
✅ SUCCESS!
```

---

## The Three Layers That Must Align

```
┌─────────────────────────────────────────────────────────────┐
│                  MCP SERVER (Source of Truth)                │
│              (src/mcp_server_stdio.py)                       │
│                                                              │
│    Parameters: key_column, value_column                      │
│    Line 2063-2070: Defines the schema                        │
│    Line 2998-2999: Receives and uses parameters              │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ↓ MUST MATCH
┌─────────────────────────────────────────────────────────────┐
│            HTTP BRIDGE (Request Validation)                  │
│              (src/mcp_http_bridge.py)                        │
│                                                              │
│    Class YoYMetricsRequest (lines 508-515)                   │
│    key_column: str                                           │
│    value_column: str                                         │
│                                                              │
│    This validates incoming API requests                      │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ↓ MUST MATCH
┌─────────────────────────────────────────────────────────────┐
│           LLM SYSTEM PROMPT (Instruction)                    │
│              (src/run_llm.py)                                │
│                                                              │
│    Lines 146-155: Example tool call                          │
│    "key_column": "country_name"                              │
│    "value_column": "emissions_tonnes"                        │
│                                                              │
│    This tells LLM what parameter names to use                │
└─────────────────────────────────────────────────────────────┘
```

---

## Common Mistakes & How to Avoid Them

### Mistake #1: Changing Only One Layer
❌ **DON'T DO THIS:**
```
❌ Fixed run_llm.py but forgot mcp_http_bridge.py
Result: LLM generates correct parameters, but API rejects them
```

✅ **DO THIS INSTEAD:**
```
✅ Fix ALL three layers:
   1. Verify MCP Server has the correct names (source of truth)
   2. Update HTTP Bridge request model
   3. Update LLM system prompt example
```

### Mistake #2: Using Abbreviations
❌ **DON'T USE:**
- `key_col` (abbreviation of key_column)
- `val_col` (abbreviation of value_column)
- `keyCol` (wrong case style)

✅ **ALWAYS USE:**
- `key_column` (full name, snake_case)
- `value_column` (full name, snake_case)

### Mistake #3: Not Restarting Services
❌ **If you don't restart the bridge**, Python won't reload the changed request model
```
# ❌ WRONG:
# Edit mcp_http_bridge.py but don't restart
# Result: Old request model still running

# ✅ CORRECT:
pkill -9 -f "mcp_http_bridge"  # Kill old process
sleep 2
python src/mcp_http_bridge.py &  # Start new process with new code
```

---

## Prevention Checklist

Before committing API changes:

- [ ] **Check MCP Server** - What parameters does it expect? (src/mcp_server_stdio.py)
- [ ] **Check HTTP Bridge** - Does the request model match? (src/mcp_http_bridge.py)
- [ ] **Check LLM Prompt** - Does the example use correct names? (src/run_llm.py)
- [ ] **Test the endpoint** - Does it accept the correct parameters?
- [ ] **Restart services** - Has the bridge been restarted with new code?
- [ ] **Document** - Have you updated API_PARAMETER_REFERENCE.md?

---

## Tools for Debugging

### 1. Test API Endpoint Directly
```bash
# Test with correct parameters
curl -X POST http://localhost:8010/metrics/yoy \
  -H "Content-Type: application/json" \
  -d '{"file_id":"transport-country-year","key_column":"country_name","value_column":"emissions_tonnes","base_year":2020,"compare_year":2023}'

# Should return: 200 OK
# Or: {"results": [...]}
```

### 2. Check HTTP Bridge Logs
```bash
tail -50 mcp_bridge.log

# Look for:
# ✅ "MCP Request: tools/call"
# ✅ "Status 200"
# ❌ "Error: key_column is a required property"
```

### 3. Verify MCP Server Schema
```bash
grep -n "key_column\|value_column" src/mcp_server_stdio.py | head -20
```

### 4. Test LLM Query
```bash
python src/run_llm.py "What is the trend in Pakistan's transport emissions from 2020 to 2023?"
```

---

## Reference Documents

- **API_PARAMETER_REFERENCE.md** - Complete reference for all API parameters
- **API_FIX_SUMMARY.md** - Detailed fix history and testing results
- **system_prompt.txt** - The full LLM system prompt (if using custom file)

---

## Quick Reference Table

| Component | File | Line(s) | Parameter | Correct Name |
|-----------|------|---------|-----------|--------------|
| MCP Server | src/mcp_server_stdio.py | 2063-2070 | (schema) | `key_column` |
| MCP Server | src/mcp_server_stdio.py | 2998 | (args) | `key_column` |
| HTTP Bridge | src/mcp_http_bridge.py | 510-511 | Model field | `key_column` |
| LLM Prompt | src/run_llm.py | 149 | Example | `key_column` |
| HTTP Bridge | src/mcp_http_bridge.py | 510-511 | Model field | `value_column` |
| LLM Prompt | src/run_llm.py | 150 | Example | `value_column` |

---

## Success Indicators

After applying all fixes, you should see:

✅ metrics.yoy endpoint returns 200 OK
✅ LLM generates temporal trend queries
✅ Queries return year-over-year change percentages
✅ Temporal trend analysis questions work correctly
✅ No more "Invalid MCP response" errors

---

## Support

If you encounter issues after following this guide:

1. **Check all three layers are synchronized** (MCP Server → HTTP Bridge → LLM Prompt)
2. **Restart the HTTP bridge** (services need to reload code)
3. **Test the API endpoint directly** (to isolate if it's a parameter issue)
4. **Check the logs** (mcp_bridge.log and console output)
5. **Verify parameter names** (use exact names from this guide)

