"""Recompute new experiments, retaining failures and every high-gap result."""

from pathlib import Path
import argparse
import hashlib
import json
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from algo.data import load, reference
from algo.verify import verify

BASE = ROOT / "results/optimization_v2"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def analyze(stage, complete=True):
    folder = BASE / stage
    protocol = read(folder / "protocol.json")
    for relative, expected in protocol["sources"].items():
        assert (
            hashlib.sha256((folder / "source" / relative).read_bytes()).hexdigest()
            == expected
        )
    manifest = read(ROOT / "data/manifest.json")
    assert (
        hashlib.sha256((ROOT / "data/manifest.json").read_bytes()).hexdigest()
        == protocol["manifest_sha256"]
    )
    refs = {r["instance"]: r for r in manifest["reference_instances"]}
    instances = {
        name: load(ROOT / "data/instances" / (name + ".vrp"))
        for name in protocol["instances"]
    }
    for name, ins in instances.items():
        routes, cost = reference(ROOT / "data/instances" / (name + ".sol"))
        checked = verify(routes, ins)
        assert checked["valid"] and abs(checked["distance"] / 10 - cost) < 1e-7
        assert abs(cost - refs[name]["reference_distance"]) < 1e-7
    rows = []
    hashes = {}
    for path in sorted((folder / "runs").glob("*.json")):
        item = read(path)
        job = item["job"]
        result = item["result"]
        ins = instances[job["instance"]]
        valid = False
        gap = None
        if result["status"] == "feasible":
            checked = verify(result["routes"], ins)
            assert (
                checked["valid"]
                and abs(checked["distance"] / 10 - result["cost"]) < 1e-7
            )
            valid = True
            gap = 100 * (
                result["cost"] / refs[job["instance"]]["reference_distance"] - 1
            )
            assert abs(gap - item["gap_pct"]) < 1e-7
            trace = result["trace"]
            assert all(b["best"] <= a["best"] + 1e-7 for a, b in zip(trace, trace[1:]))
            assert abs(trace[-1]["best"] - result["cost"]) < 1e-7
        initial = read(folder / "initials" / f"{job['id']:04d}.json")
        if initial["routes"] is not None:
            checked = verify(initial["routes"], ins)
            assert checked["valid"]
            assert (
                item.get("initial_routes_sha256")
                == hashlib.sha256(json.dumps(initial["routes"]).encode()).hexdigest()
            )
            if valid:
                assert abs(result["initial_cost"] - checked["distance"] / 10) < 1e-7
        diagnostics = result.get("diagnostics", {})
        attempts = diagnostics.get("attempts", 0)
        if attempts:
            assert sum(v for k, v in diagnostics.items() if k != "attempts") == attempts
        rows.append(
            dict(
                run=job["id"],
                instance=job["instance"],
                n=job["n"],
                seed=job["seed"],
                profile=job["variant"],
                method=result.get("method"),
                status=result["status"],
                valid=valid,
                distance=result.get("cost"),
                reference_distance=refs[job["instance"]]["reference_distance"],
                gap_pct=gap,
                runtime_s=result["runtime_s"],
                construction_s=item.get("initial", {}).get("seconds"),
                total_s=item.get("total_s"),
                budget_s=job["seconds"] + job.get("continuation_seconds", 0),
                gap_at25_pct=(
                    100
                    * (
                        result["stages"][0]["cost"]
                        / refs[job["instance"]]["reference_distance"]
                        - 1
                    )
                    if result.get("stages")
                    else None
                ),
                initial_gap_pct=100
                * (
                    result.get("initial_cost", 0)
                    / refs[job["instance"]]["reference_distance"]
                    - 1
                ),
                vehicles=result.get("vehicles"),
                proposals=result.get("iterations", 0),
                cycles=result.get("cycles", 0),
                feasible_proposals=result.get("valid_proposals", 0),
                **{"diag_" + k: v for k, v in diagnostics.items()},
            )
        )
        hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    df = pd.DataFrame(rows)
    expected = {
        (j["id"], variant) for j in protocol["jobs"] for variant in j["variants"]
    }
    actual = set(zip(df.run, df.profile))
    assert not df.duplicated(["run", "profile"]).any()
    if complete:
        assert actual == expected
    summary = (
        df.groupby(["n", "profile"])
        .agg(
            runs=("valid", "size"),
            feasible=("valid", "sum"),
            mean_gap=("gap_pct", "mean"),
            median_gap=("gap_pct", "median"),
            std_gap=("gap_pct", "std"),
            best_gap=("gap_pct", "min"),
            worst_gap=("gap_pct", "max"),
            under5=("gap_pct", lambda s: int(s.lt(5).sum())),
            under6=("gap_pct", lambda s: int(s.lt(6).sum())),
            under7=("gap_pct", lambda s: int(s.lt(7).sum())),
            mean_search_s=("runtime_s", "mean"),
            mean_total_s=("total_s", "mean"),
            max_total_s=("total_s", "max"),
        )
        .reset_index()
    )
    per_instance = (
        df.groupby(["instance", "n", "profile"])
        .agg(
            runs=("valid", "size"),
            feasible=("valid", "sum"),
            mean_gap=("gap_pct", "mean"),
            std_gap=("gap_pct", "std"),
            best_gap=("gap_pct", "min"),
            worst_gap=("gap_pct", "max"),
            under5=("gap_pct", lambda s: int(s.lt(5).sum())),
            under6=("gap_pct", lambda s: int(s.lt(6).sum())),
            under7=("gap_pct", lambda s: int(s.lt(7).sum())),
            mean_time_s=("total_s", "mean"),
        )
        .reset_index()
    )
    df.to_csv(folder / "flat.csv", index=False)
    summary.to_csv(folder / "summary.csv", index=False)
    per_instance.to_csv(folder / "instances.csv", index=False)
    payload = dict(
        complete=actual == expected,
        runs=len(df),
        instances=int(df.instance.nunique()),
        failures=int((~df.valid).sum()),
        summary=summary.to_dict("records"),
        hashes=hashes,
    )
    (folder / "analysis.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return df, summary, per_instance, payload


def select():
    if (BASE / "validation/protocol.json").exists():
        print("Selection frozen before validation; preserving", BASE / "selection.json")
        print(json.dumps(read(BASE / "selection.json"), indent=2))
        return
    df, summary, _, _ = analyze("development")
    variants = read(BASE / "development/protocol.json")["configs"]
    if (BASE / "adaptive/progress.json").exists() and read(
        BASE / "adaptive/progress.json"
    )["complete"]:
        extra, extra_summary, _, _ = analyze("adaptive")
        df = pd.concat([df, extra], ignore_index=True)
        summary = pd.concat([summary, extra_summary], ignore_index=True)
        variants.update(read(BASE / "adaptive/protocol.json")["configs"])
    large = summary[summary.n.eq(1000)].set_index("profile")
    small = summary[summary.n.eq(100)].set_index("profile")
    candidates = [
        v
        for v in variants
        if v.startswith("ils")
        and small.loc[v, "mean_gap"] <= small.loc["ils_groups", "mean_gap"] + 1
    ]
    best_ils = min(candidates, key=lambda v: large.loc[v, "mean_gap"])
    best_sa = min(
        [v for v in variants if v.startswith("sa")],
        key=lambda v: large.loc[v, "mean_gap"],
    )

    def full_config(label):
        stage = (
            "adaptive"
            if (BASE / "adaptive/protocol.json").exists()
            and label in read(BASE / "adaptive/protocol.json")["configs"]
            else "development"
        )
        path = next(
            p
            for p in (BASE / stage / "runs").glob("*.json")
            if read(p)["job"]["variant"] == label
        )
        config = read(path)["result"]["settings"].copy()
        config.pop("seconds", None)
        config.pop("seed", None)
        return config

    payload = dict(
        rule="Minimum development mean gap at 1000; ILS small-instance mean cannot regress by over one percentage point",
        ils=full_config(best_ils),
        sa=full_config(best_sa),
        chosen_ils=best_ils,
        chosen_sa=best_sa,
        development_instances=read(BASE / "development/protocol.json")["instances"],
        selection_before_validation=True,
    )
    (BASE / "selection.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--stage",
        choices=["development", "adaptive", "validation", "regression"],
        default="development",
    )
    parser.add_argument("--select", action="store_true")
    args = parser.parse_args()
    if args.select:
        select()
    else:
        _, summary, _, payload = analyze(args.stage)
        print(summary.to_string(index=False))
        print("Verified:", payload["runs"], "runs;", payload["failures"], "failures")
