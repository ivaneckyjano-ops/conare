#!/usr/bin/env python3
"""Exchange a Saxo demo authorization code and save tokens to data/tokens_demo.json

Usage:
  python3 save_tokens_demo.py bfe681a6-90f5-4807-80bd-2663f47aeebd
"""
import sys
import os
import time
import json
import requests

CLIENT_ID = os.getenv("SAXO_CLIENT_ID", "2d7a66918b594af5bc2ac830a3b79d2c")
CLIENT_SECRET = os.getenv("SAXO_CLIENT_SECRET", "2f5ad858c3eb4ee9b5207d9be5c9c8c5")
TOKEN_URL = "https://sim.logonvalidation.net/token"
REDIRECT_URI = "http://127.0.0.1:8765/callback/demo"
TOKENS_FILE = "data/tokens_demo.json"


def exchange_code(code: str) -> dict:
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    r = requests.post(TOKEN_URL, data=data, headers=headers, timeout=30)
    try:
        j = r.json()
    except Exception:
        print("Failed to parse JSON response:\n", r.text)
        raise
    # Accept 2xx or 201 which Saxo sometimes returns
    if str(r.status_code).startswith("2") and "access_token" in j:
        j["obtained_at"] = int(time.time())
        os.makedirs(os.path.dirname(TOKENS_FILE), exist_ok=True)
        with open(TOKENS_FILE, "w") as f:
            json.dump(j, f, indent=2)
        print(f"Saved tokens to {TOKENS_FILE}")
        return j
    else:
        print("Token exchange failed:", r.status_code, j)
        raise SystemExit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 save_tokens_demo.py <code>")
        raise SystemExit(2)
    code = sys.argv[1]
    exchange_code(code)
