"""Kommandozeile: `python -m dynpricing.cli run [--as-of YYYY-MM-DD]`."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import date

from .config import CONFIG_PATH, Paths, load_config
from .db import connect, store_raw, store_run
from .historical_data import event_nights
from .pipeline import run
from .reporting import plan_rows, revenue_summary, write_calendar_csv, write_plan_csv, write_ranges_csv, write_report, write_strategy_json
from .validation import backtest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="dynpricing")
    sub = parser.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="Pricing-Kalender, Strategie und Report erzeugen")
    r.add_argument("--as-of", type=date.fromisoformat, default=date.today())
    r.add_argument("--config", default=str(CONFIG_PATH))
    r.add_argument("--no-db", action="store_true")
    args = parser.parse_args(argv)

    paths = Paths()
    cfg = load_config(args.config)
    result = run(args.as_of, cfg, paths)

    write_calendar_csv(result, paths.output / "pricing_calendar_12m.csv")
    s = write_strategy_json(result, paths.output / "strategy.json")
    by_year: dict[int, list[dict]] = {}
    for a, b in cfg["regulation"].get("rental_windows", []):
        start, end = max(date.fromisoformat(a), args.as_of), date.fromisoformat(b)
        if start <= end:
            by_year.setdefault(start.year, []).extend(plan_rows(result, start, end))
    for year, rows in by_year.items():
        write_plan_csv(rows, paths.output / f"preisplan_{year}.csv")
        write_ranges_csv(rows, paths.output / f"airbnb_eingabe_{year}.csv")
    rev = revenue_summary(result)
    (paths.output / "umsatzprognose.json").write_text(json.dumps(rev, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(result, s, paths.reports / "pricing_report.md")

    if result.history:
        bt = backtest({p.demand.day: p.static_price for p in result.prices}, result.history, event_nights(result.events))
        if bt:
            (paths.output / "backtest.json").write_text(json.dumps(asdict(bt), default=str, indent=2), encoding="utf-8")

    if not args.no_db:
        con = connect(paths.processed / "pricing.db")
        store_raw(con, result.events, result.metrics, cfg["property"]["lat"], cfg["property"]["lon"])
        store_run(con, args.as_of.isoformat(), result.bands.base, json.dumps(cfg, default=str), result.prices)
        con.close()

    print(f"Basispreis {s['basispreis']} EUR | Wochentag {s['normaler_wochentagspreis_mo_do']} | "
          f"Wochenende {s['normaler_wochenendpreis_fr_sa']} | Min {s['preisgrenzen']['Minimum Price']} | "
          f"Max {s['preisgrenzen']['Maximum Price']}")
    print(f"Kalender: {paths.output / 'pricing_calendar_12m.csv'}")
    print(f"Report:   {paths.reports / 'pricing_report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
