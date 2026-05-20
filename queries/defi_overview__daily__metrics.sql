-- Base metrics layer for aggregate-level analysis.
-- Joins raw DefiLlama data with computed ratios.

SELECT
	date
	, tvl
	, dex_volume
	, fees
	, stablecoin_mcap
	, options_volume
	, open_interest
	, active_addresses

	-- OI-adjusted TVL: adds estimated margin (20% of OI, ~5x avg leverage)
	, tvl + COALESCE(open_interest, 0) * 0.20 AS tvl_oi_adj

	-- velocity: capital turnover
	, CASE
		WHEN tvl IS NULL OR tvl < 1e6 THEN NULL
		ELSE dex_volume / tvl
	END AS velocity

	-- fee efficiency: revenue per dollar of TVL
	, CASE
		WHEN tvl IS NULL OR tvl < 1e6 THEN NULL
		ELSE fees / tvl
	END AS fee_per_tvl

	-- leverage ratio: OI relative to locked capital
	, CASE
		WHEN tvl IS NULL OR tvl < 1e6 THEN NULL
		ELSE open_interest / tvl
	END AS oi_to_tvl

	-- stablecoin penetration
	, CASE
		WHEN tvl IS NULL OR tvl < 1e6 THEN NULL
		ELSE stablecoin_mcap / tvl
	END AS stable_to_tvl

	-- volume intensity
	, CASE
		WHEN stablecoin_mcap IS NULL OR stablecoin_mcap < 1e6 THEN NULL
		ELSE dex_volume / stablecoin_mcap
	END AS volume_to_stable

	-- fees per active user
	, CASE
		WHEN active_addresses IS NULL OR active_addresses < 100 THEN NULL
		ELSE fees / active_addresses
	END AS fees_per_address

	-- volume per active user
	, CASE
		WHEN active_addresses IS NULL OR active_addresses < 100 THEN NULL
		ELSE dex_volume / active_addresses
	END AS volume_per_address

FROM dune.ghrjeondata.defi_overview_daily
WHERE tvl IS NOT NULL
	OR dex_volume IS NOT NULL
