#!/usr/bin/env python3
"""
Saxo Demo Trader - Automatizovaný trading s reálnym Saxo API
Používa token-proxy pre získanie tokenov a implementuje hedging stratégiu.
"""
import os
import time
import json
import requests
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

# Konfigurácia
TOKEN_PROXY_URL = os.getenv("TOKEN_PROXY_URL", "http://91.98.81.44:8080/token")
SAXO_API_BASE = "https://gateway.saxobank.com/sim/openapi"  # Demo endpoint
POSITIONS_STORE_URL = os.getenv("POSITIONS_STORE_URL", "http://91.98.81.44:8090")

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SaxoDemoTrader:
    """Saxo Demo Trading Client s automatickým token managementom"""
    
    def __init__(self):
        self.session = requests.Session()
        self.client_key = None
        self.account_key = None
        
    def get_access_token(self) -> str:
        """Získa aktuálny access token z token-proxy"""
        try:
            response = self.session.get(TOKEN_PROXY_URL, timeout=10)
            response.raise_for_status()
            token_data = response.json()
            return token_data["access_token"]
        except Exception as e:
            logger.error(f"Chyba pri získaní tokenu: {e}")
            raise
    
    def make_api_request(self, method: str, endpoint: str, data: Dict = None) -> Dict:
        """Vykoná API request na Saxo s automatickým token refreshom"""
        token = self.get_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        url = f"{SAXO_API_BASE}{endpoint}"
        
        try:
            if method.upper() == "GET":
                response = self.session.get(url, headers=headers, timeout=30)
            elif method.upper() == "POST":
                response = self.session.post(url, headers=headers, json=data, timeout=30)
            elif method.upper() == "PUT":
                response = self.session.put(url, headers=headers, json=data, timeout=30)
            elif method.upper() == "DELETE":
                response = self.session.delete(url, headers=headers, timeout=30)
            else:
                raise ValueError(f"Nepodporovaná HTTP metóda: {method}")
            
            response.raise_for_status()
            return response.json() if response.content else {}
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP chyba {response.status_code}: {response.text}")
            raise
        except Exception as e:
            logger.error(f"API request chyba: {e}")
            raise
    
    def get_client_info(self) -> Dict:
        """Získa informácie o klientovi a nastaví client_key"""
        try:
            client_info = self.make_api_request("GET", "/port/v1/clients/me")
            self.client_key = client_info.get("ClientKey")
            logger.info(f"Client Key: {self.client_key}")
            return client_info
        except Exception as e:
            logger.error(f"Chyba pri získaní client info: {e}")
            raise
    
    def get_accounts(self) -> List[Dict]:
        """Získa zoznam účtov"""
        try:
            accounts = self.make_api_request("GET", "/port/v1/accounts/me")
            if accounts.get("Data"):
                # Použij prvý účet
                self.account_key = accounts["Data"][0].get("AccountKey")
                logger.info(f"Account Key: {self.account_key}")
            return accounts.get("Data", [])
        except Exception as e:
            logger.error(f"Chyba pri získaní účtov: {e}")
            raise
    
    def get_positions(self) -> List[Dict]:
        """Získa aktuálne pozície"""
        try:
            endpoint = f"/port/v1/positions/me?ClientKey={self.client_key}"
            positions = self.make_api_request("GET", endpoint)
            return positions.get("Data", [])
        except Exception as e:
            logger.error(f"Chyba pri získaní pozícií: {e}")
            return []
    
    def get_balance_and_margin(self) -> Dict:
        """Získa balance a margin informácie"""
        try:
            endpoint = f"/port/v1/balances/me?ClientKey={self.client_key}&AccountKey={self.account_key}"
            balance = self.make_api_request("GET", endpoint)
            return balance
        except Exception as e:
            logger.error(f"Chyba pri získaní balance: {e}")
            return {}
    
    def search_instruments(self, query: str, asset_types: List[str] = None) -> List[Dict]:
        """Vyhľadá inštrumenty (akcie, opcie, atď.)"""
        if asset_types is None:
            asset_types = ["Stock", "StockOption"]
        
        try:
            endpoint = f"/ref/v1/instruments"
            params = {
                "Keywords": query,
                "AssetTypes": ",".join(asset_types),
                "$top": 50
            }
            
            # Append query parameters
            query_string = "&".join([f"{k}={v}" for k, v in params.items()])
            endpoint_with_params = f"{endpoint}?{query_string}"
            
            instruments = self.make_api_request("GET", endpoint_with_params)
            return instruments.get("Data", [])
        except Exception as e:
            logger.error(f"Chyba pri vyhľadávaní inštrumentov: {e}")
            return []
    
    def place_order(self, order_data: Dict) -> Dict:
        """Zadá objednávku (BUY/SELL)"""
        try:
            endpoint = "/trade/v2/orders"
            order_result = self.make_api_request("POST", endpoint, order_data)
            logger.info(f"Order placed: {order_result}")
            return order_result
        except Exception as e:
            logger.error(f"Chyba pri zadávaní orderu: {e}")
            raise
    
    def create_market_order(self, uic: int, asset_type: str, amount: float, 
                          buy_sell: str, account_key: str = None) -> Dict:
        """Vytvorí market order"""
        if account_key is None:
            account_key = self.account_key
            
        order_data = {
            "AccountKey": account_key,
            "Amount": abs(amount),
            "AssetType": asset_type,
            "BuySell": buy_sell,  # "Buy" alebo "Sell"
            "OrderType": "Market",
            "Uic": uic
        }
        
        return self.place_order(order_data)
    
    def get_market_data(self, uic: int, asset_type: str) -> Dict:
        """Získa market data pre inštrument"""
        try:
            endpoint = f"/trade/v1/infoprices/subscriptions"
            subscription_data = {
                "ContextId": "MyContext",
                "ReferenceId": f"price_{uic}",
                "Arguments": {
                    "Uic": uic,
                    "AssetType": asset_type
                }
            }
            
            # Pre demo použijeme jednoduché API na získanie ceny
            # V reálnom prostredí by sme použili streaming subscriptions
            endpoint = f"/trade/v1/infoprices/list?Uics={uic}&AssetType={asset_type}"
            market_data = self.make_api_request("GET", endpoint)
            return market_data
        except Exception as e:
            logger.error(f"Chyba pri získaní market data: {e}")
            return {}


