# DuneSQL Style Conventions

SQL style for dashboard queries. All queries read from materialized views, not raw uploaded tables.

## General Style

- CTE chains with leading comma: `, name AS (`
- Tab indent inside CTEs
- Leading commas for column lists
- `CASE WHEN` for safe division (not `NULLIF` shortcuts)
- Floor check on denominator: `< 1e6` for USD values, `< 1e3` for small metrics
- Clamp extreme values: `GREATEST(-5.0, LEAST(5.0, ...))`
- `CROSS JOIN` for joining single-row CTEs (not `LEFT JOIN ... ON 1=1`)
- `APPROX_PERCENTILE(col, 0.5)` for medians

## Async Data Population (critical for snapshot queries)

Off-chain data sources populate metrics at different times. The latest date for TVL may not have volume or stablecoin data yet. This causes snapshot queries to return mostly nulls if they naively pick `MAX(date)`.

**Anchor on the reference entity.** For cross-chain queries, use the largest/most-reliable chain (e.g., Ethereum) to determine the latest complete date:

```sql
WITH latest_day AS (
    SELECT MAX(date) AS max_date
    FROM dune.namespace.result_dashboard_chain_metrics
    WHERE chain = 'Ethereum'
        AND tvl IS NOT NULL
        AND dex_volume IS NOT NULL
        AND stablecoin_mcap IS NOT NULL
)
```

**Why not just `AND dex_volume IS NOT NULL` without anchoring?** Because `MAX(date)` across ALL chains picks the latest date where ANY single chain has volume — but that day may have only 2/25 chains populated. Anchoring on Ethereum ensures the date has broad coverage.

Apply this pattern to:
- `latest_day` CTE in snapshot queries (chain__current, heatmaps, KPIs)
- `d30_vals` / `ytd_vals` comparison date CTEs
- Any query that joins current values with historical comparison points

For **aggregate** (non-chain) queries, anchor on multiple metrics instead of a chain:
```sql
WHERE tvl IS NOT NULL
    AND dex_volume IS NOT NULL
    AND stablecoin_mcap IS NOT NULL
```

## Query Patterns

### Simple Timeseries (7d MA)

```sql
SELECT
    date
    , chain
    , AVG(metric) OVER (
        PARTITION BY chain
        ORDER BY date
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ) AS metric_7d_ma
FROM dune.namespace.result_dashboard_metrics
WHERE metric IS NOT NULL
ORDER BY date, chain
```

### KPI Snapshot

```sql
WITH latest_day AS (
    SELECT MAX(date) AS max_date
    FROM dune.namespace.result_dashboard_metrics
    WHERE tvl IS NOT NULL
        AND dex_volume IS NOT NULL
        AND stablecoin_mcap IS NOT NULL
)

, current_vals AS (
    SELECT tvl, dex_volume, fees
    FROM dune.namespace.result_dashboard_metrics
    WHERE date = (SELECT max_date FROM latest_day)
)

, d7_vals AS (
    SELECT tvl, dex_volume, fees
    FROM dune.namespace.result_dashboard_metrics
    WHERE date = (
        SELECT MAX(date)
        FROM dune.namespace.result_dashboard_metrics
        WHERE date <= (SELECT max_date - INTERVAL '7' DAY FROM latest_day)
            AND tvl IS NOT NULL
    )
)

, d30_vals AS (...)

SELECT
    c.tvl AS current_tvl
    , CASE
        WHEN d7.tvl IS NULL OR d7.tvl < 1e6 THEN NULL
        ELSE (c.tvl - d7.tvl) / d7.tvl
    END AS tvl_7d_pct
    , CASE
        WHEN d30.tvl IS NULL OR d30.tvl < 1e6 THEN NULL
        ELSE (c.tvl - d30.tvl) / d30.tvl
    END AS tvl_30d_pct
FROM current_vals c
CROSS JOIN d7_vals d7
CROSS JOIN d30_vals d30
```

### MoM Heatmap (Pivoted)

```sql
WITH monthly_avg AS (
    SELECT
        chain
        , DATE_TRUNC('month', date) AS month_start
        , AVG(metric) AS avg_metric
    FROM ...
    GROUP BY 1, 2
)

, with_mom AS (
    SELECT
        chain, month_start, avg_metric
        , LAG(avg_metric) OVER (PARTITION BY chain ORDER BY month_start) AS prev
    FROM monthly_avg
)

, mom_raw AS (
    SELECT
        chain, month_start
        , CASE
            WHEN prev IS NULL OR prev < 1e6 THEN NULL
            ELSE GREATEST(-5.0, LEAST(5.0,
                (avg_metric - prev) / prev
            ))
        END AS mom_growth_rate
    FROM with_mom
)

-- Pivot: m-01 = latest month, m-12 = oldest
SELECT
    chain
    , MAX(CASE WHEN month_start = (SELECT max_month FROM latest_month) THEN mom_growth_rate END) AS "m-01"
    , MAX(CASE WHEN month_start = DATE_ADD('month', -1, (SELECT max_month FROM latest_month)) THEN mom_growth_rate END) AS "m-02"
    ...
```

### Chain Current Snapshot

```sql
-- Anchor on Ethereum for complete data (see "Async Data Population" above)
WITH latest_day AS (
    SELECT MAX(date) AS max_date
    FROM dune.namespace.result_dashboard_chain_metrics
    WHERE chain = 'Ethereum'
        AND tvl IS NOT NULL
        AND dex_volume IS NOT NULL
        AND stablecoin_mcap IS NOT NULL
)

, current_vals AS (
    SELECT chain, tvl, dex_volume, ...
    FROM dune.namespace.result_dashboard_chain_metrics
    WHERE date = (SELECT max_date FROM latest_day)
)

, totals AS (
    SELECT SUM(tvl) AS total_tvl, ...
    FROM current_vals
)

SELECT
    c.chain
    , c.tvl
    , CASE
        WHEN t.total_tvl < 1e6 THEN NULL
        ELSE c.tvl / t.total_tvl
    END AS tvl_share
FROM current_vals c
CROSS JOIN totals t
ORDER BY c.tvl DESC
```

## File Naming

`{dashboard}__{scope}__{period}__{metric}.sql`

Examples:
- `defi_overview__kpis.sql`
- `defi_overview__daily__tvl.sql`
- `defi_overview__chain__daily__velocity.sql`
- `defi_overview__chain__monthly__tvl_heatmap.sql`
- `defi_overview__chain__volume_share.sql`
