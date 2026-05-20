---
name: data-plumber
description: "End-to-end data pipeline builder: external API → transform → Dune upload → materialized view → dashboard queries. Use when user says 'build a pipeline', 'create a dashboard from scratch', 'upload to Dune', 'source data from X and put it on Dune', or needs to set up a new analytics dashboard with off-chain data."
compatibility: Requires Python 3.10+, DUNE_API_KEY in local .env, network access. macOS/Linux/Windows.
allowed-tools: Bash Read Write Edit
metadata:
  author: gahyejeon
  version: "1.0.0"
---

# Data Plumber

Build end-to-end data pipelines that take off-chain API data, transform it for Dune, and produce dashboard-ready queries with a materialized view layer.

## Architecture

```
pipeline/fetch.py → DefiLlama API → data/raw/ (JSON)
    ↓
pipeline/ingest.py → parse + flatten → Supabase (incremental)
    ↓
pipeline/transform.py → SELECT from Supabase → data/csv/ (CSV, raw columns only)
    ↓
pipeline/upload.py → data/csv/ → Dune uploaded_table (DUNE_API_KEY from .env)
    ↓
Dune Materialized View (compute derived metrics here — single source of truth)
    ↓
queries/*.sql → dashboard queries (SELECT from matview only)
```

## Directory Structure

```
run.py                        # Pipeline orchestrator
pipeline/                     # Core pipeline modules
  fetch.py                    #   API → JSON
  ingest.py                   #   JSON → Supabase
  db.py                       #   Supabase client + helpers
  transform.py                #   Supabase → CSV
  upload.py                   #   CSV → Dune
.env                          # SUPABASE_URL, SUPABASE_SERVICE_KEY, DUNE_API_KEY
schema.sql                    # Supabase table definitions
queries/                      # SQL files for dashboard
  {dashboard}__kpis.sql
  {dashboard}__daily__{metric}.sql
  {dashboard}__chain__{metric}.sql
references/
  tables.yml                  # uploaded tables + matview schemas
  queries.yml                 # query metadata, columns, query_ids
  dashboard.yml               # section layout, viz types
  styles.yml                  # color palette
data/                         # Runtime output (gitignored)
  raw/                        # Fetched JSON
  csv/                        # Exported CSVs
.github/workflows/
  pipeline.yml                # Scheduled daily pipeline
```

## Pipeline Steps

### 1. Data Sourcing (pipeline/fetch.py)

Async fetcher using aiohttp with bounded concurrency (8 concurrent). See [references/fetch-patterns.md](references/fetch-patterns.md).

Key conventions:
- Output goes to `data/raw/{group}/{source_name}.json`
- All outputs wrapped in `{"data": ..., "source": ..., "fetched_at": ...}`
- Per-chain fetches run concurrently via `asyncio.gather` with semaphore (replaces sequential sleep loops)
- Handle 404/500 gracefully — some entities lack certain metrics (e.g., Bitcoin has no stablecoins)
- Use endpoint name mappings when API names differ from display names (e.g., `Optimism → "OP Mainnet"`)
- **Always `quote()` entity names in ALL endpoint URLs** — not just ones you know have spaces today. New entities will break without it

### 2. Ingest (pipeline/ingest.py)

Parse raw JSON, flatten into structured rows, upsert into Supabase with incremental date filtering.

Key conventions:
- Incremental: query `MAX(date)` from Supabase, only insert rows newer than that
- Category table (snapshot): always full upsert
- Batch upsert with NaN/Inf cleaning via `pipeline/db.py`
- `--full` flag to bypass incremental and re-upsert everything
- First run inserts all historical data; subsequent runs append new dates only

### 3. Transform (pipeline/transform.py)

Read from Supabase, export to Dune-ready CSVs. See [references/transform-conventions.md](references/transform-conventions.md).

Key rules:
- **Raw data only** — no computed metrics in the pipeline. Velocity, fee/TVL, ratios all go in DuneSQL matviews
- Reads from Supabase (not local JSON) — transform is a trivial SELECT → CSV
- Use `defaultdict` for building sparse timeseries (not all sources cover the same dates)
- Timestamps as `YYYY-MM-DD HH:MM:SS` UTC
- Empty string for missing values (CSV nulls)

### 4. Upload (pipeline/upload.py)

Push CSVs to Dune via API. See [references/upload-workflow.md](references/upload-workflow.md).

Key conventions:
- Read `DUNE_API_KEY` from local `.env` file (not shell env)
- Explicit schema definition in `TABLES` dict — never rely on auto-infer
- Support `--table`, `--clear`, `--recreate`, `--dry-run` flags
- `create` = 10 credits, `insert` = 1 credit, `clear` = free
- Use `--recreate` (delete + create) when schema changes (column add/remove)
- Tables accessible as `dune.{namespace}.{table_name}`