class HedgingStrategy:
    """Implementácia hedging stratégie pre Saxo demo trading"""
    
    def __init__(self, trader: SaxoDemoTrader):
        self.trader = trader
        self.risk_threshold = 0.02  # 2% risk threshold
        self.hedge_ratio = 0.8  # 80% hedge ratio
        
    def analyze_portfolio_risk(self, positions: List[Dict]) -> Dict:
        """Analyzuje riziko portfólia"""
        total_exposure = 0
        equity_exposure = 0
        option_exposure = 0
        
        for position in positions:
            market_value = position.get("MarketValue", 0)
            asset_type = position.get("PositionBase", {}).get("AssetType", "")
            
            total_exposure += market_value
            
            if asset_type == "Stock":
                equity_exposure += market_value
            elif asset_type in ["StockOption", "StockIndexOption"]:
                option_exposure += market_value
        
        return {
            "total_exposure": total_exposure,
            "equity_exposure": equity_exposure,
            "option_exposure": option_exposure,
            "hedge_needed": equity_exposure > 0 and abs(option_exposure / equity_exposure) < self.hedge_ratio
        }
    
    def find_hedge_instruments(self, symbol: str) -> List[Dict]:
        """Nájde vhodné hedging inštrumenty (PUT opcie)"""
        try:
            # Hľadaj PUT opcie pre daný symbol
            options = self.trader.search_instruments(
                query=symbol,
                asset_types=["StockOption"]
            )
            
            # Filtruj iba PUT opcie s rozumným expiry
            puts = []
            for option in options:
                if (option.get("PutCall") == "Put" and 
                    option.get("ExpiryDate") and
                    self._is_reasonable_expiry(option.get("ExpiryDate"))):
                    puts.append(option)
            
            return puts[:5]  # Vráť max 5 najlepších opcií
            
        except Exception as e:
            logger.error(f"Chyba pri hľadaní hedge inštrumentov: {e}")
            return []
    
    def _is_reasonable_expiry(self, expiry_date: str) -> bool:
        """Kontroluje, či je expiry dátum rozumný (1-6 mesiacov)"""
        try:
            expiry = datetime.fromisoformat(expiry_date.replace('Z', '+00:00'))
            now = datetime.now()
            days_to_expiry = (expiry - now).days
            return 30 <= days_to_expiry <= 180
        except:
            return False
    
    def execute_hedge(self, equity_position: Dict, hedge_instruments: List[Dict]) -> Dict:
        """Vykoná hedging transakciu"""
        try:
            if not hedge_instruments:
                return {"status": "failed", "reason": "No hedge instruments found"}
            
            # Vyberte najvhodnejšiu PUT opciu (najbližšie k at-the-money)
            best_put = hedge_instruments[0]  # Zjednodušené - v realite by sme vybrali najlepšiu
            
            # Vypočítaj množstvo na hedge
            equity_value = equity_position.get("MarketValue", 0)
            hedge_amount = int(abs(equity_value) * self.hedge_ratio / 100)  # PUT opcie sa obchodujú po 100
            
            if hedge_amount > 0:
                order_result = self.trader.create_market_order(
                    uic=best_put.get("Uic"),
                    asset_type="StockOption",
                    amount=hedge_amount,
                    buy_sell="Buy"
                )
                
                return {
                    "status": "success",
                    "order": order_result,
                    "hedge_instrument": best_put,
                    "hedge_amount": hedge_amount
                }
            else:
                return {"status": "failed", "reason": "Hedge amount too small"}
                
        except Exception as e:
            logger.error(f"Chyba pri hedge exekúcii: {e}")
            return {"status": "failed", "reason": str(e)}


