# defi-analyst

Data pipeline for the [DeFi Overview — Cross-Chain Analysis](https://dune.com/ghrjeondata/defi-overview-cross-chain-analysis) Dune dashboard.

Fetches DeFi metrics from DefiLlama, ingests into Supabase with incremental dedup, exports Dune-ready CSVs, and uploads to Dune datasets. Scheduled daily via GitHub Actions.

## Pipeline

```
pipeline/fetch.py → DefiLlama API → data/raw/ (JSON, async)
    ↓
pipeline/ingest.py → parse + flatten → Supabase (structured tables, incremental)
    ↓
pipeline/transform.py → SELECT from Supabase → data/csv/ (CSV)
    ↓
pipeline/upload.py → data/csv/ → Dune uploaded tables
    ↓
Dune matviews → Dashboard queries → Visualizations
```

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# Fill in SUPABASE_URL, SUPABASE_SERVICE_KEY, and DUNE_API_KEY
```

Run `schema.sql` in the Supabase SQL Editor to create the tables.

For GitHub Actions: add `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, and `DUNE_API_KEY` as repository secrets.

## Usage

```bash
# Full pipeline (orchestrator)
python run.py                              # fetch → ingest → transform → upload
python run.py --steps fetch,ingest         # specific steps only
python run.py --skip upload                # all except upload
python run.py --full                       # force full ingest refresh
python run.py --dry-run                    # preview without side effects

# Individual modules
python -m pipeline.fetch --list            # see all 16 sources
python -m pipeline.fetch --source tvl_historical
python -m pipeline.fetch --group users
python -m pipeline.ingest --status         # show row counts and latest dates
python -m pipeline.ingest --dry-run
python -m pipeline.ingest --full           # force re-ingest all historical data
python -m pipeline.upload --dry-run
python -m pipeline.upload --table category --clear
```

## How it works

### Fetch (async)

Pulls 16 sources from DefiLlama's free API using `aiohttp` with a semaphore (`MAX_CONCURRENT=8`). Single-request sources run in parallel. Per-chain sources (7 sources × 25 chains = 175 requests) use `asyncio.gather` with bounded concurrency instead of sequential loops.

### Ingest (incremental)

Each fetch source maps to a specific Supabase table and column:

| Source | → Table | Column |
|--------|---------|--------|
| `tvl_historical` | `defi_daily` | `tvl` |
| `dex_volumes` | `defi_daily` | `dex_volume` |
| `fees_overview` | `defi_daily` | `fees` |
| `stablecoin_mcap_history` | `defi_daily` | `stablecoin_mcap` |
| `options_volumes` | `defi_daily` | `options_volume` |
| `open_interest` | `defi_daily` | `open_interest` |
| `active_users` | `defi_daily` | `active_addresses` |
| `chain_tvl_history` | `defi_chain_daily` | `tvl` |
| `chain_dex_volumes_history` | `defi_chain_daily` | `dex_volume` |
| `chain_fees_history` | `defi_chain_daily` | `fees` |
| `chain_stablecoin_mcap_history` | `defi_chain_daily` | `stablecoin_mcap` |
| `chain_open_interest_history` | `defi_chain_daily` | `open_interest` |
| `chain_active_users_history` | `defi_chain_daily` | `active_addresses` |
| `chain_fees` | `defi_chain_category` | fee breakdown by category |
| `chain_dex_volumes` | `defi_chain_category` | volume breakdown by category |
| `chain_tvl_by_category` | `defi_chain_category` | TVL breakdown by category |

Parses raw JSON from `data/raw/`, flattens into structured rows, and upserts into Supabase:

1. Queries `MAX(date)` from the target table
2. Filters parsed rows to only those with `date > max_date`
3. Batch-upserts new rows (500 per batch, with retry on transient errors)
4. Logs each run to `ingestion_log` (source, counts, duration)

First run ingests all historical data. Subsequent runs append only new dates. Use `--full` to bypass the watermark and re-upsert everything (needed if DefiLlama corrects historical data).

Category table (`defi_chain_category`) always does a full upsert — it's a snapshot, not timeseries.

### Transform

Reads from Supabase tables, exports three Dune-ready CSVs to `data/csv/`. Paginated fetches handle tables with >1000 rows. Appends ` 00:00:00` to dates for Dune's timestamp format.

### Upload

Pushes CSVs to Dune via their API. Creates tables with explicit schema definitions (never auto-infer). Supports `--clear` for full refresh and `--recreate` for schema changes.

## Supabase tables

| Table | PK | Rows | Description |
|-------|-----|------|-------------|
| `defi_daily` | (date) | ~4,000 | Aggregate daily: TVL, volume, fees, stablecoins, options, OI, active addresses |
| `defi_chain_daily` | (date, chain) | ~39,000 | Per-chain daily metrics for 25 chains |
| `defi_chain_category` | (chain, metric, category) | ~1,200 | Category breakdown snapshot (fees, volume, TVL) |
| `ingestion_log` | id | audit | Tracks every ingest run with timing and row counts |

## Dune tables

| Table | Type | Description |
|-------|------|-------------|
| `dune.ghrjeondata.defi_overview_daily` | uploaded | Aggregate daily timeseries |
| `dune.ghrjeondata.defi_overview_chain_daily` | uploaded | Per-chain daily timeseries |
| `dune.ghrjeondata.defi_overview_chain_category` | uploaded | Category breakdown snapshot |
| `result_defi_overview_daily_metrics` | matview | Aggregate + computed ratios |
| `result_defi_overview_chain_daily_metrics` | matview | Per-chain + computed ratios |

Materialized views compute all derived metrics from the raw uploaded tables. Dashboard queries read from matviews only. Matviews must be manually rematerialized in Dune UI after re-uploading data.

## Derived metrics

Computed in Dune matviews — raw pipeline never computes ratios:

| Metric | Formula | What it measures |
|--------|---------|-----------------|
| velocity | dex_volume / tvl | Capital turnover |
| fee_per_tvl | fees / tvl | Revenue per dollar locked |
| fee_efficiency | fees / tvl_oi_adj | Fee generation per adjusted TVL |
| volume_efficiency | fees / dex_volume | Fee extraction per dollar traded |
| oi_to_tvl | open_interest / tvl | Leverage proxy |
| stable_to_tvl | stablecoin_mcap / tvl | Stablecoin penetration |
| volume_to_stable | dex_volume / stablecoin_mcap | Trading intensity |
| fees_per_address | fees / active_addresses | Revenue per user |
| volume_per_address | dex_volume / active_addresses | Volume per user |

## Data sources

All data sourced from [DefiLlama](https://defillama.com/)'s free API (no key needed) across two domains:

| Domain | Base URL | Covers |
|--------|----------|--------|
| Core | https://api.llama.fi | TVL, volumes, fees, OI, options, active users |
| Stablecoins | https://stablecoins.llama.fi | Stablecoin market cap (aggregate + per-chain) |

On-chain metrics are powered by community-maintained protocol adapters:
[TVL adapters](https://github.com/DefiLlama/DefiLlama-Adapters) · [volume/fees/derivatives adapters](https://github.com/DefiLlama/dimension-adapters) · [API docs](https://api-docs.defillama.com/llms-free.txt)

16 sources across 6 groups:

| Group | Sources | What it covers |
|-------|---------|----------------|
| stablecoins | 1 | Historical total stablecoin market cap |
| tvl | 2 | Historical DeFi TVL, TVL by category per chain |
| volumes | 4 | DEX volume, options volume, open interest, per-chain DEX volume categories |
| fees | 2 | Protocol fees/revenue (aggregate + per-chain categories) |
| chain_history | 5 | Per-chain timeseries: TVL, volume, fees, stablecoins, OI |
| users | 2 | Active DeFi users (aggregate + per-chain) |

## Project structure

```
run.py                        # Pipeline orchestrator
pipeline/                     # Core pipeline modules
  __init__.py
  fetch.py                    #   DefiLlama API → data/raw/ (async, 8 concurrent)
  ingest.py                   #   data/raw/ → Supabase (incremental)
  db.py                       #   Supabase client + helpers
  transform.py                #   Supabase → data/csv/
  upload.py                   #   data/csv/ → Dune API
schema.sql                    # Supabase table definitions
requirements.txt              # aiohttp, supabase, python-dotenv
.env.example                  # Template for credentials
.github/workflows/
  pipeline.yml                # Scheduled daily pipeline (6am UTC)
queries/                      # 16 Dune SQL files (reference copies)
references/                   # Dashboard metadata
  queries.yml                 #   Query IDs, columns, viz IDs
  tables.yml                  #   Uploaded table + matview schemas
  dashboard.yml               #   Dashboard layout, widget positions
  styles.yml                  #   Color palette for charts
.claude/skills/               # Claude Code skills (see below)
data/                         # Runtime output (gitignored)
  raw/                        #   Fetched JSON from DefiLlama
  csv/                        #   Exported CSVs for Dune upload
```

## Claude Code skills

Three skills in `.claude/skills/` give Claude Code project-aware capabilities when working in this repo:

### `dune` — Dune CLI

Full Dune CLI reference for querying on-chain data via DuneSQL. Covers:
- Query management (create, get, update, run, run-sql)
- Dataset discovery (search tables, search by contract address)
- Visualization management (create, update, delete charts)
- Dashboard management (create, update, widget layout)
- DuneSQL cheatsheet (types, functions, common patterns)
- Credit optimization and API conventions

10 reference docs in `.claude/skills/dune/references/`.

### `data-plumber` — Pipeline conventions

End-to-end pipeline building patterns adapted for this project's architecture (fetch → Supabase ingest → transform → Dune upload → matview → queries). Covers:
- Fetch patterns (async, per-chain concurrency, error handling)
- Supabase ingest conventions (incremental watermark, batch upsert, retry)
- Transform conventions (raw columns only, no computed metrics in pipeline)
- Upload workflow (explicit schemas, credit costs, `--recreate` vs `--clear`)
- Matview layer (single source of truth for derived metrics)
- SQL conventions (query naming, combined queries, tier patterns)
- YAML schema documentation patterns

5 reference docs in `.claude/skills/data-plumber/references/`.

### `defi-overview` — Dashboard conventions

Project-specific conventions for this dashboard (Dune dashboard 212511):
- Derived metric definitions (TVL+, velocity, fee efficiency, volume efficiency, OI leverage, per-address metrics)
- Query hierarchy with IDs (base metrics → matview → combined → tiers → heatmaps)
- Heatmap patterns (absolute median vs MoM growth)
- Color schemes (timeseries families, category pie palette)
- Key table mappings (uploaded → matview → queries)

## Chains tracked

Ethereum, Solana, BSC, Bitcoin, Tron, Base, Arbitrum, Hyperliquid L1, Polygon, MegaETH, Avalanche, Sui, Monad, Optimism, Cronos, Ink, Aptos, Mantle, Starknet, Stellar, Movement, Flare, Cardano, Near, Rootstock.

Static list derived from DefiLlama `/v2/chains` top chains by TVL (May 2025). Shared across `pipeline/fetch.py`, `pipeline/ingest.py`, and `pipeline/transform.py` (TODO: update top chain list ingestion to dynamic).

## Built with AI

This pipeline was designed and built with assistance from [Claude Code](https://claude.ai/claude-code) and [Dune Skills](https://github.com/duneanalytics/skills), using DefiLlama's LLM-friendly API documentation as the primary data source reference.

### How it worked

**1. API discovery via `llms-free.txt`**

DefiLlama publishes a plain-text, LLM-optimized version of their API docs at [`api-docs.defillama.com/llms-free.txt`](https://api-docs.defillama.com/llms-free.txt). Claude Code consumed this file to understand all 31 free endpoints — their paths, parameters, response shapes, and relationships. No manual API exploration was needed.

**2. Source mapping and schema design**

From the API surface, Claude Code mapped 16 endpoints across 6 groups (stablecoins, tvl, volumes, fees, chain_history, users) to 3 Supabase tables. The schema was designed to mirror what the Dune dashboard needs — not what the API returns. This meant flattening nested JSON, normalizing unix timestamps to dates, and merging multiple endpoints into single rows (e.g., `defi_daily` combines TVL, volume, fees, stablecoins, options, OI, and active addresses from 7 different API calls).

**3. Incremental ingestion pattern**

The watermark-based incremental ingestion (`MAX(date)` → filter → upsert only new rows) was designed to handle DefiLlama's append-only timeseries data efficiently. First run ingests all historical data; subsequent runs append only new dates. The `--full` flag exists because DefiLlama occasionally corrects historical data retroactively.

**4. Async fetch architecture**

The original fetcher (from `angela-v1/data-sourcer/defillama/`) used synchronous `urllib` — one request at a time. Claude Code rewrote it using `aiohttp` with `asyncio.Semaphore(8)` for bounded concurrency. Per-chain sources (7 sources × 25 chains = 175 requests) use `asyncio.gather` instead of sequential loops, cutting fetch time from ~2 minutes to ~15 seconds.

**5. Derived metrics layer**

Claude Code designed the matview layer to keep the pipeline simple (raw data only) while computing all derived metrics (velocity, fee efficiency, volume efficiency, OI leverage, per-address metrics) in Dune SQL. This separation means adding a new ratio never requires a pipeline change — just update the matview SQL.

**6. Dashboard queries and visualizations**

16 dashboard queries were built using Claude Code's `dune` skill, which provides full Dune CLI access for query creation, execution, visualization management, and dashboard layout. Queries follow a hierarchy: base matviews → combined timeseries → tiered chain breakdowns → heatmaps.

### Development progression

```
Phase 1: API exploration
    → consumed llms-free.txt + raw API reference
    → identified endpoint quirks (naming, response shapes, async population)
    ↓
Phase 2: Production pipeline
    → async fetcher (aiohttp, 16 sources, bounded concurrency)
    → Supabase persistence layer (incremental ingestion)
    → Dune upload + matview layer
    → 16 dashboard queries + visualizations
    → Claude Code skills for ongoing development
```

### Claude Code skills

Three custom skills in `.claude/skills/` encode this project's conventions so Claude Code can extend the pipeline without re-learning the architecture. `data-plumber` captures the fetch → ingest → transform → upload patterns with Supabase incremental logic. `defi-overview` encodes the dashboard's metric definitions, query hierarchy, and color schemes. `dune` provides the full Dune CLI reference for query/viz/dashboard management.

## GitHub Actions

The workflow (`.github/workflows/pipeline.yml`) runs the full pipeline daily at 6am UTC.

Required repository secrets:
- `SUPABASE_URL` — Supabase project URL
- `SUPABASE_SERVICE_KEY` — Supabase service role key
- `DUNE_API_KEY` — Dune API key

Manual trigger via `workflow_dispatch` supports optional inputs:
- `steps` — comma-separated steps to run (default: all)
- `full` — force full ingest refresh (boolean)
