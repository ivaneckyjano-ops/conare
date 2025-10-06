#!/usr/bin/env python3
"""Positions Store Service

Simple read-only aggregation store for live positions, backed by SQLite.
Ingests position snapshots via POST /ingest and only updates rows when price change
exceeds a configurable threshold per instrument.

Config via env:
- HOST (default 0.0.0.0)
- PORT (default 8090)
- DB_PATH (default /data/positions.db)
- THRESHOLD_PCT (default 0.005 = 0.5%)
- THRESHOLDS_FILE (default /data/thresholds.json) optional per-UIC thresholds
"""
import os
import json
import time
import sqlite3
from typing import Optional, Dict
from flask import Flask, request, jsonify


HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8090"))
DB_PATH = os.getenv("DB_PATH", "/data/positions.db")
DEFAULT_THRESHOLD = float(os.getenv("THRESHOLD_PCT", "0.005"))  # 0.5%
THRESHOLDS_FILE = os.getenv("THRESHOLDS_FILE", "/data/thresholds.json")

app = Flask(__name__)


def _connect():
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db():
    with _connect() as conn:
        c = conn.cursor()
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS positions (
                uic INTEGER PRIMARY KEY,
                symbol TEXT,
                account_id TEXT,
                amount REAL,
                last_price REAL,
                pnl REAL,
                updated_at INTEGER
            )
            """
        )
        conn.commit()


def _load_thresholds() -> Dict[str, float]:
    try:
        with open(THRESHOLDS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        # ensure floats
        return {str(k): float(v) for k, v in data.items()}
    except Exception:
        return {}


def _should_update(old_price: Optional[float], new_price: Optional[float], uic: str, thresholds: Dict[str, float]) -> bool:
    if new_price is None:
        return False
    if old_price is None:
        return True
    thr = thresholds.get(str(uic), DEFAULT_THRESHOLD)
    try:
        if old_price == 0:
            # avoid div by zero; any non-zero change triggers update
            return abs(new_price) > 0
        rel = abs(new_price - old_price) / abs(old_price)
        return rel >= thr
    except Exception:
        return True


@app.route("/health")
def health():
    return jsonify({"ok": True})


@app.route("/positions", methods=["GET"])
def list_positions():
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM positions ORDER BY updated_at DESC").fetchall()
        out = [dict(r) for r in rows]
    return jsonify({"count": len(out), "data": out})


@app.route("/positions/<uic>", methods=["GET"])
def get_position(uic: str):
    with _connect() as conn:
        row = conn.execute("SELECT * FROM positions WHERE uic=?", (int(uic),)).fetchone()
        if not row:
            return jsonify({"error": "not found"}), 404
        return jsonify(dict(row))


@app.route("/ingest", methods=["POST"])
def ingest():
    payload = request.get_json(silent=True) or {}
    items = payload.get("Data") or payload.get("Positions") or []
    thresholds = _load_thresholds()
    now = int(time.time())
    updated = 0
    skipped = 0
    with _connect() as conn:
        cur = conn.cursor()
        for p in items:
            base = p.get("PositionBase", {})
            fmt = p.get("DisplayAndFormat", {})
            view = p.get("PositionView", {})
            try:
                uic = int(base.get("Uic")) if base.get("Uic") is not None else None
            except Exception:
                uic = None
            if not uic:
                skipped += 1
                continue
            symbol = fmt.get("Symbol") or base.get("Symbol") or str(uic)
            account_id = base.get("AccountId")
            amount = base.get("Amount")
            last_price_new = view.get("CurrentPrice")
            pnl = view.get("ProfitLossOnTrade")

            row = cur.execute("SELECT last_price FROM positions WHERE uic=?", (uic,)).fetchone()
            last_price_old = row[0] if row else None

            if _should_update(last_price_old, last_price_new, str(uic), thresholds):
                cur.execute(
                    """
                    INSERT INTO positions (uic, symbol, account_id, amount, last_price, pnl, updated_at)
                    VALUES(?,?,?,?,?,?,?)
                    ON CONFLICT(uic) DO UPDATE SET
                        symbol=excluded.symbol,
                        account_id=excluded.account_id,
                        amount=excluded.amount,
                        last_price=excluded.last_price,
                        pnl=excluded.pnl,
                        updated_at=excluded.updated_at
                    """,
                    (uic, symbol, str(account_id) if account_id is not None else None, amount, last_price_new, pnl, now),
                )
                updated += 1
            else:
                skipped += 1
        conn.commit()
    return jsonify({"ok": True, "updated": updated, "skipped": skipped, "count": len(items)})


def main():
    _init_db()
    app.run(host=HOST, port=PORT, debug=False)


if __name__ == "__main__":
    main()
