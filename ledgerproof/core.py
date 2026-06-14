"""Core engine for LEDGERPROOF.

No third-party imports. All amounts are handled with :class:`decimal.Decimal`
to avoid binary floating-point drift in money math.

Ledger format (JSON)
--------------------
A ledger is a JSON array of *entries*. Each entry is an object::

    {
      "id": "txn-0001",            # unique transaction id (string)
      "date": "2026-01-01",        # ISO date or datetime (string, optional)
      "memo": "opening balance",   # free text (optional)
      "lines": [                    # >= 2 postings
        {"account": "assets:cash",  "debit": "100.00", "credit": "0"},
        {"account": "equity:open",  "debit": "0",      "credit": "100.00"}
      ],
      "prev_hash": "...",          # set by chaining (optional on input)
      "hash": "..."                # set by chaining (optional on input)
    }

A line uses ``debit`` and ``credit`` non-negative amounts (strings or numbers).
Exactly one of them is normally non-zero, but both-zero lines are tolerated.

The hash chain is built from the *content* of each entry (id, date, memo,
lines) plus the previous entry's hash. ``verify_ledger`` recomputes the chain
and compares it against the stored hashes to detect retroactive edits.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional

GENESIS_HASH = "0" * 64
_TWOPLACES = Decimal("0.01")


class LedgerError(Exception):
    """Raised when a ledger cannot be parsed into entries at all."""


def _to_decimal(value: Any, where: str) -> Decimal:
    if value is None or value == "":
        return Decimal("0")
    try:
        # Route through str so floats like 0.1 don't carry binary noise.
        d = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise LedgerError(f"invalid amount {value!r} at {where}") from exc
    if not d.is_finite():
        raise LedgerError(
            f"invalid amount {value!r} at {where}: must be a finite number"
        )
    return d


@dataclass
class Line:
    account: str
    debit: Decimal
    credit: Decimal

    def to_dict(self) -> Dict[str, str]:
        return {
            "account": self.account,
            "debit": format(self.debit, "f"),
            "credit": format(self.credit, "f"),
        }


@dataclass
class Entry:
    id: str
    lines: List[Line]
    date: Optional[str] = None
    memo: Optional[str] = None
    prev_hash: Optional[str] = None
    hash: Optional[str] = None
    index: int = -1

    def total_debit(self) -> Decimal:
        return sum((ln.debit for ln in self.lines), Decimal("0"))

    def total_credit(self) -> Decimal:
        return sum((ln.credit for ln in self.lines), Decimal("0"))

    def content_payload(self) -> Dict[str, Any]:
        """Canonical, hashable representation of the entry's *content*.

        Excludes ``hash`` (the field we are deriving) but includes
        ``prev_hash`` so the chain is tamper-evident.
        """
        return {
            "id": self.id,
            "date": self.date,
            "memo": self.memo,
            "lines": [ln.to_dict() for ln in self.lines],
            "prev_hash": self.prev_hash,
        }

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"id": self.id}
        if self.date is not None:
            d["date"] = self.date
        if self.memo is not None:
            d["memo"] = self.memo
        d["lines"] = [ln.to_dict() for ln in self.lines]
        if self.prev_hash is not None:
            d["prev_hash"] = self.prev_hash
        if self.hash is not None:
            d["hash"] = self.hash
        return d


@dataclass
class Finding:
    kind: str            # 'unbalanced' | 'broken_chain' | 'bad_structure'
    entry_id: str
    index: int
    message: str
    detail: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kind": self.kind,
            "entry_id": self.entry_id,
            "index": self.index,
            "message": self.message,
            "detail": self.detail,
        }


@dataclass
class VerificationResult:
    ok: bool
    entry_count: int
    findings: List[Finding]
    account_balances: Dict[str, str]
    total_debit: str
    total_credit: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "entry_count": self.entry_count,
            "total_debit": self.total_debit,
            "total_credit": self.total_credit,
            "finding_count": len(self.findings),
            "findings": [f.to_dict() for f in self.findings],
            "account_balances": self.account_balances,
        }


def _parse_entry(raw: Any, index: int) -> Entry:
    if not isinstance(raw, dict):
        raise LedgerError(f"entry #{index} is not an object")
    eid = str(raw.get("id", f"entry-{index}"))
    raw_lines = raw.get("lines")
    if not isinstance(raw_lines, list) or not raw_lines:
        raise LedgerError(f"entry {eid!r} (#{index}) has no 'lines' list")
    lines: List[Line] = []
    for j, rl in enumerate(raw_lines):
        if not isinstance(rl, dict):
            raise LedgerError(f"entry {eid!r} line #{j} is not an object")
        account = rl.get("account")
        if not account or not isinstance(account, str):
            raise LedgerError(f"entry {eid!r} line #{j} missing 'account'")
        debit = _to_decimal(rl.get("debit", 0), f"{eid} line {j} debit")
        credit = _to_decimal(rl.get("credit", 0), f"{eid} line {j} credit")
        if debit < 0 or credit < 0:
            raise LedgerError(
                f"entry {eid!r} line #{j} has negative amount"
            )
        lines.append(Line(account=account, debit=debit, credit=credit))
    return Entry(
        id=eid,
        lines=lines,
        date=raw.get("date"),
        memo=raw.get("memo"),
        prev_hash=raw.get("prev_hash"),
        hash=raw.get("hash"),
        index=index,
    )


def load_entries(data: Any) -> List[Entry]:
    """Parse a ledger (a list of entry dicts, or a JSON string) into Entries."""
    if isinstance(data, (str, bytes)):
        try:
            data = json.loads(data)
        except json.JSONDecodeError as exc:
            raise LedgerError(f"invalid JSON: {exc}") from exc
    if isinstance(data, dict) and "entries" in data:
        data = data["entries"]
    if not isinstance(data, list):
        raise LedgerError("ledger must be a JSON array of entries")
    return [_parse_entry(raw, i) for i, raw in enumerate(data)]


def compute_entry_hash(entry: Entry) -> str:
    """SHA-256 over the entry's canonical content (incl. prev_hash)."""
    payload = json.dumps(
        entry.content_payload(),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def chain_entries(entries: List[Entry], genesis: str = GENESIS_HASH) -> List[Entry]:
    """Populate ``prev_hash`` and ``hash`` for every entry, in order.

    Returns the same list (mutated in place) so callers can serialize a
    freshly-sealed ledger.
    """
    prev = genesis
    for entry in entries:
        entry.prev_hash = prev
        entry.hash = compute_entry_hash(entry)
        prev = entry.hash
    return entries


def verify_ledger(
    entries: List[Entry], genesis: str = GENESIS_HASH
) -> VerificationResult:
    """Verify balance invariants and the hash chain.

    Balance checks always run for every entry. Chain checks run only when the
    ledger actually carries hashes (a freshly drafted ledger with no hashes is
    not penalized for tamper-evidence it never claimed).
    """
    findings: List[Finding] = []
    account_balances: Dict[str, Decimal] = {}
    total_debit = Decimal("0")
    total_credit = Decimal("0")

    # Detect duplicate entry IDs up-front so callers get a clear signal.
    seen_ids: Dict[str, int] = {}
    for entry in entries:
        if entry.id in seen_ids:
            findings.append(
                Finding(
                    kind="bad_structure",
                    entry_id=entry.id,
                    index=entry.index,
                    message=(
                        f"duplicate entry id {entry.id!r} "
                        f"(first seen at index {seen_ids[entry.id]})"
                    ),
                    detail={
                        "first_index": seen_ids[entry.id],
                        "duplicate_index": entry.index,
                    },
                )
            )
        else:
            seen_ids[entry.id] = entry.index

    has_chain = any(e.hash for e in entries)
    prev = genesis

    for entry in entries:
        d = entry.total_debit()
        c = entry.total_credit()
        total_debit += d
        total_credit += c

        # --- balance invariant -------------------------------------------
        if d != c:
            findings.append(
                Finding(
                    kind="unbalanced",
                    entry_id=entry.id,
                    index=entry.index,
                    message=(
                        f"debits ({format(d, 'f')}) != credits "
                        f"({format(c, 'f')}); off by "
                        f"{format(d - c, 'f')}"
                    ),
                    detail={
                        "debit": format(d, "f"),
                        "credit": format(c, "f"),
                        "difference": format(d - c, "f"),
                    },
                )
            )
        if len(entry.lines) < 2:
            findings.append(
                Finding(
                    kind="bad_structure",
                    entry_id=entry.id,
                    index=entry.index,
                    message="entry has fewer than 2 postings",
                    detail={"line_count": len(entry.lines)},
                )
            )

        for ln in entry.lines:
            account_balances[ln.account] = (
                account_balances.get(ln.account, Decimal("0"))
                + ln.debit
                - ln.credit
            )

        # --- hash chain (tamper-evidence) --------------------------------
        if has_chain:
            if entry.prev_hash != prev:
                findings.append(
                    Finding(
                        kind="broken_chain",
                        entry_id=entry.id,
                        index=entry.index,
                        message=(
                            "prev_hash does not match the previous entry's "
                            "hash (chain break — an earlier entry was edited, "
                            "reordered, inserted, or removed)"
                        ),
                        detail={
                            "expected_prev_hash": prev,
                            "stored_prev_hash": entry.prev_hash,
                        },
                    )
                )
            recomputed = compute_entry_hash(entry)
            if entry.hash != recomputed:
                findings.append(
                    Finding(
                        kind="broken_chain",
                        entry_id=entry.id,
                        index=entry.index,
                        message=(
                            "stored hash does not match recomputed content "
                            "hash (this entry's content was edited after "
                            "sealing)"
                        ),
                        detail={
                            "stored_hash": entry.hash,
                            "recomputed_hash": recomputed,
                        },
                    )
                )
            # Advance the chain using the *stored* hash so a single edit
            # surfaces as one localized break plus the dependent links,
            # rather than masking later entries entirely.
            prev = entry.hash or recomputed

    quantized = {
        acct: format(bal.quantize(_TWOPLACES) if bal == bal.quantize(_TWOPLACES) or True else bal, "f")
        for acct, bal in sorted(account_balances.items())
    }

    return VerificationResult(
        ok=not findings,
        entry_count=len(entries),
        findings=findings,
        account_balances=quantized,
        total_debit=format(total_debit, "f"),
        total_credit=format(total_credit, "f"),
    )
