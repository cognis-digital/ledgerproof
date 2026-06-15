"""Hardening tests — edge cases, bad input, and error-path coverage.

All tests here were added as part of the production hardening pass and cover
paths that previously raised unhandled exceptions or produced silent wrong
results.
"""
from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ledgerproof.core import LedgerError, load_entries, verify_ledger  # noqa: E402
from ledgerproof.cli import main  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _two_line_entry(eid: str, amount: str = "10.00"):
    return {
        "id": eid,
        "lines": [
            {"account": "assets:cash", "debit": amount, "credit": "0"},
            {"account": "equity:open", "debit": "0", "credit": amount},
        ],
    }


# ---------------------------------------------------------------------------
# core.py — _to_decimal: non-finite amounts
# ---------------------------------------------------------------------------

class TestNonFiniteAmounts:
    def test_infinity_rejected(self):
        data = json.dumps([
            {"id": "t1", "lines": [
                {"account": "a", "debit": "Infinity", "credit": "0"},
                {"account": "b", "debit": "0", "credit": "Infinity"},
            ]}
        ])
        with pytest.raises(LedgerError, match="finite"):
            load_entries(data)

    def test_negative_infinity_rejected(self):
        data = json.dumps([
            {"id": "t1", "lines": [
                {"account": "a", "debit": "-Infinity", "credit": "0"},
                {"account": "b", "debit": "0", "credit": "0"},
            ]}
        ])
        with pytest.raises(LedgerError):
            load_entries(data)


# ---------------------------------------------------------------------------
# core.py — duplicate entry IDs
# ---------------------------------------------------------------------------

class TestDuplicateEntryIds:
    def test_duplicate_ids_flagged(self):
        data = json.dumps([_two_line_entry("dup"), _two_line_entry("dup")])
        entries = load_entries(data)
        result = verify_ledger(entries)
        assert result.ok is False
        dup_findings = [f for f in result.findings if f.kind == "bad_structure"]
        assert any("duplicate" in f.message for f in dup_findings)

    def test_unique_ids_not_flagged(self):
        data = json.dumps([_two_line_entry("a"), _two_line_entry("b")])
        entries = load_entries(data)
        result = verify_ledger(entries)
        assert result.ok is True


# ---------------------------------------------------------------------------
# core.py — empty ledger
# ---------------------------------------------------------------------------

class TestEmptyLedger:
    def test_empty_array_parses(self):
        entries = load_entries("[]")
        assert entries == []

    def test_empty_ledger_verifies_ok(self):
        result = verify_ledger([])
        assert result.ok is True
        assert result.entry_count == 0
        assert result.total_debit == "0"
        assert result.total_credit == "0"
        assert result.account_balances == {}


# ---------------------------------------------------------------------------
# cli.py — _cmd_seal write error returns exit code 2
# ---------------------------------------------------------------------------

class TestSealWriteError:
    def test_seal_bad_output_path_exits_2(self, tmp_path, capsys):
        src = tmp_path / "draft.json"
        src.write_text(json.dumps([_two_line_entry("x")]), encoding="utf-8")
        bad_out = str(tmp_path / "no_such_dir" / "out.json")
        rc = main(["seal", str(src), "-o", bad_out])
        assert rc == 2
        err = capsys.readouterr().err
        assert "error" in err.lower()


# ---------------------------------------------------------------------------
# cli.py — missing file returns exit code 2 with message on stderr
# ---------------------------------------------------------------------------

class TestMissingFileError:
    def test_verify_missing_file_exits_2(self, capsys):
        rc = main(["verify", "/no/such/ledger_abcxyz.json"])
        assert rc == 2
        err = capsys.readouterr().err
        assert "error" in err.lower()

    def test_seal_missing_file_exits_2(self, capsys):
        rc = main(["seal", "/no/such/draft_abcxyz.json"])
        assert rc == 2
        err = capsys.readouterr().err
        assert "error" in err.lower()


