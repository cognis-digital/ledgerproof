#!/usr/bin/env python3
"""Minimal, dependency-free webhook forwarder for Cognis findings.

Reads JSON findings on stdin and POSTs them to a URL (SIEM/Slack/Jira bridge).
Usage:  <tool> scan . --format json | python integrations/webhook.py --url URL
"""
from __future__ import annotations

import argparse
import sys
import urllib.request
from urllib.parse import urlparse


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Forward ledgerproof JSON findings to a webhook URL."
    )
    ap.add_argument("--url", required=True, help="Destination URL (http/https)")
    ap.add_argument("--header", action="append", default=[], help="Key: Value")
    args = ap.parse_args()

    # Validate URL scheme before attempting any network I/O.
    parsed = urlparse(args.url)
    if parsed.scheme not in ("http", "https"):
        print(
            f"error: --url must use http or https scheme, got {parsed.scheme!r}",
            file=sys.stderr,
        )
        return 2
    if not parsed.netloc:
        print("error: --url is missing a host", file=sys.stderr)
        return 2

    payload = sys.stdin.buffer.read()
    if not payload.strip():
        print("error: no input on stdin", file=sys.stderr)
        return 2

    req = urllib.request.Request(args.url, data=payload, method="POST")
    req.add_header("Content-Type", "application/json")
    for h in args.header:
        k, _, v = h.partition(":")
        req.add_header(k.strip(), v.strip())
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            print(f"posted {len(payload)} bytes -> {r.status}")
        return 0
    except Exception as e:
        print(f"webhook error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
