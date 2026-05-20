# Dune Query Style Guide

Conventions for writing and managing Dune queries in this project.

---

## Naming

- **Query title on Dune must exactly match the local SQL filename** (without `.sql`).
  - e.g. file `defi_overview__chain__current.sql` → Dune title `defi_overview__chain__current`
- Use double-underscore `__` as the hierarchy separator: `{dashboard}__{grain}__{metric}`.
- Grain tokens: `daily`, `chain`, `chain__daily`, `chain__monthly`.
- **Disambiguate velocity types**: use `dex_velocity` (vol/tvl) for DEX trading turnover. Reserve `velocity` unqualified for future use (e.g. `payment_velocity` for stablecoin transfer volume / stablecoin mcap).

---

## KPI / Counter Formatting

**Always output both raw and truncated columns.** Raw values allow future permutations without re-querying. Truncated columns are for direct use in Dune counter widgets with a static Suffix.

| Scale | Divisor | Column suffix | Dune widget suffix |
|-------|---------|---------------|--------------------|
| Billions | `/ 1e9` | `_B` | `B` |
| Millions | `/ 1e6` | `_M` | `M` |
| Percent | already `* 100` | `_pct` | `%` |

Use `ROUND(..., 4)` minimum on all truncated values — enough precision for flexibility while avoiding scientific notation.

Example:
```sql
-- Raw (keep for future permutations)
, c.tvl
, c.dex_volume AS dex_volume_24h
, c.fees AS fees_24h
-- Truncated for counter widgets (4 decimal minimum)
, ROUND(c.tvl / 1e9, 4) AS tvl_B              -- 85.5918 → displays "85.5918B"
, ROUND(c.fees / 1e6, 4) AS fees_24h_M        -- 55.484  → displays "55.484M"
, ROUND(100.0 * (c.tvl - d30.tvl) / d30.tvl, 4) AS tvl_change_30d_pct  -- -12.883 → "-12.883%"
```

---

## Consolidating Queries

When multiple charts pull from the same base table with only column selection differing, consolidate into one query with all columns. Create separate **visualizations** on that single query, each selecting relevant columns via `columnMapping`.

Benefits:
- One execution refreshes all charts
- Easier to maintain
- Fewer query IDs to track

Example: `defi_overview__daily__combined` outputs raw metrics + derived ratios + 7d/30d MAs → 8 separate viz widgets all point to this one query.

---

## Moving Averages

Always provide both 7d and 30d MAs for timeseries metrics:

```sql
AVG(tvl) OVER (ORDER BY date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS tvl_7d_ma
AVG(tvl) OVER (ORDER BY date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) AS tvl_30d_ma
```

---

## Chain Tier Structure

Split chain timeseries by tier for **chart legibility** — mega chains flatten smaller ones on stacked charts. Same pattern as stablecoin-analyst.

### Design principles (from stablecoin-analyst)
- **One query per tier**, same columns — just different threshold in the `tier` CTE
- **Current snapshot is unfiltered** — the table shows all chains, sortable
- **Heatmaps/shares use a single cut** (>= $1B) — not further tiered since they're tables, not stacked charts
- **Matview keeps all chains** — tier filtering in downstream queries only
- **Adding a tier = copy the SQL, change the threshold** — no schema changes needed

### Tier definitions

| Tier | Threshold | Purpose |
|------|-----------|---------|
| Tier 1 | TVL >= $1B | Dashboard charts — the meaningful chains |
| Tier 2 | TVL < $1B | Future expansion for emerging chains |

### SQL pattern

```sql
WITH tier AS (
	SELECT chain
	FROM dune.ghrjeondata.result_defi_overview_chain_daily_metrics
	WHERE date = (SELECT MAX(date) FROM ... WHERE chain = 'Ethereum' AND tvl IS NOT NULL)
		AND tvl >= 5e9          -- Tier 1
		-- AND tvl < 5e9        -- add upper bound for Tier 2
)

SELECT ...
FROM base_table m
INNER JOIN tier t ON m.chain = t.chain
WHERE tvl IS NOT NULL
```

### Query naming

```
defi_overview__chain__daily__tier1         -- tier 1 timeseries (>= $1B)
defi_overview__chain__current              -- unfiltered snapshot (table)
defi_overview__chain_all__daily__combined  -- unfiltered timeseries (reference, not on dashboard)
```

### Consistent chain colors

Use brand colors in `seriesOptions` so the same chain has the same color across all charts:

