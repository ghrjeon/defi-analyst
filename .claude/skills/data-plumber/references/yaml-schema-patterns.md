# YAML Schema Documentation Patterns

Three reference files document a dashboard's data layer.

## tables.yml

Documents uploaded tables and materialized views.

```yaml
database: dune
namespace: ghrjeondata
source: defillama

tables:
  # --- Uploaded Tables ---
  - name: defi_overview_daily
    type: uploaded_table
    table: dune.ghrjeondata.defi_overview_daily
    description: >
      Aggregate daily DeFi metrics sourced from DefiLlama.
    granularity: daily
    update_method: clear + insert (full refresh via upload.py)
    columns:
      - name: date
        type: timestamp
        description: Calendar date (UTC midnight).
      - name: tvl
        type: double
        nullable: true
        unit: usd
        description: Total value locked.

  # --- Materialized Views ---
  - name: defi_overview_daily_metrics
    type: materialized_view
    table: dune.ghrjeondata.result_defi_overview_daily_metrics
    description: >
      Raw data + computed ratios. All queries read from here.
    granularity: daily
    columns:
      # ... raw columns same as uploaded table ...
      - name: velocity
        type: double
        nullable: true
        description: "dex_volume / tvl. Capital turnover."

  # --- Derived metric definitions ---
  derived_metrics:
    - name: velocity
      formula: dex_volume / NULLIF(tvl, 0)
      description: Capital turnover.
```

Key fields: `type` (uploaded_table | materialized_view), `table` (full Dune path), `update_method`, `unit` on columns.

## queries.yml

Organized by dashboard section:

```yaml
dashboard: defi_overview
sections:
  - name: "Section 1: KPIs"
    queries:
      - file: defi_overview__kpis.sql
        query_id: 7509707  # filled in after creating on Dune
        title: DeFi Overview KPIs
        description: Current values + 7d/30d/YTD changes.
        source_table: result_defi_overview_daily_metrics
        columns:
          - name: current_tvl
            type: double
            unit: usd
            description: Latest TVL.
          - name: tvl_7d_pct
            type: double
            unit: ratio
            description: 7-day TVL change.
```

Key fields: `file` (local SQL), `query_id` (Dune, filled after creation), `source_table`, column definitions with `unit`.

## dashboard.yml

Layout reference:

```yaml
dashboard: defi_overview
title: DeFi Overview
sections:
  - name: KPIs
    position: top
    widgets:
      - query: defi_overview__kpis
        viz_type: counter
        notes: "7d/30d/YTD % changes"

  - name: Aggregate Timeseries
    widgets:
      - query: defi_overview__daily__tvl
        viz_type: area_chart
        notes: "7d MA overlay"
```
