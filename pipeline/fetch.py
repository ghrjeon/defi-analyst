"""
Fetch DeFi data from DefiLlama's free API.

Pulls stablecoin metrics, TVL, DEX volumes, fees, and active users.
No API key needed — all endpoints are free and public.
Fetches up to 8 sources concurrently via aiohttp.

Usage:
    python fetch.py                        # fetch all sources
    python fetch.py --source stablecoins   # fetch one source
    python fetch.py --group stablecoins    # fetch one group
    python fetch.py --list                 # see what's available
"""

import argparse
import asyncio
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

import aiohttp

PROJECT_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_DIR / "data" / "raw"

BASE_URL = "https://api.llama.fi"
STABLECOINS_URL = "https://stablecoins.llama.fi"


MAX_CONCURRENT = 8

TOP_CHAINS = [
    "Ethereum", "Solana", "BSC", "Bitcoin", "Tron", "Base",
    "Arbitrum", "Hyperliquid L1", "Polygon",
    "MegaETH", "Avalanche", "Sui", "Monad", "Optimism",
    "Cronos", "Ink", "Aptos", "Mantle", "Starknet",
    "Stellar", "Movement", "Flare", "Cardano", "Near", "Rootstock",
]

TVL_CHAIN_NAMES = {"Optimism": "OP Mainnet"}

INFRA_CATEGORIES = {"Chain", "Block Builders", "MEV"}


async def api_get(session, sem, url):
    async with sem:
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status != 200:
                    print(f"  HTTP {resp.status}: {url}")
                    return None
                return await resp.json(content_type=None)
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            print(f"  error: {e}")
            return None


def write_output(name, data, description, group=""):
    group_dir = OUTPUT_DIR / group if group else OUTPUT_DIR
    group_dir.mkdir(parents=True, exist_ok=True)
    if isinstance(data, dict):
        record_count = len(data.get("data", data))
    elif isinstance(data, list):
        record_count = len(data)
    else:
        record_count = 0
    payload = {
        "source": name,
        "group": group,
        "provider": "defillama",
        "description": description,
        "fetched_at": datetime.utcnow().isoformat() + "Z",
        "record_count": record_count,
        "data": data,
    }
    path = group_dir / f"{name}.json"
    with open(path, "w") as f:
        json.dump(payload, f, indent=2, default=str)
    print(f"  wrote {path} ({record_count} records)")


# ---------------------------------------------------------------------------
# Single-request sources
# ---------------------------------------------------------------------------

async def fetch_stablecoin_mcap_history(session, sem, name, description, group):
    data = await api_get(session, sem, f"{STABLECOINS_URL}/stablecoincharts/all?stablecoin=1")
    if data:
        write_output(name, data, description, group)


async def fetch_historical_tvl(session, sem, name, description, group):
    data = await api_get(session, sem, f"{BASE_URL}/v2/historicalChainTvl")
    if data:
        write_output(name, data, description, group)


async def fetch_dex_volumes(session, sem, name, description, group):
    data = await api_get(session, sem, f"{BASE_URL}/overview/dexs")
    if data:
        write_output(name, data, description, group)


async def fetch_fees_overview(session, sem, name, description, group):
    data = await api_get(session, sem, f"{BASE_URL}/overview/fees")
    if data:
        write_output(name, data, description, group)


async def fetch_options_volumes(session, sem, name, description, group):
    data = await api_get(session, sem, f"{BASE_URL}/overview/options")
    if data:
        write_output(name, data, description, group)


async def fetch_open_interest(session, sem, name, description, group):
    data = await api_get(session, sem, f"{BASE_URL}/overview/open-interest")
    if data:
        write_output(name, data, description, group)


async def fetch_active_users(session, sem, name, description, group):
    data = await api_get(session, sem, f"{BASE_URL}/overview/active-users")
    if data:
        write_output(name, data, description, group)


# ---------------------------------------------------------------------------
# Per-chain sources (25 chains concurrently via semaphore)
# ---------------------------------------------------------------------------

