# Data Sourcer Fetch Patterns

Conventions for `data-sourcer/{provider}/fetch.py`.

## Structure

```python
SCRIPT_DIR = Path(__file__).parent
OUTPUT_DIR = SCRIPT_DIR / "output"
BASE_URL = "https://api.example.com"

def api_get(url):
    """Fetch JSON with basic error handling."""
    req = Request(url, headers={"User-Agent": "data-sourcer/1.0"})
    try:
        with urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except HTTPError as e:
        print(f"  HTTP {e.code}: {url}")
        return None

def write_output(name, data, description, group=""):
    """Save to output/{group}/{name}.json with metadata wrapper."""
    group_dir = OUTPUT_DIR / group if group else OUTPUT_DIR
    group_dir.mkdir(parents=True, exist_ok=True)
    output = {
        "data": data,
        "metadata": {
            "source": name,
            "description": description,
            "fetched_at": datetime.now().isoformat(),
        }
    }
    path = group_dir / f"{name}.json"
    path.write_text(json.dumps(output, indent=2))
```

## Source Registry

Define sources as a dict of groups → list of `(name, description, fetch_fn)`:

```python
SOURCES = {
    "tvl": [
        ("tvl_historical", "Historical TVL", fetch_tvl_historical),
    ],
    "volumes": [
        ("dex_volumes", "DEX volumes", fetch_dex_volumes),
    ],
    "chain_history": [
        ("chain_tvl_history", "Per-chain TVL", fetch_chain_tvl_history),
    ],
}
```

CLI: `--source name`, `--group group_name`, `--list`, or no args for all.

## Per-Entity Loops (chains, tokens, etc.)

```python
TOP_CHAINS = ["Ethereum", "Solana", "BSC", "Base", "Arbitrum", ...]

# Some endpoints use different names than display names
TVL_CHAIN_NAMES = {"Optimism": "OP Mainnet"}

def fetch_chain_tvl_history():
    results = {}
    for chain in TOP_CHAINS:
        api_name = TVL_CHAIN_NAMES.get(chain, chain)
        data = api_get(f"{BASE_URL}/v2/historicalChainTvl/{quote(api_name)}")
        if data:
            results[chain] = data
        time.sleep(0.3)  # rate limit courtesy
    return results
```

Key points:
- Sleep 0.3s between per-entity requests
- **Always `quote()` chain names in ALL endpoint URLs** — not just ones you know have spaces. New chains with spaces (e.g., "Hyperliquid L1") will crash without it. Apply `quote()` universally, not selectively
- Maintain a name mapping dict when API names differ from display names
- Store results keyed by display name, not API name
- Handle 404/500 gracefully — some entities lack certain metrics (e.g., Bitcoin has no stablecoins, many chains have no open interest)
- **Expected gaps by chain**: not every chain supports every metric. Bitcoin: no stablecoins (404), no OI (500). Smaller chains often lack OI. This is normal — leave as null

## API Exploration Methodology

When adding a new provider:

1. Test each endpoint manually to confirm it's free vs paid (402 = paid/pro)
2. Check per-entity variants (e.g., `/chain/{name}` may 404 for some chains)
3. Document which endpoints returned errors and why
4. Note response shape differences between aggregate and per-entity endpoints
