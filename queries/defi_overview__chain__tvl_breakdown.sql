-- TVL breakdown by category per chain (top 10 by TVL).
-- Top 5 categories shown individually, rest rolled into "Other".
-- Powers per-chain TVL pie charts on the dashboard.

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

, tvl_raw AS (
	SELECT
		c.chain
		, c.category
		, c.total24h AS tvl
		, c.protocol_count
	FROM dune.ghrjeondata.defi_overview_chain_category c
	INNER JOIN top10 t ON c.chain = t.chain
	WHERE c.metric = 'tvl'
		AND c.total24h > 0
		AND c.category NOT IN (
			'CEX', 'Chain', 'Bridge', 'Canonical Bridge', 'Cross Chain Bridge', 'Bridge Aggregator',
			'NFT Marketplace', 'NFT Lending', 'NftFi', 'NFT Automated Strategies',
			'Gaming', 'Luck Games', 'Telegram Bot', 'Physical TCG', 'Crypto Card Issuer',
			'Developer Tools', 'Payments', 'Services', 'SoFi', 'Privacy', 'Ponzi',
			'Charity Fundraising', 'Bug Bounty', 'DAO Service Provider', 'DOR',
			'Gamified Mining', 'Governance Incentives', 'Token Locker', 'AI Agents',
			'Interface', 'OTC Marketplace', 'Staking Rental', 'DCA Tools'
		)
)

, ranked AS (
	SELECT
		chain
		, category
		, tvl
		, protocol_count
		, ROW_NUMBER() OVER (PARTITION BY chain ORDER BY tvl DESC) AS rn
	FROM tvl_raw
)

, chain_totals AS (
	SELECT chain, SUM(tvl) AS chain_total_tvl
	FROM tvl_raw
	GROUP BY chain
)

SELECT
	r.chain
	, CASE WHEN r.rn <= 5 THEN r.category ELSE 'Other' END AS category
	, SUM(r.tvl) AS tvl
	, SUM(r.protocol_count) AS protocol_count
	, ROUND(SUM(r.tvl) / MAX(ct.chain_total_tvl), 4) AS pct_of_chain
FROM ranked r
JOIN chain_totals ct ON r.chain = ct.chain
GROUP BY r.chain, CASE WHEN r.rn <= 5 THEN r.category ELSE 'Other' END
ORDER BY r.chain, tvl DESC
