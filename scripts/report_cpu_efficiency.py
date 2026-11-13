"""Tableaux et schémas CPU à partir de mesures exécutées, sans relancer les solveurs."""
from pathlib import Path
import hashlib,json,pstats,sys
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import nbformat
import numpy as np
import pandas as pd
from algo.data import load,reference
from algo.verify import verify

FOLDER=ROOT/'results/time_objective/cpu_optimization'
FIG=ROOT/'livraison/duree_figures'


def table(frame):
    from scripts.build_duration_delivery import table as render
    return render(frame)


def save(fig,name):
    fig.tight_layout();fig.savefig(FIG/(name+'.png'),dpi=160);plt.close(fig)


def analyze():
    protocol=json.loads((FOLDER/'paired_protocol.json').read_text())
    rows=[];cache={}
    for path in sorted((FOLDER/'paired').glob('*.json')):
        r=json.loads(path.read_text())
        if r['instance'] not in cache:cache[r['instance']]=load(ROOT/'data/instances'/(r['instance']+'.vrp'))
        checked=verify(r['result']['routes'],cache[r['instance']])
        assert checked['valid'] and abs(checked['duration']/10-r['duration'])<1e-7
        rows.append({k:v for k,v in r.items() if k!='result'})
    raw=pd.DataFrame(rows)
    assert len(raw)==24 and not raw.duplicated(['instance','seed','method']).any()
    before=raw[raw.method.eq('before')]
    after=raw[raw.method.eq('cached_neighbors')]
    paired=before.merge(after,on=['instance','seed','n'],suffixes=('_before','_after'),validate='one_to_one')
    assert len(paired)==12
    assert np.allclose(paired.duration_before,paired.duration_after,atol=1e-7,rtol=0)
    assert paired.trace_entries_before.eq(paired.trace_entries_after).all()
    paired['cpu_reduction_pct']=100*(1-paired.cpu_s_after/paired.cpu_s_before)
    paired['wall_reduction_pct']=100*(1-paired.wall_s_after/paired.wall_s_before)
    summary=paired.groupby(['instance','n'],as_index=False).agg(pairs=('seed','size'),
        cpu_before=('cpu_s_before','mean'),cpu_after=('cpu_s_after','mean'),
        wall_before=('wall_s_before','mean'),wall_after=('wall_s_after','mean'),
        mean_duration=('duration_after','mean'),cpu_before_std=('cpu_s_before','std'),cpu_after_std=('cpu_s_after','std'))
    summary['cpu_reduction_pct']=100*(1-summary.cpu_after/summary.cpu_before)
    overall_cpu=100*(1-paired.cpu_s_after.sum()/paired.cpu_s_before.sum())
    raw.to_csv(FOLDER/'MESURES_AVANT_APRES.csv',index=False)
    paired.to_csv(FOLDER/'PAIRES_AVANT_APRES.csv',index=False)
    summary.to_csv(FOLDER/'SYNTHESE_CACHE_CPU.csv',index=False)
    batches=[];ports=[];tasks=[]
    for path in sorted((FOLDER/'parallel').glob('workers*_rep*/batch.json')):
        batch=json.loads(path.read_text())
        batches.append({k:v for k,v in batch.items() if k not in ['cases','initializers']})
        for case in batch['cases']:
            ports.append(case)
            r=json.loads((path.parent/(case['instance']+'.json')).read_text())
            assert len(r['results'])==4 and abs(r['cpu_total_s']-r['parent_cpu_s']-r['workers_cpu_s'])<1e-7
            for result in r['results']:
                checked=verify(result['result']['routes'],cache[result['instance']])
                assert checked['valid'] and abs(checked['duration']/10-result['duration'])<1e-7
                tasks.append(dict(instance=result['instance'],seed=result['seed'],workers=case['workers'],
                    repetition=case['repetition'],duration=result['duration'],task_cpu_s=result['task_cpu_s']))
    batch_df=pd.DataFrame(batches);port_df=pd.DataFrame(ports);task_df=pd.DataFrame(tasks)
    assert len(batch_df)==6 and len(port_df)==18 and len(task_df)==72
    assert task_df.groupby(['instance','seed']).duration.agg(lambda x:x.max()-x.min()).abs().max()<1e-7
    parallel=port_df.groupby('workers',as_index=False).agg(portfolios=('instance','size'),wall_s=('wall_s','mean'),cpu_s=('cpu_total_s','mean'))
    baseline=parallel[parallel.workers.eq(1)].iloc[0]
    parallel['speedup']=baseline.wall_s/parallel.wall_s
    parallel['cpu_increase_pct']=100*(parallel.cpu_s/baseline.cpu_s-1)
    cold=batch_df.groupby('workers',as_index=False).agg(batches=('repetition','size'),startup_wall_s=('startup_wall_s','mean'),
        total_wall_s=('total_wall_s','mean'),total_cpu_s=('total_cpu_s','mean'))
    for name,frame in [('PORTEFEUILLES_PARALLELES',port_df),('MESURES_PROCESSUS',batch_df),
                       ('DEPARTS_INDIVIDUELS',task_df),('SYNTHESE_PARALLELE',parallel),('DEMARRAGE_INCLUS',cold)]:
        frame.to_csv(FOLDER/(name+'.csv'),index=False)
    fig,axes=plt.subplots(1,2,figsize=(12,4))
    x=np.arange(len(summary))
    for ax,left,right,label in [(axes[0],'cpu_before','cpu_after','CPU consommé (secondes)'),
                                (axes[1],'wall_before','wall_after','Temps écoulé (secondes)')]:
        ax.bar(x-.18,summary[left],.36,label='Avant',color='#b45309')
        ax.bar(x+.18,summary[right],.36,label='Cache',color='#128475')
        ax.set(xticks=x,xticklabels=summary.instance,ylabel=label)
        ax.tick_params(axis='x',labelrotation=20);ax.legend()
    save(fig,'cpu_cache')
    fig,axes=plt.subplots(1,2,figsize=(10,4))
    x=np.arange(len(parallel))
    axes[0].bar(x,parallel.wall_s,color='#176b89');axes[1].bar(x,parallel.cpu_s,color='#b45309')
    for ax,column,label in [(axes[0],'wall_s','Temps écoulé moyen (s)'),(axes[1],'cpu_s','CPU cumulé moyen (s)')]:
        ax.set(xticks=x,xticklabels=parallel.workers,xlabel='Nombre de processus',ylabel=label)
        for i,v in enumerate(parallel[column]):ax.text(i,v,f'{v:.2f}',ha='center',va='bottom')
    save(fig,'cpu_parallelisme')
    def sorts(path):
        stats=pstats.Stats(str(path)).stats
        return sum(value[1] for key,value in stats.items() if "'argsort' of 'numpy.ndarray'" in key[2])
    sorting_before=sorts(FOLDER/'before.prof');sorting_after=sorts(FOLDER/'after.prof')
    text=r'''### 6.12. Réduction du temps CPU et étude du parallélisme

**Trois temps à distinguer.** La durée des tournées est notre objectif métier, exprimé en unités du benchmark. Le temps écoulé du programme mesure l'attente de l'utilisateur en secondes. Le temps CPU mesure le travail utilisateur et noyau des processeurs. Le parallélisme peut réduire l'attente tout en consommant davantage de CPU : quatre processus occupés chacun dix secondes peuvent représenter environ quarante secondes CPU. Réduire le temps de calcul est un critère de performance, sans remplacer l'objectif de durée ni les contraintes de validité.

**Profilage et modification retenue.** Dans le profil renforcé, la proximité des clients était triée à nouveau à chaque demande de voisins, alors que les données d'une instance restent identiques. Sur le cas instrumenté C1_10_6, les tris NumPy passent de COUNT_BEFORE à COUNT_AFTER après ajout du cache. `DurationLocalSearch.neighbors` conserve un ordre stable couvrant les voisinages prévus et réutilise ses préfixes pour 40, 60, 80 et 120 voisins. Une demande plus grande reconstruit cet ordre ; une autre instance reçoit un nouveau cache. Le transfert des voisins vers le moteur est également évité lorsque leur nombre effectif ne change pas. Les tests comparent les listes à celles de PyVRP, y compris après agrandissement et aux bornes de taille.

Cette optimisation est développée dans notre orchestration Python ; la recherche locale reste fournie par PyVRP. Nous ne supprimons pas les vérifications pour gagner du temps. Les données, les opérateurs, les graines et l'objectif restent identiques.

**Comparaison à travail fixé.** C103, C1_10_6, R1_10_5 et RC2_10_5 sont testées avec les graines 8301–8303. Chaque version effectue les mêmes quatre départs et le même programme de recherche : 24 résolutions, soit douze paires. L'ordre avant/après alterne ; le préchauffage est exclu. Le plafond de sécurité de soixante secondes n'est jamais atteint. Les coûts et le nombre d'étapes sont identiques dans les douze paires, et toutes les solutions sont réalisables. Le profilage instrumenté sert à localiser les coûts ; les temps comparatifs ci-dessous sont mesurés sans ce profilage.

Le CPU est mesuré par `time.process_time`, qui inclut les threads natifs du processus, et le temps écoulé par `time.perf_counter`. Le tableau donne les moyennes des trois graines par instance. Le gain CPU vaut $100(1-\overline{C}_{\mathrm{après}}/\overline{C}_{\mathrm{avant}})$ ; il ne s'agit pas d'un gap de tournée au BKS.

'''.replace('COUNT_BEFORE',str(sorting_before)).replace('COUNT_AFTER',str(sorting_after))
    shown=summary[['instance','n','cpu_before','cpu_after','cpu_reduction_pct','wall_before','wall_after']].rename(columns={
        'instance':'Instance','n':'Clients','cpu_before':'CPU avant (s)','cpu_after':'CPU après (s)',
        'cpu_reduction_pct':'Réduction CPU (%)','wall_before':'Écoulé avant (s)','wall_after':'Écoulé après (s)'})
    text+=table(shown)
    text+=f'\n\nSur les douze paires, la somme des temps CPU diminue de **{overall_cpu:.2f} %**, à coût de tournée identique. Cette valeur concerne le profil renforcé et ce lot ; elle ne s’applique pas rétroactivement à toutes les campagnes ou au moteur ILS autonome.'
    text+='''

![CPU et temps écoulé avant/après réutilisation des voisinages.](../livraison/duree_figures/cpu_cache.png)

**Lecture du graphique.** Chaque paire de barres compare les mêmes trois graines, avec le même travail et les mêmes coûts finaux. À gauche, la hauteur est le CPU consommé ; à droite, le temps attendu par l'utilisateur. La baisse montre l'effet du cache, sans retirer de clients, de mouvements ou de contrôles. Les petites durées restent sensibles à la granularité des compteurs Windows et au bruit de la machine.

**Intérêt et continuité.** Après l'analyse des paramètres de recherche, cette figure étudie une accélération de l'implémentation conservant le calcul. Le cache réduit le travail répété ; le parallélisme étudié ensuite répartit ce travail sur plusieurs cœurs et répond à une autre question.

**Parallélisme testé.** Un portefeuille de quatre départs indépendants, graines 9301–9304, résout chaque instance C1_10_6, R1_10_5 et RC2_10_5. Les mêmes tâches, avec quatre départs internes chacune, sont exécutées sur un, deux puis quatre processus, avec deux répétitions et des affinités CPU enregistrées. Cela représente dix-huit portefeuilles et 72 recherches individuelles. Le meilleur résultat du portefeuille est conservé et validé ; les coûts par graine sont identiques entre les niveaux de parallélisme dans ce lot. Cette comparaison garde le travail constant : elle ne donne pas quatre fois plus de départs au mode parallèle.

Le CPU total additionne le parent et tous ses workers. Sous Windows, des handles conservés permettent de lire `GetProcessTimes` après l'arrêt des workers : le tableau des lots inclut donc aussi leurs imports, préchauffages et fermetures. Mesurer uniquement le CPU du parent aurait sous-estimé la consommation. Les tableaux par instance ci-dessous utilisent un pool déjà initialisé ; le premier chargement de l'instance et sa validation restent inclus. Les valeurs moyennes portent sur trois instances et deux répétitions, soit six portefeuilles par réglage.

'''
    text+=table(parallel.rename(columns={'workers':'Processus','portfolios':'Portefeuilles','wall_s':'Écoulé moyen (s)',
        'cpu_s':'CPU cumulé moyen (s)','speedup':'Accélération écoulée','cpu_increase_pct':'Variation CPU (%)'}))
    text+='''

![Parallélisme : attendre moins longtemps peut consommer davantage de CPU.](../livraison/duree_figures/cpu_parallelisme.png)

**Lecture des deux panneaux.** Le panneau gauche mesure le délai pour terminer les mêmes quatre recherches et valider leur meilleure solution. Le panneau droit additionne le travail CPU des processus pendant ce portefeuille. Les unités sont des secondes dans les deux cas, mais leur sens diffère : les valeurs du panneau droit ne doivent pas être divisées par le nombre de processus. Tous les résultats de durée restent identiques à travail égal dans cette expérience.

**Intérêt et choix.** Le cache réduit le CPU de chaque recherche ; multiplier les processus réduit surtout la latence. Dans le lot mesuré, le mode séquentiel optimisé reste le choix économe en CPU, tandis que plusieurs processus conviennent si le délai de réponse est prioritaire. L'autorisation du multithreading ne signifie donc pas qu'utiliser tous les cœurs minimise la consommation CPU. Notre expérimentation emploie plusieurs processus pour isoler les états et les graines sous CPython 3.12 ; ce n'est pas l'activation automatique de threads dans PyVRP.

**Démarrage et fermeture inclus.** Chaque lot suivant exécute les trois instances avec le même portefeuille. Le temps total part de la création du pool et se termine après son arrêt ; il exclut seulement le lancement initial de l'interpréteur parent, commun au protocole. Les temps CPU des workers couvrent leur vie entière. Le coût du démarrage peut réduire l'intérêt du parallélisme pour une seule petite instance.

'''
    text+=table(cold.rename(columns={'workers':'Processus','batches':'Lots','startup_wall_s':'Démarrage moyen (s)',
        'total_wall_s':'Lot complet écoulé (s)','total_cpu_s':'Lot complet CPU (s)'}))
    text+='''

**Portée et reproductibilité.** Les anciens résultats restent conservés avec leurs temps écoulés d'origine ; nous ne leur attribuons pas un CPU non mesuré. La mesure CPU actuelle concerne les nouvelles campagnes `cpu_optimization/`. Les sources avant/après, mesures par graine, coûts, contraintes et temps complets sont archivés. L'amélioration n'est pas une preuve de minimum CPU global, ni une garantie d'accélération identique sur tout ordinateur. À budget limité, le cache peut aussi laisser explorer davantage de solutions ; ce bénéfice de qualité nécessiterait une campagne distincte à budget fixé. Les meilleurs résultats précédents ne sont pas remplacés par les essais de performance.

Sources techniques : [Python, horloges de mesure](https://docs.python.org/3.12/library/time.html#time.process_time), [Windows, temps des processus](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-getprocesstimes). Les opérateurs externes restent attribués à PyVRP 0.12.2.
'''
    test_path=FOLDER/'tests.xml'
    if test_path.exists():
        xml=ET.parse(test_path).getroot()
        failures=len(list(xml.iter('failure')))+len(list(xml.iter('error')))
        skipped=len(list(xml.iter('skipped')))
        passed=len(list(xml.iter('testcase')))-failures-skipped
        text+=f'\n\n**Tests de non-régression.** La suite enregistrée après optimisation compte {passed} tests réussis, {failures} échecs et {skipped} tests ignorés. Elle inclut les comparaisons des voisinages calculés et cachés ; son fichier XML est conservé avec les mesures CPU.'
    (ROOT/'docs/TEMPS_CPU_ET_PARALLELISME.md').write_text(text+'\n',encoding='utf-8')
    info=dict(paired_runs=24,pairs=12,identical_costs=True,all_feasible=True,cpu_reduction_pct=overall_cpu,
        before_sort_calls=sorting_before,after_sort_calls=sorting_after,
        parallel_tasks=72,portfolios=18,parallel_worker_levels=[1,2,4],
        parallel_summary=parallel.to_dict('records'),cold_summary=cold.to_dict('records'))
    (FOLDER/'analysis.json').write_text(json.dumps(info,indent=2),encoding='utf-8')
    return text,info


