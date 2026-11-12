"""Paired CVRPTW experiments: baseline, new ILS and component ablations."""
import os
for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMBA_NUM_THREADS"):
    os.environ[key] = "1"
import argparse
import hashlib
import json
import multiprocessing as mp
from pathlib import Path
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import psutil
from algo.data import load
from algo.iterated import construct
from algo.optimized import solve as baseline_solve
from algo.profiles import production_settings
from algo.ils_rvnd import Settings, solve, warmup
from algo.verify import verify
from algo.relay import Settings as RelaySettings, solve as relay_solve
from web.experiments import atomic_json, read_json


def initialize(cpus):
    psutil.Process().cpu_affinity([cpus[(mp.current_process()._identity[0] - 1) % len(cpus)]])
    warmup()


def execute(job):
    name, seed, variant, seconds, folder = job
    path = Path(folder) / "runs" / f"{name}_{seed}_{variant}.json"
    if path.exists():
        record = read_json(path)
        if record.get("complete"):
            return dict(instance=name, seed=seed, variant=variant, resumed=True)
        raise RuntimeError("Incomplete existing run; use a new campaign")
    record = dict(instance=name, seed=seed, variant=variant, budget_s=seconds)
    try:
        ins = load(ROOT / "data/instances" / (name + ".vrp"))
        initial, construction = construct(ins, seed, 12)
        if initial is None:
            raise RuntimeError("Construction failed")
        record.update(initial_routes=initial, construction=construction)
        if variant in ("relay", "polished"):
            result = relay_solve(ins, RelaySettings(seconds=seconds, seed=seed,
                                 ils_fraction=.8 if variant == "polished" else .25,
                                 polish_rvnd=variant == "polished"), initial)
        elif variant in ("baseline_ils", "baseline_sa", "light", "wide", "long_sub", "short_sub"):
            parameters = {"light": dict(perturbation_strength=1),
                          "wide": dict(neighbor_count=64),
                          "long_sub": dict(sub_seconds=.6),
                          "short_sub": dict(sub_seconds=.05)}.get(variant, {})
            method = "sa" if variant == "baseline_sa" else "ils"
            result = baseline_solve(ins, production_settings(method, seconds=seconds, seed=seed, **parameters), initial)
        else:
            result = solve(ins, Settings(seconds=seconds, seed=seed,
                                         adaptive=variant != "fixed",
                                         blocks=variant != "no_blocks"), initial)
        checked = verify(result["routes"], ins)
        if not checked["valid"] or abs(checked["distance"] / 10 - result["cost"]) > 1e-7:
            raise AssertionError(checked)
        reference = next(r["reference_distance"] for r in read_json(ROOT / "data/manifest.json")["reference_instances"] if r["instance"] == name)
        record.update(valid=True, complete=True, result=result,
                      gap_pct=100 * (result["cost"] / reference - 1),
                      total_s=construction["seconds"] + result["runtime_s"])
    except Exception:
        record.update(valid=False, complete=True, error=traceback.format_exc())
    atomic_json(path, record)
    return dict(instance=name, seed=seed, variant=variant, valid=record["valid"], gap=record.get("gap_pct"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--role", choices=["development", "validation"], required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--seconds", type=float, default=20)
    parser.add_argument("--seeds", type=int, nargs="+", default=[1301, 1302])
    parser.add_argument("--variants", nargs="+", default=["baseline_ils", "rvnd", "fixed", "no_blocks"])
    args = parser.parse_args()
    if not set(args.variants) <= {"baseline_ils", "baseline_sa", "rvnd", "fixed", "no_blocks", "relay", "polished", "light", "wide", "long_sub", "short_sub"}:
        parser.error("Unknown variant")
    Settings(seconds=args.seconds)
    suffixes = [2] if args.role == "development" else [3, 4]
    names = [f"{f}_10_{i}" for f in ["C1", "C2", "R1", "R2", "RC1", "RC2"] for i in suffixes]
    label = args.label or args.role
    if not label.replace('_', '').isalnum():
        parser.error("Invalid campaign label")
    folder = ROOT / "results/optimization_v5" / label
    folder.mkdir(parents=True, exist_ok=True)
    sources = [ROOT / "algo" / (name + ".py") for name in
               ["data", "direct", "intensify", "iterated", "kernels", "model", "optimized", "profiles", "rvnd", "ils_rvnd", "relay", "verify"]]
    sources += [Path(__file__)]
    protocol = dict(role=args.role, instances=names, seeds=args.seeds, variants=args.variants,
                    seconds=args.seconds, workers=6,
                    sources={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
                    manifest_sha256=hashlib.sha256((ROOT / "data/manifest.json").read_bytes()).hexdigest(),
                    objective="DIMACS distance, capacity and strict time windows; fleet upper bound",
                    pairing="Identical deterministic initial construction per instance/seed, charged separately for every run",
                    reference="Read only after solving; never passed to search",
                    warmup="Compiled kernels preheated outside search budget",
                    python=sys.version)
    if (folder / "protocol.json").exists() and read_json(folder / "protocol.json") != protocol:
        raise RuntimeError("Frozen protocol differs")
    atomic_json(folder / "protocol.json", protocol)
    for p in sources:
        target = folder / "source" / p.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(p.read_bytes())
    jobs = [(name, seed, variant, args.seconds, str(folder)) for name in names for seed in args.seeds for variant in args.variants]
    cpus = psutil.Process().cpu_affinity()[::2][:6]
    with mp.get_context("spawn").Pool(len(cpus), initializer=initialize, initargs=(cpus,)) as pool:
        for item in pool.imap_unordered(execute, jobs):
            print(json.dumps(item), flush=True)


if __name__ == "__main__":
    main()
