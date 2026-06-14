"""LEDGERPROOF MCP server — exposes verify() as an MCP tool for Cognis.Studio."""
from __future__ import annotations

import json

from ledgerproof.core import LedgerError, load_entries, verify_ledger


def serve() -> int:
    """Start an MCP stdio server. Requires the optional 'mcp' extra:
        pip install "cognis-ledgerproof[mcp]"
    """
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError:
        print("Install the MCP extra: pip install 'cognis-ledgerproof[mcp]'")
        return 1
    app = FastMCP("ledgerproof")

    @app.tool()
    def ledgerproof_verify(ledger_json: str) -> str:
        """Verify double-entry ledger integrity and tamper-evidence.

        Accepts a JSON string (array of entry objects) and returns a JSON
        object with balance findings and hash-chain results.
        """
        try:
            entries = load_entries(ledger_json)
        except LedgerError as exc:
            return json.dumps({"ok": False, "error": str(exc)})
        result = verify_ledger(entries)
        return json.dumps(result.to_dict())

    app.run()
    return 0
