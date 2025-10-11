#!/usr/bin/env python3
"""Test všetkých dostupných tokenov"""
import json
import requests
import time
import os

CLIENT_ID = "2d7a66918b594af5bc2ac830a3b79d2c"
CLIENT_SECRET = "2f5ad858c3eb4ee9b5207d9be5c9c8c5"

TOKEN_FILES = [
    ("demo", "data/tokens_demo.json", "https://sim.logonvalidation.net/token"),
    ("live", "data/tokens_live.json", "https://live.logonvalidation.net/token"),
    ("live_reader", "data/tokens_live_reader.json", "https://live.logonvalidation.net/token")
]

def refresh_token(env_name, file_path, token_url):
    """Pokús o refresh tokenu pre dané prostredie"""
    try:
        if not os.path.exists(file_path):
            print(f"❌ {env_name}: súbor {file_path} neexistuje")
            return False
            
        with open(file_path, 'r') as f:
            tokens = json.load(f)
        
        refresh_token = tokens.get('refresh_token')
        if not refresh_token:
            print(f"❌ {env_name}: žiadny refresh token")
            return False
            
        print(f"🔄 {env_name}: pokúšam refresh...")
        
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token,
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET
        }
        
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        r = requests.post(token_url, data=data, headers=headers, timeout=15)
        
        if r.status_code == 200:
            new_tokens = r.json()
            new_tokens['obtained_at'] = int(time.time())
            new_tokens['environment'] = env_name
            
            # Backup old tokens
            backup_file = f"{file_path}.backup"
            os.rename(file_path, backup_file)
            
            # Save new tokens
            with open(file_path, 'w') as f:
                json.dump(new_tokens, f, indent=2)
            
            print(f"✅ {env_name}: refresh úspešný!")
            return True
        else:
            print(f"❌ {env_name}: refresh zlyhal ({r.status_code})")
            return False
            
    except Exception as e:
        print(f"❌ {env_name}: chyba - {e}")
        return False

def test_api_access(env_name, file_path):
    """Test API prístupu s aktuálnymi tokenmi"""
    try:
        with open(file_path, 'r') as f:
            tokens = json.load(f)
        
        access_token = tokens['access_token']
        headers = {'Authorization': f'Bearer {access_token}'}
        
        # Determine API base URL
        if env_name.startswith('demo'):
            base_url = "https://gateway.saxobank.com/sim/openapi"
        else:
            base_url = "https://gateway.saxobank.com/openapi"
        
        print(f"🧪 {env_name}: testujem API prístup...")
        
        # Test user info
        r = requests.get(f"{base_url}/ref/v1/users/me", headers=headers, timeout=10)
        
        if r.status_code == 200:
            user_info = r.json()
            print(f"✅ {env_name}: API funguje - User ID: {user_info.get('UserId')}")
            return True
        else:
            print(f"❌ {env_name}: API zlyhal ({r.status_code})")
            return False
            
    except Exception as e:
        print(f"❌ {env_name}: API test chyba - {e}")
        return False

def main():
    print("🔍 Testujem všetky dostupné tokeny...")
    print("=" * 60)
    
    working_tokens = []
    
    for env_name, file_path, token_url in TOKEN_FILES:
        print(f"\n📁 {env_name.upper()} ({file_path})")
        print("-" * 40)
        
        # Try refresh first
        if refresh_token(env_name, file_path, token_url):
            # Test API access
            if test_api_access(env_name, file_path):
                working_tokens.append((env_name, file_path))
        else:
            # If refresh failed, try testing existing tokens anyway
            if test_api_access(env_name, file_path):
                working_tokens.append((env_name, file_path))
    
    print("\n" + "=" * 60)
    print("📊 SÚHRN:")
    if working_tokens:
        print("✅ Funkčné tokeny:")
        for env_name, file_path in working_tokens:
            print(f"   - {env_name}: {file_path}")
    else:
        print("❌ Žiadne funkčné tokeny")
    
    return len(working_tokens) > 0

if __name__ == "__main__":
    success = main()
    if success:
        print("\n🚀 Môžeme pokračovať s nasadením!")
    else:
        print("\n⚠️  Potrebujeme získať nové tokeny")