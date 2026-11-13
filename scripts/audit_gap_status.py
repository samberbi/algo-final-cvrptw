"""Réévaluation indépendante de toutes les comparaisons conservées, sans recherche."""
from pathlib import Path
from functools import lru_cache
import hashlib
import json
import math
import numbers
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import pandas as pd
import vrplib
from algo.comparison_status import classify,BETTER,EQUAL,POSITIVE,FAILED


@lru_cache(maxsize=32)
def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))


@lru_cache(maxsize=32)
def raw(name,n):
    path=(ROOT/f'data/static_small/n{n}'/(name+'.txt') if n in [25,50]
          else ROOT/'data/instances'/(name+'.vrp'))
    if n in [25,50]:return vrplib.read_instance(path,instance_format='solomon',compute_edge_weights=False)
    return vrplib.read_instance(path,compute_edge_weights=False)


@lru_cache(maxsize=8192)
def evaluate(name,n,routes):
    """Coordonnées originales, arcs entiers x10, départ zéro, aucun noyau du solveur."""
    r=raw(name,n);assert len(r['demand'])==n+1
    xy=r['node_coord'];windows=r['time_window'];services=r.get('service_time',0)
    def edge(a,b):return math.floor(10*math.hypot(float(xy[a][0]-xy[b][0]),float(xy[a][1]-xy[b][1])))
    seen=[];total=travel=waiting=service=0;errors=[]
    if len(routes)>int(r['vehicles']):errors.append('flotte')
    assert float(windows[0][0])==0
    for route in routes:
        clock=load=0;previous=0
        for client in route:
            if not isinstance(client,numbers.Integral) or isinstance(client,bool) or not 1<=client<=n:
                errors.append('identifiant');break
            seen.append(client);leg=edge(previous,client)
            # L'hypot est symétrique et ne dépend d'aucun horaire de départ.
            assert leg==edge(client,previous)
            arrival=clock+leg;begin=max(arrival,round(10*float(windows[client][0])))
            if begin>round(10*float(windows[client][1])):errors.append('fenetre')
            s=round(10*float(services[client] if hasattr(services,'__len__') else services))
            travel+=leg;waiting+=begin-arrival;service+=s
            clock=begin+s;load+=float(r['demand'][client]);previous=client
        back=edge(previous,0);travel+=back;clock+=back;total+=clock
        if load>float(r['capacity'])+1e-8:errors.append('capacite')
        if clock>round(10*float(windows[0][1])):errors.append('horizon')
    if sorted(seen)!=list(range(1,n+1)):errors.append('couverture')
    assert total==travel+waiting+service
    return dict(valid=not errors,errors=errors,duration=total/10,travel=travel/10,
                waiting=waiting/10,service=service/10,vehicles=len(routes))


def check(name,n,routes):
    return evaluate(name,int(n),tuple(sorted(tuple(route) for route in routes if len(route))))


