#!/usr/bin/env python3
"""Manuálny OAuth pre Saxo DEMO - bez callback servera"""
import os
import time
import json
import requests

CLIENT_ID = os.getenv("SAXO_CLIENT_ID", "2d7a66918b594af5bc2ac830a3b79d2c")
CLIENT_SECRET = os.getenv("SAXO_CLIENT_SECRET", "2f5ad858c3eb4ee9b5207d9be5c9c8c5")
REDIRECT_URI = "http://localhost:8765/callback/demo"
TOKENS_FILE = "data/tokens_demo.json"

AUTH_BASE = "https://sim.logonvalidation.net"
TOKEN_URL = f"{AUTH_BASE}/token"

def refresh_tokens():
    """Pokús o refresh existujúcich tokenov"""
    try:
        with open(TOKENS_FILE, 'r') as f:
            tokens = json.load(f)
        
        refresh_token = tokens.get('refresh_token')
        if not refresh_token:
            print("Žiadny refresh token")
            return False
            
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token,
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET
        }
        
        print("Pokúšam refresh tokenov...")
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        r = requests.post(TOKEN_URL, data=data, headers=headers, timeout=30)
        
        print(f"Refresh response: {r.status_code}")
        if r.status_code == 200:
            new_tokens = r.json()
            new_tokens['obtained_at'] = int(time.time())
            
            with open(TOKENS_FILE, 'w') as f:
                json.dump(new_tokens, f, indent=2)
            print("✅ Refresh úspešný!")
            return True
        else:
            print(f"❌ Refresh zlyhal: {r.text}")
            return False
            
    except Exception as e:
        print(f"❌ Chyba pri refresh: {e}")
        return False

def generate_auth_url():
    """Vygeneruj OAuth URL pre manuálne prihlásenie"""
    from urllib.parse import urlencode
    import base64
    
    state = base64.urlsafe_b64encode(os.urandom(16)).decode().rstrip("=")
    
    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": "openid offline_access read trade",
        "state": state,
    }
    
    url = f"{AUTH_BASE}/authorize?{urlencode(params)}"
    
    print("\n" + "="*80)
    print("MANUÁLNY OAUTH PROCES:")
    print("="*80)
    print("1. Otvorte túto URL v prehliadači:")
    print(f"\n{url}\n")
    print("2. Prihláste sa do Saxo demo účtu")
    print("3. Potvrďte oprávnenia")
    print("4. Po presmerovaní skopírujte 'code' parameter z URL")
    print("5. Spustite: python3 manual_oauth_demo.py --code=VÁŠKÓD")
    print("="*80)
    
    return state

def exchange_code(code, state):
    """Vymení authorization code za tokeny"""
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET
    }
    
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    print("Vymieňam kod za tokeny...")
    
    r = requests.post(TOKEN_URL, data=data, headers=headers, timeout=30)
    print(f"Token exchange response: {r.status_code}")
    
    if r.status_code == 200:
        tokens = r.json()
        tokens["obtained_at"] = int(time.time())
        
        with open(TOKENS_FILE, "w") as f:
            json.dump(tokens, f, indent=2)
        print(f"✅ Tokeny uložené do {TOKENS_FILE}")
        print("✅ OAuth dokončený úspešne!")
        return True
    else:
        print(f"❌ Token exchange zlyhal: {r.text}")
        return False

if __name__ == "__main__":
    import sys
    
    # Ak je zadaný code parameter
    code_param = None
    for arg in sys.argv[1:]:
        if arg.startswith("--code="):
            code_param = arg.split("=", 1)[1]
            break
    
    if code_param:
        # Vymieň kód za tokeny
        exchange_code(code_param, None)
    else:
        # Najprv skús refresh
        if refresh_tokens():
            print("Tokeny boli úspešne obnovené!")
        else:
            # Ak refresh nevyšiel, vygeneruj auth URL
            state = generate_auth_url()