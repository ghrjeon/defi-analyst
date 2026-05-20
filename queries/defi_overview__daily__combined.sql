-- Combined aggregate timeseries: raw metrics + derived ratios + 7d/30d MAs.
-- One query powers all aggregate charts on the dashboard.

SELECT
	date
	-- Raw metrics
	, tvl
	, tvl_oi_adj
	, dex_volume
	, fees
	, stablecoin_mcap
	, open_interest
	-- Derived ratios
	, velocity AS dex_velocity
	, CASE
		WHEN tvl_oi_adj IS NULL OR tvl_oi_adj < 1e6 THEN NULL
		ELSE fees / tvl_oi_adj
	END AS fee_per_tvl
	, oi_to_tvl
	, CASE
		WHEN dex_volume IS NULL OR dex_volume < 1e6 THEN NULL
		ELSE fees / dex_volume
	END AS fee_per_vol
	-- TVL MAs
	, AVG(tvl) OVER (ORDER BY date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS tvl_7d_ma
	, AVG(tvl) OVER (ORDER BY date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) AS tvl_30d_ma
	-- Volume MAs
	, AVG(dex_volume) OVER (ORDER BY date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS dex_volume_7d_ma
	, AVG(dex_volume) OVER (ORDER BY date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) AS dex_volume_30d_ma
	-- Fees MAs
	, AVG(fees) OVER (ORDER BY date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS fees_7d_ma
	, AVG(fees) OVER (ORDER BY date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) AS fees_30d_ma
	-- Stablecoin MAs
	, AVG(stablecoin_mcap) OVER (ORDER BY date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS stablecoin_mcap_7d_ma
	, AVG(stablecoin_mcap) OVER (ORDER BY date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) AS stablecoin_mcap_30d_ma
	-- Open Interest MAs
	, AVG(open_interest) OVER (ORDER BY date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS open_interest_7d_ma
	, AVG(open_interest) OVER (ORDER BY date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) AS open_interest_30d_ma
	-- DEX Velocity MAs
	, AVG(velocity) OVER (ORDER BY date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS dex_velocity_7d_ma
	, AVG(velocity) OVER (ORDER BY date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) AS dex_velocity_30d_ma
	-- Fee efficiency MAs (using tvl_oi_adj)
	, AVG(CASE WHEN tvl_oi_adj IS NULL OR tvl_oi_adj < 1e6 THEN NULL ELSE fees / tvl_oi_adj END) OVER (ORDER BY date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS fee_per_tvl_7d_ma
	, AVG(CASE WHEN tvl_oi_adj IS NULL OR tvl_oi_adj < 1e6 THEN NULL ELSE fees / tvl_oi_adj END) OVER (ORDER BY date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) AS fee_per_tvl_30d_ma
	-- OI leverage MAs
	, AVG(oi_to_tvl) OVER (ORDER BY date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS oi_to_tvl_7d_ma
	, AVG(oi_to_tvl) OVER (ORDER BY date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) AS oi_to_tvl_30d_ma
	-- Take rate MAs
	, AVG(CASE WHEN dex_volume IS NULL OR dex_volume < 1e6 THEN NULL ELSE fees / dex_volume END) OVER (ORDER BY date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS fee_per_vol_7d_ma
	, AVG(CASE WHEN dex_volume IS NULL OR dex_volume < 1e6 THEN NULL ELSE fees / dex_volume END) OVER (ORDER BY date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) AS fee_per_vol_30d_ma
	-- Active users
	, active_addresses
	, AVG(active_addresses) OVER (ORDER BY date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS active_addresses_7d_ma
	, AVG(active_addresses) OVER (ORDER BY date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) AS active_addresses_30d_ma
	-- Per-user metrics
	, fees_per_address
	, AVG(fees_per_address) OVER (ORDER BY date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS fees_per_address_7d_ma
	, AVG(fees_per_address) OVER (ORDER BY date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) AS fees_per_address_30d_ma
	, volume_per_address
	, AVG(volume_per_address) OVER (ORDER BY date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS volume_per_address_7d_ma
	, AVG(volume_per_address) OVER (ORDER BY date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) AS volume_per_address_30d_ma
FROM dune.ghrjeondata.result_defi_overview_daily_metrics
WHERE tvl IS NOT NULL
ORDER BY date
