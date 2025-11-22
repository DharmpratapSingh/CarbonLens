# 🚀 Quick Start - ClimateGPT Streamlit UI

## In 3 Easy Steps

### Step 1: Start the MCP Server
Open a terminal and run:
```bash
python mcp_http_bridge.py
```
You should see output like:
```
Starting MCP HTTP Bridge...
Listening on http://127.0.0.1:8010
```

### Step 2: Start the Streamlit App
Open another terminal and run:
```bash
streamlit run streamlit_app.py
```
The app will open automatically in your browser at:
```
http://localhost:8501
```

### Step 3: Ask Questions!
1. Type your question in the text box
2. (Optional) Select a persona
3. Click "Ask ClimateGPT" button
4. Get your answer instantly!

---

## Example Questions to Try

### 💰 Financial Analyst Mode
```
Persona: Financial Analyst
Question: "Show me Germany's power emissions for 2023"
```
→ Gets risk-focused answer with financial implications

### 🎓 Student Mode
```
Persona: Student
Question: "What is the greenhouse effect?"
```
→ Gets friendly, easy-to-understand explanation with analogies

### 📋 Climate Analyst Mode
```
Persona: Climate Analyst
Question: "Compare Germany and France power emissions"
```
→ Gets policy-focused comparison with mitigation strategies

### 🔬 Research Scientist Mode
```
Persona: Research Scientist
Question: "What is net zero?"
Enable: Show Debug Info
```
→ Gets methodologically rigorous answer with methodology details

### 🌍 No Persona (Default)
```
Persona: No Persona
Question: "Which state in India had highest emissions in 2020?"
```
→ Gets neutral, data-focused answer

---

## Common Questions

**Q: Do I need to run both terminals?**
A: Yes! One for the MCP server, one for Streamlit app.

**Q: Can I change ports?**
A: Yes! For Streamlit:
```bash
streamlit run streamlit_app.py --server.port 9000
```

**Q: What's the "Show Debug Info" checkbox for?**
A: It shows the classification, tool calls, and database results - useful for learning how the system works.

**Q: How do I know if MCP server is working?**
A: If you see "Listening on http://127.0.0.1:8010" in the terminal, it's working!

**Q: The app says "Connection refused"**
A: Make sure MCP server is running in another terminal.

---

## Keyboard Tips

- **Focus on question box** - Click on the text area or Tab to it
- **Submit** - Click the "Ask ClimateGPT" button or use keyboard shortcut
- **Clear input** - Highlight all (Ctrl+A) and delete

---

## What You Can Ask

✅ **Fact questions:** "Germany power 2023?"
✅ **Comparisons:** "Compare Germany vs France"
✅ **Rankings:** "Top 5 US states by emissions"
✅ **Trends:** "How did X change from 2022 to 2023?"
✅ **Concepts:** "What is net zero?"
✅ **Analysis:** "Show data and explain why"

---

## Need Help?

1. **Check terminal windows** - Look for error messages
2. **Enable Debug Info** - See what's happening behind the scenes
3. **Simplify question** - Try more specific queries
4. **Check STREAMLIT_UI_GUIDE.md** - Full documentation

---

## Files in the System

```
DataSets_ClimateGPT/
├── streamlit_app.py              ← Main UI (this is what you run!)
├── run_llm.py                    ← Backend processor
├── mcp_http_bridge.py            ← Database connector
├── STREAMLIT_UI_GUIDE.md         ← Full documentation
└── QUICKSTART_STREAMLIT.md       ← This file
```

---

## Architecture

```
You (Web Browser)
    ↓
streamlit_app.py (UI)
    ↓ subprocess
run_llm.py (Process Questions)
    ↓ HTTP requests
mcp_http_bridge.py (Database API)
    ↓
EDGAR v2024 (Emissions Data)
```

---

## Done! 🎉

You're ready to use ClimateGPT!

Go to http://localhost:8501 and start asking questions about climate and emissions data.

**Have fun exploring! 🌍**
