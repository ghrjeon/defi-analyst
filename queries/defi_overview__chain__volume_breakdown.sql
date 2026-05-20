-- DEX volume breakdown by category per chain (top 10 by TVL).
-- Top 5 categories shown individually, rest rolled into "Other".
-- Powers per-chain pie charts on the dashboard.

WITH top10 AS (
	SELECT chain
	FROM dune.ghrjeondata.result_defi_overview_chain_daily_metrics
	WHERE date = (
		SELECT MAX(date)
		FROM dune.ghrjeondata.result_defi_overview_chain_daily_metrics
		WHERE chain = 'Ethereum' AND tvl IS NOT NULL
	)
	ORDER BY tvl DESC
	LIMIT 10
)

, vol_raw AS (
	SELECT
		c.chain
		, c.category
		, c.total24h
		, c.total7d
		, c.protocol_count
	FROM dune.ghrjeondata.defi_overview_chain_category c
	INNER JOIN top10 t ON c.chain = t.chain
	WHERE c.metric = 'dex_volume'
		AND c.total24h > 0
)

, ranked AS (
	SELECT
		chain
		, category
		, total24h
		, total7d
		, protocol_count
		, ROW_NUMBER() OVER (PARTITION BY chain ORDER BY total24h DESC) AS rn
	FROM vol_raw
)

, chain_totals AS (
	SELECT chain, SUM(total24h) AS chain_total_24h
	FROM vol_raw
	GROUP BY chain
)

SELECT
	r.chain
	, CASE WHEN r.rn <= 5 THEN r.category ELSE 'Other' END AS category
	, SUM(r.total24h) AS volume_24h
	, SUM(r.total7d) AS volume_7d
	, SUM(r.protocol_count) AS protocol_count
	, ROUND(SUM(r.total24h) / MAX(ct.chain_total_24h), 4) AS pct_of_chain
FROM ranked r
JOIN chain_totals ct ON r.chain = ct.chain
GROUP BY r.chain, CASE WHEN r.rn <= 5 THEN r.category ELSE 'Other' END
ORDER BY r.chain, volume_24h DESC
