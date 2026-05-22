-- NGX Signal Engine — Database Schema Bootstrap
-- Project 04 | Port 5436

-- ── RAW PRICES ──────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS ngx_prices (
    id              SERIAL PRIMARY KEY,
    ticker          TEXT NOT NULL,
    trade_date      DATE NOT NULL,
    open_price      NUMERIC(12, 4),
    high_price      NUMERIC(12, 4),
    low_price       NUMERIC(12, 4),
    close_price     NUMERIC(12, 4) NOT NULL,
    volume          BIGINT,
    market          TEXT DEFAULT 'NGX',
    ingested_at     TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (ticker, trade_date)
);

CREATE TABLE IF NOT EXISTS global_prices (
    id              SERIAL PRIMARY KEY,
    ticker          TEXT NOT NULL,
    trade_date      DATE NOT NULL,
    open_price      NUMERIC(12, 4),
    high_price      NUMERIC(12, 4),
    low_price       NUMERIC(12, 4),
    close_price     NUMERIC(12, 4) NOT NULL,
    volume          BIGINT,
    market          TEXT NOT NULL,
    ingested_at     TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (ticker, trade_date)
);

-- ── COMPUTED INDICATORS ──────────────────────────────────────

CREATE TABLE IF NOT EXISTS price_indicators (
    id              SERIAL PRIMARY KEY,
    ticker          TEXT NOT NULL,
    trade_date      DATE NOT NULL,
    market          TEXT NOT NULL,
    pct_change_1d   NUMERIC(8, 4),
    pct_change_5d   NUMERIC(8, 4),
    sma_10          NUMERIC(12, 4),
    sma_20          NUMERIC(12, 4),
    ema_10          NUMERIC(12, 4),
    ema_20          NUMERIC(12, 4),
    rsi_14          NUMERIC(8, 4),
    volume_change   NUMERIC(8, 4),
    computed_at     TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (ticker, trade_date, market)
);

-- ── SIGNAL LOG ───────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS signals (
    id              SERIAL PRIMARY KEY,
    ticker          TEXT NOT NULL,
    trade_date      DATE NOT NULL,
    signal          TEXT NOT NULL CHECK (signal IN ('BUY', 'SELL', 'HOLD')),
    signal_strength NUMERIC(5, 2),
    triggered_rules TEXT[],
    close_price     NUMERIC(12, 4),
    rsi_14          NUMERIC(8, 4),
    sma_crossover   BOOLEAN,
    volume_spike    BOOLEAN,
    generated_at    TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (ticker, trade_date)
);

-- ── LLM EXPLANATIONS ────────────────────────────────────────

CREATE TABLE IF NOT EXISTS signal_explanations (
    id              SERIAL PRIMARY KEY,
    signal_id       INTEGER REFERENCES signals(id) ON DELETE CASCADE,
    ticker          TEXT NOT NULL,
    trade_date      DATE NOT NULL,
    llm_model       TEXT DEFAULT 'gemini-2.5-flash',
    explanation     TEXT,
    conviction     TEXT,            -- High / Medium / Low
    risk_flag       TEXT CHECK (risk_flag IN ('LOW', 'MEDIUM', 'HIGH')),
    risk_reasoning  TEXT,
    prompt_tokens   INTEGER,
    generated_at    TIMESTAMPTZ DEFAULT NOW()
);

-- ── BACKTEST ─────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS backtest_runs (
    id              SERIAL PRIMARY KEY,
    run_name        TEXT NOT NULL,
    ticker          TEXT NOT NULL,
    start_date      DATE NOT NULL,
    end_date        DATE NOT NULL,
    strategy_config JSONB,
    total_trades    INTEGER,
    win_rate        NUMERIC(6, 4),
    avg_return_pct  NUMERIC(8, 4),
    max_drawdown    NUMERIC(8, 4),
    sharpe_ratio    NUMERIC(8, 4),
    run_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS backtest_trades (
    id              SERIAL PRIMARY KEY,
    run_id          INTEGER REFERENCES backtest_runs(id) ON DELETE CASCADE,
    ticker          TEXT NOT NULL,
    entry_date      DATE NOT NULL,
    exit_date       DATE,
    entry_price     NUMERIC(12, 4),
    exit_price      NUMERIC(12, 4),
    return_pct      NUMERIC(8, 4),
    signal_at_entry TEXT CHECK (signal_at_entry IN ('BUY', 'SELL', 'HOLD')),
    outcome         TEXT CHECK (outcome IN ('WIN', 'LOSS', 'OPEN'))
);

-- ── AUDIT ────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS ingest_audit (
    id              SERIAL PRIMARY KEY,
    source          TEXT NOT NULL,
    tickers_loaded  TEXT[],
    rows_inserted   INTEGER,
    rows_skipped    INTEGER,
    errors          TEXT[],
    run_at          TIMESTAMPTZ DEFAULT NOW()
);

-- ── PORTFOLIO ────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS portfolio_positions (
    id              SERIAL PRIMARY KEY,
    run_date        DATE NOT NULL,
    ticker          TEXT NOT NULL,
    signal          TEXT NOT NULL,
    score           NUMERIC(8, 2),
    weight          NUMERIC(8, 4),
    close_price     NUMERIC(12, 4),
    conviction      TEXT,            -- from LLM: High / Medium / Low
    risk_flag       TEXT,            -- from LLM: LOW / MEDIUM / HIGH
    excluded        BOOLEAN DEFAULT FALSE,
    exclusion_reason TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (run_date, ticker)
);

CREATE INDEX IF NOT EXISTS idx_portfolio_run_date ON portfolio_positions (run_date DESC);

-- ── INDEXES ──────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_ngx_prices_ticker_date    ON ngx_prices (ticker, trade_date DESC);
CREATE INDEX IF NOT EXISTS idx_global_prices_ticker_date ON global_prices (ticker, trade_date DESC);
CREATE INDEX IF NOT EXISTS idx_signals_ticker_date       ON signals (ticker, trade_date DESC);
CREATE INDEX IF NOT EXISTS idx_signals_signal            ON signals (signal);
CREATE INDEX IF NOT EXISTS idx_backtest_trades_run       ON backtest_trades (run_id);
CREATE INDEX IF NOT EXISTS idx_indicators_ticker_date    ON price_indicators (ticker, trade_date DESC);
