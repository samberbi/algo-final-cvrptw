"""Measured development and balanced validation, with immutable raw records."""

import os

for key in (
    "OMP_NUM_THREADS",
    "NUMBA_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
):
    os.environ[key] = "1"
from pathlib import Path
import argparse
import hashlib
import importlib
import json
import multiprocessing as mp
import random
import shutil
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import psutil
from algo.data import load
from algo.optimized import Settings, construct, solve, warmup
from algo.verify import verify
from web.experiments import atomic_json, read_json

FAMILIES = ["C1", "C2", "R1", "R2", "RC1", "RC2"]
DEVELOPMENT = {
    "ils_groups": dict(method="ils"),
    "ils_swap_star": dict(method="ils", swap_star=True),
    "ils_temporal": dict(method="ils", neighbor_mode="mixed"),
    "ils_groups240": dict(method="ils", group_size=240),
    "sa_edge": dict(method="sa"),
    "sa_total": dict(method="sa", temperature_mode="total", temperature_ratio=0.02),
}
OUT = None
CONFIGS = None
FROZEN = None


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def initialize(cpus, folder, configs, baseline):
    global OUT, CONFIGS, FROZEN
    OUT, CONFIGS = Path(folder), configs
    index = (mp.current_process()._identity[0] - 1) % len(cpus)
    psutil.Process().cpu_affinity([cpus[index]])
    warmup()
    if baseline:
        FROZEN = importlib.import_module("results.revision_ils.source.algo.iterated")
        FROZEN.warmup()


