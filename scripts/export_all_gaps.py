"""Vue complète des écarts conservés ; aucune résolution ni sélection par coût."""
from pathlib import Path
import json
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]


def main():
    out=ROOT/'results/gap_tables';out.mkdir(parents=True,exist_ok=True)
    initial=pd.read_csv(ROOT/'results/time_objective/catalogue/instances.csv')
    archive=pd.read_csv(ROOT/'results/time_objective/best_duration/COUVERTURE_472_ESSAIS.csv')
    best=archive.groupby(['instance','n']).agg(archive_essais=('seed','size'),
        archive_moyen_pct=('best_delta_pct','mean'),archive_pire_pct=('best_delta_pct','max')).reset_index()
    master=initial[['instance','n','mean_delta_reference_pct']].rename(columns={'mean_delta_reference_pct':'initial_moyen_pct'}).merge(best,on=['instance','n'],how='outer')
    details=[]
    def add(instance,n,campaign,method,seed,duration,ref,kind,gap,valid,source,budget=None,view=False):
        details.append(dict(instance=instance,n=n,campagne=campaign,methode=method,graine=seed,
            duree=duration,reference_duree=ref,type_reference=kind,ecart_pct=gap,
            gap_certifie_pct=None,realisable=bool(valid),budget_s=budget,source=source,
            vue_archive_non_nouveau_run=view))
    flat=pd.read_csv(ROOT/'results/time_objective/catalogue/flat.csv')
    for r in flat.itertuples():
        add(r.instance,r.n,'campagne_initiale',r.method,r.seed,r.duration,r.reference_duration,
            'Plan public distance reevalue en duree',r.delta_reference_pct,r.valid,r.source,r.budget_s)
    refs=initial.set_index('instance').reference_duration.to_dict()
    for r in archive.itertuples():
        add(r.instance,r.n,'archive_selection_budgets_mixtes','selection_archive',r.seed,r.duration,refs[r.instance],
            'Plan public distance reevalue en duree',r.best_delta_pct,True,r.source,view=True)
    fresh=pd.read_csv(ROOT/'results/final_static/TOUS_LES_ESSAIS.csv')
    examples={}
    for r in fresh.itertuples():
        add(r.instance,r.n,r.campaign,r.method,r.seed,r.duration,r.independent_reference,
            'OR-Tools independant du lot, non optimalite prouvee',r.delta_independent_pct,r.valid,r.source,r.budget_s)
        if pd.notna(r.public_duration):
            add(r.instance,r.n,r.campaign,r.method,r.seed,r.duration,r.public_duration,
                'Plan public distance reevalue en duree',r.delta_public_pct,r.valid,r.source,r.budget_s)
        if r.method=='refined' and r.valid:
            examples.setdefault((r.instance,r.n),dict(instance=r.instance,n=r.n,
                exemple_ecart_pct=r.delta_independent_pct,exemple_methode=r.method,
                exemple_reference='OR-Tools independant du lot',exemple_campagne=r.campaign,exemple_source=r.source))
    base=ROOT/'results/terminal_validation'
    index=json.loads((base/'SOURCE_INDEX.json').read_text())
    for label in index:
        candidates=list(base.glob('*/campaigns/'+label))+list((base/'complements').glob(label))
        assert len(candidates)==1
        for path in sorted(candidates[0].glob('*.json')):
            record=json.loads(path.read_text(encoding='utf-8'))
            if 'measurement' not in record:continue
            r=record['measurement'];source=path.relative_to(ROOT).as_posix()
            add(r['instance'],r['n'],label,r['method'],r['seed'],r['duration'],r['reference_duration'],
                r['reference_type'],r['delta_reference_pct'],r['valid'],source,r['requested_seconds'])
            if r['method']=='refined' and r['valid'] and r['reference_duration'] is not None:
                examples[(r['instance'],r['n'])]=dict(instance=r['instance'],n=r['n'],
                    exemple_ecart_pct=r['delta_reference_pct'],exemple_methode='refined',
                    exemple_reference=r['reference_type'],exemple_campagne=label,exemple_source=source)
            elif r['method']=='refined' and r['valid']:
                examples.setdefault((r['instance'],r['n']),dict(instance=r['instance'],n=r['n'],
                    exemple_ecart_pct=None,exemple_methode='refined',exemple_reference='NON DISPONIBLE',
                    exemple_campagne=label,exemple_source=source))
    master=master.merge(pd.DataFrame(examples.values()),on=['instance','n'],how='outer')
    # Les deux cas présents seulement dans l'audit des références restent identifiés.
    for path in (ROOT/'results/final_static/reference_audit').glob('*_25.json'):
        record=json.loads(path.read_text());r=record['comparison'];result=record['result']
        if not ((master.instance==r['instance']) & (master.n==25)).any():
            master=pd.concat([master,pd.DataFrame([dict(instance=r['instance'],n=25,
                exemple_reference='Controle OR-Tools de reference seulement ; aucun ecart de notre methode',
                exemple_source=path.relative_to(ROOT).as_posix())])],ignore_index=True)
        add(r['instance'],25,'audit_reference_publiee','ortools_reference',4101,result['cost'],None,
            'Reference seulement ; comparaison Phonin non certifiee compatible',None,True,
            path.relative_to(ROOT).as_posix(),3)
    master=master.sort_values(['n','instance']).reset_index(drop=True)
    master['n']=master.n.astype(int)
    master.to_csv(out/'TABLEAU_GAPS_TOUTES_INSTANCES.csv',index=False,encoding='utf-8-sig')
    ledger=pd.DataFrame(details).sort_values(['n','instance','campagne','methode','graine'])
    ledger.to_csv(out/'DETAIL_TOUS_LES_ECARTS.csv',index=False,encoding='utf-8-sig')
    summary=master.groupby('n').agg(instances=('instance','size'),
        archive_moyenne_par_instance_pct=('archive_moyen_pct','mean'),
        pire_essai_archive_pct=('archive_pire_pct','max')).reset_index()
    summary.to_csv(out/'SYNTHESE_PAR_TAILLE.csv',index=False,encoding='utf-8-sig')
    short=master[['instance','n','initial_moyen_pct','archive_moyen_pct','archive_pire_pct',
                  'exemple_ecart_pct','exemple_reference','exemple_campagne']].copy()
    short.columns=['Instance','Clients','Initial moyen (%)','Archive moyenne (%)','Pire archive (%)',
                   'Exemple renforce (%)','Reference de cet exemple','Campagne de cet exemple']
    header='''# Tous les écarts des instances CVRPTW statiques testées

Une ligne par instance/taille : 363 lignes, dont deux contrôles de référence
sans essai de notre méthode (C105/25 et C106/25). Les 361 autres ont été résolues
avec au moins un de nos profils. Les variantes TD sont hors de ce modèle.

- **Initial / archive** : écarts signés à la durée du plan public distance
  réévalué, même référence pour ces deux colonnes. L'archive sélectionne les
  meilleurs résultats conservés à budgets variables ; elle n'est pas une
  nouvelle campagne uniforme. Sa pire valeur est le maximum parmi ses graines.
- **Exemple renforcé** : un essai identifié du profil renforcé, avec sa propre
  référence et campagne. La priorité va aux commandes terminal puis aux pilotes ;
  les exemples ne sont pas sélectionnés selon leur coût. Les références des
  colonnes archive et exemple peuvent différer : ne pas en déduire un gain direct.
- **ND** : résultat, référence ou comparaison non disponible. Les échecs et tous
  les autres profils sont dans `DETAIL_TOUS_LES_ECARTS.csv`, avec les sources.
- Aucun de ces écarts aux plans réalisables ne constitue un gap certifié à un
  optimum temporel. Les valeurs négatives et nulles sont conservées.
- Le détail comprend des vues de l'archive et plusieurs références d'un même
  essai : son nombre de lignes ne constitue pas le nombre de nouveaux runs.

'''
    body=short.astype(object).where(pd.notna(short),None).to_markdown(index=False,floatfmt='.4f',missingval='ND')
    (out/'TABLEAU_GAPS_TOUTES_INSTANCES.md').write_text(header+body+'\n',encoding='utf-8')
    print(summary.to_string(index=False))
    print(json.dumps(dict(instances=len(master),detail_rows=len(ledger),folder=str(out)),indent=2))


if __name__=='__main__':main()
