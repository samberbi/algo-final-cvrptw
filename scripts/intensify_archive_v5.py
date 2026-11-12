"""Improve the higher-effort archive; charge its full previous generation cost."""
import os
for key in ["OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMBA_NUM_THREADS"]: os.environ[key] = "1"
from pathlib import Path
import json
import sys
import hashlib
import multiprocessing as mp
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import psutil
from algo.data import load
from algo.relay import Settings, solve
from algo.optimized import warmup
from algo.verify import verify
from web.experiments import read_json, atomic_json


def initialize(cpus):
    psutil.Process().cpu_affinity([cpus[(mp.current_process()._identity[0] - 1) % len(cpus)]])
    warmup()


def run(name):
    folder = ROOT / "results/optimization_v5/portfolio_intensified"
    target = folder / (name + ".json")
    if target.exists(): return read_json(target)
    source = ROOT / "results/optimization_v5/portfolio" / (name + ".json")
    previous = read_json(source)
    ins = load(ROOT / "data/instances" / (name + ".vrp"))
    result = solve(ins, Settings(seconds=60, seed=1501, ils_fraction=1/3), previous["result"]["routes"])
    check = verify(result["routes"], ins)
    assert check["valid"] and result["cost"] <= previous["result"]["cost"] + 1e-7
    reference = next(r["reference_distance"] for r in read_json(ROOT / "data/manifest.json")["reference_instances"] if r["instance"] == name)
    record = dict(instance=name, source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                  previous_gap=previous["gap_pct"], gap_pct=100*(result["cost"]/reference-1),
                  result=result, total_effort_s=previous["total_effort_s"] + result["runtime_s"],
                  scope="Higher-effort archive with one intensification per instance; not independent repeated-run statistics")
    atomic_json(target, record)
    print(name, round(previous["gap_pct"],3), "->", round(record["gap_pct"],3), flush=True)
    return record


if __name__ == "__main__":
    names = read_json(ROOT / "results/optimization_v5/validation/protocol.json")["instances"]
    folder = ROOT / "results/optimization_v5/portfolio_intensified"
    atomic_json(folder / "protocol.json", dict(instances=names, seconds=60, seed=1501,
        ils_fraction=1/3, source_generation="All 16 eligible trajectories per instance, then restricted partitioning; full previous effort charged",
        sources={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in [ROOT/"algo/relay.py", ROOT/"algo/optimized.py", ROOT/"algo/iterated.py", ROOT/"algo/profiles.py", Path(__file__)]}))
    cpus = psutil.Process().cpu_affinity()[::2][:6]
    with mp.get_context("spawn").Pool(len(cpus), initializer=initialize, initargs=(cpus,)) as pool:
        rows = list(pool.imap_unordered(run, names))
    import pandas as pd
    frame = pd.DataFrame([{k:r[k] for k in ["instance", "previous_gap", "gap_pct", "total_effort_s"]} for r in rows])
    frame.to_csv(folder / "summary.csv", index=False)
    atomic_json(folder / "analysis.json", dict(instances=len(rows), intensifications=len(rows),
        mean_gap=float(frame.gap_pct.mean()), worst_gap=float(frame.gap_pct.max()),
        mean_effort_s=float(frame.total_effort_s.mean()),
        scope="One combined archive per instance, not a mean of independent 40-second runs"))
