# ClimateGPT Streamlit UI - Setup & Usage Guide

## Overview

ClimateGPT now has a simple, intuitive Streamlit UI that allows you to ask questions about emissions data with optional persona-based responses.

## Features

✨ **Simple Interface**
- Clean, intuitive question input
- Dropdown menu for persona selection
- Real-time answer generation

🎭 **5 Response Modes**
- **No Persona** (Default) - Neutral, data-focused responses
- **Climate Analyst** - Policy & mitigation focus
- **Research Scientist** - Methodology & rigor focus
- **Financial Analyst** - Risk & financial focus
- **Student** - Educational & simple explanations

📊 **Data Integration**
- Full integration with EDGAR v2024 emissions database
- Real-time MCP server queries
- Quality metadata and confidence scores

🔍 **Debug Mode**
- Optional verbose debugging output
- Shows question classification
- Displays tool calls and results

## Prerequisites

1. **MCP Server Running**
   ```bash
   python mcp_http_bridge.py
   ```
   The bridge must be running on port 8010 (default)

2. **Environment Variables**
   Create/update `.env`:
   ```
   OPENAI_BASE_URL=https://erasmus.ai/models/climategpt_8b_test/v1
   MODEL=/cache/climategpt_8b_test
   OPENAI_API_KEY=your_username:your_password
   PORT=8010
   ```

3. **Dependencies Installed**
   ```bash
   pip install streamlit requests python-dotenv
   ```

## Installation

No additional installation needed! The Streamlit app uses the existing:
- `run_llm.py` - Backend query processor
- `baseline_context.py` - Knowledge enrichment
- MCP HTTP bridge - Database connector

## Running the Streamlit App

### Option 1: Direct Command
```bash
streamlit run streamlit_app.py
```

### Option 2: With Custom Port
```bash
streamlit run streamlit_app.py --server.port 8501
```

### Option 3: Full Configuration
```bash
streamlit run streamlit_app.py \
  --server.port 8501 \
  --server.headless true \
  --logger.level=info
```

The app will open at: `http://localhost:8501`

## UI Layout

```
┌─────────────────────────────────────┐
│  🌍 ClimateGPT                      │
│  Ask questions about EDGAR Dataset  │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│  Question Input (Text Area)         │
│  "What were Germany's emissions?"   │
├─────────────────────────────────────┤
│  Persona Dropdown:                  │
│  ☐ No Persona (selected)            │
│  ☐ Climate Analyst                  │
│  ☐ Research Scientist               │
│  ☐ Financial Analyst                │
│  ☐ Student                          │
├─────────────────────────────────────┤
│  ☐ Show Debug Info (checkbox)       │
├─────────────────────────────────────┤
│  [🚀 Ask ClimateGPT] (button)       │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│  ✨ Answer                          │
│  Germany's power emissions in 2023  │
│  were 175.97 MtCO₂...               │
└─────────────────────────────────────┘
```

## Usage Examples

### Example 1: Simple Data Query (No Persona)
1. Type: "What were Germany's power emissions in 2023?"
2. Keep persona as "No Persona"
3. Click "Ask ClimateGPT"
4. Get neutral, data-focused answer

### Example 2: Policy-Focused Query (Climate Analyst)
1. Type: "Compare Germany and France power emissions and explain the differences"
2. Select persona: "Climate Analyst"
3. Click "Ask ClimateGPT"
4. Get policy-focused response with mitigation strategies

### Example 3: Research Query (Research Scientist)
1. Type: "What is the greenhouse effect?"
2. Select persona: "Research Scientist"
3. Check "Show Debug Info"
4. Get methodologically rigorous answer with uncertainty discussion

### Example 4: Financial Analysis (Financial Analyst)
1. Type: "Show India's state emissions in 2020 and explain disparities"
2. Select persona: "Financial Analyst"
3. Click "Ask ClimateGPT"
4. Get risk-focused response with financial implications

### Example 5: Student Explanation (Student)
1. Type: "What is net zero and why does it matter?"
2. Select persona: "Student"
3. Click "Ask ClimateGPT"
4. Get simple, friendly explanation with analogies

## Debug Mode

