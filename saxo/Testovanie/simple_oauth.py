#!/usr/bin/env python3
"""Jednoduchý OAuth test - iba vygeneruje URL"""
import os
from urllib.parse import urlencode
import base64

CLIENT_ID = "2d7a66918b594af5bc2ac830a3b79d2c"
REDIRECT_URI = "http://localhost:8765/callback/demo"
AUTH_BASE = "https://sim.logonvalidation.net"

def generate_simple_auth_url():
    state = base64.urlsafe_b64encode(os.urandom(16)).decode().rstrip("=")
    
    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": "openid offline_access read trade",
        "state": state,
    }
    
    url = f"{AUTH_BASE}/authorize?{urlencode(params)}"
    
    print("🔗 SAXO DEMO OAuth URL:")
    print("=" * 80)
    print(url)
    print("=" * 80)
    print()
    print("📋 Kroky:")
    print("1. Skopírujte URL vyššie")
    print("2. Otvorte v prehliadači")
    print("3. Prihláste sa do Saxo demo účtu")
    print("4. Po presmerovaní skopírujte celú URL z adresového riadka")
    print("5. Pošlite mi URL s 'code' parametrom")
    print()
    print(f"💾 State pre validáciu: {state}")
    
    return state

if __name__ == "__main__":
    generate_simple_auth_url()