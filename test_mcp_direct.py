#!/usr/bin/env python3
"""Direct test of MCP server to bypass HTTP bridge"""
import json
import subprocess
import sys

# Start MCP server
mcp_process = subprocess.Popen(
    [sys.executable, "mcp_server_stdio.py"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    bufsize=1
)

# Initialize
init_request = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "test-client", "version": "1.0"}
    }
}

print("→ Sending initialize request")
mcp_process.stdin.write(json.dumps(init_request) + "\n")
mcp_process.stdin.flush()
response = mcp_process.stdout.readline()
print(f"← Initialize response: {response}")

# Call query_emissions tool
query_request = {
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/call",
    "params": {
        "name": "query_emissions",
        "arguments": {
            "file_id": "transport-country-year",
            "select": ["country_name", "year", "emissions_tonnes"],
            "where": {"country_name": "United States of America"},
            "limit": 5
        }
    }
}

print("\n→ Sending query_emissions request")
print(f"Request: {json.dumps(query_request, indent=2)}")
mcp_process.stdin.write(json.dumps(query_request) + "\n")
mcp_process.stdin.flush()
response = mcp_process.stdout.readline()
print(f"\n← Query response: {response}")

# Parse and pretty print
try:
    response_obj = json.loads(response)
    print(f"\nParsed response:\n{json.dumps(response_obj, indent=2)}")
except Exception as e:
    print(f"\nFailed to parse response: {e}")

# Clean up
mcp_process.terminate()
