-- defi-analyst schema
-- Run in Supabase SQL Editor (Dashboard → SQL → New Query)

-- Aggregate daily DeFi metrics (one row per date)
CREATE TABLE defi_daily (
    date             DATE NOT NULL PRIMARY KEY,
    tvl              DOUBLE PRECISION,
    dex_volume       DOUBLE PRECISION,
    fees             DOUBLE PRECISION,
    stablecoin_mcap  DOUBLE PRECISION,
    options_volume   DOUBLE PRECISION,
    open_interest    DOUBLE PRECISION,
    active_addresses DOUBLE PRECISION,
    fetched_at       TIMESTAMPTZ NOT NULL
);

CREATE INDEX idx_defi_daily_date ON defi_daily (date DESC);

-- Per-chain daily metrics (one row per date+chain)
CREATE TABLE defi_chain_daily (
    date             DATE NOT NULL,
    chain            TEXT NOT NULL,
    tvl              DOUBLE PRECISION,
    dex_volume       DOUBLE PRECISION,
    fees             DOUBLE PRECISION,
    stablecoin_mcap  DOUBLE PRECISION,
    open_interest    DOUBLE PRECISION,
    active_addresses DOUBLE PRECISION,
    fetched_at       TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (date, chain)
);

CREATE INDEX idx_chain_daily_chain ON defi_chain_daily (chain, date DESC);

-- Category breakdown snapshot (latest values, upserted each refresh)
CREATE TABLE defi_chain_category (
    chain            TEXT NOT NULL,
    metric           TEXT NOT NULL,
    category         TEXT NOT NULL,
    total24h         DOUBLE PRECISION,
    total7d          DOUBLE PRECISION,
    protocol_count   INTEGER,
    fetched_at       TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (chain, metric, category)
);

-- Audit trail
CREATE TABLE ingestion_log (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source          TEXT NOT NULL,
    target_table    TEXT NOT NULL,
    records_total   INT NOT NULL,
    records_new     INT NOT NULL,
    records_skipped INT NOT NULL,
    ingested_at     TIMESTAMPTZ DEFAULT NOW(),
    duration_ms     INT
);
