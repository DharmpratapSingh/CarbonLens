# 🚀 ClimateGPT QuickStart Guide

## Problem: Not Getting Answers?

If you're experiencing issues with the Streamlit UI not returning answers, follow these steps:

---

## ⚡ Quick Fix (3 Steps)

### Step 1: Check Current Status
```bash
python check_setup.py
```

This will show you exactly what's wrong.

### Step 2: Install Dependencies (if needed)
```bash
pip install streamlit requests fastapi pandas altair python-dotenv uvicorn
```

### Step 3: Set Your API Credentials

Edit `.env` file:
```bash
nano .env
```

Change this line:
```bash
OPENAI_API_KEY=your_username:your_password
```

To your actual credentials from https://erasmus.ai

**Example:**
```bash
OPENAI_API_KEY=john.doe@example.com:MySecurePass123
```

⚠️ **Important:** The format MUST be `username:password` with a colon `:` in the middle.

---

## 🎯 Start the Application

### Option A: Automatic (Recommended)
```bash
./setup_and_start.sh
```

This will:
- Validate your configuration
- Start MCP Bridge (port 8010)
- Start Streamlit UI (port 8501)
- Open logs in `logs/` directory

### Option B: Manual

**Terminal 1 - Start MCP Bridge:**
```bash
python mcp_http_bridge.py
```

**Terminal 2 - Start Streamlit:**
```bash
streamlit run enhanced_climategpt_with_personas.py
```

---

## 🌐 Access the Application

Once started, open your browser to:
```
http://localhost:8501
```

You should see:
- 🟢 Green status indicators for MCP and LLM
- A persona selector (Climate Analyst, Research Scientist, etc.)
- A chat input box at the bottom

---

## ✅ Test Your Setup

Try asking this question:
```
What were the top 5 countries for transport emissions in 2023?
```

**Expected Result:**
- You should get a response within 5-10 seconds
- The response should include actual numbers (MtCO₂)
- It should be formatted according to your selected persona
- You should see response time at the bottom

---

## 🔧 Common Issues

### Issue 1: "OPENAI_API_KEY is not set correctly"

**Fix:**
```bash
# Edit .env file
nano .env

# Make sure the line looks like:
OPENAI_API_KEY=your_username:your_password

# NOT like:
OPENAI_API_KEY="your_username:your_password"  # ❌ No quotes
OPENAI_API_KEY=your_username your_password     # ❌ No space
```

### Issue 2: "Missing Python package"

**Fix:**
```bash
pip install streamlit requests fastapi pandas altair python-dotenv uvicorn
```

### Issue 3: "MCP Bridge not running"

**Fix:**
```bash
# In a separate terminal:
python mcp_http_bridge.py

# Check if it's running:
curl http://localhost:8010/health
# Should return: {"status":"healthy","mcp_server":"running"}
```

### Issue 4: Port already in use

**Fix:**
```bash
# Kill existing processes
pkill -f mcp_http_bridge
pkill -f streamlit

# Then restart
./setup_and_start.sh
```

---

## 📊 Architecture (What's Happening Behind the Scenes)

When you ask a question:

1. **Streamlit UI** (port 8501) receives your question
2. Sends it to **MCP HTTP Bridge** (port 8010)
3. Bridge converts HTTP → **MCP Protocol** (stdio)
4. **MCP Server** queries the **DuckDB** emissions database
5. Results flow back through the chain
6. **Persona Engine** formats the response according to your selected persona
7. You see the answer in the UI!

---

## 🎓 Understanding the Personas

ClimateGPT has 4 personas that shape how answers are presented:

1. **📈 Climate Analyst** - Focus on actionable insights and policy
2. **🔬 Research Scientist** - Emphasis on methodology and data quality
3. **💼 Financial Analyst** - Risk signals and trends for investors
4. **🎓 Student** - Simple, educational explanations

Select the persona that matches your needs using the dropdown in the UI.

---

## 📝 Logs & Debugging

Logs are stored in `logs/` directory:

```bash
# Watch MCP Bridge logs
tail -f logs/mcp_bridge.log

# Watch Streamlit logs
tail -f logs/streamlit.log

# Search for errors
grep -i error logs/*.log
```

---

## 🛑 Stopping the Application

### If started with `setup_and_start.sh`:
Press `Ctrl+C` in the terminal

### If started manually:
```bash
pkill -f mcp_http_bridge
pkill -f streamlit
```

---

## 🆘 Still Having Issues?

1. **Run the diagnostic:**
   ```bash
   python check_setup.py
   ```

2. **Check the detailed setup guide:**
   ```bash
   cat SETUP_INSTRUCTIONS.md
   ```

3. **Verify environment variables:**
   ```bash
   source .env
   env | grep -E "(OPENAI_|MCP_)"
   ```

4. **Test MCP Bridge health:**
   ```bash
   curl -v http://localhost:8010/health
   ```

5. **Check processes:**
   ```bash
   ps aux | grep -E "(mcp_http_bridge|streamlit)" | grep -v grep
   ```

---

## 📚 Additional Resources

- `SETUP_INSTRUCTIONS.md` - Detailed setup instructions
- `check_setup.py` - Automated diagnostic tool
- `setup_and_start.sh` - Automated startup script
- `.env` - Environment configuration

---

## ✨ You're All Set!

Once everything is green in `check_setup.py` and both services are running, you're ready to explore climate emissions data with ClimateGPT!

Happy exploring! 🌍
