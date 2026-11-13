"""Vérifie et présente les trois reprises difficiles ; aucune recherche."""
from pathlib import Path
import json
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def text():
    from algo.data import load, reference
    from algo.verify import verify
    folder = ROOT/'results/time_objective/quality_cpu_check'
    names = ['C2_10_2_4101', 'C2_10_7_4101', 'C2_10_7_4102']
    rows = []
    for name in names:
        path = folder/(name+'_continued.json')
        if not path.exists():
            path = folder/(name+'.json')
        row = json.loads(path.read_text())
        ins = load(ROOT/'data/instances'/(row['instance']+'.vrp'))
        checked = verify(row['routes'], ins)
        refs, _ = reference(ROOT/'data/instances'/(row['instance']+'.sol'))
        ref = verify(refs, ins)
        assert checked['valid'] and ref['valid']
        delta = 100*(checked['duration']/ref['duration']-1)
        assert abs(delta-row['delta_reference_pct']) < 1e-7
        assert abs(checked['duration']/10-row['duration']) < 1e-7
        assert row['below_6'] == (delta < 6)
        assert row['below_120_cpu'] == (row['total_including_warmup_cpu_s'] < 120)
        rows.append(row)
    lines = ['### Contrôle conjoint qualité–CPU sur trois reprises difficiles', '',
        'Ces trois résolutions ont été recalculées à neuf, sans transmettre les témoins au moteur. '
        'La construction renforcée est suivie de HGS externe pendant 30 puis 20 secondes. '
        'C2_10_2, encore à +6,02 %, reçoit ensuite 50 secondes supplémentaires, '
        'facturées au cumul. Le temps de cette première tentative reste compté.', '',
        '| Instance | Graine | Écart en durée | CPU cumulé (s) | Temps écoulé cumulé (s) |',
        '|---|---:|---:|---:|---:|']
    for row in rows:
        lines.append(f"| {row['instance']} | {row['seed']} | {row['delta_reference_pct']:+.2f} % | "
                     f"{row['total_including_warmup_cpu_s']:.2f} | {row['total_including_warmup_wall_s']:.2f} |")
    lines += ['',
        'Le CPU inclut le préchauffage mesuré dans chaque worker et toutes les phases '
        'de résolution, y compris la vérification finale ; le démarrage de l’interpréteur '
        'est exclu. Les trois instances sont lancées sur des processus distincts. '
        'La limite de deux minutes est contrôlée **par résolution**, pas sur la somme '
        'CPU des trois workers. Cette vérification est a posteriori ; elle ne constitue '
        'pas un arrêt matériel garanti à 120 secondes.', '',
        'Ces cas ont été sélectionnés pour leur lenteur historique : ce contrôle ne '
        'garantit pas les deux critères sur toutes les instances, graines et machines. '
        'Les écarts portent sur les durées des plans témoins, pas sur des optimums temporels. '
        'Les meilleurs résultats historiques restent conservés séparément.', '',
        'Pour reproduire ce lot optionnel (trois résolutions seulement) :', '',
        '```powershell',
        '.\\.venv\\Scripts\\python.exe scripts/check_quality_time.py --label qualite_portable',
        '.\\.venv\\Scripts\\python.exe scripts/continue_quality_time.py --label qualite_portable',
        '```', '',
        'La continuation est destinée uniquement à C2_10_2 et vérifie la marge CPU '
        'mesurée avant de démarrer. Les tests rapides de l’annexe restent disponibles '
        'pour un simple contrôle de fonctionnement.']
    receipt = dict(cases=3, all_feasible=True,
        below_6=sum(r['below_6'] for r in rows), below_120_cpu=sum(r['below_120_cpu'] for r in rows),
        max_cpu_s=max(r['total_including_warmup_cpu_s'] for r in rows),
        scope='Selected difficult cases, full measured pipelines, not all-instance guarantee')
    (folder/'VALIDATION.json').write_text(json.dumps(receipt, indent=2))
    return '\n'.join(lines)


if __name__ == '__main__':
    print(text())
