#!/usr/bin/env python3
"""Minimálny test OAuth (iba získanie tokenov).
Spustiteľný script, doplňte `CLIENT_ID` a voliteľne `SAXO_CLIENT_SECRET` v env.
Používa redirect URI http://127.0.0.1:8765/callback (musia sa zhodovať s registráciou v Saxo app).
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
from urllib.parse import urlencode, urlparse, parse_qs

import requests

# --- Configure ---
# Prefer environment variables for secrets - safer than editing the file.
CLIENT_ID = os.getenv("SAXO_CLIENT_ID", "TU_DAJ_SVOJ_APPKEY")  # povinne doplň alebo nastav env SAXO_CLIENT_ID
CLIENT_SECRET = os.getenv("SAXO_CLIENT_SECRET", "").strip()  # nechaj prázdne, ak nemáš secret
ENV = (os.getenv("SAXO_ENV") or "sim").lower()  # "sim" alebo "live"
REDIRECT_URI = os.getenv("REDIRECT_URI", "http://127.0.0.1:8765/callback")  # môžeš prebiť env premennou

if ENV == "live":
    AUTH_BASE = "https://live.logonvalidation.net"
else:
    AUTH_BASE = "https://sim.logonvalidation.net"

AUTH_URL = f"{AUTH_BASE}/authorize"
TOKEN_URL = f"{AUTH_BASE}/token"

TOKENS_FILE = os.getenv("TOKENS_FILE", "tokens_min.json")
SCOPES = "openid offline_access read trade"


def _now() -> int:
    return int(time.time())


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def pkce_pair():
    verifier = b64url(os.urandom(40))
    challenge = b64url(hashlib.sha256(verifier.encode()).digest())
    return verifier, challenge


def save_tokens(tokens: dict):
    # compute expires_at for convenience
    now = int(time.time())
    expires_in = int(tokens.get("expires_in", 0) or 0)
    if expires_in:
        tokens["expires_at"] = now + expires_in - 30
    tokens["obtained_at"] = now

    # Atomic write: write to temp file in same directory and replace
    path = TOKENS_FILE
    dirpath = os.path.dirname(path) or "."
    try:
        os.makedirs(dirpath, exist_ok=True)
    except Exception:
        pass
    tmp_path = os.path.join(dirpath, f".{os.path.basename(path)}.tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(tokens, f, indent=2)
        f.flush()
        os.fsync(f.fileno())
    try:
        os.replace(tmp_path, path)
    except Exception:
        # fallback: try simple write
        with open(path, "w", encoding="utf-8") as f:
            json.dump(tokens, f, indent=2)
    # ensure file permissions are private
    try:
        os.chmod(path, 0o600)
    except Exception:
        pass


def load_tokens():
    if not os.path.exists(TOKENS_FILE):
        return None
    try:
        with open(TOKENS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def try_refresh(tokens: dict):
    """Attempt to refresh tokens in-place. Returns new tokens or None on failure."""
    if not tokens or "refresh_token" not in tokens:
        return None
    data = {
        "grant_type": "refresh_token",
        "refresh_token": tokens["refresh_token"],
        "client_id": CLIENT_ID,
    }
    if CLIENT_SECRET:
        data["client_secret"] = CLIENT_SECRET
    headers = {"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"}
    r = requests.post(TOKEN_URL, data=data, headers=headers, timeout=30)
    if r.status_code != 200:
        print(f"Refresh failed: {r.status_code} {r.text}")
        return None
    new_tokens = r.json()
    # preserve refresh_token if not returned
    new_tokens["refresh_token"] = new_tokens.get("refresh_token", tokens.get("refresh_token"))
    save_tokens(new_tokens)
    return new_tokens


class Handler(BaseHTTPRequestHandler):
    got = None

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path != urlparse(REDIRECT_URI).path:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")
            return
        params = {k: v[0] for k, v in parse_qs(parsed.query).items()}
        Handler.got = params
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK, window can be closed.")
        threading.Thread(target=self.server.shutdown, daemon=True).start()

    def log_message(self, *args, **kwargs):
        # silence default logging
        return


def start_server():
    parsed = urlparse(REDIRECT_URI)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 80
    httpd = HTTPServer((host, port), Handler)
    print(f"Callback server listening on {host}:{port}")
    httpd.serve_forever()


def main():
    # allow overriding the module-level TOKENS_FILE via CLI
    global TOKENS_FILE
    # CLI options: allow running without opening the browser and override tokens file
    parser = argparse.ArgumentParser(description="Minimal Saxo OAuth test (get tokens).")
    parser.add_argument("--no-browser", action="store_true", dest="no_browser",
                        help="Don't open a browser automatically; print the auth URL instead.")
    parser.add_argument("--manual", action="store_true", dest="manual",
                        help="Manual mode: don't start callback server; paste redirected URL or code into terminal.")
    parser.add_argument("--tokens-file", dest="tokens_file", default=TOKENS_FILE,
                        help=f"Path to tokens file (default: {TOKENS_FILE})")
    parser.add_argument("--print-url-only", action="store_true",
                        help="Only print the authorization URL and exit (use with --manual).")
    parser.add_argument("--redirect-url", dest="redirect_url", default=None,
                        help="Provide the full redirected URL (non-interactive manual mode).")
    parser.add_argument("--code", dest="auth_code", default=None,
                        help="Provide the authorization code directly (non-interactive manual mode).")
    parser.add_argument("--expected-state", dest="expected_state", default=None,
                        help="Expected state value to validate against (use when exchanging an already-produced redirect URL).")
    args = parser.parse_args()

    TOKENS_FILE = args.tokens_file

    if not CLIENT_ID or CLIENT_ID == "TU_DAJ_SVOJ_APPKEY":
        raise SystemExit("Chyba: chýba CLIENT_ID (AppKey). Nastavte env SAXO_CLIENT_ID alebo upravte skript.")

    # Try to load existing tokens and refresh if needed
    existing = load_tokens()
    if existing:
        exp = int(existing.get("expires_at", 0) or 0)
        if exp and exp > _now():
            print(f"Found valid tokens in {TOKENS_FILE}, expires_at={exp} -> skipping interactive login")
            return existing
        print("Existing tokens present but expired or missing expires_at - attempting refresh if refresh_token is available")
        refreshed = try_refresh(existing)
        if refreshed:
            print(f"Refresh succeeded, tokens saved to {TOKENS_FILE}")
            return refreshed
        print("Refresh failed or not possible - proceeding to interactive login.")

    use_secret = bool(CLIENT_SECRET)
    verifier = challenge = None
    if not use_secret:
        verifier, challenge = pkce_pair()

    state = b64url(os.urandom(16))
    # Allow overriding state when reusing a previously generated redirect URL
    if args.expected_state:
        state = args.expected_state
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
    print("ENV:", ENV)
    print("AUTH_URL:", AUTH_URL)
    print("TOKEN_URL:", TOKEN_URL)
    print("Opening browser:\n", url)

    if args.manual and args.print_url_only:
        # In print-url-only mode, just show URL and exit without attempting token exchange
        print("\nprint-url-only: Authorization URL above. Exiting without waiting.")
        return 0

    # If manual mode is requested, do not start the server; instead prompt for the redirected URL / code
    if args.manual:
        # Non-interactive overrides
        state_cb = None
        if args.redirect_url:
            try:
                parsed_cb = urlparse(args.redirect_url)
                qs = parse_qs(parsed_cb.query)
                code = qs.get('code', [None])[0]
                state_cb = qs.get('state', [None])[0]
            except Exception:
                code = None
                state_cb = None
            if not code:
                raise SystemExit('redirect-url provided but `code` param not found')
            # If user didn't provide expected_state explicitly, align local state with callback state
            if state_cb and not args.expected_state:
                state = state_cb
            cb = {"code": code, "state": state_cb}
        elif args.auth_code:
            cb = {"code": args.auth_code, "state": None}
        else:
            print('\nManual mode: open the URL below in your browser, complete login, then paste the full redirected URL or the value of the `code` parameter here.')
            print(url)
            raw = input('\nPaste redirected URL or code: ').strip()
            # try to extract code and state if a full URL was pasted
            code = None
            try:
                parsed_cb = urlparse(raw)
                qs = parse_qs(parsed_cb.query)
                code = qs.get('code', [None])[0]
                state_cb = qs.get('state', [None])[0]
            except Exception:
                code = None
                state_cb = None

            if not code:
                # maybe user pasted just the code
                code = raw

            if not code:
                raise SystemExit('Neplatný vstup: nenašiel som parameter `code`. Skús znova.')

            cb = {'code': code, 'state': state_cb}
        # proceed to exchange code for tokens (cb prepared above)
    else:
        t = threading.Thread(target=start_server, daemon=True)
        t.start()
        # If user requested no-browser, don't attempt to open the browser programmatically
        if not args.no_browser:
            try:
                webbrowser.open(url)
            except Exception:
                pass

    # V manualnom rezime nečakáme na HTTP callback server – používateľ vložil URL/kód ručne.
    if not args.manual:
        # čakaj max 180s na callback
        deadline = time.time() + 180
        while Handler.got is None and time.time() < deadline:
            time.sleep(0.2)
        if Handler.got is None:
            raise SystemExit("Neprišiel callback. Skontroluj: redirect URI v Saxo app = presne http://127.0.0.1:8765/callback, firewall/port 8765, a či si dokončil login v prehliadači.")
        cb = Handler.got
    # cb is defined either from manual input or callback handler
    print("Callback params:", cb)
    if "error" in cb:
        raise SystemExit(f"OAuth error: {cb.get('error_description') or cb['error']}")
    # If we have state from callback and it differs, fail to prevent CSRF; if not present, continue.
    if cb.get("state") and cb.get("state") != state:
        raise SystemExit("State mismatch.")

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
    print("Token resp status:", r.status_code)
    print("Token resp headers:", dict(r.headers))
    print("Token resp body:", r.text)

    if not (200 <= r.status_code < 300):
        raise SystemExit(f"Token exchange failed: {r.status_code}")

    tokens = r.json()
    tokens["obtained_at"] = int(time.time())
    with open(TOKENS_FILE, "w", encoding="utf-8") as f:
        json.dump(tokens, f, indent=2)
    print(f"Tokens saved to {TOKENS_FILE}")


if __name__ == "__main__":
    main()
