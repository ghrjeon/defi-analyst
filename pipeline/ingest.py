"""
Ingest fetched DefiLlama JSON into Supabase.

Parses raw JSON from data/raw/, flattens into structured rows,
and upserts into Supabase tables with incremental date filtering.

Usage:
    python ingest.py                    # ingest all tables
    python ingest.py --table daily      # just aggregate metrics
    python ingest.py --table chain      # just per-chain metrics
    python ingest.py --table category   # just category snapshot
    python ingest.py --full             # force full refresh (ignore max_date)
    python ingest.py --dry-run          # preview without writing
    python ingest.py --status           # show row counts and latest dates
"""

import argparse
import json
import sys
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .db import get_client, get_max_date, upsert_batch, log_ingestion

PROJECT_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_DIR / "data" / "raw"

TOP_CHAINS = [
    "Ethereum", "Solana", "BSC", "Bitcoin", "Tron", "Base",
    "Arbitrum", "Hyperliquid L1", "Polygon",
    "MegaETH", "Avalanche", "Sui", "Monad", "Optimism",
    "Cronos", "Ink", "Aptos", "Mantle", "Starknet",
    "Stellar", "Movement", "Flare", "Cardano", "Near", "Rootstock",
]


def load_json(path):
    with open(path) as f:
        return json.load(f)


def ts_to_date(ts):
    return datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%Y-%m-%d")


def fetched_at_now():
    return datetime.utcnow().isoformat() + "Z"


