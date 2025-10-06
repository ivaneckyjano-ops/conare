#!/usr/bin/env python3
"""Simple token refresher daemon for Saxo tokens.

This imports helper functions from `test_oauth_min.py` (load_tokens, try_refresh, save_tokens)
and runs a loop that refreshes tokens when they are close to expiry.
Designed to run as a lightweight systemd service on a droplet.
"""
import time
import sys
import argparse

from test_oauth_min import load_tokens, try_refresh, save_tokens, _now


def run_daemon(interval: int = 30, margin: int = 120, exit_on_missing: bool = False):
    """Loop forever, checking tokens every `interval` seconds.
    If tokens.expires_at <= now + margin, attempt refresh.
    """
    print(f"Starting token daemon: interval={interval}s, refresh when <= {margin}s until expiry")
    backoff = 5
    while True:
        tokens = load_tokens()
        if not tokens:
            msg = "No tokens found (tokens file missing or unreadable)."
            print(msg)
            if exit_on_missing:
                print("Exiting because --exit-on-missing set")
                return 1
            time.sleep(interval)
            continue

        exp = int(tokens.get("expires_at", 0) or 0)
        now = _now()
        ttl = exp - now if exp else None
        if ttl is None:
            print("Tokens have no expires_at; attempting refresh")
            refreshed = try_refresh(tokens)
            if refreshed:
                print("Refresh succeeded (no expires_at case)")
                backoff = 5
            else:
                print("Refresh failed; backing off")
                time.sleep(backoff)
                backoff = min(backoff * 2, 300)
            continue

        print(f"Token TTL: {ttl}s")
        if ttl <= margin:
            print("TTL below margin -> attempting refresh")
            refreshed = try_refresh(tokens)
            if refreshed:
                print("Refresh succeeded")
                backoff = 5
            else:
                print("Refresh failed; will retry after backoff")
                time.sleep(backoff)
                backoff = min(backoff * 2, 300)
                continue
        else:
            # enough time; reset backoff and sleep
            backoff = 5

        time.sleep(interval)


def main():
    parser = argparse.ArgumentParser(description="Daemon to refresh Saxo tokens periodically.")
    parser.add_argument("--interval", type=int, default=30, help="Poll interval in seconds (default 30)")
    parser.add_argument("--margin", type=int, default=120, help="Refresh when token TTL <= margin seconds (default 120)")
    parser.add_argument("--exit-on-missing", action="store_true", help="Exit if tokens file is missing")
    parser.add_argument("--tokens-file", dest="tokens_file", default=None, help="Path to tokens file (overrides env TOKENS_FILE)")
    args = parser.parse_args()

    # allow overriding the module-level TOKENS_FILE via CLI
    global TOKENS_FILE
    if args.tokens_file:
        TOKENS_FILE = args.tokens_file

    try:
        rc = run_daemon(interval=args.interval, margin=args.margin, exit_on_missing=args.exit_on_missing)
        if rc:
            sys.exit(rc)
    except KeyboardInterrupt:
        print("Token daemon interrupted by user")


if __name__ == "__main__":
    main()
