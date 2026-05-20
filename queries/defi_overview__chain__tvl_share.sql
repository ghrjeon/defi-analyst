WITH tier1 AS (
	SELECT chain
	FROM dune.ghrjeondata.result_defi_overview_chain_daily_metrics
	WHERE date = (SELECT MAX(date) FROM dune.ghrjeondata.result_defi_overview_chain_daily_metrics WHERE chain = 'Ethereum' AND tvl IS NOT NULL)
		AND tvl >= 1e9
)

, monthly_chain AS (
	SELECT
		m.chain
		, DATE_TRUNC('month', date) AS month_start
		, AVG(tvl) AS avg_tvl
	FROM dune.ghrjeondata.result_defi_overview_chain_daily_metrics m
	INNER JOIN tier1 t ON m.chain = t.chain
	WHERE tvl IS NOT NULL
		AND date >= DATE '2020-01-01'
	GROUP BY 1, 2
)

, monthly_totals AS (
	SELECT
		month_start
		, SUM(avg_tvl) AS total_tvl
	FROM monthly_chain
	GROUP BY 1
)

SELECT
	mc.month_start
	, mc.chain
	, CASE
		WHEN mt.total_tvl IS NULL OR mt.total_tvl < 1e6 THEN NULL
		ELSE mc.avg_tvl / mt.total_tvl
	END AS tvl_share_pct
FROM monthly_chain mc
JOIN monthly_totals mt ON mc.month_start = mt.month_start
ORDER BY mc.month_start, mc.chain