# ---------------------------------------------------------------------------
# cli.py — malformed JSON returns exit code 2
# ---------------------------------------------------------------------------

class TestMalformedJson:
    def test_verify_malformed_json_exits_2(self, tmp_path, capsys):
        bad = tmp_path / "bad.json"
        bad.write_text("{not valid json}", encoding="utf-8")
        rc = main(["verify", str(bad)])
        assert rc == 2
        err = capsys.readouterr().err
        assert "error" in err.lower()

    def test_verify_non_array_json_exits_2(self, tmp_path, capsys):
        bad = tmp_path / "obj.json"
        bad.write_text(json.dumps({"foo": "bar"}), encoding="utf-8")
        rc = main(["verify", str(bad)])
        assert rc == 2
        err = capsys.readouterr().err
        assert "error" in err.lower()


# ---------------------------------------------------------------------------
# cli.py — binary / non-UTF-8 file returns exit code 2 (UnicodeDecodeError)
# ---------------------------------------------------------------------------

class TestBinaryFileError:
    def test_verify_binary_file_exits_2(self, tmp_path, capsys):
        """A file that cannot be decoded as UTF-8 must not raise a traceback."""
        bad = tmp_path / "binary.json"
        bad.write_bytes(b"\xff\xfe not valid utf-8 \x00\x01")
        rc = main(["verify", str(bad)])
        assert rc == 2
        err = capsys.readouterr().err
        assert "error" in err.lower()

    def test_seal_binary_file_exits_2(self, tmp_path, capsys):
        bad = tmp_path / "binary.json"
        bad.write_bytes(b"\xff\xfe not valid utf-8 \x00\x01")
        rc = main(["seal", str(bad)])
        assert rc == 2
        err = capsys.readouterr().err
        assert "error" in err.lower()


# ---------------------------------------------------------------------------
# core.py — large-exponent Decimal does not crash quantize in verify_ledger
# ---------------------------------------------------------------------------

class TestLargeAmountBalance:
    def test_large_exponent_amount_does_not_crash(self):
        """Amounts like 1E+100 must not raise InvalidOperation in verify_ledger."""
        data = json.dumps([
            {"id": "big", "lines": [
                {"account": "assets:huge", "debit": "1E+100", "credit": "0"},
                {"account": "equity:huge", "debit": "0", "credit": "1E+100"},
            ]}
        ])
        entries = load_entries(data)
        result = verify_ledger(entries)
        # balanced, so ok=True (no balance findings)
        balance_findings = [f for f in result.findings if f.kind == "unbalanced"]
        assert not balance_findings
        # account_balances must contain a key for each account
        assert "assets:huge" in result.account_balances
        assert "equity:huge" in result.account_balances


# ---------------------------------------------------------------------------
# core.py — non-string date/memo rejected with clear LedgerError
# ---------------------------------------------------------------------------

class TestNonStringFields:
    def test_integer_date_rejected(self):
        data = json.dumps([
            {"id": "t1", "date": 20260101, "lines": [
                {"account": "a", "debit": "5", "credit": "0"},
                {"account": "b", "debit": "0", "credit": "5"},
            ]}
        ])
        with pytest.raises(LedgerError, match="date"):
            load_entries(data)

    def test_list_memo_rejected(self):
        data = json.dumps([
            {"id": "t1", "memo": ["not", "a", "string"], "lines": [
                {"account": "a", "debit": "5", "credit": "0"},
                {"account": "b", "debit": "0", "credit": "5"},
            ]}
        ])
        with pytest.raises(LedgerError, match="memo"):
            load_entries(data)

    def test_string_date_and_memo_accepted(self):
        """String values for date and memo must still work as before."""
        data = json.dumps([
            {"id": "t1", "date": "2026-01-01", "memo": "ok", "lines": [
                {"account": "a", "debit": "5", "credit": "0"},
                {"account": "b", "debit": "0", "credit": "5"},
            ]}
        ])
        entries = load_entries(data)
        assert entries[0].date == "2026-01-01"
        assert entries[0].memo == "ok"