def yesterday():
    """Cutoff date — only ingest up to yesterday to avoid partial rows."""
    return (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# Parsers — raw JSON → flat rows
# ---------------------------------------------------------------------------

def parse_defi_daily():
    """Parse aggregate timeseries sources into defi_daily rows."""
    daily = defaultdict(dict)

    path = RAW_DIR / "tvl" / "tvl_historical.json"
    if path.exists():
        for row in load_json(path)["data"]:
            d = ts_to_date(row["date"])
            daily[d]["tvl"] = row["tvl"]

    path = RAW_DIR / "volumes" / "dex_volumes.json"
    if path.exists():
        data = load_json(path)["data"]
        for ts, vol in data.get("totalDataChart", []):
            d = ts_to_date(ts)
            daily[d]["dex_volume"] = vol

    path = RAW_DIR / "fees" / "fees_overview.json"
    if path.exists():
        data = load_json(path)["data"]
        for ts, fees in data.get("totalDataChart", []):
            d = ts_to_date(ts)
            daily[d]["fees"] = fees

    path = RAW_DIR / "stablecoins" / "stablecoin_mcap_history.json"
    if path.exists():
        for row in load_json(path)["data"]:
            d = ts_to_date(row["date"])
            daily[d]["stablecoin_mcap"] = row.get("totalCirculatingUSD", {}).get("peggedUSD")

    path = RAW_DIR / "volumes" / "options_volumes.json"
    if path.exists():
        data = load_json(path)["data"]
        for ts, vol in data.get("totalDataChart", []):
            d = ts_to_date(ts)
            daily[d]["options_volume"] = vol

    path = RAW_DIR / "volumes" / "open_interest.json"
    if path.exists():
        data = load_json(path)["data"]
        for ts, oi in data.get("totalDataChart", []):
            d = ts_to_date(ts)
            daily[d]["open_interest"] = oi

    path = RAW_DIR / "users" / "active_users.json"
    if path.exists():
        data = load_json(path)["data"]
        for ts, users in data.get("totalDataChart", []):
            d = ts_to_date(ts)
            daily[d]["active_addresses"] = users

    now = fetched_at_now()
    cutoff = yesterday()
    rows = []
    for d in sorted(daily.keys()):
        if d > cutoff:
            continue
        rows.append({
            "date": d,
            "tvl": daily[d].get("tvl"),
            "dex_volume": daily[d].get("dex_volume"),
            "fees": daily[d].get("fees"),
            "stablecoin_mcap": daily[d].get("stablecoin_mcap"),
            "options_volume": daily[d].get("options_volume"),
            "open_interest": daily[d].get("open_interest"),
            "active_addresses": daily[d].get("active_addresses"),
            "fetched_at": now,
        })
    return rows


def parse_defi_chain_daily():
    """Parse per-chain timeseries sources into defi_chain_daily rows."""
    chain_daily = defaultdict(lambda: defaultdict(dict))

    path = RAW_DIR / "chain_history" / "chain_tvl_history.json"
    if path.exists():
        data = load_json(path)["data"]
        for chain, points in data.items():
            for row in points:
                d = ts_to_date(row["date"])
                chain_daily[d][chain]["tvl"] = row["tvl"]

    path = RAW_DIR / "chain_history" / "chain_dex_volumes_history.json"
    if path.exists():
        data = load_json(path)["data"]
        for chain, points in data.items():
            for ts, vol in points:
                d = ts_to_date(ts)
                chain_daily[d][chain]["dex_volume"] = vol

    path = RAW_DIR / "chain_history" / "chain_fees_history.json"
    if path.exists():
        data = load_json(path)["data"]
        for chain, points in data.items():
            for ts, fees in points:
                d = ts_to_date(ts)
                chain_daily[d][chain]["fees"] = fees

    path = RAW_DIR / "chain_history" / "chain_stablecoin_mcap_history.json"
    if path.exists():
        data = load_json(path)["data"]
        for chain, points in data.items():
            for row in points:
                d = ts_to_date(row["date"])
                chain_daily[d][chain]["stablecoin_mcap"] = row.get("totalCirculatingUSD", {}).get("peggedUSD")

    path = RAW_DIR / "chain_history" / "chain_open_interest_history.json"
    if path.exists():
        data = load_json(path)["data"]
        for chain, points in data.items():
            for ts, oi in points:
                d = ts_to_date(ts)
                chain_daily[d][chain]["open_interest"] = oi

    path = RAW_DIR / "users" / "chain_active_users_history.json"
    if path.exists():
        data = load_json(path)["data"]
        for chain, points in data.items():
            for ts, users in points:
                d = ts_to_date(ts)
                chain_daily[d][chain]["active_addresses"] = users

    now = fetched_at_now()
    cutoff = yesterday()
    rows = []
    for d in sorted(chain_daily.keys()):
        if d > cutoff:
            continue
        for chain in TOP_CHAINS:
            if chain not in chain_daily[d]:
                continue
            rows.append({
                "date": d,
                "chain": chain,
                "tvl": chain_daily[d][chain].get("tvl"),
                "dex_volume": chain_daily[d][chain].get("dex_volume"),
                "fees": chain_daily[d][chain].get("fees"),
                "stablecoin_mcap": chain_daily[d][chain].get("stablecoin_mcap"),
                "open_interest": chain_daily[d][chain].get("open_interest"),
                "active_addresses": chain_daily[d][chain].get("active_addresses"),
                "fetched_at": now,
            })
    return rows


def parse_defi_chain_category():
    """Parse category breakdown sources into defi_chain_category rows."""
    rows = []
    now = fetched_at_now()

    path = RAW_DIR / "fees" / "chain_fees.json"
    if path.exists():
        for chain_data in load_json(path)["data"]:
            chain = chain_data.get("chain")
            if chain not in TOP_CHAINS:
                continue
            for cat in chain_data.get("by_category", []):
                if cat["total24h"] == 0 and cat["total7d"] == 0:
                    continue
                rows.append({
                    "chain": chain,
                    "metric": "fees",
                    "category": cat["category"],
                    "total24h": cat["total24h"],
                    "total7d": cat["total7d"],
                    "protocol_count": cat["protocol_count"],
                    "fetched_at": now,
                })

    path = RAW_DIR / "volumes" / "chain_dex_volumes.json"
    if path.exists():
        for chain_data in load_json(path)["data"]:
            chain = chain_data.get("chain")
            if chain not in TOP_CHAINS:
                continue
            for cat in chain_data.get("by_category", []):
                if cat["total24h"] == 0 and cat["total7d"] == 0:
                    continue
                rows.append({
                    "chain": chain,
                    "metric": "dex_volume",
                    "category": cat["category"],
                    "total24h": cat["total24h"],
                    "total7d": cat["total7d"],
                    "protocol_count": cat["protocol_count"],
                    "fetched_at": now,
                })

    path = RAW_DIR / "tvl" / "chain_tvl_by_category.json"
    if path.exists():
        data = load_json(path)["data"]
        for chain in TOP_CHAINS:
            for cat in data.get(chain, []):
                if cat["tvl"] <= 0:
                    continue
                rows.append({
                    "chain": chain,
                    "metric": "tvl",
                    "category": cat["category"],
                    "total24h": cat["tvl"],
                    "total7d": None,
                    "protocol_count": cat["protocol_count"],
                    "fetched_at": now,
                })

    return rows


# ---------------------------------------------------------------------------
# Ingest functions
# ---------------------------------------------------------------------------

def ingest_daily(client, full=False, dry_run=False):
    """Ingest aggregate daily metrics."""
    rows = parse_defi_daily()
    if not rows:
        print("  no raw data found for defi_daily")
        return

    if not full and not dry_run:
        max_date = get_max_date(client, "defi_daily")
        if max_date:
            before = len(rows)
            rows = [r for r in rows if r["date"] > max_date]
            print(f"  incremental: {before} total, {len(rows)} new (after {max_date})")

    if dry_run:
        print(f"  [dry-run] defi_daily: {len(rows)} rows")
        return

    t0 = time.time()
    total, new, skipped = upsert_batch(client, "defi_daily", rows, "date")
    duration = int((time.time() - t0) * 1000)
    print(f"  defi_daily: {new} upserted, {skipped} unchanged ({duration}ms)")
    log_ingestion(client, "defi_daily", "defi_daily", total, new, skipped, duration)


def ingest_chain_daily(client, full=False, dry_run=False):
    """Ingest per-chain daily metrics."""
    rows = parse_defi_chain_daily()
    if not rows:
        print("  no raw data found for defi_chain_daily")
        return

    if not full and not dry_run:
        max_date = get_max_date(client, "defi_chain_daily")
        if max_date:
            before = len(rows)
            rows = [r for r in rows if r["date"] > max_date]
            print(f"  incremental: {before} total, {len(rows)} new (after {max_date})")

    if dry_run:
        print(f"  [dry-run] defi_chain_daily: {len(rows)} rows")
        return

    t0 = time.time()
    total, new, skipped = upsert_batch(client, "defi_chain_daily", rows, "date,chain")
    duration = int((time.time() - t0) * 1000)
    print(f"  defi_chain_daily: {new} upserted, {skipped} unchanged ({duration}ms)")
    log_ingestion(client, "defi_chain_daily", "defi_chain_daily", total, new, skipped, duration)


def ingest_category(client, dry_run=False):
    """Ingest category breakdown snapshot (always full upsert)."""
    rows = parse_defi_chain_category()
    if not rows:
        print("  no raw data found for defi_chain_category")
        return

    if dry_run:
        print(f"  [dry-run] defi_chain_category: {len(rows)} rows")
        return

    t0 = time.time()
    total, new, skipped = upsert_batch(client, "defi_chain_category", rows, "chain,metric,category")
    duration = int((time.time() - t0) * 1000)
    print(f"  defi_chain_category: {new} upserted, {skipped} unchanged ({duration}ms)")
    log_ingestion(client, "defi_chain_category", "defi_chain_category", total, new, skipped, duration)


def show_status(client):
    """Show row counts and latest dates for each table."""
    for table in ["defi_daily", "defi_chain_daily", "defi_chain_category"]:
        try:
            count_result = client.table(table).select("*", count="exact").limit(0).execute()
            count = count_result.count or 0
        except Exception:
            count = "?"

        if table == "defi_chain_category":
            print(f"  {table}: {count} rows")
        else:
            max_date = get_max_date(client, table)
            print(f"  {table}: {count} rows, latest={max_date or 'empty'}")

    try:
        log = client.table("ingestion_log").select("*").order("ingested_at", desc=True).limit(5).execute()
        if log.data:
            print(f"\n  recent ingestions:")
            for entry in log.data:
                print(f"    {entry['ingested_at'][:19]} | {entry['source']} → {entry['target_table']}: "
                      f"{entry['records_new']} new, {entry['records_skipped']} skipped ({entry['duration_ms']}ms)")
    except Exception:
        pass


def run(client=None, tables=None, full=False, dry_run=False):
    """Run ingestion. Called by run.py orchestrator or standalone."""
    if client is None and not dry_run:
        client = get_client()
    targets = tables or ["daily", "chain", "category"]
    print(f"{'[DRY RUN] ' if dry_run else ''}ingesting: {', '.join(targets)}\n")
    for target in targets:
        print(f"[{target}]")
        if target == "daily":
            ingest_daily(client, full=full, dry_run=dry_run)
        elif target == "chain":
            ingest_chain_daily(client, full=full, dry_run=dry_run)
        elif target == "category":
            ingest_category(client, dry_run=dry_run)
        print()


def main():
    parser = argparse.ArgumentParser(description="Ingest DefiLlama data into Supabase")
    parser.add_argument("--table", choices=["daily", "chain", "category"],
                        help="Ingest specific table")
    parser.add_argument("--full", action="store_true",
                        help="Force full refresh (ignore incremental max_date)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview without writing to Supabase")
    parser.add_argument("--status", action="store_true",
                        help="Show row counts and latest dates")
    args = parser.parse_args()

    if args.status:
        client = get_client()
        show_status(client)
        return

    run(
        tables=[args.table] if args.table else None,
        full=args.full,
        dry_run=args.dry_run,
    )
    print("done.")


if __name__ == "__main__":
    main()