def add_to_notebook(nb):
    from scripts.revision_duree import insert_before
    nb.cells=[c for c in nb.cells if not c.metadata.get('cpu_completion')]
    text,info=analyze()
    cell=nbformat.v4.new_markdown_cell(text);cell.metadata['cpu_completion']=True
    insert_before(nb,'## 7.',[cell])
    for c in nb.cells:
        if c.cell_type=='markdown' and c.source.startswith('### 4.4.') and 'Cache local des voisinages' not in c.source:
            marker='\n\nL’implémentation propre'
            rows='''
| Cache local des voisinages | Supprimer les tris répétés sur une instance immuable | Listes identiques à PyVRP et coûts identiques sur douze paires ; CPU mesuré en section 6.12 |
| Étude multiprocessus | Distinguer délai de réponse et CPU consommé | Un, deux et quatre processus ; parent et workers comptés, démarrage publié |'''
            assert marker in c.source
            c.source=c.source.replace(marker,rows+marker)
        if c.cell_type=='markdown' and c.source.startswith('## 7.') and 'réduction du CPU' not in c.source:
            c.source=c.source.replace('Les fichiers `results/time_objective/catalogue/runs/`',
                'La section 6.12 mesure séparément la réduction du CPU par cache et la baisse du temps écoulé par parallélisme, avec le coût de tous les processus. Le profil économe ne confond pas ces deux objectifs.\n\nLes fichiers `results/time_objective/catalogue/runs/`')
    return info


def main():
    from scripts.revision_duree import write_markdown
    path=ROOT/'notebooks/Livrable_Final_CVRPTW.ipynb'
    nb=nbformat.read(path,as_version=4)
    code=[c.source for c in nb.cells if c.cell_type=='code']
    info=add_to_notebook(nb)
    assert code==[c.source for c in nb.cells if c.cell_type=='code']
    nbformat.validate(nb);nbformat.write(nb,path);write_markdown(nb)
    print(json.dumps(info,indent=2))


if __name__=='__main__':main()
