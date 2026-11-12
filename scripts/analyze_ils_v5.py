"""Audit actual CVRPTW runs and recompute paired statistics."""
from pathlib import Path
import hashlib
import json
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import pandas as pd
from algo.data import load
from algo.verify import verify

BASE = ROOT / "results/optimization_v5"


def analyze(label):
    folder = BASE / label
    protocol = json.loads((folder / "protocol.json").read_text(encoding="utf-8"))
    manifest = json.loads((ROOT / "data/manifest.json").read_text(encoding="utf-8"))
    missing_snapshots = []
    for relative, expected in protocol["sources"].items():
        snapshot = folder / "source" / relative
        if snapshot.exists():
            assert hashlib.sha256(snapshot.read_bytes()).hexdigest() == expected
        else:
            missing_snapshots.append(relative)
    # Intermediate code archives are kept outside the assessed ZIP. Its current
    # source remains runnable; the complete final validation snapshot is required.
    if label == "validation":
        assert not missing_snapshots, missing_snapshots
    refs = {r["instance"]: r for r in manifest["reference_instances"]}
    cases, rows = {}, []
    expected = {(name, seed, variant) for name in protocol["instances"] for seed in protocol["seeds"] for variant in protocol["variants"]}
    found = set()
    hashes = {}
    for path in sorted((folder / "runs").glob("*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        name, seed, variant = record["instance"], record["seed"], record["variant"]
        assert (name, seed, variant) in expected and (name, seed, variant) not in found
        found.add((name, seed, variant))
        hashes[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
        row = dict(instance=name, seed=seed, profile=variant, n=refs[name]["n"],
                   valid=record.get("valid", False), status="feasible" if record.get("valid") else "error",
                   budget_s=record["budget_s"], reference_distance=refs[name]["reference_distance"])
        if record.get("valid"):
            if name not in cases:
                file = ROOT / "data/instances" / (name + ".vrp")
                assert hashlib.sha256(file.read_bytes()).hexdigest() == manifest["files"][file.name]["sha256"]
                cases[name] = load(file)
            check = verify(record["result"]["routes"], cases[name])
            assert check["valid"]
            distance = check["distance"] / 10
            assert abs(distance - record["result"]["cost"]) < 1e-7
            gap = 100 * (distance / row["reference_distance"] - 1)
            assert abs(gap - record["gap_pct"]) < 1e-7
            row.update(distance=distance, gap_pct=gap, vehicles=check["vehicles"],
                       runtime_s=record["result"]["runtime_s"], total_s=record["total_s"],
                       initial_cost=verify(record["initial_routes"], cases[name])["distance"] / 10)
        rows.append(row)
    assert found == expected, f"Missing {len(expected - found)} runs"
    frame = pd.DataFrame(rows)
    if frame.valid.any():
        assert frame[frame.valid].groupby(["instance", "seed"]).initial_cost.nunique().max() == 1
    summary = frame.groupby("profile").agg(runs=("valid", "size"), feasible=("valid", "sum"),
        mean_gap=("gap_pct", "mean"), std_gap=("gap_pct", "std"), median_gap=("gap_pct", "median"),
        best_gap=("gap_pct", "min"), worst_gap=("gap_pct", "max"),
        under5=("gap_pct", lambda x: int((x < 5).sum())), under6=("gap_pct", lambda x: int((x < 6).sum())),
        under7=("gap_pct", lambda x: int((x < 7).sum())), mean_search_s=("runtime_s", "mean"), mean_total_s=("total_s", "mean")).reset_index()
    instances = frame.groupby(["instance", "profile"]).agg(mean_gap=("gap_pct", "mean"), std_gap=("gap_pct", "std"),
        best_gap=("gap_pct", "min"), worst_gap=("gap_pct", "max"), mean_distance=("distance", "mean"),
        bks=("reference_distance", "first"), runs=("valid", "size"), feasible=("valid", "sum")).reset_index()
    frame.to_csv(folder / "flat.csv", index=False)
    summary.to_csv(folder / "summary.csv", index=False)
    instances.to_csv(folder / "instances.csv", index=False)
    payload = dict(trajectories=len(frame), instances=len(protocol["instances"]),
                   source_snapshots_complete=not missing_snapshots,
                   intermediate_source_snapshots_not_supplied=missing_snapshots,
                   feasible=int(frame.valid.sum()), summary=summary.to_dict("records"), raw_sha256=hashes)
    (folder / "analysis.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return frame, summary, instances


if __name__ == "__main__":
    for label in sys.argv[1:] or ["development", "development_relay", "development_parameters", "validation"]:
        _, summary, _ = analyze(label)
        print(label)
        print(summary.to_string(index=False))
