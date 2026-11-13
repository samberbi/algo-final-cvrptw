"""Solve without reading a BKS; references belong to reporting scripts only."""

from pathlib import Path
from dataclasses import asdict
import argparse, json, time
from algo.data import load
from algo.optimized import solve, Settings, warmup
from algo.profiles import production_settings
from algo.verify import verify


def main():
    """Lit les options, charge l’instance, préchauffe et lance le profil choisi.
    Vérifie ensuite la solution et écrit les résultats ; la BKS sert uniquement au bilan."""
    p = argparse.ArgumentParser(
        description="CVRPTW : durée totale des tournées, capacité et fenêtres strictes"
    )
    p.add_argument(
        "instance", help="Nom fourni, par exemple R202 ou R1_10_1, ou chemin .vrp"
    )
    p.add_argument(
        "--seconds",
        type=float,
        default=10.0,
        help="Budget ; pour ils_hgs et ils_hgs_refined, somme des deux recherches, hors construction et préparation externe",
    )
    p.add_argument("--seed", type=int, default=11)
    p.add_argument(
        "--method",
        choices=[
            "ils",
            "sa",
            "ils_rvnd",
            "ils_sp",
            "ils_v6",
            "ils_cached",
            "ils_hgs",
            "ils_hgs_refined",
            "duration_refined",
        ],
        default="ils",
    )
    p.add_argument("--objective", choices=["duration", "distance"], default="duration")
    p.add_argument(
        "--intensify",
        action="store_true",
        help="Ajoute cinq secondes dès 400 clients et une seconde passe à 1 000",
    )
    p.add_argument("--output", default="results/solution.json")
    a = p.parse_args()
    root = Path(__file__).resolve().parent
    if not 0 <= a.seed < 2**31:
        p.error("La graine doit être entre 0 et 2147483647")
    if a.intensify and a.objective != "distance":
        p.error("Intensification réservée à la distance")
    if a.method == 'duration_refined' and a.objective != 'duration':
        p.error('duration_refined minimise uniquement la durée totale')
    path = Path(a.instance)
    if not path.is_file():
        path = root / "data/instances" / (a.instance + ".vrp")
    ins = load(path)
    if a.objective == 'duration':
        from algo.duration import solve as duration_solve, Settings as DurationSettings, warmup as duration_warmup
        if a.method not in ('ils','sa','ils_hgs','ils_hgs_refined','duration_refined'):
            p.error('Cette variante historique ne possède pas de version en durée')
        warming=time.perf_counter();duration_warmup();startup=time.perf_counter()-warming
        if a.method == 'duration_refined':
            from algo.duration_refine import solve as refined_duration_solve
            result=refined_duration_solve(ins,seed=a.seed,seconds=a.seconds)
        else:
            method='hybrid' if a.method in ('ils_hgs','ils_hgs_refined') else a.method
            result=duration_solve(ins,DurationSettings(seconds=a.seconds,seed=a.seed,method=method))
    else:
        startup = warmup()
    if a.objective == 'duration':
        pass
    elif a.method == "ils_hgs_refined":
        from algo.refined_hybrid import (
            Settings as RefinedSettings,
            solve as refined_solve,
        )

        result = refined_solve(
            ins, RefinedSettings(search_seconds=a.seconds, seed=a.seed)
        )
    elif a.method == "ils_hgs":
        from algo.hybrid_reference import (
            Settings as HybridSettings,
            solve as hybrid_solve,
        )

        result = hybrid_solve(
            ins, HybridSettings(search_seconds=a.seconds, seed=a.seed)
        )
    elif a.method in ("ils_v6", "ils_cached"):
        from algo.experimental_v6 import Settings as V6Settings, solve as v6_solve
        from algo.cached_iterated import warmup as warmup_cache

        warm_start = time.perf_counter()
        warmup_cache()
        startup += time.perf_counter() - warm_start
        params = asdict(production_settings("ils", seconds=a.seconds, seed=a.seed))
        params.update(cached_evaluation=True, temporal_groups=a.method == "ils_v6")
        result = v6_solve(ins, V6Settings(**params))
    elif a.method == "ils_sp":
        from algo.ils_sp import Settings as SPSettings, solve as sp_solve

        result = sp_solve(ins, SPSettings(seconds=a.seconds, seed=a.seed))
    elif a.method == "ils_rvnd":
        from algo.ils_rvnd import (
            Settings as RVNDSettings,
            solve as rvnd_solve,
            warmup as warmup_rvnd,
        )

        warm_start = time.perf_counter()
        warmup_rvnd()
        startup += time.perf_counter() - warm_start
        result = rvnd_solve(ins, RVNDSettings(seconds=a.seconds, seed=a.seed))
    else:
        result = solve(
            ins, production_settings(method=a.method, seconds=a.seconds, seed=a.seed)
        )
    if a.intensify and ins.n >= 400 and result["status"] == "feasible":
        from ameliorations.decomposition import polish

        result["stages"] = []
        for offset in ([600000, 700000] if ins.n == 1000 else [600000]):
            improved = polish(ins, result["routes"], 5.0, a.seed + offset)
            result["stages"].append(
                dict(cost=improved["cost"], runtime_s=improved["runtime_s"])
            )
            result.update(
                routes=improved["routes"],
                cost=improved["cost"],
                vehicles=improved["vehicles"],
                runtime_s=result["runtime_s"] + improved["runtime_s"],
                metrics=verify(improved["routes"], ins),
            )
    result["warmup_seconds"] = startup
    target = root / a.output
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, indent=2))
    print(
        result["status"],
        "coût",
        result.get("cost"),
        "temps",
        round(result["runtime_s"], 3),
        "s",
    )
    print(target)


if __name__ == "__main__":
    main()