```json
{
  "Ethereum": "#B0B0B0", "Solana": "#9945FF", "BSC": "#F0B90B",
  "Bitcoin": "#F7931A", "Tron": "#FF0013", "Base": "#0052FF",
  "Arbitrum": "#28A0F0", "Hyperliquid L1": "#00FF88", "Polygon": "#E040FB"
}
```

Pass as `"seriesOptions"` in viz options. Apply to ALL chain-dimension charts.

---

## Stock vs Flow Metrics

- **Stock metrics** (TVL, stablecoin mcap, OI): point-in-time balances. Use MoM % change for comparisons.
- **Flow metrics** (volume, fees): daily activity. Use averages or medians for comparisons — MoM % on a single day is too noisy.
- **Derived ratios** (velocity, fee efficiency, volume efficiency): treat like stock metrics for heatmaps — MoM growth of the monthly average.

In heatmaps:
- Stock / ratios → MoM growth rate (%)
- Flow → either median daily value (absolute $) OR MoM growth of the monthly average — both are valid, keep both

---

## MoM Growth Heatmap Pattern

Reusable SQL pattern for 12-month MoM growth heatmaps. Replace `<metric_expr>` with the metric expression.

```sql
WITH latest_day AS (
	SELECT MAX(date) AS max_date
	FROM dune.ghrjeondata.result_defi_overview_chain_daily_metrics
	WHERE chain = 'Ethereum' AND tvl IS NOT NULL AND dex_volume IS NOT NULL
)
, latest_month AS (
	SELECT DATE_TRUNC('month', max_date) AS max_month FROM latest_day
)
, current_tvl AS (
	SELECT chain, tvl AS current_tvl
	FROM dune.ghrjeondata.result_defi_overview_chain_daily_metrics
	WHERE date = (SELECT max_date FROM latest_day)
)
, monthly_avg AS (
	SELECT chain, DATE_TRUNC('month', date) AS month_start
		, AVG(<metric_expr>) AS avg_val
	FROM dune.ghrjeondata.result_defi_overview_chain_daily_metrics
	WHERE <metric_not_null_filter>
		AND date >= DATE_ADD('month', -13, (SELECT max_date FROM latest_day))
	GROUP BY 1, 2
)
, with_mom AS (
	SELECT chain, month_start, avg_val
		, LAG(avg_val) OVER (PARTITION BY chain ORDER BY month_start) AS prev_val
	FROM monthly_avg
)
, mom_raw AS (
	SELECT chain, month_start
		, CASE WHEN prev_val IS NULL OR prev_val < <floor> THEN NULL
			ELSE (avg_val - prev_val) / prev_val END AS mom_growth
	FROM with_mom
)
, overall AS (
	SELECT chain
		, APPROX_PERCENTILE(mom_growth, 0.5) AS median_12m_growth
		, CAST(COUNT_IF(mom_growth > 0) AS VARCHAR) || '/12' AS num_positive
	FROM mom_raw
	WHERE month_start >= DATE_ADD('month', -11, (SELECT max_month FROM latest_month))
		AND month_start <= (SELECT max_month FROM latest_month)
	GROUP BY 1
)
SELECT ct.chain, ct.current_tvl, o.median_12m_growth, o.num_positive
	, MAX(CASE WHEN m.month_start = (SELECT max_month FROM latest_month) THEN m.mom_growth END) AS "m-01"
	-- ... m-02 through m-11 ...
	, MAX(CASE WHEN m.month_start = DATE_ADD('month', -11, (SELECT max_month FROM latest_month)) THEN m.mom_growth END) AS "m-12"
FROM current_tvl ct
LEFT JOIN mom_raw m ON ct.chain = m.chain
LEFT JOIN overall o ON ct.chain = o.chain
WHERE ct.current_tvl >= 1e9
GROUP BY 1, 2, 3, 4
ORDER BY 2 DESC
```

**Floor values** for `prev_val` null guard:
- Dollar metrics (volume, fees, TVL): `1e6` or `1e3`
- Ratios (velocity, efficiency): `1e-8`

**Viz options**: use the same heatmap table options for all — `0.0%` format with `coloredPositiveValues`/`coloredNegativeValues` on m-01..m-12 and median columns.

---

## Percentage Columns

Always wrap percentage calculations with `ROUND(..., N)` to prevent scientific notation (e.g. `4.477e-7`):

```sql
ROUND(100.0 * (c.tvl - d30.tvl) / d30.tvl, 1) AS tvl_30d_pct
```

