# DeFi Overview Dashboard

Project-specific conventions for the cross-chain DeFi health dashboard (Dune dashboard 212511).

## Pipeline

```
pipeline/fetch.py → data/raw/ (JSON)
    ↓
pipeline/ingest.py → Supabase (structured tables, incremental)
    ↓
pipeline/transform.py → data/csv/ (CSV)
    ↓
pipeline/upload.py → Dune uploaded tables
    ↓
Dune materialized views → dashboard queries → visualizations
```

Orchestrator: `python run.py` runs all steps. Scheduled daily via GitHub Actions.

## Derived Metrics

All ratios are defined in base metrics layers and consumed by downstream queries.

| Metric | Formula | Meaning |
|--------|---------|---------|
| **TVL+** (`tvl_oi_adj`) | `tvl + open_interest * 0.20` | Adjusted TVL — estimates perp margin at ~5x leverage. Applied to ALL chains. |
| **Dex Velocity** | `dex_volume / tvl` | Daily capital turnover per dollar of liquidity. |
| **Fee Efficiency** | `fees / tvl_oi_adj` | Fee generation per dollar of adjusted liquidity (TVL+). |
| **Volume Efficiency** | `fees / dex_volume` | Fee extraction per dollar traded. |
| **OI Leverage** | `open_interest / tvl` | Leverage proxy — OI relative to locked capital. |
| **Fees per Address** | `fees / active_addresses` | Revenue per active user. |
| **Volume per Address** | `dex_volume / active_addresses` | Trading volume per active user. |

### Naming rules
- Use the human names above in viz titles and documentation, not the column names.
- Viz titles include the formula: "Fee Efficiency (Fees/TVL+)", "DEX Velocity (Vol/TVL)", "Volume Efficiency (Fees/Vol)".
- `velocity` unqualified = `dex_velocity`. Reserve prefix for future velocity types (e.g. `payment_velocity`).

## Query Hierarchy

| Layer | Query ID | Role |
|-------|----------|------|
| Base aggregate metrics | 7509574 | Raw metrics + derived ratios (matview: `result_defi_overview_daily_metrics`) |
| Base chain metrics | 7509578 | Per-chain raw + derived (matview: `result_defi_overview_chain_daily_metrics`) |
| Daily combined | 7515317 | All aggregate timeseries + MAs — powers 9 dashboard charts |
| Chain current | 7509762 | Per-chain snapshot — raw metrics only (unfiltered) |
| Chain current derived | 7531349 | Per-chain snapshot — derived efficiency ratios only (unfiltered) |
| Chain summary | 7523954 | Per-chain snapshot with derived metrics (TVL >= $1B, dashboard table) |
| Chain tiers | 7517108, 7517109 | Tier 1 (>=$5B) and Tier 2 ($1B-$5B) chain timeseries |

### chain__current column order (7509762 — raw metrics)

```
chain → tvl → tvl_ytd_pct → oi_notional → margin_tvl_est
→ dex_volume_24h → total_volume_ytd → defi_fees_24h → total_fees_ytd
→ stablecoin_mcap
```

### chain__current__derived column order (7531349 — ratios)

```
chain → dex_velocity → fee_efficiency → volume_efficiency
```

### chain__current__summary (7523954 — dashboard table, TVL >= $1B)

Has both raw + derived. Efficiency ratios clamped with `GREATEST(..., 0.0001)`.

## Heatmaps

Two types of heatmaps — absolute medians (flow metrics) and MoM growth (everything else):

### Absolute median heatmaps (existing)

| Heatmap | Query ID | Metric |
|---------|----------|--------|
| Volume | 7512437 | Median daily DEX volume |
| Velocity | 7512360 | Median daily velocity |

### MoM growth heatmaps

| Heatmap | Query ID | Viz ID | Metric |
|---------|----------|--------|--------|
| TVL Growth | 7509774 | — | TVL MoM % change |
| Volume Growth | 7531438 | 11482208 | DEX volume MoM % change |
| Fee Growth | 7531444 | 11482209 | Fees MoM % change |
| Velocity Growth | 7531391 | 11482184 | Velocity MoM % change |
| Fee Efficiency Growth | 7531392 | 11482185 | Fee efficiency MoM % change |
| Volume Efficiency Growth | 7531394 | 11482186 | Volume efficiency MoM % change |
| Active Addresses Growth | — | — | Active addresses MoM % change |

All MoM heatmaps follow the same SQL pattern (see `dune-query-style.md` MoM Growth Heatmap Pattern). Table vizzes use `0.0%` with green/red coloring.

## Color Schemes

All colors documented in `references/styles.yml`.

### Timeseries (3 intensities: light raw → medium 30d MA → dark 7d MA)

| Scheme | Colors | Used by |
|--------|--------|---------|
| Blue | `#C8D8E8 → #8FB0D0 → #4C78A8` | TVL |
| Orange | `#F5DEB3 → #D4A84B → #E68A00` | DEX Volume, DEX Velocity |
| Green | `#C8E6C0 → #8BC07F → #59A14F` | Fees, Fee Efficiency |
| Coral | `#FFD0CB → #FF9E96 → #FF6F61` | Open Interest |
| Red | `#F5CBCC → #EB9293 → #E15759` | OI Leverage |
| Purple | `#D4C5E2 → #A893C4 → #7B68A8` | Volume Efficiency |

**Rule**: derived metrics inherit the color of their parent metric. Cross-metric ratios (volume efficiency = fees/vol) get a distinct family.

### Category pie charts

Consistent muted palette across all pie charts (fee + volume breakdowns). See `references/styles.yml` `category_colors` section.

## Key Tables (Dune namespace: `ghrjeondata`)

| Table | Type | Content |
|-------|------|---------|
| `defi_overview_daily` | uploaded | Aggregate timeseries |
| `defi_overview_chain_daily` | uploaded | Per-chain timeseries (25 chains) |
| `defi_overview_chain_category` | uploaded | Snapshot: fee/volume/TVL by protocol category per chain |
| `result_defi_overview_daily_metrics` | matview | Aggregate + derived ratios |
| `result_defi_overview_chain_daily_metrics` | matview | Per-chain + derived ratios + tvl_oi_adj |

Matviews must be rematerialized on Dune UI after schema changes to base layers.

## Reference files

All in `references/`:

| File | Content |
|------|---------|
| `queries.yml` | All query IDs, column schemas, viz IDs |
| `styles.yml` | Color schemes (timeseries + category pies) |
| `tables.yml` | Uploaded table schemas |
| `dashboard.yml` | Dashboard section layout |
