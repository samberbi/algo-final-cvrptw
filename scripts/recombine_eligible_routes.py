"""Higher-effort archive, separate from the equal-budget validation statistics."""
from pathlib import Path
import hashlib
import json
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from algo.data import load
from algo.route_pool import RoutePool
from web.experiments import read_json, atomic_json


def main():
    protocol = read_json(ROOT / "results/optimization_v5/validation/protocol.json")
    refs = {r["instance"]: r["reference_distance"] for r in read_json(ROOT / "data/manifest.json")["reference_instances"]}
    out = ROOT / "results/optimization_v5/portfolio"
    out.mkdir(exist_ok=True)
    rows = []
    for name in protocol["instances"]:
        target = out / (name + ".json")
        if target.exists():
            rows.append(read_json(target)); continue
        pool = RoutePool(load(ROOT / "data/instances" / (name + ".vrp")))
        sources, constructions = {}, {}
        search_s = extra_construction_s = 0.0
        runs = 0
        for path in sorted((ROOT / "results/optimization_v2/validation/runs").glob("*.json")):
            record = read_json(path)
            if record["job"]["instance"] != name or not record.get("valid"):
                continue
            if record["job"]["variant"] not in ("optimized_ils", "optimized_sa"):
                raise ValueError("Unexpected source method")
            sources[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
            pool.add_solution(record["result"]["routes"])
            for stage in record["result"].get("stages", []): pool.add_solution(stage["routes"])
            search_s += record["result"]["runtime_s"]
            constructions[record["job"]["id"]] = record["initial"]["seconds"]
            runs += 1
        for path in sorted((ROOT / "results/optimization_v5/validation/runs").glob(name + "_*.json")):
            record = read_json(path)
            if not record.get("complete") or not record.get("valid"):
                raise ValueError("Incomplete source")
            sources[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
            pool.add_solution(record["result"]["routes"])
            pool.add_solution(record["initial_routes"])
            search_s += record["result"]["runtime_s"]
            extra_construction_s += record["construction"]["seconds"]
            runs += 1
        assert runs == 16, (name, runs)
        before = pool.best_cost / 10
        result = pool.recombine(2.0)
        effort = search_s + sum(constructions.values()) + extra_construction_s + result["runtime_s"]
        row = dict(instance=name, input_runs=runs, sources_sha256=sources,
                   best_input_gap=100 * (before / refs[name] - 1), gap_pct=100 * (result["cost"] / refs[name] - 1),
                   result=result, generation_search_s=search_s,
                   generation_construction_s=sum(constructions.values()) + extra_construction_s,
                   total_effort_s=effort,
                   scope="Higher-effort archive: all sixteen input trajectories charged; not an independent two-second solve")
        atomic_json(target, row)
        rows.append(row)
        print(name, round(row["best_input_gap"], 3), "->", round(row["gap_pct"], 3), flush=True)
    import pandas as pd
    frame = pd.DataFrame([{k:r[k] for k in ["instance", "input_runs", "best_input_gap", "gap_pct", "total_effort_s"]} for r in rows])
    frame.to_csv(out / "summary.csv", index=False)
    atomic_json(out / "analysis.json", dict(recombinations=len(rows), instances=len(rows),
        mean_gap=float(frame.gap_pct.mean()), worst_gap=float(frame.gap_pct.max()),
        mean_effort_s=float(frame.total_effort_s.mean()),
        scope="Portfolio, not a mean of single-run solver gaps"))


if __name__ == "__main__":
    main()
