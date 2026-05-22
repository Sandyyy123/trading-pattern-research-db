"""ingest.py - load TradingView CSV exports into SQLite."""
import json
import sqlite3
import pandas as pd


def load_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    if "time" in df.columns:
        df["datetime"] = pd.to_datetime(df["time"], unit="s", errors="coerce")
        if df["datetime"].isna().all():
            df["datetime"] = pd.to_datetime(df["time"], errors="coerce")
    df.columns = [c.lower().replace(" ", "_") for c in df.columns]
    return df


def create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS candles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            datetime TEXT NOT NULL,
            open REAL, high REAL, low REAL, close REAL, volume REAL,
            indicators TEXT,
            UNIQUE(symbol, datetime)
        );
        CREATE TABLE IF NOT EXISTS pattern_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candle_id INTEGER REFERENCES candles(id),
            pattern_id TEXT NOT NULL,
            market_regime TEXT,
            trigger_dt TEXT
        );
        CREATE TABLE IF NOT EXISTS outcomes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER REFERENCES pattern_events(id),
            bars_forward INTEGER,
            max_gain_pct REAL,
            max_drawdown_pct REAL,
            close_pct REAL,
            result TEXT
        );
    """)
    conn.commit()


def ingest(csv_path: str, symbol: str, db_path: str = "research.db") -> int:
    df = load_csv(csv_path)
    conn = sqlite3.connect(db_path)
    create_schema(conn)
    core_cols = {"datetime", "open", "high", "low", "close", "volume", "time"}
    indicator_cols = [c for c in df.columns if c not in core_cols]
    rows_inserted = 0
    for _, row in df.iterrows():
        indicators = {c: row[c] for c in indicator_cols if pd.notna(row.get(c))}
        try:
            conn.execute(
                "INSERT OR IGNORE INTO candles "
                "(symbol, datetime, open, high, low, close, volume, indicators) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (symbol, str(row.get("datetime", "")),
                 row.get("open"), row.get("high"), row.get("low"),
                 row.get("close"), row.get("volume"), json.dumps(indicators))
            )
            rows_inserted += 1
        except Exception:
            pass
    conn.commit()
    conn.close()
    return rows_inserted
