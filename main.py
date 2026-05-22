"""main.py - CLI entry point for the trading pattern research pipeline."""
import argparse
from ingest import ingest
from scanner import scan, load_patterns
from stats import track_outcomes, compute_edge_report


def main():
    parser = argparse.ArgumentParser(description="Trading Pattern Research Database")
    parser.add_argument("--csv", required=True, help="TradingView CSV export path")
    parser.add_argument("--symbol", default="ASSET", help="Symbol name e.g. BTCUSD")
    parser.add_argument("--patterns", default="patterns.yaml", help="Pattern config YAML")
    parser.add_argument("--db", default="research.db", help="SQLite database path")
    parser.add_argument("--window", type=int, default=10, help="Forward bars for outcome")
    parser.add_argument("--out", default="edge_report.csv", help="Output CSV path")
    args = parser.parse_args()

    print(f"[1/4] Ingesting {args.csv} ...")
    n = ingest(args.csv, args.symbol, args.db)
    print(f"      {n} candles loaded")

    print(f"[2/4] Loading patterns from {args.patterns} ...")
    patterns = load_patterns(args.patterns)
    print(f"      {len(patterns)} patterns defined")

    print(f"[3/4] Scanning for pattern events ...")
    events = scan(args.db, args.symbol, patterns)
    print(f"      {events} events detected")

    print(f"[4/4] Computing edge statistics (window={args.window}) ...")
    track_outcomes(args.db, args.symbol)
    report = compute_edge_report(args.db, window=args.window)
    report.to_csv(args.out, index=False)
    print(f"\nEdge report -> {args.out}")
    print(report.to_string(index=False))


if __name__ == "__main__":
    main()
