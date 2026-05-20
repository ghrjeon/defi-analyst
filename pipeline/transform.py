"""
Export Supabase data to Dune-ready CSVs.

Reads from Supabase tables, produces:
  - data/csv/defi_overview_daily.csv           (aggregate timeseries)
  - data/csv/defi_overview_chain_daily.csv     (per-chain timeseries)
  - data/csv/defi_overview_chain_category.csv  (category breakdown snapshot)

Usage:
    python transform.py
"""

import csv
from pathlib import Path

from .db import get_client, fetch_all

PROJECT_DIR = Path(__file__).resolve().parent.parent
CSV_DIR = PROJECT_DIR / "data" / "csv"

TOP_CHAINS = [
    "Ethereum", "Solana", "BSC", "Bitcoin", "Tron", "Base",
    "Arbitrum", "Hyperliquid L1", "Polygon",
    "MegaETH", "Avalanche", "Sui", "Monad", "Optimism",
    "Cronos", "Ink", "Aptos", "Mantle", "Starknet",
    "Stellar", "Movement", "Flare", "Cardano", "Near", "Rootstock",
]


def write_csv(path, columns, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({c: row.get(c, "") for c in columns})
    print(f"wrote {path} ({len(rows)} rows)")


def build_aggregate(client):
    """Export defi_daily → defi_overview_daily.csv"""
    rows = fetch_all(client, "defi_daily")
    columns = [
        "date", "tvl", "dex_volume", "fees", "stablecoin_mcap",
        "options_volume", "open_interest", "active_addresses",
    ]
    for row in rows:
        row["date"] = row["date"] + " 00:00:00"
    write_csv(CSV_DIR / "defi_overview_daily.csv", columns, rows)


def build_chain(client):
    """Export defi_chain_daily → defi_overview_chain_daily.csv"""
    rows = fetch_all(client, "defi_chain_daily", filters={"chain": TOP_CHAINS})
    columns = [
        "date", "chain", "tvl", "dex_volume", "fees",
        "stablecoin_mcap", "open_interest", "active_addresses",
    ]
    for row in rows:
        row["date"] = row["date"] + " 00:00:00"
    write_csv(CSV_DIR / "defi_overview_chain_daily.csv", columns, rows)


def build_category(client):
    """Export defi_chain_category → defi_overview_chain_category.csv"""
    rows = fetch_all(client, "defi_chain_category", order_by="chain")
    columns = ["chain", "metric", "category", "total24h", "total7d", "protocol_count"]
    write_csv(CSV_DIR / "defi_overview_chain_category.csv", columns, rows)


def run(client=None):
    """Run transform. Called by run.py orchestrator or standalone."""
    if client is None:
        client = get_client()
    build_aggregate(client)
    build_chain(client)
    build_category(client)


def main():
    print("exporting Supabase → Dune CSVs\n")
    run()
    print("\ndone.")


if __name__ == "__main__":
    main()
