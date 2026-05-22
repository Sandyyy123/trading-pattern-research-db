# Trading Pattern Research Database

A structured research framework to identify statistically significant trading edges from TradingView historical exports.

## What it does

- Ingests TradingView CSV exports (OHLCV + indicators) into SQLite
- Scans for configurable pattern conditions (YAML-driven)
- Tracks forward outcomes (N-bar gain/drawdown) for every pattern event
- Computes win rate, expectancy, profit factor, and p-value per pattern
- Segments results by market regime (trending vs ranging vs volatile)

## Architecture

```
TradingView CSV  ->  ingest.py  ->  SQLite DB (candles + events + outcomes)
patterns.yaml    ->  scanner.py ->  pattern_events table
                     stats.py   ->  edge_report.csv
```

## Setup

```bash
pip install -r requirements.txt
python main.py --csv data/BTCUSD_1D.csv --symbol BTCUSD --patterns patterns.yaml
```

## Output

| Pattern | Occurrences | Win Rate | Expectancy | p-value | Edge |
|---------|-------------|----------|------------|---------|------|
| RSI30 + ATR expansion | 84 | 67% | +0.91% | 0.003 | Confirmed |
| MA crossover high volume | 112 | 54% | +0.15% | 0.41 | Marginal |

## Author
Dr. Sandeep Grover - PhD Data Science
