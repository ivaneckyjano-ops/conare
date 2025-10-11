#!/bin/bash
# Test skript pre Saxo Demo Trader

echo "🧪 Testovanie Saxo Demo Trader..."

# Test 1: Token connectivity
echo "1️⃣ Test token-proxy pripojenia..."
curl -s http://91.98.81.44:8080/token | head -5 || echo "❌ Token-proxy nedostupný"

# Test 2: Positions store connectivity  
echo "2️⃣ Test positions store pripojenia..."
curl -s http://91.98.81.44:8090/positions | head -5 || echo "❌ Positions store nedostupný"

# Test 3: Základné Saxo API test (pomocou našich tokenov)
echo "3️⃣ Test Saxo API pripojenia..."
python3 -c "
import requests
import json

# Získaj token
try:
    token_resp = requests.get('http://91.98.81.44:8080/token')
    token = token_resp.json()['access_token']
    print(f'✅ Token získaný: {token[:20]}...')
    
    # Test Saxo API
    headers = {'Authorization': f'Bearer {token}'}
    api_resp = requests.get('https://gateway.saxobank.com/sim/openapi/port/v1/clients/me', headers=headers)
    
    if api_resp.status_code == 200:
        client_info = api_resp.json()
        print(f'✅ Saxo API funguje: {client_info.get(\"Name\", \"Unknown\")}')
    else:
        print(f'❌ Saxo API chyba: {api_resp.status_code}')
        
except Exception as e:
    print(f'❌ Test chyba: {e}')
"

echo "✅ Test dokončený. Ak všetky testy prešli, môžeš spustiť:"
echo "python3 saxo_demo_trader.py"