def update_positions_store(positions: List[Dict]):
    """Aktualizuje positions store s novými pozíciami"""
    try:
        # Konvertuj Saxo pozície do formátu positions store
        converted_positions = []
        for pos in positions:
            position_base = pos.get("PositionBase", {})
            converted_pos = {
                "Uic": position_base.get("Uic"),
                "AssetType": position_base.get("AssetType"),
                "Amount": position_base.get("Amount", 0),
                "CanBeClosed": position_base.get("CanBeClosed", True),
                "SourceOrderId": position_base.get("SourceOrderId", ""),
                "ExecutionTimeOpen": position_base.get("ExecutionTimeOpen", ""),
                "Status": position_base.get("Status", "Open"),
                "MarketValue": pos.get("MarketValue", 0),
                "ProfitLossOnTrade": pos.get("ProfitLossOnTrade", 0)
            }
            converted_positions.append(converted_pos)
        
        # Pošli do positions store
        payload = {"Data": {"Positions": converted_positions}}
        response = requests.post(f"{POSITIONS_STORE_URL}/ingest", json=payload, timeout=10)
        response.raise_for_status()
        logger.info(f"Updated positions store with {len(converted_positions)} positions")
        
    except Exception as e:
        logger.error(f"Chyba pri aktualizácii positions store: {e}")


def main():
    """Hlavná funkcia - demo trading loop"""
    logger.info("🚀 Spúšťam Saxo Demo Trader...")
    
    try:
        # Inicializuj trader
        trader = SaxoDemoTrader()
        strategy = HedgingStrategy(trader)
        
        # Získaj základné info
        client_info = trader.get_client_info()
        accounts = trader.get_accounts()
        
        logger.info(f"Pripojený ako: {client_info.get('Name')}")
        logger.info(f"Počet účtov: {len(accounts)}")
        
        # Hlavný trading loop
        while True:
            try:
                logger.info("📊 Získavam aktuálne pozície...")
                positions = trader.get_positions()
                balance = trader.get_balance_and_margin()
                
                logger.info(f"Pozície: {len(positions)}")
                logger.info(f"Cash Balance: {balance.get('CashBalance', 'N/A')}")
                
                # Aktualizuj positions store
                update_positions_store(positions)
                
                # Analyzuj risk a vykonaj hedging ak treba
                risk_analysis = strategy.analyze_portfolio_risk(positions)
                logger.info(f"Risk Analysis: {risk_analysis}")
                
                if risk_analysis.get("hedge_needed"):
                    logger.info("🛡️ Hedging potrebný...")
                    
                    # Nájdi equity pozície ktoré potrebujú hedge
                    for position in positions:
                        position_base = position.get("PositionBase", {})
                        if position_base.get("AssetType") == "Stock":
                            symbol = position_base.get("Symbol", "")
                            logger.info(f"Hľadám hedge pre {symbol}...")
                            
                            hedge_instruments = strategy.find_hedge_instruments(symbol)
                            if hedge_instruments:
                                hedge_result = strategy.execute_hedge(position, hedge_instruments)
                                logger.info(f"Hedge result: {hedge_result}")
                
                # Demo: každých 30 sekúnd
                logger.info("⏳ Čakám 30 sekúnd...")
                time.sleep(30)
                
            except KeyboardInterrupt:
                logger.info("👋 Stopping trader...")
                break
            except Exception as e:
                logger.error(f"Chyba v trading loop: {e}")
                time.sleep(10)  # Krátka pauza pred retry
                
    except Exception as e:
        logger.error(f"Kritická chyba: {e}")
        raise


if __name__ == "__main__":
    main()