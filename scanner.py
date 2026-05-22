"""scanner.py - detect pattern events from candles table."""
import json
import sqlite3
import yaml
import pandas as pd
from typing import Any


def load_patterns(yaml_path: str) -> list:
    with open(yaml_path) as f:
        return yaml.safe_load(f)["patterns"]


def classify_regime(df: pd.DataFrame, idx: int, lookback: int = 20) -> str:
    if idx < lookback:
        return "unknown"
    window = df["close"].iloc[idx - lookback:idx]
    mean = window.mean()
    std = window.std()
    close = df["close"].iloc[idx]
    if close > mean + 0.5 * std:
        return "uptrend"
    elif close < mean - 0.5 * std:
        return "downtrend"
    return "ranging"


def eval_condition(df: pd.DataFrame, idx: int, cond: dict) -> bool:
    indicator = cond["indicator"]
    if indicator not in df.columns:
        return False
    val = df[indicator].iloc[idx]
    prev_val = df[indicator].iloc[idx - 1] if idx > 0 else None

    if "crosses_above" in cond and prev_val is not None:
        return prev_val < cond["crosses_above"] <= val

    if "crosses_above_col" in cond and prev_val is not None:
        col = cond["crosses_above_col"]
        if col not in df.columns:
            return False
        col_val = df[col].iloc[idx]
        col_prev = df[col].iloc[idx - 1]
        return prev_val < col_prev and val >= col_val

    if "greater_than" in cond:
        return val > cond["greater_than"]

    if "greater_than_col" in cond:
        col = cond["greater_than_col"]
        return col in df.columns and val > df[col].iloc[idx]

    if "greater_than_rolling_multiple" in cond:
        cfg = cond["greater_than_rolling_multiple"]
        col = cfg.get("col", indicator)
        window = cfg.get("window", 20)
        mult = cfg.get("multiplier", 1.0)
        if col not in df.columns or idx < window:
            return False
        rolling_mean = df[col].iloc[idx - window:idx].mean()
        return val > rolling_mean * mult

    return False


def scan(db_path: str, symbol: str, patterns: list) -> int:
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        "SELECT id, datetime, open, high, low, close, volume, indicators "
        "FROM candles WHERE symbol=? ORDER BY datetime",
        (symbol,)
    ).fetchall()
    if not rows:
        conn.close()
        return 0

    ids = [r[0] for r in rows]
    records = []
    for r in rows:
        d = {"datetime": r[1], "open": r[2], "high": r[3],
             "low": r[4], "close": r[5], "volume": r[6]}
        try:
            d.update(json.loads(r[7] or "{}"))
        except Exception:
            pass
        records.append(d)
    df = pd.DataFrame(records)

    events_inserted = 0
    for pat in patterns:
        pat_id = pat["id"]
        regime_filter = pat.get("regime_filter")
        for i in range(1, len(df)):
            if not all(eval_condition(df, i, c) for c in pat["conditions"]):
                continue
            regime = classify_regime(df, i)
            if regime_filter and regime != regime_filter:
                continue
            conn.execute(
                "INSERT INTO pattern_events (candle_id, pattern_id, market_regime, trigger_dt) "
                "VALUES (?, ?, ?, ?)",
                (ids[i], pat_id, regime, df["datetime"].iloc[i])
            )
            events_inserted += 1
    conn.commit()
    conn.close()
    return events_inserted
