WITH latest_day AS (
	SELECT MAX(date) AS max_date
	FROM dune.ghrjeondata.result_defi_overview_daily_metrics
	WHERE tvl IS NOT NULL
		AND dex_volume IS NOT NULL
		AND stablecoin_mcap IS NOT NULL
)

, current_vals AS (
	SELECT
		date
		, tvl
		, dex_volume
		, fees
		, stablecoin_mcap
		, open_interest
		, active_addresses
	FROM dune.ghrjeondata.result_defi_overview_daily_metrics
	WHERE date = (SELECT max_date FROM latest_day)
)

, d7_vals AS (
	SELECT
		tvl
		, dex_volume
		, stablecoin_mcap
		, open_interest
	FROM dune.ghrjeondata.result_defi_overview_daily_metrics
	WHERE date = (
		SELECT MAX(date)
		FROM dune.ghrjeondata.result_defi_overview_daily_metrics
		WHERE date <= (SELECT max_date - INTERVAL '7' DAY FROM latest_day)
			AND tvl IS NOT NULL
	)
)

, d30_vals AS (
	SELECT
		tvl
		, dex_volume
		, stablecoin_mcap
		, open_interest
	FROM dune.ghrjeondata.result_defi_overview_daily_metrics
	WHERE date = (
		SELECT MAX(date)
		FROM dune.ghrjeondata.result_defi_overview_daily_metrics
		WHERE date <= (SELECT max_date - INTERVAL '30' DAY FROM latest_day)
			AND tvl IS NOT NULL
	)
)

, ytd_vals AS (
	SELECT
		tvl
		, stablecoin_mcap
		, open_interest
	FROM dune.ghrjeondata.result_defi_overview_daily_metrics
	WHERE date = (
		SELECT MIN(date)
		FROM dune.ghrjeondata.result_defi_overview_daily_metrics
		WHERE date >= DATE '2026-01-01'
			AND tvl IS NOT NULL
	)
)

SELECT
	c.date AS data_as_of
	-- Raw values
	, c.tvl
	, c.dex_volume AS dex_volume_24h
	, c.fees AS fees_24h
	, c.stablecoin_mcap
	, c.open_interest
	-- Truncated for counter widgets
	, ROUND(c.tvl / 1e9, 4) AS tvl_B
	, ROUND(c.dex_volume / 1e9, 4) AS dex_volume_24h_B
	, ROUND(c.fees / 1e6, 4) AS fees_24h_M
	, ROUND(c.stablecoin_mcap / 1e9, 4) AS stablecoin_mcap_B
	, ROUND(c.open_interest / 1e9, 4) AS open_interest_B
	, c.active_addresses
	, ROUND(c.active_addresses / 1e6, 2) AS active_addresses_M
	-- Percentage changes
	, CASE
		WHEN d7.tvl IS NULL OR d7.tvl < 1e6 THEN NULL
		ELSE ROUND(100.0 * (c.tvl - d7.tvl) / d7.tvl, 4)
	END AS tvl_change_7d_pct
	, CASE
		WHEN d30.tvl IS NULL OR d30.tvl < 1e6 THEN NULL
		ELSE ROUND(100.0 * (c.tvl - d30.tvl) / d30.tvl, 4)
	END AS tvl_change_30d_pct
	, CASE
		WHEN ytd.tvl IS NULL OR ytd.tvl < 1e6 THEN NULL
		ELSE ROUND(100.0 * (c.tvl - ytd.tvl) / ytd.tvl, 4)
	END AS tvl_change_ytd_pct
	, CASE
		WHEN d30.stablecoin_mcap IS NULL OR d30.stablecoin_mcap < 1e6 THEN NULL
		ELSE ROUND(100.0 * (c.stablecoin_mcap - d30.stablecoin_mcap) / d30.stablecoin_mcap, 4)
	END AS stablecoin_mcap_change_30d_pct
	, CASE
		WHEN d30.open_interest IS NULL OR d30.open_interest < 1e6 THEN NULL
		ELSE ROUND(100.0 * (c.open_interest - d30.open_interest) / d30.open_interest, 4)
	END AS open_interest_change_30d_pct
FROM current_vals c
CROSS JOIN d7_vals d7
CROSS JOIN d30_vals d30
CROSS JOIN ytd_vals ytd
