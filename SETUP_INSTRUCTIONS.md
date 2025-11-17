# ClimateGPT Setup Instructions

## 🚨 Issue: Not Getting Answers in Streamlit UI

If you're not getting answers when asking questions via the Streamlit UI, it's likely because:

1. **Missing Environment Variables** - The `OPENAI_API_KEY` is not set
2. **Services Not Running** - MCP server and Streamlit are not started
3. **Connection Issues** - The UI can't reach the MCP server

---

## ✅ Solution: Quick Setup

### Step 1: Set Up Environment Variables

1. **Edit the `.env` file:**
   ```bash
   nano .env
   ```

2. **Set your ClimateGPT API credentials:**
   ```bash
   # Replace with your actual credentials
   OPENAI_API_KEY=your_username:your_password
   ```

3. **Get credentials:**
   - Visit: https://erasmus.ai
   - Log in and get your API credentials
   - Format: `username:password`

### Step 2: Start the Application

**Option A: Automated Startup (Recommended)**
```bash
./setup_and_start.sh
```

This script will:
- ✅ Validate your environment configuration
- ✅ Start the MCP HTTP Bridge server (port 8010)
- ✅ Start the Streamlit UI (port 8501)
- ✅ Check health status
- ✅ Show you the URLs to access

**Option B: Manual Startup**
```bash
# Terminal 1: Start MCP Bridge
python mcp_http_bridge.py

# Terminal 2: Start Streamlit (in a new terminal)
streamlit run enhanced_climategpt_with_personas.py
```

### Step 3: Access the Application

Open your browser and navigate to:
```
http://localhost:8501
```

---

## 🔍 Troubleshooting

### Issue: "OPENAI_API_KEY environment variable is required"

**Solution:**
1. Make sure `.env` file exists in the project root
2. Check that `OPENAI_API_KEY` is set in the format `username:password`
3. Ensure no extra spaces or quotes around the value

### Issue: "Connection failed. Please check if the MCP server is running"

**Solution:**
1. Check if MCP Bridge is running:
   ```bash
   curl http://localhost:8010/health
   ```
   Should return: `{"status":"healthy","mcp_server":"running"}`

2. If not running, start it:
   ```bash
   python mcp_http_bridge.py
   ```

3. Check the logs:
   ```bash
   tail -f logs/mcp_bridge.log
   ```

### Issue: "Request timed out" or "No response"

**Causes:**
1. MCP server not running
2. Network connectivity issues
3. API credentials incorrect

**Solution:**
1. Restart both services:
   ```bash
   pkill -f mcp_http_bridge
   pkill -f streamlit
   ./setup_and_start.sh
   ```

2. Verify environment variables:
   ```bash
   source .env
   echo $OPENAI_API_KEY
   echo $MCP_URL
   echo $OPENAI_BASE_URL
   ```

### Issue: Port already in use

**Solution:**
```bash
# Kill existing processes
pkill -f mcp_http_bridge
pkill -f streamlit

# Or find and kill specific ports
lsof -ti:8010 | xargs kill -9  # MCP Bridge
lsof -ti:8501 | xargs kill -9  # Streamlit
```

---

## 🏗️ Architecture Overview

```
┌─────────────────┐
│  Streamlit UI   │  http://localhost:8501
│  (Port 8501)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  MCP HTTP       │  http://localhost:8010
│  Bridge         │  (FastAPI wrapper)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  MCP Server     │  stdio protocol
│  (stdio)        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  DuckDB         │
│  (Emissions DB) │
└─────────────────┘
```

**Data Flow:**
1. User asks question in Streamlit UI
2. UI sends request to MCP HTTP Bridge
3. Bridge converts HTTP → MCP protocol (stdio)
4. MCP Server queries DuckDB
5. Response flows back up the chain

---

## 🔧 Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | ✅ Yes | - | ClimateGPT API credentials (`username:password`) |
| `OPENAI_BASE_URL` | No | `https://erasmus.ai/models/climategpt_8b_test/v1` | ClimateGPT API base URL |
| `MODEL` | No | `/cache/climategpt_8b_test` | Model path |
| `MCP_URL` | No | `http://127.0.0.1:8010` | MCP Bridge URL |
| `ENVIRONMENT` | No | `development` | Environment mode |
| `LOG_LEVEL` | No | `INFO` | Logging level |
| `LLM_MAX_CONCURRENCY` | No | `2` | Max concurrent LLM requests |
| `MCP_TOOL_CACHE_SIZE` | No | `256` | MCP response cache size |

---

## 📊 Verification Checklist

- [ ] `.env` file exists and contains `OPENAI_API_KEY`
- [ ] API key is in format `username:password`
- [ ] MCP Bridge is running on port 8010
- [ ] Streamlit UI is running on port 8501
- [ ] Can access http://localhost:8010/health
- [ ] Can access http://localhost:8501
- [ ] Status indicators show green in Streamlit UI
- [ ] Test question returns an answer

---

## 🚀 Quick Test

Once everything is running, try this test question in the Streamlit UI:

```
What were the top 5 countries for transport emissions in 2023?
```

**Expected Result:**
- You should see a response with actual data
- Response time should be displayed
- Data should be formatted according to your selected persona

---

## 📝 Logs Location

Logs are stored in the `logs/` directory:
- `logs/mcp_bridge.log` - MCP HTTP Bridge logs
- `logs/streamlit.log` - Streamlit application logs

View logs in real-time:
```bash
tail -f logs/mcp_bridge.log
tail -f logs/streamlit.log
```

---

## 💡 Additional Help

If you still have issues after following these steps:

1. **Check process status:**
   ```bash
   ps aux | grep -E "(mcp_http_bridge|streamlit)" | grep -v grep
   ```

2. **Check network connectivity:**
   ```bash
   curl -v http://localhost:8010/health
   curl -v http://localhost:8501
   ```

3. **Review logs for errors:**
   ```bash
   cat logs/mcp_bridge.log | grep -i error
   cat logs/streamlit.log | grep -i error
   ```

4. **Restart everything:**
   ```bash
   ./setup_and_start.sh
   ```

---

## 📚 Related Files

- `enhanced_climategpt_with_personas.py` - Main Streamlit UI
- `mcp_http_bridge.py` - HTTP-to-MCP protocol bridge
- `mcp_server_stdio.py` - True MCP protocol server
- `climategpt_persona_engine.py` - Persona processing logic
- `.env` - Environment configuration
- `setup_and_start.sh` - Automated setup script
