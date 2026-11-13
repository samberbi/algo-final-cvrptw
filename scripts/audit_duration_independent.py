"""Audit indépendant des données et tournées, sans importer algo.verify/load.

Lit les fichiers originaux avec VRPLIB, recalcule chaque arc euclidien tronqué
en dixièmes, simule les horaires depuis zéro et contrôle toutes les contraintes.
Ne relance aucune recherche et ne modifie aucun résultat historique.
"""
from pathlib import Path
from functools import lru_cache
from collections import Counter
import csv
import hashlib
import json
import math
import numbers
import traceback
import vrplib

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'results/time_objective/independent_audit'


@lru_cache(maxsize=4)
def data(name):
    raw = vrplib.read_instance(ROOT/'data/instances'/(name+'.vrp'), compute_edge_weights=False)
    return raw


def evaluate(name, routes):
    """Arithmétique entière ×10 ; aucun cache temporel du moteur n'est utilisé."""
    raw = data(name)
    n = len(raw['demand'])-1
    xy, windows = raw['node_coord'], raw['time_window']
    service = raw.get('service_time', 0)
    def arc(a, b):
        return math.floor(10*math.hypot(float(xy[a][0])-float(xy[b][0]),
                                      float(xy[a][1])-float(xy[b][1])))
    errors, seen, details = [], [], []
    used = [r for r in routes if len(r)]
    if len(used) > int(raw['vehicles']):
        errors.append('fleet')
    for index, route in enumerate(used):
        clock = travel = waiting = services = 0
        load = 0.
        previous = 0
        for client in route:
            if not isinstance(client, numbers.Integral) or isinstance(client, bool) or not 1 <= client <= n:
                errors.append(f'client:{client}')
                break
            seen.append(client)
            length = arc(previous, client)
            arrival = clock+length
            start = max(arrival, round(10*float(windows[client][0])))
            if start > round(10*float(windows[client][1])):
                errors.append(f'window:{client}')
            s = float(service[client]) if hasattr(service, '__len__') else float(service)
            s = round(10*s)
            waiting += start-arrival
            services += s
            travel += length
            load += float(raw['demand'][client])
            clock = start+s
            previous = client
        length = arc(previous, 0)
        travel += length
        clock += length
        if load > float(raw['capacity'])+1e-7:
            errors.append(f'capacity:{index}')
        if clock > round(10*float(windows[0][1])):
            errors.append(f'depot:{index}')
        assert clock == travel+waiting+services
        details.append(dict(duration=clock, travel=travel, waiting=waiting, service=services))
    if sorted(seen) != list(range(1, n+1)):
        errors.append('coverage_or_duplicate')
    values = {key:sum(r[key] for r in details)/10 for key in ['duration', 'travel', 'waiting', 'service']}
    return dict(valid=not errors, errors=errors, n=n, vehicles=len(used),
                makespan=max((r['duration'] for r in details), default=0)/10, **values)


