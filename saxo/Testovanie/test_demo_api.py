#!/usr/bin/env python3
"""Test Saxo Demo API s tokenmi"""
import json
import requests

def test_demo_api():
    """Test demo API endpoints s existujúcimi tokenmi"""
    try:
        with open('data/tokens_demo.json', 'r') as f:
            tokens = json.load(f)
        
        access_token = tokens['access_token']
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        # Test základného API endpoint
        base_url = "https://gateway.saxobank.com/sim/openapi"
        
        print("🧪 Testujem Saxo Demo API...")
        
        # 1. Test user info
        print("\n1️⃣  Test /ref/v1/users/me")
        r = requests.get(f"{base_url}/ref/v1/users/me", headers=headers)
        print(f"Status: {r.status_code}")
        if r.status_code == 200:
            user_info = r.json()
            print(f"✅ User ID: {user_info.get('UserId')}")
            print(f"✅ Account: {user_info.get('AccountKey')}")
        else:
            print(f"❌ Chyba: {r.text}")
            
        # 2. Test accounts
        print("\n2️⃣  Test /port/v1/accounts/me")
        r = requests.get(f"{base_url}/port/v1/accounts/me", headers=headers)
        print(f"Status: {r.status_code}")
        if r.status_code == 200:
            accounts = r.json()
            print(f"✅ Počet účtov: {len(accounts.get('Data', []))}")
            for acc in accounts.get('Data', [])[:2]:  # Prvé 2
                print(f"   Account: {acc.get('AccountKey')} - {acc.get('Currency')}")
        else:
            print(f"❌ Chyba: {r.text}")
            
        # 3. Test positions
        print("\n3️⃣  Test /port/v1/positions/me")
        r = requests.get(f"{base_url}/port/v1/positions/me", headers=headers)
        print(f"Status: {r.status_code}")
        if r.status_code == 200:
            positions = r.json()
            print(f"✅ Počet pozícií: {len(positions.get('Data', []))}")
            for pos in positions.get('Data', [])[:3]:  # Prvé 3
                print(f"   Position: {pos.get('NetPositionId')} - {pos.get('AssetType')}")
        else:
            print(f"❌ Chyba: {r.text}")
            
        print("\n🎉 Demo API test dokončený!")
        return True
        
    except Exception as e:
        print(f"❌ Chyba pri teste: {e}")
        return False

if __name__ == "__main__":
    test_demo_api()