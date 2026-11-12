"""Document executed v6 trials, including all regressions and cumulative costs."""
from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import nbformat
from algo.data import load
from algo.verify import verify
from scripts.analyze_v6 import analyze,BASE
from scripts.export_report import markdown_table
from scripts.build_ils_v5_delivery import execute

LABELS={'baseline':'ILS de référence','cache':'Cache de préfixes','temporal':'Groupes temporels','combined':'Cache et groupes temporels'}


def main():
    dev,ds,_,da=analyze('development')
    df,summary,cases,analysis=analyze('validation')
    target,ts,_,ta=analyze('targeted_120')
    follow,fs,_,fa=analyze('cache_followup')
    cold=json.loads((BASE/'cold_portfolio/analysis.json').read_text())
    out=BASE/'updated_archive';out.mkdir(exist_ok=True)
    archive=[]
    originals=ROOT/'results/optimization_v5/portfolio_intensified'
    for path in sorted(originals.glob('*_*.json')):
        previous=json.loads(path.read_text())
        name=previous['instance']
        record=dict(instance=name,origin=str(path.relative_to(ROOT)),origin_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                    result=previous['result'],previous_gap=previous['gap_pct'],gap_pct=previous['gap_pct'],
                    total_effort_s=previous['total_effort_s'],additional_runs=[])
        rows=target[target.instance.eq(name)]
        if len(rows):
            assert len(rows)==2
            costs=[]
            for _,r in rows.iterrows():
                file=BASE/'targeted_120/runs'/f"{name}_{int(r.seed)}_{r.profile}.json"
                measured=json.loads(file.read_text())
                record['additional_runs'].append(dict(path=str(file.relative_to(ROOT)),sha256=hashlib.sha256(file.read_bytes()).hexdigest()))
                record['total_effort_s']+=measured['total_s']
                costs.append(measured)
            winner=min(costs,key=lambda r:r['result']['cost'])
            if winner['result']['cost']<record['result']['cost']-1e-8:
                record.update(result=winner['result'],gap_pct=winner['gap_pct'])
        ins=load(ROOT/'data/instances'/(name+'.vrp'))
        checked=verify(record['result']['routes'],ins)
        assert checked['valid'] and abs(checked['distance']/10-record['result']['cost'])<1e-7
        (out/(name+'.json')).write_text(json.dumps(record),encoding='utf-8')
        archive.append({k:record[k] for k in ['instance','previous_gap','gap_pct','total_effort_s']})
    updated=pd.DataFrame(archive)
    assert len(updated)==12
    updated.to_csv(out/'summary.csv',index=False)
    archive_analysis=dict(instances=12,mean_gap=float(updated.gap_pct.mean()),worst_gap=float(updated.gap_pct.max()),
                          mean_effort_s=float(updated.total_effort_s.mean()),
                          scope='Fixed twelve-instance archive; nine unchanged, three targeted with two additional 120s branches; all branches charged')
    (out/'analysis.json').write_text(json.dumps(archive_analysis,indent=2))
    comparison=analysis['comparisons'][0]
    gain=comparison['improvement_pp'];ci=comparison['instance_bootstrap95']
    qualifies=gain>.2 and ci[0]>0
    decision=dict(recommended='combined' if qualifies else 'baseline',
                  adopted_by_default=False,reason='A larger repeated confirmation is required before changing the public baseline defaults',
                  paired_validation=comparison,validation_instances=12,seeds_per_instance=2)
    decision['cache_followup']=fa['comparisons']
    decision['cache_followup_scope']='Exploratory post-hoc analysis; 24 new cache runs and 24 reused baseline measurements'
    (BASE/'decision.json').write_text(json.dumps(decision,indent=2))
    figures=ROOT/'livraison/ils_v6_figures';figures.mkdir(exist_ok=True)
    fig,ax=plt.subplots(figsize=(8,3.2))
    ss=ds.copy();ss.profile=ss.profile.map(LABELS)
    ax.bar(ss.profile,ss.mean_gap,color=['#64748b','#0f766e','#0891b2','#b45309'])
    ax.set(ylabel='Gap moyen (%)',title='Développement : 6 instances × 2 graines, plafond 20 s')
    ax.tick_params(axis='x',labelrotation=10);fig.tight_layout();fig.savefig(figures/'development.png',dpi=160);plt.close(fig)
    pivot=cases.pivot(index='instance',columns='profile',values='mean_gap')
    fig,ax=plt.subplots(figsize=(8,4))
    x=np.arange(len(pivot));ax.plot(x,pivot.baseline,'o-',label=LABELS['baseline'])
    ax.plot(x,pivot.combined,'s-',label=LABELS['combined'])
    ax.axhline(6,linestyle='--',color='#b45309',label='Cible 6 %')
    ax.set_xticks(x,pivot.index,rotation=55,ha='right');ax.set_ylabel('Gap moyen à la BKS (%)');ax.legend()
    fig.tight_layout();fig.savefig(figures/'validation.png',dpi=160);plt.close(fig)
    fixed=pd.read_csv(BASE/'fixed_work_summary.csv')
    fig,ax=plt.subplots(figsize=(7,3))
    ax.bar(fixed.instance,fixed.speedup,color='#0f766e');ax.axhline(1,color='#64748b',linestyle='--')
    ax.set(ylabel='Temps complet / temps avec cache',title='Travail identique : médiane de six répétitions')
    ax.tick_params(axis='x',labelrotation=25);fig.tight_layout();fig.savefig(figures/'speed.png',dpi=160);plt.close(fig)
    stats=summary[['profile','runs','mean_gap','std_gap','worst_gap','under6','under7','mean_search_s','mean_total_s']].copy()
    stats.profile=stats.profile.map(LABELS)
    stats.columns=['Méthode','Essais','Gap moyen %','Écart-type','Pire gap %','Sous 6 %','Sous 7 %','Recherche s','Total s']
    percase=pivot.rename(columns=LABELS).reset_index()
    target_table=target.pivot(index='instance',columns='profile',values='gap_pct').rename(columns=LABELS).reset_index()
    previous=pd.read_csv(originals/'summary.csv').set_index('instance')
    target_table.insert(1,'Avant %',target_table.instance.map(previous.gap_pct))
    conclusion=("La combinaison présente un gain moyen apparié positif sur ce lot ; cela justifie une confirmation plus répétée avant de changer le défaut."
                if qualifies else "Les résultats ne satisfont pas notre règle exploratoire de confirmation : le moteur de référence reste le défaut.")
    follow_table=fs[['profile','runs','mean_gap','worst_gap','mean_search_s']].copy()
    follow_table.profile=follow_table.profile.map(LABELS)
    follow_table.columns=['Méthode','Mesures comparées','Gap moyen %','Pire gap %','Recherche s']
    follow_text=f"""## Suivi exploratoire du cache seul

Après lecture de la confirmation de la combinaison, 24 résolutions supplémentaires isolent le cache seul sur les mêmes douze instances et graines, au même plafond de 40 secondes. Les 24 mesures ILS de référence déjà obtenues sont réutilisées, pas exécutées ni comptées une seconde fois. Les listes initiales de tournées sont comparées exactement par empreinte, au-delà de la seule égalité des coûts.

{markdown_table(follow_table)}

Le gain apparié du cache seul est {fa['comparisons'][0]['improvement_pp']:.3f} point, intervalle exploratoire {fa['comparisons'][0]['instance_bootstrap95']}. Cette analyse est effectuée après observation d’un autre candidat sur le même lot : elle ne remplace pas une confirmation indépendante et ne déclenche pas un changement de défaut. Ses essais ont été réalisés dans un lot séparé avec le même nombre de processus, ce qui ajoute une limite à la comparaison des temps. Les 24 nouveaux essais sont identifiés dans `cache_followup/` ; les tableaux de comparaison contiennent aussi les 24 références réutilisées.
"""
    text=f"""# Évaluations avec cache et regroupement temporel — CVRPTW

## Périmètre et invariants

Cette étude complète v5 ; elle ne remplace pas ses résultats. Le problème reste le CVRPTW à distance DIMACS : chaque client exactement une fois, capacité limitée, fenêtres strictes sur le début du service, attente autorisée, retour au dépôt et flotte maximale. Les matrices, demandes, services et fenêtres sont inchangés. Les BKS ne sont lues qu’après les résolutions.

## Changements réellement implémentés

**Cache exact de préfixes.** `algo/cached_local.py` mémorise, après p clients inchangés, l’heure de départ, la distance parcourue et la charge cumulée. Lors d’un mouvement, l’évaluation repart de cet état et recalcule le suffixe modifié, puis le retour au dépôt. Les contrôles de capacité et de fenêtres restent complets sur cette partie. Le préfixe doit correspondre exactement au préfixe utilisé pour construire le cache ; cette précondition est assurée par les mouvements. Une inversion 2-opt conserve seulement le préfixe avant l’inversion. L’évaluation entière indépendante est conservée pour les solutions retournées.

Les tableaux sont dimensionnés selon la plus longue tournée actuelle et agrandis si nécessaire. Une première allocation selon le nombre total de clients était plus lente : le diagnostic négatif est conservé dans `initial_cache_diagnostic.md`. Les caches sont reconstruits après chaque mouvement ; nous ne prétendons pas à une évaluation constante de toute la recherche. Le recuit direct n’est pas accéléré par ce cache de recherche locale.

**Regroupement de tournées complètes.** `algo/temporal_groups.py` rapproche les clients selon la distance, l’attente minimale inévitable et le retard minimal inévitable entre leurs fenêtres. Le score dirigé est $d_{{ij}}+0,2\\max(0,e_j-l_i-s_i-t_{{ij}})+\\max(0,e_i+s_i+t_{{ij}}-l_j)$ ; le score symétrique retient le minimum des deux sens. Pour chaque tournée pivot tirée aléatoirement, les tournées partenaires sont classées par leur meilleur couple de clients. Le score est une heuristique de classement, pas un nouveau coût ni une preuve de faisabilité. Le nombre de clients par groupe et la limite de flotte gardent les règles de la référence.

`algo/cached_iterated.py` et `algo/experimental_v6.py` constituent des variantes explicites, pour conserver les sources de référence utilisées dans les anciennes mesures.

## Vitesse à travail identique

Les deux recherches locales exécutent les mêmes mouvements, mêmes graines, mêmes limites et mêmes solutions finales, sur six solutions réalisables à 1 000 clients produites précédemment. La compilation est exclue, l’ordre des deux variantes alterne et six répétitions sont réalisées sur un même cœur logique. Un ratio supérieur à 1 indique un gain. Les différences de quelques pour cent restent sensibles au bruit sur ces courtes mesures ; le gain observé sur R2 est plus marqué. Ce tableau ne démontre pas à lui seul une amélioration du gap.

{markdown_table(fixed.rename(columns=dict(instance='Instance',cached='Cache s',full='Complet s',speedup='Ratio')))}

## Développement et ablation

48 résolutions, six instances `_10_5`, graines 1701 et 1702, plafond de 20 secondes. Les quatre variantes isolent cache seul, regroupement seul et combinaison. Les paramètres numériques de l’ILS restent ceux de la référence. La combinaison est retenue pour la confirmation avant lecture de ses résultats.

{markdown_table(ds[['profile','runs','mean_gap','worst_gap']].assign(profile=lambda d:d.profile.map(LABELS)).rename(columns=dict(profile='Variante',runs='Essais',mean_gap='Gap moyen %',worst_gap='Pire gap %')))}

## Validation distincte à budget court

48 résolutions sur douze autres instances `_10_6` et `_10_7`, graines 1801 et 1802, plafond de 40 secondes. Les mêmes départs sont construits avec douze tentatives et vérifiés par paire ; leur construction est comptée séparément dans chaque résolution. Les six processus sont placés sur des cœurs logiques distincts ; le préchauffage est hors budget. Les géographies peuvent avoir figuré dans d’autres campagnes historiques : le lot est séparé du réglage v6, sans prétendre à une validation totalement aveugle.

{markdown_table(stats)}

L’amélioration moyenne appariée de la combinaison est **{gain:.3f} point de pourcentage**, avec intervalle bootstrap exploratoire par instance **[{ci[0]:.3f} ; {ci[1]:.3f}]**. Un nombre positif favorise la nouvelle variante. Les douze instances sont rééchantillonnées en conservant leurs deux graines ensemble. Deux graines restent limitées pour estimer la variabilité. {conclusion}

Les moyennes de ce nouveau lot ne se comparent pas directement aux 10,127 % de v5, mesurés sur d’autres instances. Chaque tableau inclut toutes les instances prévues et chaque méthode possède le même nombre de répétitions.

{markdown_table(percase)}

## Diagnostic ciblé à 120 secondes supplémentaires

Les trois cas difficiles connus repartent exactement de l’archive v5, graine 1901, avec 120 secondes pour la référence et 120 pour la variante. Ce sont six résolutions supplémentaires sur trois départs déjà optimisés, pas des départs neufs. Une seule graine par cas interdit une conclusion robuste sur la méthode à long budget.

{markdown_table(target_table)}

L’archive globale garde ses douze instances : neuf solutions sont inchangées et trois retiennent la meilleure solution réalisable des deux branches, choisie par distance. Les deux branches sont facturées, même si l’une n’améliore rien. Le gap moyen de cette archive est **{archive_analysis['mean_gap']:.3f} %**, son pire cas **{archive_analysis['worst_gap']:.3f} %**, pour un effort cumulé moyen **{archive_analysis['mean_effort_s']:.1f} secondes par instance**, avec budgets désormais différents selon les cas. Ce n’est pas une moyenne de résolutions indépendantes de 40 ou 120 secondes et ce n’est pas une comparaison équitable du temps nécessaire à partir de zéro.

## Reproduction et limites

Les JSON, sources figées, empreintes, CSV et protocoles sont dans `results/optimization_v6/`. `python scripts/analyze_v6.py` revérifie les sources, les données, les couvertures, les capacités, les fenêtres, les retours, les distances et les départs appariés. Chaque reprise refuse un protocole différent ; une nouvelle expérience doit utiliser un nouveau `--label`.

Les tests différentiels couvrent aussi des distances non métriques, des temps de trajet distincts des distances et des fenêtres serrées. Une croissance de tournée créée par 2-opt* teste l’agrandissement des caches. Les temps restent dépendants du matériel et des mesures parallèles. Le trafic variable, plus de 1 000 clients et une garantie d’optimalité ne sont pas démontrés.

Sources : [Ribas et ses coauteurs, ILS pour le VRPTW](https://luizsatoru.github.io/conteudo/artigos/PAPER%20IESM2011-SABIR.pdf), [Vidal et ses coauteurs, informations de séquences et fenêtres](https://www.cirrelt.ca/documentstravail/cirrelt-2012-23.pdf). Les composants sont adaptés à notre code ; les performances des publications ne sont pas attribuées à notre solveur.
"""
    cold_text=f"""## Ensemble de trois recherches depuis des départs neufs

Pour chaque couple instance/graine de la validation, une seconde combinaison utilise uniquement les trois trajectoires correspondantes : référence, variante combinée et cache seul. Elle ne lit ni archive historique, ni autre graine. Les 24 ensembles couvrent les douze instances et deux graines. Le partitionnement dispose d’au plus deux secondes et tous les temps de construction et de recherche des trois entrées sont facturés.

Le meilleur des trois essais atteint {cold['mean_best_input_gap']:.3f} % de gap moyen ; la recombinaison atteint **{cold['mean_gap']:.3f} %**, avec pire gap **{cold['worst_gap']:.3f} %** et effort cumulé moyen **{cold['mean_effort_s']:.1f} secondes par ensemble**. Une grande part du gain vient donc de l’effort supplémentaire et du meilleur des trois essais ; l’apport marginal du partitionnement est plus faible. Nous n’avons pas exécuté de référence unique à partir de zéro avec ce même effort total : ce résultat ne démontre pas une supériorité à temps égal. Les 24 recombinaisons réutilisent des résolutions déjà comptées et ne sont pas 72 nouvelles recherches.

Le code `algo/portfolio_v6.py` fournit cette combinaison comme méthode explicite. La commande `python scripts/run_portfolio_v6.py R2_10_6 --seconds-per-search 40 --partition-seconds 2 --seed 1801` lance trois recherches, et non une résolution de 40 secondes. Cette nouvelle commande partage une seule construction initiale, alors que les mesures du tableau facturent les trois constructions effectivement réalisées dans les campagnes d’origine ; le temps de la commande doit être mesuré séparément. Son fonctionnement est testé, sans attribuer au nouveau point d’entrée une campagne complète non exécutée.

Les sorties individuelles de ces ensembles sont dans `cold_portfolio/flat.csv` et leurs sources sont vérifiables par empreinte. Cette option reste expérimentale ; le moteur de référence conserve son rôle de défaut.
"""
    text+='\n\n'+follow_text+'\n\n'+cold_text
    (ROOT/'docs/AMELIORATIONS_ILS_V6.md').write_text(text,encoding='utf-8')
    notebook=nbformat.v4.new_notebook()
    notebook.cells=[nbformat.v4.new_markdown_cell(text),nbformat.v4.new_code_cell(
        "from pathlib import Path\nfrom IPython.display import Image, display\nROOT=next(p for p in [Path.cwd(),*Path.cwd().parents] if (p/'algo/experimental_v6.py').exists())\n"+
        '\n'.join(f"display(Image(filename=str(ROOT/'livraison/ils_v6_figures/{n}.png')))" for n in ['speed','development','validation']))]
    execute(notebook,ROOT/'notebooks/Ameliorations_ILS_V6.ipynb')
    mainpath=ROOT/'notebooks/Livrable_Final_CVRPTW.ipynb'
    nb=nbformat.read(mainpath,as_version=4)
    nb.cells=[c for c in nb.cells if not c.metadata.get('ils_v6_extension')]
    brief=f"""## 10. Cache des évaluations et regroupement temporel

Cette nouvelle étude CVRPTW ajoute un cache exact du préfixe inchangé des tournées et une sélection spatiale et temporelle de tournées complètes. Les contrôles et l’objectif restent identiques. Les résultats v5 précédents restent identifiés par leur propre lot.

Après 48 essais de réglage sur six instances, 48 essais appariés de confirmation portent sur douze autres instances à 1 000 clients, deux graines et un plafond de 40 secondes, avec construction séparée.

{markdown_table(stats)}

{conclusion} L’amélioration appariée est {gain:.3f} point, intervalle exploratoire [{ci[0]:.3f} ; {ci[1]:.3f}]. Les résultats détaillés, l’ablation et les limites figurent dans `docs/AMELIORATIONS_ILS_V6.md` et le notebook exécuté `Ameliorations_ILS_V6.ipynb`.

Un suivi exploratoire ajoute 24 résolutions du cache seul en réutilisant les 24 mesures de référence. Son gap moyen est {fs.set_index('profile').loc['cache','mean_gap']:.3f} %, contre {fs.set_index('profile').loc['baseline','mean_gap']:.3f} % pour la référence. Ce suivi est effectué après lecture de la confirmation et ne constitue pas une nouvelle validation indépendante.

En combinant les trois trajectoires issues de chaque même couple instance/graine, les 24 ensembles obtiennent {cold['mean_gap']:.3f} % de gap moyen, pire {cold['worst_gap']:.3f} %, pour un effort cumulé moyen de {cold['mean_effort_s']:.1f} secondes. Ces trois recherches et leurs constructions sont toutes facturées. Il manque une référence unique au même effort total pour conclure à une supériorité ; ce bilan ne remplace pas la comparaison à 40 secondes.

Sur trois cas difficiles, six essais supplémentaires à 120 secondes repartent de l’archive déjà optimisée. La moyenne de l’archive à douze instances devient {archive_analysis['mean_gap']:.3f} %, pire cas {archive_analysis['worst_gap']:.3f} %, avec un effort cumulé moyen de {archive_analysis['mean_effort_s']:.1f} secondes par instance. Neuf solutions restent inchangées ; les trois autres facturent les deux branches de recherche. Ce bilan à budgets hétérogènes ne remplace pas la comparaison à 40 secondes.
"""
    cell=nbformat.v4.new_markdown_cell(brief);cell.metadata['ils_v6_extension']=True;nb.cells.append(cell)
    cell=nbformat.v4.new_code_cell("display(Image(filename=str(ROOT/'livraison/ils_v6_figures/validation.png')))")
    cell.metadata.update(ils_v6_extension=True,figure_captions=['Confirmation v6 : douze instances distinctes, deux graines, même plafond de 40 secondes ; tous les cas.'])
    nb.cells.append(cell)
    execute(nb,mainpath)
    (ROOT/'LIVRABLE_FINAL.md').write_text('\n\n'.join(c.source for c in nb.cells if c.cell_type=='markdown'),encoding='utf-8')
    df.to_csv(ROOT/'livraison/RESULTATS_ILS_V6.csv',index=False)
    (ROOT/'livraison/RESULTATS_ILS_V6.html').write_text('<!doctype html><meta charset="utf-8"><title>CVRPTW v6</title><h1>Validation : tous les 48 essais</h1>'+stats.to_html(index=False)+df.to_html(index=False),encoding='utf-8')
    readme=ROOT/'README.md'
    previous_text=readme.read_text(encoding='utf-8')
    previous_text=previous_text.split('<!-- V6_CURRENT -->')[0]
    previous_text+=f"\n<!-- V6_CURRENT -->\n## Nouvelle étude v6\n\n48 essais de développement, 48 de confirmation à 1 000 clients et six diagnostics à 120 secondes. Gain apparié de la combinaison cache/groupes temporels : {gain:.3f} point, intervalle exploratoire [{ci[0]:.3f} ; {ci[1]:.3f}]. Le moteur public de référence reste inchangé ; la nouvelle variante est accessible avec `--method ils_v6`.\n\nL’archive à budgets cumulés hétérogènes atteint {archive_analysis['mean_gap']:.3f} % en moyenne, pire {archive_analysis['worst_gap']:.3f} %, effort moyen {archive_analysis['mean_effort_s']:.1f} s par instance. Ce n’est pas un résultat obtenu à partir de zéro en 40 secondes.\n\n[Explications v6](docs/AMELIORATIONS_ILS_V6.md), [notebook exécuté](notebooks/Ameliorations_ILS_V6.ipynb), [tous les résultats](livraison/RESULTATS_ILS_V6.html).\n"
    readme.write_text(previous_text,encoding='utf-8')
    with readme.open('a',encoding='utf-8') as handle:
        handle.write(f"\nLe suivi du cache seul contient 24 nouvelles résolutions et réutilise 24 références, sans les recompter. Les 24 ensembles de trois recherches depuis des départs neufs atteignent {cold['mean_gap']:.3f} % en moyenne, pour {cold['mean_effort_s']:.1f} s d’effort cumulé moyen, pire {cold['worst_gap']:.3f} %. Ce bilan n’est pas une comparaison à 40 secondes.\n\n`python scripts/run_portfolio_v6.py R2_10_6 --seconds-per-search 40 --seed 1801` lance explicitement trois recherches. `--method ils_cached` dans la CLI principale teste le cache seul. `python scripts/validate_v6.py` contrôle l’édition courante après les tests.\n")
    (ROOT/'livraison/LIRE_DABORD.md').write_text("""# Livraison actuelle — étude CVRPTW v6

Ouvrir `RAPPORT_CVRPTW.pdf` ou `../notebooks/Livrable_Final_CVRPTW.ipynb`. Les sections 9 et 10 distinguent les études successives ; leurs populations et budgets ne se mélangent pas.

`VALIDATION.json` pointe vers `validation_ils_v6.json`, justificatif courant. Les reçus v5 et antérieurs décrivent leurs éditions historiques.

`RESULTATS_ILS_V6.html` et `.csv` : 48 confirmations à 1 000 clients. Le suivi du cache seul ajoute 24 recherches et réutilise les 24 références déjà mesurées. Les 24 ensembles de trois recherches constituent un autre bilan, à effort supérieur. L’archive consolidée conserve douze autres instances et facture les recherches supplémentaires ciblées.

Les fichiers détaillés, limites, code et références figurent dans `../docs/AMELIORATIONS_ILS_V6.md` et le notebook exécuté `Ameliorations_ILS_V6.ipynb`. Le moteur de référence reste le défaut. Les variantes et ensembles n’offrent aucune garantie sur une nouvelle instance.
""",encoding='utf-8')
    print(json.dumps(dict(decision=decision,archive=archive_analysis),ensure_ascii=False))


if __name__=='__main__':main()