def write_csv(path, rows):
    fields = sorted({k for r in rows for k in r})
    with path.open('w', newline='', encoding='utf-8-sig') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((ROOT/'data/manifest.json').read_text())
    names = {r['instance'] for r in manifest['reference_instances']}
    issues, references, checks = [], {}, []
    for filename, info in manifest['files'].items():
        path = ROOT/'data/instances'/filename
        if hashlib.sha256(path.read_bytes()).hexdigest() != info['sha256']:
            issues.append(dict(source=filename, error='Original file SHA256 mismatch'))
    for name in sorted(names):
        raw = vrplib.read_solution(ROOT/'data/instances'/(name+'.sol'))
        ref = evaluate(name, raw['routes'])
        references[name] = ref
        if not ref['valid'] or abs(ref['travel']-float(raw['cost'])) > 1e-6:
            issues.append(dict(source=name+'.sol', error='Reference infeasible or distance mismatch', details=ref))
    print(f'{len(references)} plans temoins recalcules', flush=True)
    counts = Counter()
    # Plusieurs copies d'une même solution peuvent exister : elles sont comptées
    # comme enregistrements contrôlés, jamais comme nouvelles résolutions.
    cache = {}
    files = sorted((ROOT/'results/time_objective').rglob('*.json'))+sorted((ROOT/'results/local').rglob('*.json'))
    for path in files:
        relative = path.relative_to(ROOT)
        if OUT in path.parents or any(p.startswith('source') for p in relative.parts):
            continue
        record = json.loads(path.read_text(encoding='utf-8-sig'))
        if not isinstance(record, dict):
            continue
        measurement = record.get('measurement', record)
        result = record.get('result', record)
        if not isinstance(result, dict) or not isinstance(measurement, dict):
            continue
        name = measurement.get('instance', record.get('instance'))
        if name not in names:
            continue
        routes = result.get('routes')
        if routes is None:
            if measurement.get('valid') is False:
                counts['recorded_failures_without_routes'] += 1
            continue
        if result.get('objective') not in [None, 'duration', 'sum_route_duration']:
            counts['other_objectives_skipped'] += 1
            continue
        try:
            canonical = tuple(sorted(tuple(r) for r in routes if len(r)))
            key = (name, canonical)
            if key not in cache:
                cache[key] = evaluate(name, routes)
            own = cache[key]
            ref = references[name]
            errors = list(own['errors'])
            def compare(label, actual, expected):
                if actual is not None and abs(float(actual)-expected) > 1e-6:
                    errors.append(label)
            compare('result_cost_mismatch', result.get('cost'), own['duration'])
            compare('record_duration_mismatch', measurement.get('duration'), own['duration'])
            compare('reference_duration_mismatch', measurement.get('reference_duration'), ref['duration'])
            delta = 100*(own['duration']/ref['duration']-1)
            for field in ['delta_reference_pct', 'gap_duree_pct', 'delta_pct', 'final_pct']:
                compare(field+'_mismatch', measurement.get(field), delta)
            metrics = result.get('metrics')
            if isinstance(metrics, dict):
                for field in ['duration', 'travel', 'waiting', 'makespan']:
                    value = metrics.get(field)
                    compare('metrics_'+field+'_mismatch', None if value is None else value/10, own[field])
            for field in ['travel', 'waiting', 'service', 'makespan']:
                compare('result_'+field+'_mismatch', result.get(field), own[field])
            row = dict(source=relative.as_posix(), instance=name, seed=measurement.get('seed'),
                n=own['n'], valid=own['valid'], checks_ok=not errors,
                delta_duration_pct=delta, delta_travel_pct=100*(own['travel']/ref['travel']-1),
                delta_makespan_pct=100*(own['makespan']/ref['makespan']-1),
                **{'own_'+k:v for k,v in own.items() if k not in ['errors', 'n', 'valid']},
                **{'reference_'+k:v for k,v in ref.items() if k not in ['errors', 'n', 'valid']})
            checks.append(row)
            if errors:
                issues.append(dict(source=relative.as_posix(), error=';'.join(errors)))
        except Exception:
            issues.append(dict(source=relative.as_posix(), error=traceback.format_exc()))
        if len(checks) and len(checks) % 250 == 0:
            print(f'{len(checks)} enregistrements controles', flush=True)
    write_csv(OUT/'AUDIT_TOUS_RESULTATS.csv', checks)
    write_csv(OUT/'AUDIT_TEMOINS_356.csv', [dict(instance=n, **{k:v for k,v in r.items() if k!='errors'}) for n,r in sorted(references.items())])
    large = sorted([r for r in checks if r['delta_duration_pct'] < -20], key=lambda r:r['delta_duration_pct'])
    write_csv(OUT/'ECARTS_NEGATIFS_IMPORTANTS.csv', large)
    by_source = {r['source']:r for r in checks}
    archive_rows = []
    with (ROOT/'results/time_objective/best_duration/COUVERTURE_472_ESSAIS.csv').open(encoding='utf-8-sig') as stream:
        for indexed in csv.DictReader(stream):
            row = by_source.get(indexed['source'])
            if row is None:
                issues.append(dict(source=indexed['source'], error='Archive source not audited'))
                continue
            if (abs(float(indexed['duration'])-row['own_duration']) > 1e-6
                    or abs(float(indexed['best_delta_pct'])-row['delta_duration_pct']) > 1e-6):
                issues.append(dict(source=indexed['source'], error='Archive CSV mismatch'))
            archive_rows.append(row)
    grouped = {}
    for row in archive_rows:
        grouped.setdefault(row['instance'], []).append(row)
    per_instance = []
    for name, trials in sorted(grouped.items()):
        numeric = ['delta_duration_pct', 'delta_travel_pct', 'delta_makespan_pct',
                   'own_duration', 'own_travel', 'own_waiting', 'own_service', 'own_vehicles', 'own_makespan',
                   'reference_duration', 'reference_travel', 'reference_waiting', 'reference_service',
                   'reference_vehicles', 'reference_makespan']
        per_instance.append(dict(instance=name, n=trials[0]['n'], archived_trials=len(trials),
            **{k:sum(r[k] for r in trials)/len(trials) for k in numeric}))
    write_csv(OUT/'COMPARAISON_356_INSTANCES.csv', per_instance)
    summary = dict(reference_instances=len(references), solution_records_checked=len(checks),
        unique_instance_route_sets=len(cache), original_hashes_checked=len(manifest['files']),
        issues=len(issues), archive_records_checked=len(archive_rows),
        archived_instances_checked=len(grouped),
        negative_records=sum(r['delta_duration_pct']<0 for r in checks),
        below_minus_20_records=len(large), **counts,
        scope='Recorded complete solutions only; duplicates are not new runs; no search rerun',
        objective='sum of route return times, fixed departure zero; not makespan or variable departure duration')
    (OUT/'BILAN.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    (OUT/'ANOMALIES.json').write_text(json.dumps(issues, indent=2), encoding='utf-8')
    report = f'''# Audit indépendant des écarts en durée

{len(references)} témoins, {len(checks)} enregistrements de solutions et les
{len(archive_rows)} lignes de l'archive ont été contrôlés. Il s'agit de
{len(cache)} couples instance–ensemble de tournées distincts : les copies ne
sont pas comptées comme de nouveaux essais. Anomalies détectées : **{len(issues)}**.

Le recalcul repart des coordonnées et fenêtres originales, sans importer
`algo.verify` ou `algo.data`. Chaque arc est recalculé en distance euclidienne
tronquée au dixième ; horaires et durées sont évalués en entiers ×10. Les contrôles
portent sur la couverture unique, la capacité, la flotte maximale, les fenêtres,
le retour au dépôt, les services, les coûts enregistrés, les écarts et les
empreintes des {len(manifest['files'])} fichiers originaux. Les {sum('/catalogue/runs/' in r['source'] for r in checks)}
essais du catalogue initial sont inclus. Aucune recherche n'est relancée.

## Ce qui explique les valeurs négatives

L'objectif utilisé est la **somme des durées des tournées avec départs à zéro**.
Le témoin a été choisi pour la distance. Son attente peut être élevée et se
cumule entre véhicules. Les services sont identiques entre deux plans complets.
Un écart négatif indique une durée cumulée inférieure au témoin ; il ne prouve
pas une amélioration par rapport à un optimum temporel. La durée du dernier
camion est une autre mesure, le makespan, et peut évoluer dans l'autre sens.

Sur RC201, la solution locale observée a 4 véhicules, 2 010,4 de trajets,
205,8 d'attentes et 1 000 de services, soit 3 216,2 de durée cumulée. Le témoin
a 9 véhicules, 1 261,8 de trajets, 4 243,5 d'attentes et 1 000 de services,
soit 6 505,3. L'écart −50,56 % provient donc d'un gain d'attente qui dépasse
la hausse des trajets. Ce n'est pas une réduction de 50 % du temps CPU ni
de l'heure de fin de l'ensemble des livraisons.

## Limite méthodologique à conserver

Le calcul est cohérent avec notre modèle. En revanche, la référence n'est pas
une BKS en durée : le seuil « écart inférieur à +6 % au témoin » ne démontre
pas une distance à l'optimum sous 6 %. Il ne faut ni prendre la valeur absolue
des écarts ni les plafonner à zéro, ni changer les unités pour les rapprocher.

Si les départs pouvaient être retardés, une partie des attentes du témoin
pourrait disparaître. Ce serait une autre hypothèse de modélisation, à appliquer
aux deux solutions et à réévaluer complètement ; cet audit ne la change pas.

## Fichiers de lecture

- `COMPARAISON_356_INSTANCES.csv` : les 356 instances de l'archive, décomposition
  solution/témoin, flottes, écarts de durée, de trajet et de makespan. Les colonnes
  propres sont moyennées sur les graines archivées de chaque instance ; les
  budgets sont mixtes et ce tableau n'est pas une campagne uniforme nouvelle.
- `AUDIT_TOUS_RESULTATS.csv` : chaque enregistrement contrôlé, avec son fichier source.
- `AUDIT_TEMOINS_356.csv` : chaque témoin réévalué indépendamment.
- `ECARTS_NEGATIFS_IMPORTANTS.csv` : tous les enregistrements sous −20 %, copies incluses.
- `ANOMALIES.json` et `BILAN.json` : anomalies et périmètre exact du contrôle.

Reproduction : `python scripts/audit_duration_independent.py`.
'''
    (OUT/'EXPLICATION_AUDIT.md').write_text(report, encoding='utf-8')
    print(json.dumps(summary, indent=2), flush=True)
    if issues:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
