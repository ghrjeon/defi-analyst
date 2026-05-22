# DeFi Overview: Cross-Chain Analysis

### This dashboard provides cross-chain analysis of DeFi trends focused on TVL, volume, and fees. Data is sourced from DefiLlama API (See [Methodology](#methodology)).

---

# Summary (As of May 2026)

### DeFi TVL has contracted to $85.6B, down 42% from the November 2025 peak, but the ecosystem's revenue capacity has remained strong. Daily fees of $55M roughly match the 2021 peak despite half the locked capital, indicating a structural improvement in how efficiently DeFi monetizes liquidity.

### The chain landscape has split into two models. Ethereum still anchors 55% of TVL, but its volume share has declined to 19%, with capital sitting primarily in staking, lending, and RWA. Execution-heavy chains such as Solana, Base, and Sui turn over capital at 3–6x Ethereum's rate and now command outsized shares of volume and fees relative to their TVL. Hyperliquid has emerged as the third-largest fee earner ($364M YTD), almost entirely from derivatives.

### This divergence reflects a broader shift: DeFi fee generation is no longer dominated by spot Dex trading. Lending, perps, prediction markets, launchpads, and staking all contribute meaningfully across chains. Diversified product streams suggest the ecosystem is maturing, building durable economics rather than cycling on liquidity alone.

### There are several limitations to the study. Current metrics understate the full picture. For example, perps volume ($26B daily) is excluded from velocity calculations, and CLOB capital treatment is ambiguous. A deeper data investigation into metrics and capital structures across different DeFi primitives would sharpen the cross-chain comparison. 

### On Radar: As regulatory CLARITY improves, stablecoinsa nd tokenized assets are likely to become more tightly integrated with DeFi infrastructure. The key question is which chains will capture market share across different use cases, across expanding product x user types. 


---

# Aggregate Trends
 
### DeFi TVL stands at **$85.6B** as of May 2026, down **42%** from the November 2025 peak of **$147B** and roughly **48% below the 2021 high**, partly reflecting the lower asset prices against USD.
### Despite the decline in locked capital, DeFi ecosystem generates approximately **$55M in daily fees**. This level is roughly in line with the Q4 2021 peak of **$50M**, suggesting that fee earned per dollar locked has structurally improved over the past four years. 

### DeFi fees in data include Dex trading fees, lending interest, perps, and derivatives fees, launchpad fees, staking-related fees, and other protocol-level charges. The metric captures total fees paid by users, including both LP and protocol revenue. In [TVL and Fee Composition](#tvl-and-fee-composition), we further break down the diversity across chains.

### Daily active DeFi addresses remain elevated at **12.5M**. While the aggregate liquidity contracts through cycles, user activity and protocol monetization seem to have found a new baseline as DeFi products continue to mature and diversify.

### Dex Volume is currently running at approximately **$6.6B/day**, with the 30-day moving average generally in the **$5–7B** range, down from **$10B+** at the start of 2025. Solana leads with around 30% market share, followed by Ethereum and Binance. The composite DeFi volume is likely far larger, given that perps protocols are not included in the data.

### Active DeFi Addresses remain around **12.5M**, though this should be interpreted as a lower-bound estimate. Some chains tracked by DefiLlama, notably **Hyperliquid L1** and **Sui**, do not currently have active-address adapters, meaning reported figures likely understate actual DeFi participation. 

### Ethereum remains the dominant TVL venue, holding **$44.2B**, or roughly **55%** of total DeFi TVL. However, volume dominance tells a different story. **Solana** makes **32%** of Dex volume despite holding only 7% for TVL. Base has also gained volume share at 12%, while Ethereum's share declined from it's 70% heights in 2021 to around 19% since 2025.

---

# TVL Efficiency and Dex Velocity

### TVL Efficiency and Dex Velocity proxies how productively capital is being used within the ecosystem.

