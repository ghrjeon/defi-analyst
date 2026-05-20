-- 12-month MoM growth heatmap for active addresses by chain.

WITH latest_day AS (
	SELECT MAX(date) AS max_date
	FROM dune.ghrjeondata.result_defi_overview_chain_daily_metrics
	WHERE chain = 'Ethereum' AND tvl IS NOT NULL AND dex_volume IS NOT NULL
)
, latest_month AS (
	SELECT DATE_TRUNC('month', max_date) AS max_month FROM latest_day
)
, current_vals AS (
	SELECT chain, active_addresses AS current_active_addresses
	FROM dune.ghrjeondata.result_defi_overview_chain_daily_metrics
	WHERE date = (SELECT max_date FROM latest_day)
)
, monthly_avg AS (
	SELECT chain, DATE_TRUNC('month', date) AS month_start
		, AVG(active_addresses) AS avg_val
	FROM dune.ghrjeondata.result_defi_overview_chain_daily_metrics
	WHERE active_addresses IS NOT NULL AND date >= DATE_ADD('month', -13, (SELECT max_date FROM latest_day))
	GROUP BY 1, 2
)
, with_mom AS (
	SELECT chain, month_start, avg_val
		, LAG(avg_val) OVER (PARTITION BY chain ORDER BY month_start) AS prev_val
	FROM monthly_avg
)
, mom_raw AS (
	SELECT chain, month_start
		, CASE WHEN prev_val IS NULL OR prev_val < 100 THEN NULL ELSE (avg_val - prev_val) / prev_val END AS mom_growth
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
SELECT ct.chain, ct.current_active_addresses, o.median_12m_growth, o.num_positive
	, MAX(CASE WHEN m.month_start = (SELECT max_month FROM latest_month) THEN m.mom_growth END) AS "m-01"
	, MAX(CASE WHEN m.month_start = DATE_ADD('month', -1,  (SELECT max_month FROM latest_month)) THEN m.mom_growth END) AS "m-02"
	, MAX(CASE WHEN m.month_start = DATE_ADD('month', -2,  (SELECT max_month FROM latest_month)) THEN m.mom_growth END) AS "m-03"
	, MAX(CASE WHEN m.month_start = DATE_ADD('month', -3,  (SELECT max_month FROM latest_month)) THEN m.mom_growth END) AS "m-04"
	, MAX(CASE WHEN m.month_start = DATE_ADD('month', -4,  (SELECT max_month FROM latest_month)) THEN m.mom_growth END) AS "m-05"
	, MAX(CASE WHEN m.month_start = DATE_ADD('month', -5,  (SELECT max_month FROM latest_month)) THEN m.mom_growth END) AS "m-06"
	, MAX(CASE WHEN m.month_start = DATE_ADD('month', -6,  (SELECT max_month FROM latest_month)) THEN m.mom_growth END) AS "m-07"
	, MAX(CASE WHEN m.month_start = DATE_ADD('month', -7,  (SELECT max_month FROM latest_month)) THEN m.mom_growth END) AS "m-08"
	, MAX(CASE WHEN m.month_start = DATE_ADD('month', -8,  (SELECT max_month FROM latest_month)) THEN m.mom_growth END) AS "m-09"
	, MAX(CASE WHEN m.month_start = DATE_ADD('month', -9,  (SELECT max_month FROM latest_month)) THEN m.mom_growth END) AS "m-10"
	, MAX(CASE WHEN m.month_start = DATE_ADD('month', -10, (SELECT max_month FROM latest_month)) THEN m.mom_growth END) AS "m-11"
	, MAX(CASE WHEN m.month_start = DATE_ADD('month', -11, (SELECT max_month FROM latest_month)) THEN m.mom_growth END) AS "m-12"
FROM current_vals ct
LEFT JOIN mom_raw m ON ct.chain = m.chain
LEFT JOIN overall o ON ct.chain = o.chain
GROUP BY 1, 2, 3, 4
ORDER BY 2 DESC