### 5. Materialized View Layer

Create matviews in Dune UI (CLI can't create them). They compute all derived metrics from raw uploaded tables.

Key principles:
- **Single source of truth** — all dashboard queries read from matviews, never from raw tables
- Compute ratios with `/ NULLIF(denominator, 0)` for safe division
- Matview naming: `result_{dashboard}_{granularity}_metrics`
- Document matview schemas in `tables.yml` alongside uploaded tables
- When adding new metrics, extend the matview SQL, not the pipeline
- **Matviews must be manually refreshed** in Dune UI after re-uploading data — CLI can't do this. Always remind the user

### 6. Dashboard Queries

SQL files in `queries/` directory. See [references/sql-conventions.md](references/sql-conventions.md).

Naming: `{dashboard}__{scope}__{period}__{metric}.sql`
- scope: aggregate, chain, protocol
- period: daily, monthly, snapshot (no period suffix)

**Critical: async data population.** Off-chain sources populate at different times. The latest date for TVL may not have volume data yet. Snapshot queries must anchor on a reference entity (e.g., Ethereum) to pick a date with complete data across all metrics. See [references/sql-conventions.md](references/sql-conventions.md) for the pattern.

### Adding a New Dashboard Query (end-to-end)

This is a single atomic flow — execute all steps without pausing for confirmation between them:

1. **Write the SQL file** in `queries/`
2. **Create the query on Dune** — `dune query create --name "..." --sql "$(cat queries/file.sql)" -o json`
3. **Execute the query** — `dune query run <id> -o json` — viz won't render without results
4. **Create the visualization** — `dune viz create` — match formatting of existing similar vizzes (`dune viz get <ref_id> -o json` to copy options)
5. **Update the dashboard** — `dune dashboard get <id> -o json` → append new viz widget with position → `dune dashboard update` with all widgets
6. **Update local docs** — add entry to `queries.yml` (with `query_id`) and `dashboard.yml`
7. **Run sync checker** to verify everything lines up

For updating an existing query: update SQL file → `dune query update <id> --sql "$(cat ...)"` → `dune query run <id>` → update docs. One flow, no stops.

## Query Architecture Patterns

### Aggregate vs Chain-Level

```
Aggregate (no chain dimension):
  __daily__combined         → one query, multiple vizs via columnMapping

Chain-level (date × chain):
  __chain__current          → unfiltered snapshot table (all chains)
  __chain__daily__tier1_*   → tiered timeseries (for chart legibility)
  __chain__daily__tier2_*
  __chain_all__daily__*     → unfiltered reference (not on dashboard)
  __chain__monthly__*       → heatmaps/shares (single threshold cut, not tiered)
```

### Combined Query Pattern

Same base table + same grain + same filters = one query. Different vizs select different columns via `columnMapping`. Tier queries are combined across metrics (tvl, volume, fees, velocity, fee_efficiency all in one query per tier).

### What Goes Where

| Element | Where |
|---------|-------|
| Raw columns + ratios | Matview |
| MAs, tier filters, pivots | Downstream queries |
| Formatting (ROUND, /1e9) | KPI queries only |
| Tier thresholds | Downstream `tier` CTE |

## Schema Documentation (YAML)

Three reference files document the full system. See [references/yaml-schema-patterns.md](references/yaml-schema-patterns.md).

- `tables.yml` — uploaded tables + matview column definitions, types, units
- `queries.yml` — query metadata organized by dashboard section, with column descriptions and query_ids
- `dashboard.yml` — section layout, widget types, notes

## Credit Optimization

- Matview layer means each dashboard query is a cheap SELECT, not a recomputation
- `create` costs 10 credits — avoid unnecessary recreates
- `insert` costs 1 credit — fine for daily refreshes
- Use `--clear` + `--insert` for full refresh (not recreate)
- Batch API exploration in a single session to avoid redundant fetches

## Reference Documents

| Topic | Reference |
|-------|-----------|
| Data sourcer fetch.py patterns | [fetch-patterns.md](references/fetch-patterns.md) |
| Transform conventions | [transform-conventions.md](references/transform-conventions.md) |
| Upload workflow | [upload-workflow.md](references/upload-workflow.md) |
| SQL style conventions | [sql-conventions.md](references/sql-conventions.md) |
| YAML schema patterns | [yaml-schema-patterns.md](references/yaml-schema-patterns.md) |
| Dune table upload API | See `dune` skill: [table-upload.md](../dune/references/table-upload.md) |
