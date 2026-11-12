"""Explicit three-search command; never label it as a single short resolution."""

from pathlib import Path
import argparse, json, sys, time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from algo.data import load
from algo.portfolio_v6 import Settings, solve
from algo.cached_iterated import warmup

if __name__ == "__main__":
    p = argparse.ArgumentParser(
        description="CVRPTW : trois ILS complètes et combinaison de tournées"
    )
    p.add_argument("instance")
    p.add_argument("--seconds-per-search", type=float, default=40)
    p.add_argument("--partition-seconds", type=float, default=2)
    p.add_argument("--seed", type=int, default=1801)
    p.add_argument("--output", default="results/local/portfolio_v6.json")
    a = p.parse_args()
    cfg = Settings(a.seconds_per_search, a.partition_seconds, a.seed)
    path = Path(a.instance)
    if not path.exists():
        path = ROOT / "data/instances" / (a.instance + ".vrp")
    start = time.perf_counter()
    warmup()
    startup = time.perf_counter() - start
    result = solve(load(path), cfg)
    result["warmup_s"] = startup
    out = ROOT / a.output
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    print(
        json.dumps(
            dict(
                status=result["status"],
                distance=result.get("cost"),
                runtime_s=result["runtime_s"],
                search_budgets=f"3 x {a.seconds_per_search} seconds",
                output=str(out),
            ),
            ensure_ascii=False,
        )
    )
