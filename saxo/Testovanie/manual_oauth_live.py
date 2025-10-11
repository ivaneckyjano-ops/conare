#!/usr/bin/env python3
"""Manual OAuth for Saxo LIVE - without callback server"""
import os
import time
import json
import requests

CLIENT_ID = "2d7a66918b594af5bc2ac830a3b79d2c"
CLIENT_SECRET = "2f5ad858c3eb4ee9b5207d9be5c9c8c5"
REDIRECT_URI = "http://127.0.0.1:8765/callback/demo"
TOKENS_FILE = "data/tokens_live.json"

AUTH_BASE = "https://live.logonvalidation.net"
TOKEN_URL = f"{AUTH_BASE}/token"

def exchange_code_live(code, state):
    """Exchange authorization code for LIVE tokens"""
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET
    }
    
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    print("🔄 Vymieňam kod za LIVE tokeny...")
    
    r = requests.post(TOKEN_URL, data=data, headers=headers, timeout=30)
    print(f"Token exchange response: {r.status_code}")
    
    if r.status_code == 200:
        tokens = r.json()
        tokens["obtained_at"] = int(time.time())
        tokens["environment"] = "live"
        
        with open(TOKENS_FILE, "w") as f:
            json.dump(tokens, f, indent=2)
        print(f"✅ LIVE tokeny uložené do {TOKENS_FILE}")
        print("✅ LIVE OAuth dokončený úspešne!")
        
        # Show token info
        print("\n📊 Token info:")
        print(f"   Access token: {tokens['access_token'][:50]}...")
        print(f"   Refresh token: {tokens.get('refresh_token', 'N/A')}")
        print(f"   Expires in: {tokens.get('expires_in', 'N/A')} seconds")
        return True
    else:
        print(f"❌ Token exchange zlyhal: {r.text}")
        return False

def test_live_tokens():
    """Test LIVE API with fresh tokens"""
    try:
        with open(TOKENS_FILE, 'r') as f:
            tokens = json.load(f)
        
        access_token = tokens['access_token']
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        base_url = "https://gateway.saxobank.com/openapi"
        
        print("\n🧪 Testujem Saxo LIVE API...")
        
        # Test user info
        print("\n1️⃣  Test /ref/v1/users/me")
        r = requests.get(f"{base_url}/ref/v1/users/me", headers=headers)
        print(f"Status: {r.status_code}")
        if r.status_code == 200:
            user_info = r.json()
            print(f"✅ User ID: {user_info.get('UserId')}")
            print(f"✅ Account: {user_info.get('AccountKey')}")
        else:
            print(f"❌ Chyba: {r.text[:200]}...")
            
        return r.status_code == 200
        
    except Exception as e:
        print(f"❌ Chyba pri teste: {e}")
        return False

if __name__ == "__main__":
    import sys
    
    # Check for code parameter
    code_param = None
    for arg in sys.argv[1:]:
        if arg.startswith("--code="):
            code_param = arg.split("=", 1)[1]
            break
    
    if code_param:
        # Exchange code for tokens
        if exchange_code_live(code_param, None):
            # Test the tokens
            test_live_tokens()
    else:
        print("❌ Chýba --code parameter")
        print("Usage: python3 manual_oauth_live.py --code=YOUR_CODE")
        print("\nPo dokončení OAuth v prehliadači skopírujte 'code' parameter z URL")
        print("a spustite: python3 manual_oauth_live.py --code=VÁŠKÓD")