def _aggregate_by_category(protocols, exclude_infra=False):
    cats = {}
    for p in protocols:
        cat = p.get("category") or "Unknown"
        if exclude_infra and cat in INFRA_CATEGORIES:
            continue
        if cat not in cats:
            cats[cat] = {"category": cat, "total24h": 0, "total7d": 0, "protocol_count": 0}
        cats[cat]["total24h"] += p.get("total24h") or 0
        cats[cat]["total7d"] += p.get("total7d") or 0
        cats[cat]["protocol_count"] += 1
    return sorted(cats.values(), key=lambda x: x["total24h"], reverse=True)


async def fetch_chain_dex_volumes(session, sem, name, description, group):
    async def fetch_one(chain):
        data = await api_get(session, sem, f"{BASE_URL}/overview/dexs/{quote(chain)}?excludeTotalDataChart=true&excludeTotalDataChartBreakdown=true")
        if not data:
            return None
        protocols = data.get("protocols", [])
        top_protos = []
        for p in sorted(protocols, key=lambda x: x.get("total24h") or 0, reverse=True)[:5]:
            top_protos.append({
                "name": p.get("name"), "category": p.get("category"),
                "total24h": p.get("total24h"), "total7d": p.get("total7d"),
            })
        return {
            "chain": chain,
            "total24h": data.get("total24h"),
            "total48hto24h": data.get("total48hto24h"),
            "total7d": data.get("total7d"),
            "total30d": data.get("total30d"),
            "change_1d": data.get("change_1d"),
            "change_7d": data.get("change_7d"),
            "top_protocols": top_protos,
            "by_category": _aggregate_by_category(protocols),
        }

    results = [r for r in await asyncio.gather(*[fetch_one(c) for c in TOP_CHAINS]) if r]
    write_output(name, results, description, group)


async def fetch_chain_fees(session, sem, name, description, group):
    async def fetch_one(chain):
        data = await api_get(session, sem, f"{BASE_URL}/overview/fees/{quote(chain)}?excludeTotalDataChart=true&excludeTotalDataChartBreakdown=true")
        if not data:
            return None
        protocols = data.get("protocols", [])
        top_protos = []
        for p in sorted(protocols, key=lambda x: x.get("total24h") or 0, reverse=True)[:5]:
            top_protos.append({
                "name": p.get("name"), "category": p.get("category"),
                "total24h": p.get("total24h"), "total7d": p.get("total7d"),
                "dailyRevenue": p.get("dailyRevenue"),
            })
        return {
            "chain": chain,
            "total24h": data.get("total24h"),
            "total48hto24h": data.get("total48hto24h"),
            "total7d": data.get("total7d"),
            "total30d": data.get("total30d"),
            "change_1d": data.get("change_1d"),
            "change_7d": data.get("change_7d"),
            "top_protocols": top_protos,
            "by_category": _aggregate_by_category(protocols),
        }

    results = [r for r in await asyncio.gather(*[fetch_one(c) for c in TOP_CHAINS]) if r]
    write_output(name, results, description, group)


async def fetch_chain_tvl_by_category(session, sem, name, description, group):
    data = await api_get(session, sem, f"{BASE_URL}/protocols")
    if not data:
        return
    results = {}
    for chain in TOP_CHAINS:
        cats = {}
        for p in data:
            cat = p.get("category") or "Unknown"
            chain_tvls = p.get("chainTvls", {})
            tvl = chain_tvls.get(chain)
            if tvl is None or tvl <= 0:
                continue
            if cat not in cats:
                cats[cat] = {"category": cat, "tvl": 0, "protocol_count": 0}
            cats[cat]["tvl"] += tvl
            cats[cat]["protocol_count"] += 1
        results[chain] = sorted(cats.values(), key=lambda x: x["tvl"], reverse=True)
    write_output(name, results, description, group)


