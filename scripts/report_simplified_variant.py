"""Rapport d'ablation construction seule / renforcé, sans sélection selon le gap."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import pandas as pd
import vrplib
from scripts.audit_gap_status import check
from algo.comparison_status import BETTER,EQUAL,present,positive_text,describe_positive


def main():
    p=argparse.ArgumentParser();p.add_argument('--label',default='variante_simplifiee_comparaison');args=p.parse_args()
    if not args.label.replace('_','').replace('-','').isalnum():p.error('Label invalide')
    source=ROOT/'results/local'/args.label
    out=ROOT/'results/simplified_variant'/args.label
    out.mkdir(parents=True,exist_ok=True)
    protocol=json.loads((source/'protocol.json').read_text())
    assert protocol['methods']==['construction','refined']
    assert protocol['arguments']['seeds']==[4101,4102]
    rows=[]
    for path in sorted(source.glob('*.json')):
        record=json.loads(path.read_text(encoding='utf-8'))
        if 'measurement' not in record:continue
        row=record['measurement'];result=record['result']
        if row['valid']:
            own=check(row['instance'],row['n'],result['routes'])
            assert own['valid'] and abs(own['duration']-row['duration'])<1e-7
            ref=record['reference'];refpath=ROOT/ref['source']
            if refpath.suffix=='.sol':routes=vrplib.read_solution(refpath)['routes']
            else:
                external=json.loads(refpath.read_text())
                assert external['method']=='ortools'
                routes=external['result']['routes']
            checked=check(row['instance'],row['n'],routes)
            assert checked['valid'] and abs(checked['duration']-row['reference_duration'])<1e-7
            delta=100*(own['duration']/checked['duration']-1)
            assert abs(delta-row['delta_reference_pct'])<1e-7
        rows.append(row)
    frame=pd.DataFrame(rows)
    assert len(frame)==32 and not frame.duplicated(['instance','n','method','seed']).any()
    for path in source.iterdir():
        target=out/path.name
        if path.is_dir() and path.name=='source':
            shutil.copytree(path,target,dirs_exist_ok=True)
        elif path.is_file():
            if target.exists():assert target.read_bytes()==path.read_bytes()
            else:shutil.copy2(path,target)
    for rel,expected in protocol['sources'].items():
        assert hashlib.sha256((out/'source'/rel).read_bytes()).hexdigest()==expected
    aggregate=[]
    for (instance,n,method),g in frame.groupby(['instance','n','method']):
        good=g[g.valid]
        assert len(g.reference_duration.dropna().unique())==1
        ref=float(g.reference_duration.dropna().iloc[0])
        deltas=good.delta_reference_pct
        signed=float(deltas.mean()) if len(deltas) else None
        if len(good)!=len(g):display='Échec(s) de recherche — voir détail'
        elif deltas.gt(0).all():display=positive_text(signed)+' %'
        elif deltas.eq(0).all():display='Référence égalée — optimalité non démontrée'
        elif deltas.lt(0).all():display='Référence dépassée sur les deux graines'
        else:display='Résultats mixtes — détail des deux graines conservé'
        aggregate.append(dict(instance=instance,clients=int(n),methode=method,essais=len(g),
            faisables=len(good),duree_moyenne=float(good.duration.mean()) if len(good) else None,
            reference=ref,type_reference=g.reference_type.iloc[0],ecart_moyen_signe_pct=signed,
            gap_moyen_presente=display,cpu_moyen_s=float(g.cpu_s.mean()),reel_moyen_s=float(g.wall_s.mean()),
            references_depassees=int(deltas.lt(0).sum()),references_egalees=int(deltas.eq(0).sum()),
            ecarts_positifs=int(deltas.gt(0).sum()),depassements_six=int(deltas.gt(6).sum())))
    stats=pd.DataFrame(aggregate).sort_values(['clients','instance','methode'])
    stats.to_csv(out/'STATISTIQUES_COMPAREES.csv',index=False,encoding='utf-8-sig')
    positive_summaries=[]
    for method,g in frame.groupby('method'):
        d=describe_positive(g.delta_reference_pct.replace({float('nan'):None}).tolist())
        positive_summaries.append(dict(methode=method,essais=len(g),positifs=d['positive_count'],
            references_depassees=d['reference_better_count'],references_egalees=d['equal_count'],
            moyenne_positive_pct=d['positive_mean'],mediane_positive_pct=d['positive_median'],
            superieurs_six=d['above_six']))
    pd.DataFrame(positive_summaries).to_csv(out/'MOYENNES_POSITIVES_CONDITIONNELLES.csv',index=False,encoding='utf-8-sig')
    table=stats.pivot(index=['instance','clients'],columns='methode',values='gap_moyen_presente').reset_index()
    table=table.sort_values(['clients','instance'])
    table.columns.name=None
    table.columns=['Instance','Clients','Construction seule : gap moyen / statut','Renforcé : gap moyen / statut']
    body='''# Variante simplifiée — construction seule, ablation explicite

La variante testée est **construction seule**, déjà disponible dans le projet :
douze constructions regret-2, sélection du meilleur plan selon la durée totale,
sans ILS, sans recuit, sans recherche locale PyVRP, sans HGS et sans partitionnement.
Ce profil est une heuristique constructive, pas une nouvelle métaheuristique.
Le profil renforcé reste le profil de production ; il n'est pas remplacé.

Le lot a été fixé avant les résultats : six familles à 100 clients, C101/25
et R2_10_8/1000 ; graines 4101 et 4102. Aucun arrêt ou choix de solution n'est
piloté par le gap. Les références sont lues après la résolution. Les mêmes
contraintes et le même objectif trajets + attentes + services sont appliqués.

La construction s'arrête après douze tentatives. Le renforcé reçoit cinq
secondes de budget total souple. Ce sont des niveaux d'effort différents,
mesurés par CPU et temps réel ; ce n'est pas une preuve d'égalité de CPU.
Chaque tournée et chaque référence a été recalculée indépendamment à partir
des coordonnées originales. Les deux méthodes ont exactement les mêmes
références par instance. C101/25 utilise OR-Tools enregistré ; les autres cas
utilisent les plans publics distance réévalués en durée, sans preuve d'optimum.

Le gap moyen présenté est la moyenne des deux graines lorsque les deux écarts
sont positifs. Lorsqu'elles battent ou égalent la référence, un statut le dit.
Les valeurs signées réelles et toutes les graines restent dans les CSV.
Une référence dépassée ne devient pas un optimum et aucun résultat n'est forcé
entre les bornes souhaitées.

'''+table.to_markdown(index=False)+'''

## Détail de la qualité et du temps

'''+stats[['instance','clients','methode','essais','faisables','duree_moyenne','reference',
          'cpu_moyen_s','reel_moyen_s','references_depassees','references_egalees','ecarts_positifs','depassements_six']].to_markdown(index=False,floatfmt='.4f')+'''

La simplification ne garantit pas un écart entre les bornes académiques :
elle peut augmenter les attentes, dépasser six pour cent, ou continuer à
améliorer un témoin heuristique. Le choix de référence reste déterminant.
Les observations de ce petit lot ne sont pas généralisées aux 356 instances.
Ces essais d'ablation ne remplacent ni les meilleures solutions archivées ni
les statistiques des campagnes précédentes.
'''
    (out/'RAPPORT_VARIANTE_SIMPLIFIEE.md').write_text(body,encoding='utf-8')
    with (out/'RAPPORT_VARIANTE_SIMPLIFIEE.md').open('a',encoding='utf-8') as stream:
        stream.write('\n\n## Effectifs et moyenne conditionnelle\n\n')
        public_stats=pd.DataFrame(positive_summaries)
        for column in ['moyenne_positive_pct','mediane_positive_pct']:
            public_stats[column]=public_stats[column].map(lambda v:positive_text(float(v))+' %' if pd.notna(v)
                else 'Références dépassées ou égalées')
        stream.write(public_stats.to_markdown(index=False))
        stream.write('\n\nLa moyenne positive ne porte que sur la colonne positifs. Elle ne représente pas tous les essais et ne constitue pas un gap certifié. Les références hétérogènes et les statuts restent explicitement décrits.\n')
    receipt=dict(validated=True,instances=frame[['instance','n']].drop_duplicates().shape[0],
        resolutions=len(frame),feasible=int(frame.valid.sum()),seeds=[4101,4102],
        signed_deltas_preserved=True,original_algorithms_unchanged=True,production_default_unchanged=True,
        constraints_independently_checked=True,reference_read_after_search=True,
        no_guaranteed_target_gap=True)
    (out/'VALIDATION.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    print(table.to_string(index=False))
    print(pd.DataFrame(positive_summaries).to_string(index=False))
    print(json.dumps(receipt,indent=2))


if __name__=='__main__':main()
