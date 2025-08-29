"""Command-line interface for LEDGERPROOF.

Examples
--------
Verify a ledger and gate CI on it (exit code is non-zero on any finding)::

    python -m ledgerproof verify demos/01-basic/ledger.json
    python -m ledgerproof verify ledger.json --format json | jq .

Seal a draft ledger (compute the hash chain) and write it back out::

    python -m ledgerproof seal draft.json -o sealed.json
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import List, Optional

from . import TOOL_NAME, TOOL_VERSION
from .core import (
    LedgerError,
    chain_entries,
    load_entries,
    verify_ledger,
)


def _read(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def _render_table(result, path: str) -> str:
    lines: List[str] = []
    status = "OK" if result.ok else "FAIL"
    lines.append(f"LEDGERPROOF {TOOL_VERSION}  —  {path}")
    lines.append("-" * 60)
    lines.append(f"entries        : {result.entry_count}")
    lines.append(f"total debit    : {result.total_debit}")
    lines.append(f"total credit   : {result.total_credit}")
    lines.append(f"findings       : {len(result.findings)}")
    lines.append(f"status         : {status}")
    if result.account_balances:
        lines.append("")
        lines.append("account balances (debit - credit):")
        width = max(len(a) for a in result.account_balances)
        for acct, bal in result.account_balances.items():
            lines.append(f"  {acct.ljust(width)}  {bal:>14}")
    if result.findings:
        lines.append("")
        lines.append("findings:")
        for f in result.findings:
            lines.append(
                f"  [{f.kind}] entry {f.entry_id!r} (#{f.index}): {f.message}"
            )
    return "\n".join(lines)


def _cmd_verify(args) -> int:
    try:
        entries = load_entries(_read(args.ledger))
    except (LedgerError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    result = verify_ledger(entries)
    if args.format == "json":
        out = result.to_dict()
        out["tool"] = TOOL_NAME
        out["version"] = TOOL_VERSION
        out["source"] = args.ledger
        print(json.dumps(out, indent=2))
    else:
        print(_render_table(result, args.ledger))
    return 0 if result.ok else 1


def _cmd_seal(args) -> int:
    try:
        entries = load_entries(_read(args.ledger))
    except (LedgerError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    chain_entries(entries)
    payload = [e.to_dict() for e in entries]
    text = json.dumps(payload, indent=2)
    if args.output and args.output != "-":
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
        if args.format == "json":
            print(json.dumps({
                "tool": TOOL_NAME,
                "version": TOOL_VERSION,
                "sealed": len(entries),
                "output": args.output,
                "final_hash": entries[-1].hash if entries else None,
            }, indent=2))
        else:
            print(f"sealed {len(entries)} entries -> {args.output}")
    else:
        print(text)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=TOOL_NAME,
        description=(
            "Verify double-entry ledger integrity: prove debits == credits "
            "per transaction and detect retroactive edits via a hash chain."
        ),
        epilog=(
            "examples:\n"
            "  python -m ledgerproof verify ledger.json\n"
            "  python -m ledgerproof verify ledger.json --format json | jq .\n"
            "  python -m ledgerproof seal draft.json -o sealed.json\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version", action="version",
        version=f"{TOOL_NAME} {TOOL_VERSION}",
    )
    parser.add_argument(
        "--format", choices=["table", "json"], default="table",
        help="output format (default: table)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_verify = sub.add_parser(
        "verify",
        help="verify balance invariants + hash chain (exit 1 on findings)",
        description=(
            "Verify a ledger. Exits 0 when clean, 1 when findings exist "
            "(use as a CI gate), 2 on input/parse errors."
        ),
    )
    p_verify.add_argument(
        "ledger", help="path to ledger JSON file, or '-' for stdin"
    )
    p_verify.set_defaults(func=_cmd_verify)

    p_seal = sub.add_parser(
        "seal",
        help="compute the hash chain for a draft ledger and write it out",
        description=(
            "Populate prev_hash/hash on every entry so future edits are "
            "detectable, then emit the sealed ledger."
        ),
    )
    p_seal.add_argument(
        "ledger", help="path to draft ledger JSON file, or '-' for stdin"
    )
    p_seal.add_argument(
        "-o", "--output", default="-",
        help="output path (default: stdout)",
    )
    p_seal.set_defaults(func=_cmd_seal)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