async def fetch_chain_tvl_history(session, sem, name, description, group):
    async def fetch_one(chain):
        api_chain = TVL_CHAIN_NAMES.get(chain, chain)
        data = await api_get(session, sem, f"{BASE_URL}/v2/historicalChainTvl/{quote(api_chain)}")
        return chain, data

    pairs = await asyncio.gather(*[fetch_one(c) for c in TOP_CHAINS])
    results = {chain: data for chain, data in pairs if data}
    write_output(name, results, description, group)


async def fetch_chain_dex_volumes_history(session, sem, name, description, group):
    async def fetch_one(chain):
        data = await api_get(session, sem, f"{BASE_URL}/overview/dexs/{quote(chain)}?excludeTotalDataChartBreakdown=true")
        return chain, data.get("totalDataChart", []) if data else None

    pairs = await asyncio.gather(*[fetch_one(c) for c in TOP_CHAINS])
    results = {chain: chart for chain, chart in pairs if chart}
    write_output(name, results, description, group)


async def fetch_chain_fees_history(session, sem, name, description, group):
    async def fetch_one(chain):
        data = await api_get(session, sem, f"{BASE_URL}/overview/fees/{quote(chain)}?excludeTotalDataChartBreakdown=true")
        return chain, data.get("totalDataChart", []) if data else None

    pairs = await asyncio.gather(*[fetch_one(c) for c in TOP_CHAINS])
    results = {chain: chart for chain, chart in pairs if chart}
    write_output(name, results, description, group)


async def fetch_chain_stablecoin_mcap_history(session, sem, name, description, group):
    async def fetch_one(chain):
        data = await api_get(session, sem, f"{STABLECOINS_URL}/stablecoincharts/{quote(chain)}")
        return chain, data

    pairs = await asyncio.gather(*[fetch_one(c) for c in TOP_CHAINS])
    results = {chain: data for chain, data in pairs if data}
    write_output(name, results, description, group)


async def fetch_chain_open_interest_history(session, sem, name, description, group):
    async def fetch_one(chain):
        data = await api_get(session, sem, f"{BASE_URL}/overview/open-interest/{quote(chain)}")
        return chain, data.get("totalDataChart", []) if data else None

    pairs = await asyncio.gather(*[fetch_one(c) for c in TOP_CHAINS])
    results = {chain: chart for chain, chart in pairs if chart}
    write_output(name, results, description, group)


async def fetch_chain_active_users_history(session, sem, name, description, group):
    async def fetch_one(chain):
        data = await api_get(session, sem, f"{BASE_URL}/overview/active-users/{quote(chain)}")
        return chain, data.get("totalDataChart", []) if data else None

    pairs = await asyncio.gather(*[fetch_one(c) for c in TOP_CHAINS])
    results = {chain: chart for chain, chart in pairs if chart}
    write_output(name, results, description, group)


# ---------------------------------------------------------------------------
# Source registry
# ---------------------------------------------------------------------------

