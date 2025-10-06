#!/usr/bin/env python3
"""Live reader: read-only status from Saxo Live using the live-reader token proxy.

Fetches an access token from the token-proxy and calls the OpenAPI endpoints for
positions, accounts, and open orders. Prints short summaries and can save raw JSON.
Exits with non-zero on unexpected HTTP errors.
"""
import os
import sys
import json
import argparse
import requests


def get_token(proxy_url: str, timeout: float = 5.0) -> str:
    r = requests.get(proxy_url, timeout=timeout)
    r.raise_for_status()
    data = r.json() or {}
    token = data.get("access_token")
    if not token:
        raise RuntimeError("Token proxy returned no access_token")
    return token


def get_gateway_base(env: str | None = None) -> str:
    # For live reader we default to LIVE; allow override via env var
    env = (env or os.getenv("SAXO_ENV") or "live").lower()
    if env == "sim":
        return os.getenv("GATEWAY_BASE", "https://gateway.saxobank.com/sim/openapi")
    return os.getenv("GATEWAY_BASE", "https://gateway.saxobank.com/openapi")


def _req_json(access_token: str, url: str, params: dict | None = None) -> requests.Response:
    headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
    return requests.get(url, headers=headers, params=(params or {}), timeout=30)


def get_positions(access_token: str, gateway_base: str) -> dict:
    url = f"{gateway_base}/port/v1/positions/me"
    params = {"FieldGroups": "PositionBase,DisplayAndFormat,PositionView"}
    r = _req_json(access_token, url, params)
    if r.status_code == 401:
        raise SystemExit("Unauthorized (401). Check that the token has 'read' scope and is LIVE.")
    r.raise_for_status()
    return r.json()


def get_accounts(access_token: str, gateway_base: str) -> dict:
    url = f"{gateway_base}/port/v1/accounts/me"
    params = {"FieldGroups": "AccountDetails,AccountSummary"}
    r = _req_json(access_token, url, params)
    if r.status_code == 401:
        raise SystemExit("Unauthorized (401) for accounts. Check scopes.")
    r.raise_for_status()
    return r.json()


def get_open_orders(access_token: str, gateway_base: str) -> dict:
    url = f"{gateway_base}/trade/v2/orders/me"
    # Filter to open/working orders only
    params = {"Status": "Working"}
    r = _req_json(access_token, url, params)
    if r.status_code == 401:
        raise SystemExit("Unauthorized (401) for orders. Check scopes.")
    r.raise_for_status()
    return r.json()


def main():
    ap = argparse.ArgumentParser(description="Read-only live account status via token proxy")
    ap.add_argument("--proxy", default=os.getenv("PROXY_URL", "http://token-proxy-live-reader:8080/token"),
                    help="Token proxy URL (default: http://token-proxy-live-reader:8080/token inside compose)")
    ap.add_argument("--env", dest="env", default=os.getenv("SAXO_ENV", "live"), choices=["live", "sim"],
                    help="Environment for gateway base (default: live)")
    ap.add_argument("--json-out", dest="json_out", default=None, help="Optional path to save raw JSON (positions)")
    ap.add_argument("--no-positions", action="store_true", help="Skip positions fetch")
    ap.add_argument("--accounts", action="store_true", help="Also fetch accounts summary")
    ap.add_argument("--orders", action="store_true", help="Also fetch open orders")
    ap.add_argument("--post-to-store", dest="store_url", default=os.getenv("STORE_URL"),
                    help="If set, POST positions JSON to this URL (e.g., http://positions-store:8090/ingest)")
    args = ap.parse_args()

    try:
        token = get_token(args.proxy)
        gateway = get_gateway_base(args.env)
        if not args.no_positions:
            data = get_positions(token, gateway)
            rows = data.get("Data") or data.get("Positions") or []
            print(f"Positions count: {len(rows)}")
            for p in rows[:5]:
                base = p.get("PositionBase", {})
                fmt = p.get("DisplayAndFormat", {})
                view = p.get("PositionView", {})
                sym = fmt.get("Symbol") or base.get("Symbol") or base.get("Uic")
                acc = base.get("AccountId")
                amt = base.get("Amount")
                px = view.get("CurrentPrice")
                pnl = view.get("ProfitLossOnTrade")
                print(f"- {sym} acc={acc} amount={amt} price={px} PnL={pnl}")

            if args.json_out or args.store_url:
                try:
                    if args.json_out:
                        os.makedirs(os.path.dirname(args.json_out) or ".", exist_ok=True)
                        with open(args.json_out, "w", encoding="utf-8") as f:
                            json.dump(data, f, indent=2)
                        print(f"Saved JSON to {args.json_out}")
                    if args.store_url:
                        hdrs = {"Content-Type": "application/json"}
                        rs = requests.post(args.store_url, headers=hdrs, data=json.dumps(data), timeout=15)
                        print(f"Store ingest status: {rs.status_code} {rs.text[:200]}")
                except Exception as e:
                    print(f"Warning: failed to write JSON: {e}")

        if args.accounts:
            accs = get_accounts(token, gateway)
            items = accs.get("Data") or accs.get("Accounts") or []
            print(f"Accounts count: {len(items)}")
            for a in items[:5]:
                aid = a.get("AccountId") or a.get("AccountKey")
                summ = a.get("AccountSummary") or {}
                bal = summ.get("NetEquityForMargin") or summ.get("CashBalance")
                print(f"- Account {aid} balance={bal}")

        if args.orders:
            ords = get_open_orders(token, gateway)
            items = ords.get("Data") or ords.get("Orders") or []
            print(f"Open orders count: {len(items)}")
            for o in items[:5]:
                oid = o.get("OrderId") or o.get("OrderIdGuid")
                sym = (o.get("DisplayAndFormat") or {}).get("Symbol") or o.get("Uic")
                st = o.get("Status")
                side = o.get("BuySell")
                qty = o.get("Amount")
                print(f"- Order {oid} {side} {qty} {sym} status={st}")
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(2)


if __name__ == "__main__":
    main()