def main():
    out=ROOT/'results/presentation_status';out.mkdir(parents=True,exist_ok=True)
    original=ROOT/'results/gap_tables/DETAIL_TOUS_LES_ECARTS.csv'
    data=pd.read_csv(original);fresh=pd.read_csv(ROOT/'results/final_static/TOUS_LES_ESSAIS.csv')
    refs={r.source:r.reference_source for r in fresh.itertuples()}
    rows=[];issues=[]
    for index,row in data.iterrows():
        if pd.isna(row.ecart_pct):continue
        try:
            record=read(str(ROOT/row.source));result=record.get('result',record)
            own=check(row.instance,row.n,result['routes'])
            if str(row.type_reference).startswith('Plan public'):
                refpath=ROOT/'data/instances'/(row.instance+'.sol')
                ref_routes=vrplib.read_solution(refpath)['routes']
                kind='Plan public sélectionné pour la distance, réévalué en durée ; pas optimum temporel'
            else:
                saved=record.get('reference',{})
                refpath=ROOT/(saved.get('source') or refs[row.source])
                reference_record=read(str(refpath))
                assert reference_record.get('method')=='ortools'
                ref_routes=reference_record['result']['routes']
                kind='OR-Tools indépendant, solution heuristique en durée, sans preuve d’optimalité'
            reference=check(row.instance,row.n,ref_routes)
            assert own['valid'] and reference['valid'],(own,reference)
            assert abs(own['duration']-row.duree)<1e-7
            assert abs(reference['duration']-row.reference_duree)<1e-7
            delta=100*(own['duration']/reference['duration']-1)
            assert abs(delta-row.ecart_pct)<1e-7
            status=classify(own['duration'],reference['duration'])
            same_plan=tuple(sorted(tuple(r) for r in result['routes']))==tuple(sorted(tuple(r) for r in ref_routes))
            cause=('Référence heuristique battue avec les mêmes coûts et contraintes' if status==BETTER
                   else 'Même plan et même coût, optimalité non démontrée' if status==EQUAL and same_plan
                   else 'Plans distincts de même coût, optimalité non démontrée' if status==EQUAL
                   else 'Coût supérieur au comparateur réalisable')
            rows.append(dict(index=index,instance=row.instance,n=row.n,campagne=row.campagne,methode=row.methode,
                graine=row.graine,duree_solution=own['duration'],duree_reference=reference['duration'],
                ancien_ecart_pct=row.ecart_pct,nouveau_calcul_pct=delta,statut=status,cause=cause,
                statut_reference=kind,source=row.source,source_reference=refpath.relative_to(ROOT).as_posix(),
                correction='Aucune correction des coûts ; qualification de la comparaison',verification='OK',
                trajets_solution=own['travel'],attentes_solution=own['waiting'],services_solution=own['service'],
                trajets_reference=reference['travel'],attentes_reference=reference['waiting'],services_reference=reference['service']))
        except Exception as error:issues.append(dict(index=index,source=row.source,error=repr(error)))
    (out/'ANOMALIES.json').write_text(json.dumps(issues,indent=2,ensure_ascii=False),encoding='utf-8')
    if issues:raise RuntimeError(f'{len(issues)} contradictions à examiner : '+str(out/'ANOMALIES.json'))
    audited=pd.DataFrame(rows);audited.to_csv(out/'AUDIT_COMPARAISONS.csv',index=False,encoding='utf-8-sig')
    cases=audited[audited.ancien_ecart_pct.le(0)]
    cases.to_csv(out/'CAS_NEGATIFS_ET_NULS.csv',index=False,encoding='utf-8-sig')
    aggregates=[]
    for keys,group in audited.groupby(['instance','n','campagne','methode','statut_reference']):
        values=group.nouveau_calcul_pct
        mean=float(values.mean());median=float(values.median())
        if abs(mean)<=1e-10 or abs(median)<=1e-10:
            aggregates.append(dict(instance=keys[0],n=keys[1],campagne=keys[2],methode=keys[3],
                effectif=len(values),moyenne_originale_pct=mean,mediane_originale_pct=median,
                positifs=int(values.gt(0).sum()),negatifs=int(values.lt(0).sum()),egaux=int(values.eq(0).sum()),
                interpretation=('Annulation de signes ; ne prouve aucune égalité individuelle'
                    if values.gt(0).any() and values.lt(0).any() else 'Égalités individuelles présentes ; aucun optimum déduit'),
                traitement='Moyenne positive conditionnelle avec effectif, ou non applicable'))
    pd.DataFrame(aggregates).to_csv(out/'MOYENNES_MEDIANES_NULLES.csv',index=False,encoding='utf-8-sig')
    summary=dict(validated=True,records_checked=len(audited),nonpositive_records=len(cases),
        improved_reference=int(audited.statut.eq(BETTER).sum()),equal_reference=int(audited.statut.eq(EQUAL).sum()),
        positive=int(audited.statut.eq(POSITIVE).sum()),errors=0,
        zero_mean_or_median_groups=len(aggregates),
        raw_source_sha256=hashlib.sha256(original.read_bytes()).hexdigest(),
        scope='Recorded comparisons, including archive views and multiple references per trial; not new solve counts',
        invariants='Fixed symmetric floor-to-tenths arcs, zero departures, service-start windows, waiting/service/return, capacity/fleet/horizon/coverage')
    (out/'AUDIT.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding='utf-8')
    columns=['instance','n','methode','campagne','duree_solution','duree_reference','ancien_ecart_pct',
             'nouveau_calcul_pct','cause','correction','statut_reference','verification']
    text='''# Audit des comparaisons négatives et nulles — annexe technique

Les pourcentages originaux ci-dessous sont conservés pour la traçabilité ;
ils ne sont pas transformés en faux pourcentages positifs. Le livrable principal
utilise des statuts pour ces cas et des statistiques conditionnelles explicites.

Chaque ligne a été recalculée depuis les tournées et les coordonnées originales
par une simulation indépendante des noyaux et de `algo.verify`. Départs nuls,
attentes, services, retours, unités, arrondis et toutes les contraintes sont
contrôlés. Une référence OR-Tools ou un plan distance réévalué n'est pas promu
au rang d'optimum temporel. Les colonnes de décomposition et les sources sont
disponibles dans `results/presentation_status/AUDIT_COMPARAISONS.csv`.

Plusieurs lignes peuvent concerner le même essai, ses vues d'archive ou ses
références distinctes. Ce tableau n'est pas un nouveau compteur de résolutions.

'''+json.dumps(summary,indent=2,ensure_ascii=False)+'\n\n'+cases[columns].to_markdown(index=False,floatfmt='.6f')+'''

## Bilan

Terminé : contrôle de toutes les comparaisons chiffrées du registre consolidé,
qualification des références, sauvegarde des écarts et décompositions d'origine.
Aucune anomalie de faisabilité ou de coût détectée dans ce périmètre.
Les égalités ne constituent pas des preuves d'optimalité ; les améliorations
ne sont pas déclarées meilleures solutions mondiales.

Restant : renforcer les références indépendantes et obtenir davantage de preuves
temporelles si l'on veut certifier le seuil de six pour cent sur le jeu complet.
La présente passe ne crée aucune nouvelle recherche ni référence plus forte.
'''
    (ROOT/'AUDIT_GAPS_FINAL.md').write_text(text,encoding='utf-8')
    print(json.dumps(summary,indent=2,ensure_ascii=False))


if __name__=='__main__':main()
