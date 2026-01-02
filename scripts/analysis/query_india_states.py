import requests
import json

MCP_BASE = "http://127.0.0.1:8010"

# Query 1: Highest emissions state in India 2020
query1 = {
    "file_id": "transport-admin1-year",
    "select": ["admin1_name", "country_name", "year", "emissions_tonnes"],
    "where": {"country_name": "India", "year": 2020},
    "order_by": "emissions_tonnes DESC",
    "limit": 1,
    "assist": True
}

print("Query 1: Highest emissions state in India 2020")
try:
    r = requests.post(f"{MCP_BASE}/query", json=query1, timeout=30)
    result = r.json()
    if "rows" in result and result["rows"]:
        print(json.dumps(result["rows"], indent=2))
    else:
        print("Error:", result)
except Exception as e:
    print(f"Exception: {e}")

print("\n" + "="*60 + "\n")

# Query 2: Lowest emissions state in India 2020
query2 = {
    "file_id": "transport-admin1-year",
    "select": ["admin1_name", "country_name", "year", "emissions_tonnes"],
    "where": {"country_name": "India", "year": 2020},
    "order_by": "emissions_tonnes ASC",
    "limit": 1,
    "assist": True
}

print("Query 2: Lowest emissions state in India 2020")
try:
    r = requests.post(f"{MCP_BASE}/query", json=query2, timeout=30)
    result = r.json()
    if "rows" in result and result["rows"]:
        print(json.dumps(result["rows"], indent=2))
    else:
        print("Error:", result)
except Exception as e:
    print(f"Exception: {e}")

print("\n" + "="*60 + "\n")

# Query 3: Highest emissions in Germany 2019
query3 = {
    "file_id": "transport-country-year",
    "select": ["country_name", "year", "emissions_tonnes"],
    "where": {"country_name": "Germany", "year": 2019},
    "assist": True
}

print("Query 3: Highest emissions in Germany 2019")
try:
    r = requests.post(f"{MCP_BASE}/query", json=query3, timeout=30)
    result = r.json()
    if "rows" in result and result["rows"]:
        print(json.dumps(result["rows"], indent=2))
    else:
        print("Error:", result)
except Exception as e:
    print(f"Exception: {e}")
