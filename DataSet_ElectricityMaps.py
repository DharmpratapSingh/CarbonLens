import requests
import pandas as pd
import os

# --- Config ---
BASE = "https://api.electricitymaps.com/v3"
ZONE = "DE"   # your selected zone
START = "2023-01-01T00:00:00Z"
END   = "2023-01-03T00:00:00Z"

# --- API key from environment variable ---
TOKEN = os.environ.get("ELECTRICITY_MAPS_API_KEY")
if not TOKEN:
    raise ValueError(
        "ELECTRICITY_MAPS_API_KEY environment variable is required. "
        "Set it with: export ELECTRICITY_MAPS_API_KEY=your-api-key"
    )
HEADERS = {"auth-token": TOKEN}

# --- Fetch carbon intensity history ---
params = {"zone": ZONE, "start": START, "end": END}
resp = requests.get(f"{BASE}/carbon-intensity/history", headers=HEADERS, params=params, timeout=60)
resp.raise_for_status()

data = resp.json().get("history", [])
df = pd.DataFrame(data)

# --- Inspect ---
df["datetime"] = pd.to_datetime(df["datetime"], utc=True)
print(df.head())