def execute(job):
    initial_path = OUT / "initials" / f"{job['id']:04d}.json"
    targets = {
        variant: OUT / "runs" / f"{job['id']:04d}_{variant}.json"
        for variant in job["variants"]
    }
    if all(p.exists() for p in targets.values()):
        return dict(id=job["id"], reused=True)
    ins = load(ROOT / "data/instances" / (job["instance"] + ".vrp"))
    if initial_path.exists():
        initial = read_json(initial_path)
    else:
        routes, info = construct(ins, job["seed"], 12)
        initial = dict(job=job, routes=routes, info=info)
        atomic_json(initial_path, initial)
    order = job["variants"][:]
    random.Random(job["id"] + 1931).shuffle(order)
    for variant in order:
        if targets[variant].exists():
            continue
        valid = False
        gap = None
        try:
            if initial["routes"] is None:
                result = dict(
                    status="not_found",
                    reason="Construction failed",
                    routes=None,
                    runtime_s=0.0,
                )
            elif variant == "baseline_ils":
                result = FROZEN.solve(
                    ins,
                    FROZEN.Settings(seconds=job["seconds"], seed=job["seed"]),
                    initial["routes"],
                )
            else:
                result = solve(
                    ins,
                    Settings(
                        seconds=job["seconds"], seed=job["seed"], **CONFIGS[variant]
                    ),
                    initial["routes"],
                )
            if job.get("continuation_seconds", 0) and result["status"] == "feasible":
                first = result
                continued = solve(
                    ins,
                    Settings(
                        seconds=job["continuation_seconds"],
                        seed=job["seed"] + 700000,
                        **CONFIGS[variant],
                    ),
                    first["routes"],
                )
                assert (
                    continued["status"] == "feasible"
                    and continued["cost"] <= first["cost"] + 1e-7
                )
                result = dict(continued)
                result["stages"] = [first, continued]
                result["initial_cost"] = first["initial_cost"]
                result["trace"] = first["trace"] + [
                    dict(point, elapsed_s=first["runtime_s"] + point["elapsed_s"])
                    for point in continued["trace"]
                ]
                result["runtime_s"] = first["runtime_s"] + continued["runtime_s"]
                result["cpu_s"] = first.get("cpu_s", 0) + continued.get("cpu_s", 0)
                for key in [
                    "iterations",
                    "cycles",
                    "accepted",
                    "valid_proposals",
                    "improved",
                ]:
                    result[key] = first.get(key, 0) + continued.get(key, 0)
                result["diagnostics"] = {
                    key: first.get("diagnostics", {}).get(key, 0)
                    + continued.get("diagnostics", {}).get(key, 0)
                    for key in set(first.get("diagnostics", {}))
                    | set(continued.get("diagnostics", {}))
                }
                result["operators"] = [
                    a + b
                    for a, b in zip(
                        first.get("operators", [0] * 4),
                        continued.get("operators", [0] * 4),
                    )
                ]
            if result["status"] == "feasible":
                checked = verify(result["routes"], ins)
                assert (
                    checked["valid"]
                    and abs(checked["distance"] / 10 - result["cost"]) < 1e-7
                )
                valid = True
                gap = 100 * (result["cost"] / job["reference_distance"] - 1)
            record = dict(
                job=dict(job, variant=variant),
                result=result,
                valid=valid,
                gap_pct=gap,
                reference_distance=job["reference_distance"],
                initial=initial["info"],
                initial_routes_sha256=hashlib.sha256(
                    json.dumps(initial["routes"]).encode()
                ).hexdigest(),
                total_s=result["runtime_s"] + initial["info"]["seconds"],
                cpu_affinity=psutil.Process().cpu_affinity(),
            )
        except Exception as exc:
            record = dict(
                job=dict(job, variant=variant),
                valid=False,
                gap_pct=None,
                result=dict(
                    status="error",
                    reason=str(exc),
                    traceback=traceback.format_exc(),
                    runtime_s=0.0,
                ),
            )
        atomic_json(targets[variant], record)
    return dict(
        id=job["id"], instance=job["instance"], seed=job["seed"], completed=len(order)
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--stage",
        choices=["development", "adaptive", "validation", "regression"],
        required=True,
    )
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--cpu-offset", type=int, default=0)
    args = parser.parse_args()
    out = ROOT / "results/optimization_v2" / args.stage
    out.mkdir(parents=True, exist_ok=True)
    refs = {
        r["instance"]: r
        for r in read_json(ROOT / "data/manifest.json")["reference_instances"]
    }
    if args.stage in ("development", "adaptive"):
        names = [f"{family}05" for family in FAMILIES] + [
            f"{family}_10_2" for family in FAMILIES
        ]
        seeds = [901, 902, 903]
        configs = DEVELOPMENT
        if args.stage == "adaptive":
            configs = {
                "ils_adaptive": dict(
                    method="ils", adaptive_groups=True, group_size=240
                ),
                "sa_groups240": dict(
                    method="sa",
                    group_size=240,
                    temperature_mode="total",
                    temperature_ratio=0.02,
                ),
                "sa_adaptive": dict(
                    method="sa",
                    group_size=240,
                    adaptive_groups=True,
                    temperature_mode="total",
                    temperature_ratio=0.02,
                ),
            }
        budgets = {100: 2.0, 1000: 10.0}
    else:
        selected = read_json(ROOT / "results/optimization_v2/selection.json")
        configs = {"optimized_ils": selected["ils"], "optimized_sa": selected["sa"]}
        if args.stage == "validation":
            names = [f"{f}{i:02d}" for f in FAMILIES for i in [1, 4]]
            names += [f"{f}_2_{i}" for f in FAMILIES for i in [3, 4]]
            names += [f"{f}_10_{i}" for f in FAMILIES for i in [3, 4]]
            seeds = [1001, 1002, 1003, 1004, 1005]
        else:
            names = ["C204", "R1_10_1"]
            seeds = list(range(101, 121))
            configs = {"baseline_ils": {}, "optimized_ils": selected["ils"]}
        budgets = {100: 5.0, 200: 6.0, 1000: 25.0}
    jobs = [
        dict(
            id=i,
            instance=name,
            n=refs[name]["n"],
            seed=seed,
            seconds=budgets[refs[name]["n"]],
            continuation_seconds=(
                15.0 if args.stage == "validation" and refs[name]["n"] == 1000 else 0.0
            ),
            reference_distance=refs[name]["reference_distance"],
            variants=list(configs),
        )
        for i, (name, seed) in enumerate((n, s) for n in names for s in seeds)
    ]
    allowed = psutil.Process().cpu_affinity()
    cpus = allowed[::2][args.cpu_offset : args.cpu_offset + max(1, args.workers)]
    if not cpus:
        raise ValueError("No CPU available for requested offset")
    sources = [*sorted((ROOT / "algo").glob("*.py")), Path(__file__).resolve()]
    protocol = dict(
        stage=args.stage,
        instances=names,
        seeds=seeds,
        configs=configs,
        jobs=jobs,
        runs=sum(len(j["variants"]) for j in jobs),
        workers=len(cpus),
        cpus=cpus,
        sources={str(p.relative_to(ROOT)): digest(p) for p in sources},
        manifest_sha256=digest(ROOT / "data/manifest.json"),
        objective="DIMACS distance; unchanged capacity, windows, fleet and return",
        timing="Equal improvement budgets, construction separate, sequential methods within each shared-start pair",
        prior_exposure="Development separated from new calibration validation; geography already existed in old ALNS coverage, not a blind benchmark",
        selection_rule="Prioritize development gap at 1000; retain small-instance performance within one percentage point; SA temperature selected on development only",
    )
    path = out / "protocol.json"
    if path.exists():
        assert read_json(path) == protocol, "Frozen protocol mismatch"
    else:
        atomic_json(path, protocol)
        for relative in protocol["sources"]:
            target = out / "source" / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, target)
    random.Random(1911).shuffle(jobs)
    started = time.perf_counter()
    print(
        "Frozen",
        args.stage,
        "instances",
        len(names),
        "runs",
        protocol["runs"],
        "workers",
        len(cpus),
        flush=True,
    )
    with mp.get_context("spawn").Pool(
        len(cpus),
        initializer=initialize,
        initargs=(cpus, str(out), configs, "baseline_ils" in configs),
    ) as pool:
        for completed, item in enumerate(
            pool.imap_unordered(execute, jobs, chunksize=1), 1
        ):
            atomic_json(
                out / "progress.json",
                dict(
                    completed_pairs=completed,
                    pairs=len(jobs),
                    complete=completed == len(jobs),
                    elapsed_s=time.perf_counter() - started,
                ),
            )
            print("Progress", completed, "/", len(jobs), json.dumps(item), flush=True)


if __name__ == "__main__":
    main()