### **TVL Efficiency** (fees/TVL) has roughly **doubled since 2021**: currently **0.00062** vs. 0.0003 in Q4 2021. DeFi protocols are earning 2x more fees per dollar on liquidity compared to four years ago. This signals structural improvements across with more mature and sophisticated fee tiers (concentrated liquidity, dynamic fees, etc.), broader protocol diversity beyond spot Dexs (lending, perps, prediction markets, valults, etc.), and the growth of higher-margin DeFi categories. TVL efficiency has improved +15.9% YTD, even as TVL and volume declined.

### **Dex Velocity** (vol/TVL) sits at **0.077**, within the normal 0.06-0.10 range. Despite the TVL drawdown, the remaining capital is being actively traded. Given that the current Dex Volume only includes Dexs and prediction markets, but not perps. Examining velocities across DeFi primitives would be an interesting research direction. Limitations of the study, such as Perps volume and CLOB liquidities, are further discussed in [Limitations and Future Analysis](#limitations-and-future-analysis). 

---

# Chain Breakdown

### Nine chains currently hold **TVL above $1B**. Ethereum ($44.2B) dominates but its share has drifted from 60% to 52% over the past 12 months. Below Ethereum, a competitive mid-tier has formed: Solana ($6.0B), BSC ($5.6B), Bitcoin ($5.2B), Tron ($5.1B), and Base ($5.0B) are all clustered in the $5-6B range. Arbitrum ($1.59B), Hyperliquid ($1.53B), and Polygon ($1.18B) follows. 

### **Volume Dominance** tells a different story: Solana makes 32% of DEX volume despite holding only 7% for TVL. Base has also gained volume share at 12%, while Ethereum's share declined from it's 70% heights in 2021 to around 19% since 2025. 

### **Fee Share** is similar, but Hyperliquid stands out as taking the third, with $364M in earnings YTD (9% of DeFi Fee share). Ethereum ecosystem makes $10M (39%) daily, next to Solana at $6M (30%). 

### A divergence between liquidity depth and capital velocity is one of the key features of the current DeFi landscape. Execution-heavy chains such as **Solana** with **0.15 velocity**, **Base** with **0.17**, and **Sui** with **0.14** turn over capital at roughly **3–6x** the rate of Ethereum, which sits around **0.03**. These ecosystems appear to support more frequent trading, shorter holding periods, and more active strategies.

### By contrast, lower-velocity chains such as Ethereum and Tron appear to hold capital more for yield, collateral, settlement, or custody-oriented use cases rather than rapid turnover. Fee efficiency follows a similar but not identical pattern. **Solana** at **0.00097** and **Polygon** at **0.00084**, the latter driven largely by Polymarket. Together, these patterns highlight the coexistence of multiple DeFi models within a maturing ecosystem. 

---

# TVL and Fee Compositions 

### TVL composition reveals how each chain's DeFi capital is allocated. Ethereum's TVL is diversified across Liquid Staking (23%), Lending (17%), Staking Pool (12%), and a growing RWA segment (11%). Solana follows a similar staking-led profile but with more capital in DEX liquidity pools. Base is concentrated in Lending (48%), and Polygon is prediction markets (33.5%). 

### DeFi fees include Dex trading fees, lending interest, derivatives and perps fees, launchpad fees, staking-related fees, and other protocol-level charges, capturing total fees paid by users, including both LP and protocol revenue. Fee composition varies sharply across chains. Ethereum's fees are spread across Liquid Staking (33%), Lending (21%), and CDPs (16%). Solana's $4.9M skews toward Dexs (39%) and Launchpads (23%). Hyperliquid generates half its fees from Derivatives, with another 39% from its Staking Pool. Polygon is almost entirely Prediction Market (95%). A broadening mix of use cases now contributes more meaningfully to fee generation, a sign of maturing on-chain economies rather than trading-only activity.

---

# Limitations and Future Analysis 

### Perps volume is missing. DefiLlama's derivatives volume endpoint is paywalled, so DEX volume only reflects spot trading. This understates activity on perps-heavy chains like Hyperliquid and Arbitrum, and means velocity and fee efficiency are calculated against an incomplete volume base. Adjusted metrics would likely show higher capital efficiency than currently reported.

