# defi-analyst

DeFi data pipeline: DefiLlama API → Supabase → Dune.

Dashboard: https://dune.com/ghrjeondata/defi-overview-cross-chain-analysis

## Pipeline

Four modules in `pipeline/`, run in order via `run.py` orchestrator:

```
pipeline/fetch.py    → DefiLlama API → data/raw/ (async, 8 concurrent)
pipeline/ingest.py   → data/raw/ → Supabase (incremental by MAX(date))
pipeline/transform.py → Supabase → data/csv/ (SELECT → CSV)
pipeline/upload.py   → data/csv/ → Dune uploaded tables
```

Orchestrator: `python run.py` runs all four steps in sequence.
- `--steps fetch,ingest` — run specific steps only
- `--skip upload` — exclude a step
- `--full` — force full ingest refresh (bypass incremental)
- `--dry-run` — preview without side effects

Individual modules: `python -m pipeline.fetch --list`, `python -m pipeline.ingest --status`, etc.

Scheduled via GitHub Actions (`.github/workflows/pipeline.yml`) — daily at 6am UTC, or manual trigger with optional `steps` and `full` inputs.

## Supabase

3 data tables + audit log. Schema in `schema.sql`.

| Table | PK | Description |
|-------|-----|-------------|
| `defi_daily` | (date) | 7 metrics: TVL, volume, fees, stablecoins, options, OI, active addresses |
| `defi_chain_daily` | (date, chain) | 6 metrics per chain (no options_volume) |
| `defi_chain_category` | (chain, metric, category) | Snapshot: category breakdown per chain |
| `ingestion_log` | id | Audit trail for every ingest run |

**Source → table mapping:** 16 fetch sources map to 3 Supabase tables. `defi_daily` merges 7 aggregate sources (tvl_historical, dex_volumes, fees_overview, stablecoin_mcap_history, options_volumes, open_interest, active_users) into one row per date. `defi_chain_daily` merges 6 per-chain history sources (chain_tvl_history, chain_dex_volumes_history, chain_fees_history, chain_stablecoin_mcap_history, chain_open_interest_history, chain_active_users_history) into one row per date+chain. `defi_chain_category` ingests 3 category snapshot sources (chain_fees, chain_dex_volumes, chain_tvl_by_category).

**Incremental ingestion:** timeseries tables query `MAX(date)` and only insert newer rows. Category table always full-upserts (snapshot data). Historical corrections by DefiLlama require `--full` to re-ingest — incremental only looks forward.

**Retry logic:** `pipeline/db.py` retries failed batch upserts (3 attempts, exponential backoff) to handle transient SSL/HTTP2 errors under sustained load.

## Dune

Namespace: `ghrjeondata`

| Table | Type | Description |
|-------|------|-------------|
| `defi_overview_daily` | uploaded | Aggregate daily timeseries |
| `defi_overview_chain_daily` | uploaded | Per-chain daily timeseries (25 chains) |
| `defi_overview_chain_category` | uploaded | Category breakdown snapshot |
| `result_defi_overview_daily_metrics` | matview | Aggregate + derived ratios |
| `result_defi_overview_chain_daily_metrics` | matview | Per-chain + derived ratios |

Matviews compute all derived metrics (velocity, fee efficiency, etc.) from the raw uploaded tables. Dashboard queries SELECT from matviews only, never from raw tables. Matviews must be manually rematerialized in Dune UI after schema changes.

23 dashboard queries in `queries/` are reference copies — live versions are on Dune.

Dashboard metadata in `references/` (query IDs, viz IDs, table schemas, color palette).

## Key files

| File | Purpose |
|------|---------|
| `run.py` | Pipeline orchestrator |
| `pipeline/fetch.py` | Async DefiLlama fetcher (aiohttp, 16 sources) |
| `pipeline/ingest.py` | JSON → Supabase (incremental) |
| `pipeline/db.py` | Supabase client, batch upsert, pagination, ingestion logging |
| `pipeline/transform.py` | Supabase → CSV |
| `pipeline/upload.py` | CSV → Dune API |
| `schema.sql` | Supabase table definitions |
| `.github/workflows/pipeline.yml` | Scheduled GitHub Actions workflow |
| `references/queries.yml` | All Dune queries with IDs, columns, viz IDs |
| `references/tables.yml` | Uploaded table and matview schemas |
| `references/dashboard.yml` | Dashboard layout, widget positions |
| `references/styles.yml` | Category color palette for pie charts |

## Conventions

- `TOP_CHAINS` list is shared between fetch.py, ingest.py, and transform.py — keep in sync
- `TOP_CHAINS` was derived from DefiLlama `/v2/chains` (top ~25 by TVL as of 2025-05). TODO: periodically review and update — static list may drift from actual rankings
- DefiLlama uses unix timestamps; ingest.py converts to `YYYY-MM-DD` dates
- transform.py appends ` 00:00:00` to dates for Dune timestamp format
- Category data is a snapshot (not timeseries) — always fully upserted
- Daily and chain tables on Dune are full-refresh: clear + insert
- Raw columns only in the pipeline — all derived metrics (ratios, MAs) go in Dune matviews
- Supabase client requires `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` in `.env`
- Dune upload requires `DUNE_API_KEY` in `.env`
- GitHub Actions requires all three as repository secrets

## AI development context

This project was built end-to-end by Claude Code using DefiLlama's LLM-friendly docs ([`api-docs.defillama.com/llms-free.txt`](https://api-docs.defillama.com/llms-free.txt)) as the primary API reference. The `llms-free.txt` file provided a flat-text summary of all 31 free endpoints — enough for Claude Code to map 16 sources to 3 Supabase tables, design the incremental ingestion pattern, and build the async fetch architecture without manual API exploration.


Three Claude Code skills in `.claude/skills/` encode project conventions so the agent can extend the pipeline (add metrics, sources, queries) without re-learning the architecture. See README.md "Built with AI" section for the full development process.

## Skills

Three Claude Code skills in `.claude/skills/` for working with this project:

| Skill | Trigger | What it does |
|-------|---------|--------------|
| `dune` | "query Dune", "search datasets", "create dashboard" | Dune CLI for querying on-chain data, managing queries/vizzes/dashboards, dataset discovery. 10 reference docs (DuneSQL cheatsheet, query management, viz management, etc.) |
| `data-plumber` | "build a pipeline", "upload to Dune", "add a new metric" | Pipeline conventions for this project's architecture. Covers fetch patterns, Supabase ingest, transform/upload workflows, matview layer, SQL conventions, YAML schema patterns. 5 reference docs. |
| `defi-overview` | "what's the query hierarchy", "which metrics exist", "color scheme" | Dashboard-specific conventions: derived metric definitions (TVL+, velocity, fee efficiency), query hierarchy with IDs, heatmap patterns, color schemes, key table mappings. |
