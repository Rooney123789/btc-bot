"""
BTC 5-Min ML Trading Bot - Configuration.

Central config for all modules. No secrets in this file.
"""

from pathlib import Path

# Paths
PROJECT_ROOT: Path = Path(__file__).resolve().parent
LOGS_DIR: Path = PROJECT_ROOT / "logs"
MODEL_DIR: Path = PROJECT_ROOT / "models"
DB_PATH: Path = PROJECT_ROOT / "btc_bot.db"

# Binance
BINANCE_BASE_URL: str = "https://api.binance.com"
BINANCE_SYMBOL: str = "BTCUSDT"
BINANCE_INTERVAL: str = "5m"
BINANCE_KLINES_LIMIT: int = 1000  # Max per request

# Polymarket
POLYMARKET_GAMMA_URL: str = "https://gamma-api.polymarket.com"
POLYMARKET_CLOB_URL: str = "https://clob.polymarket.com"
POLYMARKET_BTC_5M_SLUG_PATTERN: str = "btc-updown-5m"

# Risk (used in backtest & execution)
MAX_TRADE_USD: float = 10.0
MAX_RISK_PCT: float = 0.10
EDGE_THRESHOLD: float = 0.06
CONSECUTIVE_LOSS_STOP: int = 2
DAILY_DRAWDOWN_CAP_PCT: float = 0.10
INITIAL_BALANCE: float = 100.0

# Database
DB_INIT_SQL: str = """
CREATE TABLE IF NOT EXISTS binance_klines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    open_time_ms BIGINT NOT NULL,
    open REAL NOT NULL,
    high REAL NOT NULL,
    low REAL NOT NULL,
    close REAL NOT NULL,
    volume REAL NOT NULL,
    close_time_ms BIGINT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(open_time_ms)
);

CREATE TABLE IF NOT EXISTS polymarket_prices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    market_id TEXT NOT NULL,
    slug TEXT,
    yes_token_id TEXT,
    no_token_id TEXT,
    yes_price REAL,
    no_price REAL,
    resolution_time_utc TEXT,
    open_time_ms BIGINT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(market_id, open_time_ms)
);

CREATE INDEX IF NOT EXISTS idx_binance_open_time ON binance_klines(open_time_ms);
CREATE INDEX IF NOT EXISTS idx_poly_market_time ON polymarket_prices(open_time_ms);
CREATE INDEX IF NOT EXISTS idx_poly_slug ON polymarket_prices(slug);
"""
