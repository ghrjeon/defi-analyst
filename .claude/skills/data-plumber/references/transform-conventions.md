# Transform Conventions

Rules for `{dashboard}/transform.py` — converting raw JSON to Dune-ready CSVs.

## Core Rule

**Raw data only.** No computed metrics in the pipeline. Velocity, fee/TVL, ratios — all go in DuneSQL materialized views, not in the CSV.

Why: keeps the pipeline simple and the matview as single source of truth for derived metrics. Changing a formula means updating one Dune query, not re-running the whole pipeline.

## Pattern

```python
from collections import defaultdict

def build_aggregate():
    """One row per day."""
    daily = defaultdict(dict)

    # Each source populates its column(s)
    for row in load_json(path / "tvl_historical.json"):
        d = ts_to_date(row["date"])
        daily[d]["tvl"] = row["tvl"]

    for ts, vol in data.get("totalDataChart", []):
        d = ts_to_date(ts)
        daily[d]["dex_volume"] = vol

    # Write CSV
    columns = ["date", "tvl", "dex_volume", "fees", ...]
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for d in sorted(daily.keys()):
            row = {"date": d, **daily[d]}
            writer.writerow({c: row.get(c, "") for c in columns})


def build_chain():
    """One row per (date, chain)."""
    chain_daily = defaultdict(lambda: defaultdict(dict))

    for chain, rows in data.items():
        for row in rows:
            d = ts_to_date(row["date"])
            chain_daily[d][chain]["tvl"] = row["tvl"]

    # Write only TOP_CHAINS, skip unknown chains
    for d in sorted(chain_daily.keys()):
        for chain in TOP_CHAINS:
            if chain not in chain_daily[d]:
                continue
            ...
```

## Conventions

- **defaultdict for sparse timeseries** — not all sources cover the same dates
- **Timestamps**: `YYYY-MM-DD HH:MM:SS` UTC (Dune `timestamp` type)
- **Missing values**: empty string in CSV → NULL in Dune
- **Sort by date** before writing
- **Filter to known entities** (TOP_CHAINS list) — don't include every chain the API returns
- **load_json()** reads from `data-sourcer/{provider}/output/` using the metadata wrapper (`data["data"]`)
- **Output to** `{dashboard}/output/{table_name}.csv`

## Timestamp Helper

```python
from datetime import datetime, timezone

def ts_to_date(ts):
    return datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
```