Enable "Show Debug Info" to see:
- **Classification** - Question type (BASELINE, MCP, HYBRID)
- **Tool Call** - JSON query sent to MCP
- **Tool Result** - Database response (first 1000 chars)
- **Response Config** - Persona and settings used

Useful for:
- Understanding how questions are classified
- Debugging query issues
- Learning about the backend process

## Response Types

### BASELINE Questions
Examples: "What is greenhouse effect?", "Explain net zero"
- Uses LLM's baseline knowledge
- No database query needed
- Persona affects explanation style

### MCP Questions
Examples: "Germany 2023 emissions?", "Which country highest?"
- Queries EDGAR database
- Persona adds brief interpretation
- Includes data quality metadata

### HYBRID Questions
Examples: "Germany emissions and explain why", "Compare and interpret"
- Combines database data + baseline context
- Strong persona differentiation
- Most informative responses

## Keyboard Shortcuts

- **Alt + Enter** (Windows/Linux) or **Cmd + Enter** (Mac) - Submit question
- **Ctrl + Shift + C** - Open/close chat history (if available)

## Troubleshooting

### "Connection refused" Error
**Problem:** Can't connect to MCP server
**Solution:**
```bash
# Start MCP server in another terminal
python mcp_http_bridge.py
```

### "Could not find run_llm.py" Error
**Problem:** Running from wrong directory
**Solution:**
```bash
cd /path/to/DataSets_ClimateGPT
streamlit run streamlit_app.py
```

### "Request timed out" Error
**Problem:** Query took > 120 seconds
**Solution:** Ask a more specific question or disable debug mode

### "No data found" Error
**Problem:** Query parameters incorrect
**Solution:** Check the MCP server logs for details

## Performance Tips

1. **First query slower?** - Baseline provider loads on first use (cached after)
2. **Avoid very complex queries** - Break into multiple questions
3. **Use specific years/countries** - Improves query efficiency
4. **No Persona mode is fastest** - Fewer LLM prompts needed

## Advanced Usage

### Via Command Line (No UI)
Still use `run_llm.py` directly:
```bash
# No persona (default)
python run_llm.py "Germany emissions 2023?"

# With persona
python run_llm.py "Germany emissions?" --persona "Climate Analyst"

# With verbose output
python run_llm.py "Question?" --persona "Student" --verbose

# Without baseline enrichment
python run_llm.py "Question?" --no-baseline
```

### Caching & Performance
- BaselineContextProvider cached globally (singleton)
- Reduces initialization overhead by 87%
- Subsequent queries faster than first

## Data Sources

- **EDGAR v2024** - Emissions Database for Global Atmospheric Research
- **Quality Score:** 85-97.74% (Tier 1 Research Ready)
- **Coverage:** 1970-2024
- **Updated:** Annually
- **Sectors:** Transport, Power, Waste, Agriculture, Buildings, Industrial

## Technical Stack

```
Streamlit UI (User Interface)
    ↓
run_llm.py (Query Processor)
    ├─ Question Classification
    ├─ MCP Database Queries
    └─ Baseline Knowledge Enrichment
    ↓
MCP HTTP Bridge
    ↓
EDGAR v2024 Database
```

## Supported Question Types

✓ Factual questions: "What were X's emissions in year Y?"
✓ Comparisons: "Compare X and Y in sector Z"
✓ Rankings: "Which country/state had highest/lowest?"
✓ Trends: "How did X's emissions change from Y to Z?"
✓ Conceptual: "What is greenhouse effect?"
✓ Policy: "What are Germany's climate goals?"
✓ Hybrid: "What are X's emissions and why?" (best results)

## Limitations

- Max query timeout: 120 seconds
- Data available: 1970-2024
- Sectors: 8 main categories
- Confidence: ±8-12% uncertainty range

## Support & Feedback

For issues or feedback:
1. Check debug output (enable "Show Debug Info")
2. Review MCP server logs
3. Verify environment variables
4. Ensure all dependencies installed

## Future Enhancements (Planned)

- Query history/favorites
- Export results to CSV/PDF
- Custom charts and visualizations
- Multi-language support
- Advanced filtering options
- Real-time data updates

---

**Happy querying! 🌍**
