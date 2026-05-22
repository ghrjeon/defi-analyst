# DeFi Protocol Category Filtering

The TVL and fee breakdown queries exclude non-DeFi categories from DefiLlama's category taxonomy. Volume breakdown has no exclusion filter (volume categories are fewer and less noisy).

## Excluded Categories

| Category | Reason |
|----------|--------|
| CEX, Chain | Infrastructure, not DeFi protocols |
| Bridge, Canonical Bridge, Cross Chain Bridge, Bridge Aggregator | Cross-chain infra, not DeFi primitives |
| NFT Marketplace, NFT Lending, NftFi, NFT Automated Strategies | NFT ecosystem |
| Gaming, Luck Games, Telegram Bot, Physical TCG | Gaming/entertainment |
| Developer Tools, Services, Interface | Tooling, not capital-deploying protocols |
| Payments, SoFi, Privacy | Borderline — could revisit |
| Crypto Card Issuer | CeFi product |
| Ponzi, Charity Fundraising, Bug Bounty | Non-financial or illegitimate |
| DAO Service Provider, DOR | Governance tooling |
| Gamified Mining, Governance Incentives, Token Locker | Incentive mechanisms, not standalone DeFi |
| AI Agents | Emerging — not yet DeFi-native |
| OTC Marketplace, Staking Rental, DCA Tools | Niche tooling |

## Borderline Decisions

- **Payments, SoFi, AI Agents, OTC Marketplace, DCA Tools, Governance Incentives**: excluded for now but could be reconsidered as these categories mature.
- **Risk Curators**: included — these are Morpho vault curators that actively manage DeFi lending positions.
- **Liquid Staking, Staking Pool**: included — smart contract protocols tracked by DefiLlama's dimension-adapters.

## Where Applied

- `queries/defi_overview__chain__tvl_breakdown.sql` — TVL pie charts
- `queries/defi_overview__chain__fee_breakdown.sql` — Fee pie charts
- Per-chain variants of both (8 chains each)
- Volume breakdown (`defi_overview__chain__volume_breakdown.sql`) does NOT use this filter