For very small ratios (fee_per_tvl, velocity), use `ROUND(..., 4)`.

For ratios displayed in Dune table vizzes, clamp with `GREATEST()` to prevent numeral.js from rendering scientific notation (it cannot format values like `5.56e-7`):

```sql
GREATEST(fees / tvl_oi_adj, 0.0001) AS fee_efficiency
```

---

## Table Viz Formatting

Standard numeral.js formats for table visualizations:

| Data type | Format | Example |
|-----------|--------|---------|
| Dollar amounts | `$0.00a` | $44.20b, $1.65b, $912.34m |
| Percentages | `0.00%` | -34.93%, 2.70% |
| Small ratios as % | `0.00%` | 0.86% (from 0.0086) |

For change columns (YTD %, 30d %), add `coloredPositiveValues: true` and `coloredNegativeValues: true`.

Numeral.js silently breaks on very small floats (< ~1e-6) — renders raw scientific notation. Always clamp in SQL, not in the format string.

---

## Dashboard Update Gotcha

`dune dashboard update` uses **all-or-nothing replacement** per widget type. When updating, always pass **both** `--visualization-widgets` and `--text-widgets` in a single call. Passing only one will wipe the other.

```bash
# WRONG — wipes viz widgets:
dune dashboard update 212511 --text-widgets '[...]'

# CORRECT — preserves both:
dune dashboard update 212511 --visualization-widgets '[...]' --text-widgets '[...]'
```

Always fetch current state first with `dune dashboard get <id> -o json`, modify, then push the complete state back.

---

## Dashboard Layout Ownership

**The live dashboard is the source of truth for layout — not `dashboard.yml` or your memory.** The UI designer (user) rearranges widgets between sessions. Before ANY dashboard update:

1. **Always read first**: `dune dashboard get <id> -o json` — this is the current state
2. **Modify from that state** — parse the JSON, add/remove/replace specific widgets, push back
3. **Never rebuild from scratch** — never construct a widget list from memory or YAML
4. **Never drop widgets you didn't intend to change** — the all-or-nothing replacement means a missing widget = deleted widget
5. If adding new widgets, append to the highest row and let the UI designer position them

```python
# CORRECT pattern — always start from current state:
data = json.loads(subprocess.run(["dune", "dashboard", "get", "212511", "-o", "json"], capture_output=True, text=True).stdout)
viz = data['visualization_widgets']
txt = data['text_widgets']
# ... modify viz/txt ...
# Push BOTH back together:
dune dashboard update 212511 --visualization-widgets '[...]' --text-widgets '[...]'
```

`dashboard.yml` is a reference doc for what queries/sections exist — not a layout specification.

---

## Rate Limits

Dune API rate-limits at ~15 requests per burst. When making many sequential calls (renaming 20+ queries, creating vizs):
- Batch related calls (max ~12-15 per burst)
- If you hit 429, wait and retry — don't spam
- For bulk operations, use a loop with the `until` pattern for retries

---

## Visualization Creation Patterns

When creating vizs from a combined query for **stacked area charts** (per-chain):
```json
{
  "globalSeriesType": "area",
  "series": {"stacking": "normal"},
  "columnMapping": {"date": "x", "tvl": "y", "chain": "series"}
}
```

For **multi-line charts** (per-chain, no stacking):
```json
{
  "globalSeriesType": "line",
  "series": {"stacking": null},
  "columnMapping": {"date": "x", "dex_velocity_7d_ma": "y", "chain": "series"}
}
```

Key: use `"chain": "series"` to split by chain dimension. Use `stacking: "normal"` for area, `null` for line.

---

## Query Consolidation Decision Tree

When to consolidate (one query → multiple vizs):
- ✅ Same base table, same grain, same filters, different column selections
- ✅ Aggregate timeseries (all metrics share date dimension)
- ✅ Per-tier chain timeseries (all metrics share date × chain dimension)

When to keep separate:
- ❌ Different pivots/shapes (heatmaps are wide, timeseries are long)
- ❌ Different filters (growth snapshot has its own CTEs)
- ❌ Different grain (monthly shares vs daily timeseries)

---

## Matview vs Downstream Query Responsibilities

| Layer | Responsibility |
|-------|---------------|
| Matview | Raw columns + computed ratios (velocity, fee_per_tvl, oi_to_tvl). No filtering, no MAs. |
| Downstream query | Tier filtering, window functions (MAs), pivots, aggregations, formatting |

Never put tier logic in the matview. Never compute ratios in downstream queries.
