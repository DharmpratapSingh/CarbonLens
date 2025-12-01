serve:
	uv run python src/mcp_http_bridge.py

ui:
	uv run streamlit run src/streamlit_app.py

test:
	uv run pytest -q
