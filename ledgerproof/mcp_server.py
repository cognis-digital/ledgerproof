"""LEDGERPROOF MCP server — exposes scan() as an MCP tool for Cognis.Studio."""
from __future__ import annotations
from ledgerproof.core import scan, to_json

def serve() -> int:
    """Start an MCP stdio server. Requires the optional 'mcp' extra:
        pip install "cognis-ledgerproof[mcp]"
    """
    try:
        from mcp.server.fastmcp import FastMCP
    except Exception:
        print("Install the MCP extra: pip install 'cognis-ledgerproof[mcp]'")
        return 1
    app = FastMCP("ledgerproof")

    @app.tool()
    def ledgerproof_scan(target: str) -> str:
        """Verifies double-entry ledger integrity and tamper-evidence by checking balance invariants and hash-chained journal entries.. Returns JSON findings."""
        return to_json(scan(target))

    app.run()
    return 0
