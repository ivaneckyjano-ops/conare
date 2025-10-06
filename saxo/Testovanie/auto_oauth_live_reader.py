#!/usr/bin/env python3
"""Automatizovaný OAuth pre Saxo LIVE reader.

Tento skript:
1. Vygeneruje autorizačnú URL.
2. Otvorí prehliadač (ak možné).
3. Spustí lokálny callback server na port 8765.
4. Počká na dokončenie prihlásenia (používateľ musí potvrdiť v browseri).
5. Automaticky vymení kód za tokeny a uloží ich.

Použitie:
- Nastav env: SAXO_CLIENT_ID, SAXO_CLIENT_SECRET (voliteľné)
- Spusti: python auto_oauth_live_reader.py
- Otvor URL v browseri, prihlás sa, potvrď scopes.
- Skript dokončí automaticky.

Pre Codespaces: spusti v termináli, URL otvor v novom okne/tabe.
"""
import os
import time
import json
import base64
import hashlib
import threading
import webbrowser
import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlencode, parse_qs

import requests

# --- Configure ---
CLIENT_ID = os.getenv("SAXO_CLIENT_ID", "TU_DAJ_SVOJ_APPKEY")
CLIENT_SECRET = os.getenv("SAXO_CLIENT_SECRET", "").strip()
ENV = "live"  # vždy live pre reader
REDIRECT_URI = "http://127.0.0.1:8765/callback/reader"
TOKENS_FILE = "/data/tokens_live_reader.json"  # pre compose volume

AUTH_BASE = "https://live.logonvalidation.net"
AUTH_URL = f"{AUTH_BASE}/authorize"
TOKEN_URL = f"{AUTH_BASE}/token"
SCOPES = "openid offline_access read trade"

# Global pre callback
Handler = None

class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global Handler
        if self.path.startswith("/callback/reader"):
            qs = parse_qs(self.path.split('?', 1)[1] if '?' in self.path else '')
            Handler.got = {
                'code': qs.get('code', [None])[0],
                'state': qs.get('state', [None])[0],
                'error': qs.get('error', [None])[0],
                'error_description': qs.get('error_description', [None])[0],
            }
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b'<html><body><h1>OAuth dokončený!</h1><p>Môžete zatvoriť toto okno.</p></body></html>')
        else:
            self.send_response(404)
            self.end_headers()

def start_server():
    global Handler
    Handler = type('Handler', (CallbackHandler,), {'got': None})
    server = HTTPServer(('127.0.0.1', 8765), Handler)
    server.serve_forever()

def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")

def pkce_pair():
    verifier = b64url(os.urandom(40))
    challenge = b64url(hashlib.sha256(verifier.encode()).digest())
    return verifier, challenge

def load_tokens():
    try:
        with open(TOKENS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None

def try_refresh(tokens):
    refresh_token = tokens.get('refresh_token')
    if not refresh_token:
        return None
    data = {
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token,
        'client_id': CLIENT_ID,
    }
    if CLIENT_SECRET:
        data['client_secret'] = CLIENT_SECRET
    else:
        # PKCE pre refresh? Zvyčajne nie, ale skús
        pass
    headers = {'Content-Type': 'application/x-www-form-urlencoded', 'Accept': 'application/json'}
    try:
        r = requests.post(TOKEN_URL, data=data, headers=headers, timeout=30)
        if r.status_code == 200:
            new_tokens = r.json()
            new_tokens['obtained_at'] = int(time.time())
            with open(TOKENS_FILE, 'w', encoding='utf-8') as f:
                json.dump(new_tokens, f, indent=2)
            return new_tokens
    except Exception:
        pass
    return None

def main():
    if not CLIENT_ID or CLIENT_ID == "TU_DAJ_SVOJ_APPKEY":
        raise SystemExit("Chyba: chýba CLIENT_ID. Nastav env SAXO_CLIENT_ID.")

    # Skús refresh existujúcich tokenov
    existing = load_tokens()
    if existing:
        exp = int(existing.get("expires_at", 0) or 0)
        if exp and exp > int(time.time()):
            print(f"Tokeny sú platné, expires_at={exp}. Preskakujem OAuth.")
            return
        print("Pokúšam refresh tokenov...")
        refreshed = try_refresh(existing)
        if refreshed:
            print("Refresh úspešný.")
            return
        print("Refresh zlyhal, pokračujem s novým OAuth.")

    # Generuj PKCE
    use_secret = bool(CLIENT_SECRET)
    verifier = challenge = None
    if not use_secret:
        verifier, challenge = pkce_pair()

    state = b64url(os.urandom(16))
    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
        "state": state,
    }
    if not use_secret:
        params["code_challenge"] = challenge
        params["code_challenge_method"] = "S256"

    url = f"{AUTH_URL}?{urlencode(params)}"
    print("Autorizačná URL:")
    print(url)
    print("\nOtvorte túto URL v prehliadači, prihláste sa do Saxo účtu a potvrďte oprávnenia.")
    print("Po dokončení sa vráťte sem – skript dokončí automaticky.\n")

    # Spusti callback server v thread
    t = threading.Thread(target=start_server, daemon=True)
    t.start()

    # Otvor browser
    try:
        webbrowser.open(url)
    except Exception:
        print("Nepodarilo otvoriť browser automaticky. Skopírujte URL vyššie a otvorte manuálne.")

    # Čakaj na callback (max 5 min)
    deadline = time.time() + 300
    while Handler.got is None and time.time() < deadline:
        time.sleep(0.5)

    if Handler.got is None:
        raise SystemExit("Timeout: neprišiel callback. Skontrolujte redirect URI a dokončite prihlásenie.")

    cb = Handler.got
    print("Callback prijatý:", cb)
    if "error" in cb:
        raise SystemExit(f"OAuth chyba: {cb.get('error_description') or cb['error']}")
    if cb.get("state") and cb.get("state") != state:
        raise SystemExit("State mismatch – možno CSRF.")

    # Vymeň kód za tokeny
    data = {
        "grant_type": "authorization_code",
        "code": cb["code"],
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
    }
    if use_secret:
        data["client_secret"] = CLIENT_SECRET
    else:
        data["code_verifier"] = verifier

    headers = {"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"}
    r = requests.post(TOKEN_URL, data=data, headers=headers, timeout=30)
    print(f"Token exchange: {r.status_code}")
    if not (200 <= r.status_code < 300):
        raise SystemExit(f"Výmena kódu zlyhala: {r.status_code} {r.text}")

    tokens = r.json()
    tokens["obtained_at"] = int(time.time())
    with open(TOKENS_FILE, "w", encoding="utf-8") as f:
        json.dump(tokens, f, indent=2)
    print(f"Tokeny uložené do {TOKENS_FILE}")
    print("OAuth dokončený úspešne!")

if __name__ == "__main__":
    main()