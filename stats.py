"""stats.py - compute edge statistics per pattern."""
import sqlite3
import pandas as pd
from scipy import stats


def track_outcomes(db_path: str, symbol: str,
                   windows: list = None, win_threshold_pct: float = 1.0) -> None:
    if windows is None:
        windows = [5, 10, 20]
    conn = sqlite3.connect(db_path)
    candles = pd.read_sql(
        "SELECT id, datetime, close FROM candles WHERE symbol=? ORDER BY datetime",
        conn, params=(symbol,)
    )
    id_to_idx = {row.id: i for i, row in candles.iterrows()}
    events = pd.read_sql("SELECT id, candle_id FROM pattern_events", conn)

    for _, ev in events.iterrows():
        idx = id_to_idx.get(ev.candle_id)
        if idx is None:
            continue
        entry = candles.iloc[idx]["close"]
        for w in windows:
            end_idx = min(idx + w, len(candles) - 1)
            fwd = candles.iloc[idx + 1:end_idx + 1]["close"]
            if fwd.empty:
                continue
            max_gain = ((fwd.max() - entry) / entry) * 100
            max_dd = ((fwd.min() - entry) / entry) * 100
            close_pct = ((candles.iloc[end_idx]["close"] - entry) / entry) * 100
            result = (
                "win" if close_pct >= win_threshold_pct
                else "loss" if close_pct <= -win_threshold_pct
                else "breakeven"
            )
            conn.execute(
                "INSERT INTO outcomes "
                "(event_id, bars_forward, max_gain_pct, max_drawdown_pct, close_pct, result) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (ev.id, w, max_gain, max_dd, close_pct, result)
            )
    conn.commit()
    conn.close()


def compute_edge_report(db_path: str, window: int = 10) -> pd.DataFrame:
    conn = sqlite3.connect(db_path)
    df = pd.read_sql("""
        SELECT pe.pattern_id, pe.market_regime,
               o.close_pct, o.max_gain_pct, o.max_drawdown_pct, o.result
        FROM outcomes o
        JOIN pattern_events pe ON o.event_id = pe.id
        WHERE o.bars_forward = ?
    """, conn, params=(window,))
    conn.close()

    rows = []
    for pat_id, grp in df.groupby("pattern_id"):
        n = len(grp)
        wins = (grp["result"] == "win").sum()
        losses = (grp["result"] == "loss").sum()
        win_rate = wins / n if n > 0 else 0
        avg_gain = grp.loc[grp["result"] == "win", "close_pct"].mean() if wins > 0 else 0
        avg_loss = grp.loc[grp["result"] == "loss", "close_pct"].mean() if losses > 0 else 0
        expectancy = win_rate * avg_gain + (1 - win_rate) * avg_loss
        p_val = stats.binomtest(int(wins), n, p=0.5).pvalue if n > 0 else 1.0
        if n < 10:
            edge = "Needs more data"
        elif p_val < 0.05 and n >= 30:
            edge = "Confirmed"
        elif p_val < 0.15:
            edge = "Marginal"
        else:
            edge = "Noise"
        rows.append({
            "pattern_id": pat_id, "n_occurrences": n,
            "win_rate_pct": round(win_rate * 100, 1),
            "avg_gain_pct": round(avg_gain, 2),
            "avg_loss_pct": round(avg_loss, 2),
            "expectancy_pct": round(expectancy, 3),
            "p_value": round(p_val, 4),
            "edge": edge
        })
    return pd.DataFrame(rows).sort_values("expectancy_pct", ascending=False)