### CLOB treatment is ambiguous. On-chain CLOBs are partially captured in DEX volume, but resting limit orders from market makers aren't "locked" like AMM LP positions, whether they count as TVL is an open question that affects cross-chain comparisons.

### TVL varies across providers. Allium reports Hyperliquid TVL at ~$3.6B vs. DefiLlama's ~$1.53B. Discrepancies likely stem from differences in methodology, what's counted as bridge balances, margin collateral, vault deposits, or idle funds. 

### Velocity by DeFi primitive. Breaking velocity down by DeFi categories would reveal which primitives are most capital-efficient across chains. This would require more detailed protocol-level TVL and volume matching.

### Active address gaps. DefiLlama covers ~236 protocol adapters, but chains like Hyperliquid and Sui have zero coverage. Address composition analysis (e.g., retail vs. institutional vs. bots, participant-type shifts) would add depth but requires additional sourcing from Dune native tables, Allium, or chain-specific APIs.

---
# Methodology

### Core Metrics

- DeFi TVL: Tokens deposited in DeFi smart contracts, valued at current prices. Includes total adapted DeFi protocols.
- Dex Volume (24h): Trading volume. Includes prediction markets (Polymarket). Excludes perp/derivatives volume (Hyperliquid).
- DeFi Fees (24h): DeFi protocol fees, including DEX trading fees, lending interest, perps/derivatives fees, launchpads, staking, etc. Sums the total fee the user pays (LP + protocol combined).
- OI (Notional): Notional open interest in DeFi protocols. Margins are not directly reported in the Free API, but we later apply 5x to estimate maker liquidity.
- Active Addresses (24h): Daily unique addresses interacting with tracked DeFi protocols. Sourced from DefiLlama's `/overview/active-users` endpoint (~236 protocol adapters). Lower-bound estimate — some major chains (notably Hyperliquid L1 and Sui) have zero adapter coverage.
- Stablecoin Mcap: Circulating supply of USD-stablecoins (USDT, USDC, DAI, etc.).

### Derived Metrics

- TVL Efficiency: Fee / TVL -- Measures fee generation per dollar of adjusted liquidity. Higher values indicate stronger fee efficiency.
- Dex Velocity: Dex Volume (24h) / TVL -- Measures daily capital turnover per dollar of liquidity. Higher values indicate more active liquidity usage.

**Data source**: [DefiLlama](https://defillama.com/) free API -- on-chain DeFi metrics across 200+ chains, powered by community-maintained protocol adapters ([TVL adapters](https://github.com/DefiLlama/DefiLlama-Adapters) · [volume/fees/derivatives adapters](https://github.com/DefiLlama/dimension-adapters)). This dashboard pulls from 16 endpoints across two domains: [api.llama.fi](https://api.llama.fi/) (TVL, DEX volume, fees, open interest, options, active users) and [stablecoins.llama.fi](https://stablecoins.llama.fi/) (stablecoin market cap). See [API docs](https://api-docs.defillama.com/) for details -- we found [llms-free.txt](https://api-docs.defillama.com/llms-free.txt) particularly helpful for development.

**Protocol coverage**: Aggregate metrics include the full DeFi total across 200+ chains. Chain breakdowns cover a curated set of 25 top chains by TVL: Ethereum, Solana, BSC, Bitcoin, Tron, Base, Arbitrum, Hyperliquid L1, Polygon, etc. The sum of chain-level values will be less than the aggregate totals.

**Pipeline**: Data is fetched and uploaded to Dune daily. All derived metrics (velocity, TVL efficiency, etc.) are computed in Dune materialized views. For our pipeline details, ingestion logic, and query source code, see [ghrjeon/defi-analyst](https://github.com/ghrjeon/defi-analyst) on GitHub.

---

# Appendix
## Growth Heatmaps (12 Months)
