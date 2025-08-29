# Demo 01 — basic ledger verification

This demo ships a small, **sealed** double-entry ledger (`ledger.json`) with a
valid SHA-256 hash chain. It demonstrates both of LEDGERPROOF's checks.

## The ledger

Four transactions:

1. `txn-0001` — opening balance: $1,000 cash funded from equity.
2. `txn-0002` — buy $400 of inventory with cash.
3. `txn-0003` — sell inventory: $250 cash in, $200 inventory out, $50 revenue.
4. `txn-0004` — pay $120 rent expense from cash.

Every transaction balances (debits == credits), and each entry's `hash` is
derived from its content plus the previous entry's `hash`.

## Run it

```bash
python -m ledgerproof verify demos/01-basic/ledger.json
```

### Expected result

```
status         : OK
findings       : 0
```

Exit code `0`.

## Try tampering

Change any amount in an earlier entry (e.g. make `txn-0001`'s debit `9999.00`)
and re-run. You will see **two** classes of finding:

- `unbalanced` — if the edit broke the debit/credit equality, and
- `broken_chain` — because the stored `hash` no longer matches the recomputed
  content hash, *and* every later entry's `prev_hash` linkage is now wrong.

The command exits non-zero (`1`), which fails a CI gate.

To re-seal a draft after a legitimate change:

```bash
python -m ledgerproof seal demos/01-basic/ledger.json -o resealed.json
```
