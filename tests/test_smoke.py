"""Smoke tests for LEDGERPROOF. No network. Runs against the shipped demo."""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ledgerproof import (  # noqa: E402
    TOOL_NAME,
    TOOL_VERSION,
    chain_entries,
    compute_entry_hash,
    load_entries,
    verify_ledger,
)
from ledgerproof.cli import main  # noqa: E402

DEMO_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "demos", "01-basic",
)
DEMO_LEDGER = os.path.join(DEMO_DIR, "ledger.json")


def _sealed_demo_entries():
    """Load the demo ledger and (re)seal it so hashes are valid.

    The shipped JSON uses PLACEHOLDER hashes for readability; chaining
    recomputes the real chain, which is what a sealed ledger looks like.
    """
    with open(DEMO_LEDGER, "r", encoding="utf-8") as fh:
        entries = load_entries(fh.read())
    return chain_entries(entries)


def test_metadata():
    assert TOOL_NAME == "ledgerproof"
    assert TOOL_VERSION.count(".") == 2


def test_demo_parses_to_four_entries():
    entries = _sealed_demo_entries()
    assert len(entries) == 4
    assert [e.id for e in entries] == [
        "txn-0001", "txn-0002", "txn-0003", "txn-0004",
    ]


def test_sealed_demo_verifies_clean():
    entries = _sealed_demo_entries()
    result = verify_ledger(entries)
    assert result.ok is True
    assert result.findings == []
    assert result.entry_count == 4
    # whole ledger balances
    assert result.total_debit == result.total_credit
    # cash = 1000 - 400 + 250 - 120 = 730
    assert result.account_balances["assets:cash"] == "730.00"


def test_unbalanced_entry_is_detected():
    entries = _sealed_demo_entries()
    # break debit/credit equality on the first entry
    entries[0].lines[0].debit += __import__("decimal").Decimal("1.00")
    result = verify_ledger(entries)
    assert result.ok is False
    kinds = {f.kind for f in result.findings}
    assert "unbalanced" in kinds
    unbal = [f for f in result.findings if f.kind == "unbalanced"]
    assert unbal[0].entry_id == "txn-0001"


def test_retroactive_edit_breaks_chain():
    entries = _sealed_demo_entries()
    # tamper with a sealed entry's content WITHOUT re-sealing
    entries[1].memo = "tampered!"
    result = verify_ledger(entries)
    assert result.ok is False
    chain_findings = [f for f in result.findings if f.kind == "broken_chain"]
    assert chain_findings, "editing a sealed entry must break the chain"
    # the edited entry itself is flagged
    assert any(f.entry_id == "txn-0002" for f in chain_findings)


def test_hash_is_deterministic():
    entries = _sealed_demo_entries()
    h1 = compute_entry_hash(entries[0])
    h2 = compute_entry_hash(entries[0])
    assert h1 == h2 and len(h1) == 64


def test_cli_verify_clean_exit_zero(tmp_path, capsys):
    sealed = tmp_path / "sealed.json"
    entries = _sealed_demo_entries()
    sealed.write_text(
        json.dumps([e.to_dict() for e in entries]), encoding="utf-8"
    )
    rc = main(["verify", str(sealed)])
    assert rc == 0
    assert "OK" in capsys.readouterr().out


def test_cli_verify_tampered_exit_one(tmp_path):
    sealed = tmp_path / "bad.json"
    entries = _sealed_demo_entries()
    payload = [e.to_dict() for e in entries]
    # silently mutate a sealed amount -> chain + balance break
    payload[2]["lines"][0]["debit"] = "9999.00"
    sealed.write_text(json.dumps(payload), encoding="utf-8")
    rc = main(["verify", str(sealed), "--format", "json"])
    assert rc == 1


def test_cli_json_output_shape(tmp_path, capsys):
    sealed = tmp_path / "s.json"
    entries = _sealed_demo_entries()
    sealed.write_text(
        json.dumps([e.to_dict() for e in entries]), encoding="utf-8"
    )
    rc = main(["verify", str(sealed), "--format", "json"])
    out = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert out["tool"] == "ledgerproof"
    assert out["ok"] is True
    assert out["entry_count"] == 4
    assert "account_balances" in out


def test_cli_seal_roundtrips(tmp_path, capsys):
    # draft with no hashes
    draft = [
        {"id": "a", "lines": [
            {"account": "x", "debit": "5", "credit": "0"},
            {"account": "y", "debit": "0", "credit": "5"},
        ]},
    ]
    src = tmp_path / "draft.json"
    out = tmp_path / "sealed.json"
    src.write_text(json.dumps(draft), encoding="utf-8")
    rc = main(["seal", str(src), "-o", str(out)])
    assert rc == 0
    sealed_entries = load_entries(out.read_text(encoding="utf-8"))
    assert sealed_entries[0].hash and len(sealed_entries[0].hash) == 64
    # the freshly sealed ledger verifies clean
    assert verify_ledger(sealed_entries).ok is True
