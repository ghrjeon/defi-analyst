WITH latest_day AS (
	SELECT MAX(date) AS max_date
	FROM dune.ghrjeondata.result_defi_overview_chain_daily_metrics
	WHERE chain = 'Ethereum'
		AND tvl IS NOT NULL
		AND dex_volume IS NOT NULL
		AND stablecoin_mcap IS NOT NULL
)

, ytd_vals AS (
	SELECT
		chain
		, tvl
	FROM dune.ghrjeondata.result_defi_overview_chain_daily_metrics
	WHERE date = (
		SELECT MIN(date)
		FROM dune.ghrjeondata.result_defi_overview_chain_daily_metrics
		WHERE date >= DATE '2026-01-01'
			AND tvl IS NOT NULL
	)
)

, ytd_totals AS (
	SELECT
		chain
		, SUM(dex_volume) AS total_volume_ytd
		, SUM(fees) AS total_fees_ytd
	FROM dune.ghrjeondata.result_defi_overview_chain_daily_metrics
	WHERE date >= DATE '2026-01-01'
	GROUP BY chain
)

, avg_7d AS (
	SELECT
		chain
		, AVG(CASE WHEN tvl > 0 THEN dex_volume / tvl END) AS dex_velocity_7d
		, AVG(CASE WHEN tvl + COALESCE(open_interest * 0.20, 0) > 0
			THEN fees / (tvl + COALESCE(open_interest * 0.20, 0))
		END) AS fee_efficiency_7d
	FROM dune.ghrjeondata.result_defi_overview_chain_daily_metrics
	WHERE date >= DATE_ADD('day', -7, (SELECT max_date FROM latest_day))
	GROUP BY chain
)

, current_data AS (
	SELECT
		c.chain
		, c.tvl
		, CASE
			WHEN ytd.tvl IS NULL OR ytd.tvl < 1e6 THEN NULL
			ELSE ROUND((c.tvl - ytd.tvl) / ytd.tvl, 4)
		END AS tvl_ytd_pct
		, c.dex_volume AS dex_volume_24h
		, yt.total_volume_ytd
		, c.fees AS defi_fees_24h
		, yt.total_fees_ytd
		, c.stablecoin_mcap
		, c.open_interest AS oi_notional
		, c.open_interest * 0.20 AS margin_tvl_est
		, c.active_addresses AS active_addresses_24h
	FROM dune.ghrjeondata.result_defi_overview_chain_daily_metrics c
	LEFT JOIN ytd_vals ytd ON c.chain = ytd.chain
	LEFT JOIN ytd_totals yt ON c.chain = yt.chain
	WHERE c.date = (SELECT max_date FROM latest_day)
)

SELECT
	d.chain
	, d.tvl
	, ROUND(d.tvl / SUM(d.tvl) OVER (), 4) AS tvl_share_pct
	, d.tvl_ytd_pct
	, d.dex_volume_24h
	, d.total_volume_ytd
	, ROUND(d.total_volume_ytd / NULLIF(SUM(d.total_volume_ytd) OVER (), 0), 4) AS volume_share_ytd_pct
	, d.defi_fees_24h
	, d.total_fees_ytd
	, ROUND(d.total_fees_ytd / NULLIF(SUM(d.total_fees_ytd) OVER (), 0), 4) AS fees_share_ytd_pct
	, d.stablecoin_mcap
	, d.oi_notional
	, d.margin_tvl_est
	, d.tvl + COALESCE(d.margin_tvl_est, 0) AS tvl_adj
	, ROUND((d.tvl + COALESCE(d.margin_tvl_est, 0)) / SUM(d.tvl + COALESCE(d.margin_tvl_est, 0)) OVER (), 4) AS tvl_adj_share_pct
	, ROUND(a.fee_efficiency_7d, 6) AS fee_efficiency_7d
	, ROUND(a.dex_velocity_7d, 4) AS dex_velocity_7d
	, d.active_addresses_24h
	, d.chain AS chain_
FROM current_data d
LEFT JOIN avg_7d a ON d.chain = a.chain
ORDER BY d.tvl DESC
