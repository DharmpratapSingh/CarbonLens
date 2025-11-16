# Unnecessary Files - Recommended for Deletion

This document lists files that can be safely deleted to clean up the repository.

## Backup Files (DELETE)

These are backup files that should not be in version control:

1. **mcp_server_stdio.py.backup** (43KB)
   - Old backup of mcp_server_stdio.py
   - No longer needed as git tracks all changes
   - **Action: DELETE**

## Deprecated/Unused Python Files (DELETE or ARCHIVE)

1. **mcp_server.py** (164KB)
   - Old/deprecated MCP server implementation
   - Replaced by `mcp_server_stdio.py`
   - **Action: DELETE** (or move to `archive/` if you want to keep for reference)

2. **DataSet_EDGAR.py** (5.3KB)
   - Appears to be old data processing script
   - Not imported or used anywhere in main codebase
   - **Action: DELETE** (unless actively used for data preparation)

3. **DataSet_ElectricityMaps.py** (678 bytes)
   - Small data script, likely unused
   - Not referenced in main application
   - **Action: DELETE**

4. **climategpt_persona_engine.py** (48KB)
   - Old persona implementation
   - Replaced by functionality in `enhanced_climategpt_with_personas.py`
   - **Action: DELETE** (or move to `archive/`)

5. **main.py** (88 bytes)
   - Tiny file, likely a stub or old entry point
   - Not used in current architecture
   - **Action: DELETE**

## Jupyter Notebooks (OPTIONAL - Keep if actively used)

1. **EDGAR_Transport.ipynb** (693KB)
   - Large Jupyter notebook (694KB!)
   - Probably used for data exploration/analysis
   - **Action: KEEP if still used for analysis, otherwise DELETE**
   - **Note:** Consider adding to `.gitignore` if it's just for local exploration

## Test Result Files (DELETE - Should be gitignored)

All files in `testing/test_results/` directory:

```
testing/test_results/comparison_summary_*.txt (13+ files)
```

- These are test outputs that should NOT be in git
- **Action: DELETE from repository**
- **Action: Add `testing/test_results/` to `.gitignore`**

## Summary

### Immediate Deletions (High Priority)

```bash
# Backup files
rm mcp_server_stdio.py.backup

# Deprecated code
rm mcp_server.py
rm climategpt_persona_engine.py
rm main.py

# Unused data scripts (verify first!)
rm DataSet_EDGAR.py
rm DataSet_ElectricityMaps.py

# Test results (add to gitignore)
rm -rf testing/test_results/*.txt
```

### Update .gitignore

Add these lines to `.gitignore`:

```
# Test results
testing/test_results/
*.backup
*.bak
*~
*.swp

# Jupyter checkpoints
.ipynb_checkpoints/

# Local data exploration notebooks (optional)
# *.ipynb
```

## Files to KEEP

These files are necessary and should NOT be deleted:

### Core Application
- ✅ `mcp_server_stdio.py` - Main MCP server (TRUE implementation)
- ✅ `mcp_http_bridge.py` - HTTP to MCP bridge
- ✅ `enhanced_climategpt_with_personas.py` - Streamlit UI
- ✅ `run_llm.py` - LLM integration utilities

### Configuration
- ✅ `pyproject.toml` - Project metadata and dependencies
- ✅ `requirements.txt` - Python dependencies
- ✅ `docker-compose.yml` - Docker configuration
- ✅ `Makefile` - Build/run commands
- ✅ `.pre-commit-config.yaml` - Code quality hooks
- ✅ `pytest.ini` - Test configuration

### Scripts
- ✅ `run_mcp_server.sh` - Server startup script
- ✅ `run_mcp_dev.sh` - Development server script
- ✅ `start_climategpt.sh` - Application startup script

### Documentation
- ✅ `README.md` - Project documentation
- ✅ `CODE_REVIEW_REPORT.md` - Code review findings
- ✅ `docs/` - All documentation files

### Testing
- ✅ `testing/test_harness.py` - Test framework
- ✅ `testing/test_10_questions.py` - Test cases
- ✅ `testing/*.md` - Testing documentation

### Source Code
- ✅ `src/` - All source code modules

## Disk Space Savings

Estimated space to be freed:

- `mcp_server.py`: 164KB
- `mcp_server_stdio.py.backup`: 43KB
- `EDGAR_Transport.ipynb`: 693KB
- `climategpt_persona_engine.py`: 48KB
- Test results: ~50KB
- Other deprecated files: ~10KB

**Total: ~1MB** of unnecessary files

## Recommendation

1. **Immediate Action:** Delete backup files and deprecated code
2. **Review:** Check if `EDGAR_Transport.ipynb` is still needed for data analysis
3. **Gitignore:** Add test results and backup files to `.gitignore`
4. **Archive:** Consider creating an `archive/` directory for old code you want to keep for reference

---

**Generated:** 2025-11-16
**Reviewer:** Claude (Sonnet 4.5)
