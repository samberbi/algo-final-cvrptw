"""Contrôle indépendant des essais du terminal et du progrès de la politique v2."""
from pathlib import Path
import json
import hashlib
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import pandas as pd
import vrplib
from algo.comparison_status import present, classify
from scripts.audit_gap_status import check


def main():
    out = ROOT / 'results/policy_v2_audit'
    out.mkdir(parents=True, exist_ok=True)
    rows, issues = [], []
    # Ces fichiers contiennent des tournées, et non des moyennes déjà agrégées.
    for path in sorted((ROOT / 'results/local').glob('*/*.json')):
        record = json.loads(path.read_text(encoding='utf-8-sig'))
        if not isinstance(record, dict) or record.get('schema') != 'terminal_v2' or 'measurement' not in record:
            continue
        m, result = record['measurement'], record['result']
        row = dict(source=path.relative_to(ROOT).as_posix(), instance=m['instance'],
                   n=m['n'], seed=m['seed'], method=m['method'],
                   selected_method=m.get('selected_method'), valid=m['valid'],
                   duration=m.get('duration'), reference=m.get('reference_duration'),
                   signed_delta_pct=m.get('delta_reference_pct'), wall_s=m['wall_s'],
                   cpu_s=m['cpu_s'])
        try:
            if not m['valid']:
                row['cause'] = 'Échec conservé, sans coût classé'
                rows.append(row)
                continue
            own = check(m['instance'], m['n'], result['routes'])
            assert own['valid'], own['errors']
            for metric in ['duration', 'travel', 'waiting', 'service']:
                assert abs(own[metric] - m[metric]) < 1e-7, metric
            if result.get('initial_routes') is not None:
                initial = check(m['instance'], m['n'], result['initial_routes'])
                assert initial['valid']
                assert abs(initial['duration']-result['initial_cost']) < 1e-7
                assert own['duration'] <= initial['duration'] + 1e-7
                row.update(initial_duration=initial['duration'],
                           improvement=initial['duration']-own['duration'])
            ref = record.get('reference') or {}
            if ref.get('source'):
                refpath = ROOT / ref['source']
                if refpath.suffix == '.sol':
                    routes = vrplib.read_solution(refpath)['routes']
                    kind = 'Plan public distance réévalué en durée, non optimalité temporelle'
                else:
                    saved = json.loads(refpath.read_text(encoding='utf-8-sig'))
                    assert saved.get('method') == 'ortools'
                    routes = saved['result']['routes']
                    kind = 'OR-Tools indépendant, référence heuristique non prouvée optimale'
                reference = check(m['instance'], m['n'], routes)
                assert reference['valid'], reference['errors']
                assert abs(reference['duration']-m['reference_duration']) < 1e-7
                delta = 100*(own['duration']/reference['duration']-1)
                assert abs(delta-m['delta_reference_pct']) < 1e-7
                same = sorted(map(tuple, result['routes'])) == sorted(map(tuple, routes))
                row.update(reference_kind=kind, status=classify(own['duration'],reference['duration']),
                           comparison=present(own['duration'],reference['duration']),
                           same_plan=same,
                           cause=('Référence heuristique améliorée, pas un optimum battu' if delta < -1e-8
                                  else ('Même plan' if same else 'Plans distincts de même coût')
                                       + ', optimalité non démontrée' if abs(delta) <= 1e-8
                                  else 'Solution réalisable encore perfectible' if delta > 6
                                  else 'Écart positif au comparateur compatible'))
            else:
                row['cause'] = 'Pas de référence compatible enregistrée'
                row['comparison'] = present(own['duration'],None)
                row['status'] = classify(own['duration'],None)
        except Exception as error:
            issues.append(dict(source=row['source'], error=str(error)))
        rows.append(row)
    data = pd.DataFrame(rows)
    data.to_csv(out/'AUDIT_RECENTS.csv',index=False,encoding='utf-8-sig')
    (out/'ANOMALIES.json').write_text(json.dumps(issues,ensure_ascii=False,indent=2),encoding='utf-8')
    for label in ['correction_petites_pilote_v2','correction_petites_toutes_v2','correction_grandes_v2','correction_grandes_hgs_v2']:
        source = ROOT/'results/local'/label
        if source.exists():
            protocol=json.loads((source/'protocol.json').read_text(encoding='utf-8'))
            for rel,expected in protocol['sources'].items():
                assert hashlib.sha256((source/'source'/rel).read_bytes()).hexdigest()==expected,rel
            shutil.copytree(source,out/label,dirs_exist_ok=True)
    campaign = data[data.source.str.contains('/correction_petites_toutes_v2/')].copy()
    if len(campaign):
        campaign['initial_delta_pct'] = 100*(campaign.initial_duration/campaign.reference-1)
        campaign.to_csv(out/'AVANT_APRES_PETITES.csv',index=False,encoding='utf-8-sig')
        display=campaign[['instance','n','seed','initial_duration','duration','reference','comparison','wall_s','cpu_s']]
        (out/'TABLEAU_PETITES.md').write_text('# Comparaisons en durée — 72 essais réellement exécutés\n\n'
            'Graine 4101, budget souple de cinq secondes. Les références sont des plans réalisables heuristiques, '
            'sans preuve d’optimalité temporelle. Les statuts ne sont pas des pourcentages.\n\n'
            +display.to_markdown(index=False,floatfmt='.4f')+'\n',encoding='utf-8')
    large=data[data.source.str.contains('/correction_grandes_hgs_v2/')].copy()
    if len(large):
        large['initial_delta_pct']=100*(large.initial_duration/large.reference-1)
        large.to_csv(out/'AVANT_APRES_GRANDES_HGS.csv',index=False,encoding='utf-8-sig')
    deltas = data.signed_delta_pct.dropna()
    receipt = dict(checked_trials=len(data),valid=int(data.valid.sum()),issues=len(issues),
                   above_six=int((deltas>6).sum()),negative=int((deltas < -1e-8).sum()),
                   equal=int((deltas.abs()<=1e-8).sum()),
                   new_small_trials=len(campaign),new_small_valid=int(campaign.valid.sum()),
                   new_small_above_six=int((campaign.signed_delta_pct>6).sum()),
                   independent_evaluator='Original coordinates, integer x10 arcs, no solver kernels',
                   references='Heuristic feasible plans, no certified duration optimum')
    (out/'AUDIT.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(receipt,ensure_ascii=False,indent=2))
    if issues:
        raise AssertionError(issues)


if __name__ == '__main__':
    main()
