serve:
	uv run python mcp_http_bridge.py

ui:
	uv run streamlit run enhanced_climategpt_with_personas.py

test:
	uv run pytest -q
