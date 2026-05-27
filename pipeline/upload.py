"""
Upload defi-overview CSVs to Dune as datasets.

Creates tables with explicit schema, then inserts CSV data.
Requires DUNE_API_KEY env var.

Usage:
    python upload.py                  # clear + insert all tables (default)
    python upload.py --table daily    # just aggregate table
    python upload.py --table chain    # just chain table
    python upload.py --no-clear       # append without clearing (use with caution)
    python upload.py --dry-run        # show what would happen
"""

import argparse
import json
import os
import sys
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import HTTPError

PROJECT_DIR = Path(__file__).resolve().parent.parent
CSV_DIR = PROJECT_DIR / "data" / "csv"
API_BASE = "https://api.dune.com/api/v1"

TABLES = {
    "daily": {
        "table_name": "defi_overview_daily",
        "description": "DeFi overview — aggregate daily timeseries (TVL, volume, fees, stablecoins, OI)",
        "csv_file": "defi_overview_daily.csv",
        "schema": [
            {"name": "date", "type": "timestamp"},
            {"name": "tvl", "type": "double", "nullable": True},
            {"name": "dex_volume", "type": "double", "nullable": True},
            {"name": "fees", "type": "double", "nullable": True},
            {"name": "stablecoin_mcap", "type": "double", "nullable": True},
            {"name": "options_volume", "type": "double", "nullable": True},
            {"name": "open_interest", "type": "double", "nullable": True},
            {"name": "active_addresses", "type": "double", "nullable": True},
        ],
    },
    "category": {
        "table_name": "defi_overview_chain_category",
        "description": "DeFi overview — fee and volume breakdown by category per chain (latest snapshot)",
        "csv_file": "defi_overview_chain_category.csv",
        "schema": [
            {"name": "chain", "type": "varchar"},
            {"name": "metric", "type": "varchar"},
            {"name": "category", "type": "varchar"},
            {"name": "total24h", "type": "double", "nullable": True},
            {"name": "total7d", "type": "double", "nullable": True},
            {"name": "protocol_count", "type": "integer", "nullable": True},
        ],
    },
    "chain": {
        "table_name": "defi_overview_chain_daily",
        "description": "DeFi overview — per-chain daily timeseries (TVL, volume, fees, stablecoins, OI)",
        "csv_file": "defi_overview_chain_daily.csv",
        "schema": [
            {"name": "date", "type": "timestamp"},
            {"name": "chain", "type": "varchar"},
            {"name": "tvl", "type": "double", "nullable": True},
            {"name": "dex_volume", "type": "double", "nullable": True},
            {"name": "fees", "type": "double", "nullable": True},
            {"name": "stablecoin_mcap", "type": "double", "nullable": True},
            {"name": "open_interest", "type": "double", "nullable": True},
            {"name": "active_addresses", "type": "double", "nullable": True},
        ],
    },
}


def load_env():
    env_path = PROJECT_DIR / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def api_key():
    load_env()
    key = os.environ.get("DUNE_API_KEY")
    if not key:
        print("error: DUNE_API_KEY not found in env or .env file")
        sys.exit(1)
    return key


def dune_request(method, path, data=None, content_type="application/json"):
    url = f"{API_BASE}{path}"
    if data is not None and content_type == "application/json":
        body = json.dumps(data).encode()
    elif data is not None:
        body = data if isinstance(data, bytes) else data.encode()
    else:
        body = None

    req = Request(url, data=body, method=method, headers={
        "X-DUNE-API-KEY": api_key(),
        "Content-Type": content_type,
    })
    try:
        with urlopen(req, timeout=120) as resp:
            return json.loads(resp.read())
    except HTTPError as e:
        error_body = e.read().decode() if e.fp else ""
        print(f"  HTTP {e.code}: {url}")
        print(f"  {error_body[:500]}")
        return None


def create_table(config):
    print(f"creating table {config['table_name']}...")
    result = dune_request("POST", "/table/create", {
        "table_name": config["table_name"],
        "description": config["description"],
        "schema": config["schema"],
        "is_private": False,
    })
    if result:
        print(f"  {result.get('full_name', 'ok')} (existed={result.get('already_existed', False)})")
    return result


def clear_table(namespace, table_name):
    print(f"clearing {namespace}.{table_name}...")
    result = dune_request("POST", f"/table/{namespace}/{table_name}/clear")
    if result:
        print(f"  cleared")
    return result


def insert_csv(namespace, table_name, csv_path):
    print(f"inserting {csv_path.name} into {namespace}.{table_name}...")
    csv_data = csv_path.read_bytes()
    size_mb = len(csv_data) / (1024 * 1024)
    print(f"  size: {size_mb:.1f} MB")
    if size_mb > 200:
        print("  error: file exceeds 200 MB limit")
        return None
    result = dune_request("POST", f"/table/{namespace}/{table_name}/insert", csv_data, "text/csv")
    if result:
        print(f"  rows_written={result.get('rows_written')}, bytes={result.get('bytes_written')}")
    return result


def _resolve_config(config, test=False):
    if not test:
        return config
    return {**config, "table_name": config["table_name"] + "_test"}


def run(tables=None, clear=True, dry_run=False, test=False):
    """Run upload. Called by run.py orchestrator or standalone.

    Always clears before insert by default — transform.py exports the full
    dataset each time, so appending would create duplicates.
    """
    targets = tables or ["daily", "chain", "category"]

    if dry_run:
        for t in targets:
            config = _resolve_config(TABLES[t], test)
            csv_path = CSV_DIR / config["csv_file"]
            size = csv_path.stat().st_size / (1024 * 1024) if csv_path.exists() else 0
            print(f"[dry-run] {config['table_name']}: {csv_path.name} ({size:.1f} MB)")
            print(f"  columns: {[c['name'] for c in config['schema']]}")
        return

    for t in targets:
        config = _resolve_config(TABLES[t], test)
        csv_path = CSV_DIR / config["csv_file"]

        if not csv_path.exists():
            print(f"error: {csv_path} not found — run transform.py first")
            continue

        result = create_table(config)
        namespace = result.get("namespace", "ghrjeondata") if result else "ghrjeondata"

        if clear:
            clear_table(namespace, config["table_name"])

        insert_csv(namespace, config["table_name"], csv_path)
        print()


def main():
    parser = argparse.ArgumentParser(description="Upload defi-overview CSVs to Dune")
    parser.add_argument("--table", choices=list(TABLES.keys()), help="Upload specific table")
    parser.add_argument("--no-clear", action="store_true", help="Skip clearing tables before insert (append mode)")
    parser.add_argument("--recreate", action="store_true", help="Delete and recreate tables (schema change)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would happen")
    parser.add_argument("--test", action="store_true", help="Upload to _test tables instead of production")
    args = parser.parse_args()

    if args.recreate:
        targets = [args.table] if args.table else ["daily", "chain", "category"]
        for t in targets:
            config = _resolve_config(TABLES[t], args.test)
            result = create_table(config)
            namespace = result.get("namespace", "ghrjeondata") if result else "ghrjeondata"
            print(f"deleting table {namespace}.{config['table_name']}...")
            dune_request("DELETE", f"/table/{namespace}/{config['table_name']}")
            create_table(config)

    run(
        tables=[args.table] if args.table else None,
        clear=not args.no_clear,
        dry_run=args.dry_run,
        test=args.test,
    )
    print("done.")


if __name__ == "__main__":
    main()