SOURCES = {
    "stablecoin_mcap_history": {
        "fn": fetch_stablecoin_mcap_history, "group": "stablecoins",
        "description": "Historical total stablecoin market cap",
    },
    "tvl_historical": {
        "fn": fetch_historical_tvl, "group": "tvl",
        "description": "Historical total DeFi TVL across all chains",
    },
    "dex_volumes": {
        "fn": fetch_dex_volumes, "group": "volumes",
        "description": "DEX volume overview — all protocols",
    },
    "fees_overview": {
        "fn": fetch_fees_overview, "group": "fees",
        "description": "Protocol fees and revenue overview",
    },
    "chain_dex_volumes": {
        "fn": fetch_chain_dex_volumes, "group": "volumes",
        "description": "DEX volumes per chain (top 25 chains)",
    },
    "chain_fees": {
        "fn": fetch_chain_fees, "group": "fees",
        "description": "Protocol fees per chain (top 25 chains)",
    },
    "chain_tvl_by_category": {
        "fn": fetch_chain_tvl_by_category, "group": "tvl",
        "description": "TVL breakdown by protocol category per chain",
    },
    "chain_tvl_history": {
        "fn": fetch_chain_tvl_history, "group": "chain_history",
        "description": "Historical TVL per chain (top 25 chains)",
    },
    "chain_dex_volumes_history": {
        "fn": fetch_chain_dex_volumes_history, "group": "chain_history",
        "description": "Historical DEX volumes per chain (top 25 chains)",
    },
    "chain_fees_history": {
        "fn": fetch_chain_fees_history, "group": "chain_history",
        "description": "Historical fees per chain (top 25 chains)",
    },
    "chain_stablecoin_mcap_history": {
        "fn": fetch_chain_stablecoin_mcap_history, "group": "chain_history",
        "description": "Historical stablecoin mcap per chain (top 25 chains)",
    },
    "chain_open_interest_history": {
        "fn": fetch_chain_open_interest_history, "group": "chain_history",
        "description": "Historical open interest per chain (top 25 chains)",
    },
    "options_volumes": {
        "fn": fetch_options_volumes, "group": "volumes",
        "description": "Options DEX volume overview — aggregate",
    },
    "open_interest": {
        "fn": fetch_open_interest, "group": "volumes",
        "description": "Open interest overview — aggregate",
    },

    # --- Users ---
    "active_users": {
        "fn": fetch_active_users, "group": "users",
        "description": "Active DeFi users overview — aggregate timeseries",
    },
    "chain_active_users_history": {
        "fn": fetch_chain_active_users_history, "group": "users",
        "description": "Historical active DeFi users per chain (top 25 chains)",
    },
}

GROUPS = sorted(set(s["group"] for s in SOURCES.values()))


async def run(source_names=None):
    """Fetch sources concurrently. Pass None for all."""
    if source_names is None:
        targets = SOURCES
    else:
        targets = {k: SOURCES[k] for k in source_names if k in SOURCES}

    sem = asyncio.Semaphore(MAX_CONCURRENT)
    headers = {"User-Agent": "defi-analyst/1.0"}

    async with aiohttp.ClientSession(headers=headers) as session:
        tasks = []
        for name, config in targets.items():
            print(f"fetching {name}...")
            tasks.append(config["fn"](session, sem, name, config["description"], config["group"]))
        await asyncio.gather(*tasks)


def main():
    parser = argparse.ArgumentParser(description="Fetch DeFi data from DefiLlama")
    parser.add_argument("--source", help="Fetch a single source by name")
    parser.add_argument("--group", help=f"Fetch all sources in a group: {', '.join(GROUPS)}")
    parser.add_argument("--list", action="store_true", help="List available sources")
    args = parser.parse_args()

    if args.list:
        current_group = None
        for name, config in SOURCES.items():
            if config["group"] != current_group:
                current_group = config["group"]
                print(f"\n  [{current_group}]")
            print(f"    {name:30s} — {config['description']}")
        print(f"\n  groups: {', '.join(GROUPS)}")
        return

    if args.source:
        if args.source not in SOURCES:
            print(f"Unknown source: {args.source}")
            print(f"Available: {', '.join(SOURCES.keys())}")
            sys.exit(1)
        t0 = time.time()
        asyncio.run(run([args.source]))
        print(f"\ndone ({time.time() - t0:.1f}s).")
    elif args.group:
        if args.group not in GROUPS:
            print(f"Unknown group: {args.group}")
            print(f"Available: {', '.join(GROUPS)}")
            sys.exit(1)
        group_sources = [k for k, v in SOURCES.items() if v["group"] == args.group]
        print(f"fetching group '{args.group}' ({len(group_sources)} sources)\n")
        t0 = time.time()
        asyncio.run(run(group_sources))
        print(f"\ndone ({time.time() - t0:.1f}s).")
    else:
        print(f"fetching all sources ({len(SOURCES)} total)\n")
        t0 = time.time()
        asyncio.run(run())
        print(f"\ndone ({time.time() - t0:.1f}s).")


if __name__ == "__main__":
    main()
