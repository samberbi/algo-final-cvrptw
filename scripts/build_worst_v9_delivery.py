"""Document executed worst-gap work without rewriting the reference campaign."""
from pathlib import Path
import json,re,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
import nbformat
from scripts.analyze_worst_v9 import analyze,recovery,archive,restarts,BASE
from scripts.export_report import markdown_table
from scripts.build_ils_v5_delivery import execute


def main():
    dev,ds,_=analyze('development');confirm,cs,comparison=analyze('confirmation')
    recovered=recovery();flat,cases,info=archive();long=restarts()
    stats=cs.set_index('variant');old=stats.loc['split60'];new=stats.loc['split20']
    long_summary=long.groupby('strategy').agg(mean_gap=('gap_pct','mean'),worst_gap=('gap_pct','max'))
    favored=long_summary.sort_values(['worst_gap','mean_gap']).index[0]
    pool_note=('Le partitionnement n’apporte aucun gain sur ces six essais au budget testé.'
               if long.pool_gain_pp.max()<1e-7 else
               f'Le gain maximal du partitionnement est {long.pool_gain_pp.max():.3f} point ; son apport est mesuré séparément du gain des recherches.')
    figdir=ROOT/'livraison/worst_v9_figures';figdir.mkdir(exist_ok=True)
    labels=[f'{r.instance}\n{r.seed}' for r in recovered.itertuples()]
    fig,ax=plt.subplots(figsize=(10,4))
    ax.plot(labels,recovered.before,'o-',label='Campagne de référence')
    ax.plot(labels,recovered.after,'s-',label='Après 180 s supplémentaires de HGS')
    ax.axhline(7,color='#b45309',linestyle='--',label='Cible : moins de 7 %')
    ax.set(ylabel='Gap (%)',title='Les dix essais initialement au-dessus de 7 %, tous conservés')
    ax.legend(fontsize=8);ax.tick_params(axis='x',labelsize=8)
    fig.tight_layout();fig.savefig(figdir/'recovery.png',dpi=170);plt.close(fig)
    r=json.loads((BASE/'recovery180/runs/R2_10_8_2102.json').read_text())
    trace=pd.DataFrame(r['result']['trace'])
    fig,ax=plt.subplots(figsize=(8,3.3))
    ax.step(trace.elapsed_s,100*(trace.best/r['reference_distance']-1),where='post')
    ax.axhline(7,color='#b45309',linestyle='--')
    ax.set(xlabel='Temps de la reprise seule (s)',ylabel='Gap (%)',title='R2_10_8, graine initiale 2102 : convergence HGS réellement enregistrée')
    fig.tight_layout();fig.savefig(figdir/'convergence.png',dpi=170);plt.close(fig)
    pivot=confirm.pivot(index=['instance','seed'],columns='variant',values='gap_pct')
    fig,ax=plt.subplots(figsize=(9,3.6));x=range(len(pivot))
    ax.plot(list(x),pivot.split60,'o-',label='ILS 60 s + HGS 60 s')
    ax.plot(list(x),pivot.split20,'s-',label='ILS 20 s + HGS 100 s')
    ax.axhline(7,color='#b45309',linestyle='--')
    ax.set_xticks(list(x),[f'{n}\n{s}' for n,s in pivot.index],rotation=40,ha='right',fontsize=7)
    ax.set(ylabel='Gap (%)',title='Confirmation indépendante des graines : mêmes budgets de 120 s')
    ax.legend(fontsize=8);fig.tight_layout();fig.savefig(figdir/'confirmation.png',dpi=170);plt.close(fig)
    section=f'''## 9. Réduire les pires écarts : réglage du temps et reprises ciblées

### 9.1. Diagnostic et protocole

La campagne de référence v8 reste figée : son pire essai vaut 11,021 %. Dix essais, sur sept instances, dépassent ou atteignent 7 %. Les familles R2 sont particulièrement représentées. Nous avons donc évalué le partage du temps, le nombre de voisins, les redémarrages et la recombinaison de tournées. Les BKS servent à l’évaluation et à cette sélection postérieure des cas difficiles ; elles ne sont jamais transmises aux moteurs.

Sur trois cas de développement et la graine 3101, quatre variantes disposent chacune de 120 s de recherche. La variante est sélectionnée d’après son pire gap, puis sa moyenne. Toutes enregistrent la convergence interne du HGS ; la référence est réexécutée avec la même instrumentation.

{markdown_table(ds)}

Le partage 20/100 est retenu pour une confirmation sur les sept cas, avec deux nouvelles graines, 3102 et 3103. Il reste une variante contrôlée sur des cas difficiles : il ne remplace pas rétroactivement les résultats du catalogue complet.

### 9.2. Confirmation à budget inchangé

{markdown_table(cs)}

La moyenne sur ces quatorze essais passe de {old.mean_gap:.3f} % à {new.mean_gap:.3f} % ; les pires valeurs sont {old.worst_gap:.3f} % et {new.worst_gap:.3f} %. Le réglage 20/100 est sous 7 % dans {int(new.under7)}/14 essais. Deux graines par cas restent limitées et les sept instances avaient été sélectionnées d’après leurs difficultés antérieures. Il n’en résulte aucune garantie sur des graines ou instances futures.

Les deux cas à 800 clients disposent ici de 120 s, comme leur référence réexécutée ; ils n’avaient que 64 s dans le catalogue initial. La comparaison interne est à budget égal, mais elle ne doit pas être confondue avec une amélioration à coût inchangé face au catalogue pour ces deux cas.

### 9.3. Recherche longue, départs multiples et partitionnement

Une autre expérience porte sur trois cas difficiles : une recherche de 360 s, ou trois recherches de 120 s. Chaque pipeline consacre au plus 20 s à notre ILS puis le reste au HGS. Les trois départs utilisent les graines 3301, 3302 et 3303 ; la recherche longue utilise 3301. Les tournées réalisables de toutes les phases sont ensuite proposées au partitionnement restreint, avec au plus 5 s supplémentaires dans les deux stratégies.

{markdown_table(long)}

Sur ce lot, le critère du pire gap favorise la stratégie `{favored}`. {pool_note}

`before_pool` est le meilleur gap avant partitionnement ; `gap_pct` est celui obtenu après, et `pool_gain_pp` mesure son gain marginal en points. Toutes les constructions, préparations et recombinaisons sont facturées. Le budget nominal est comparable, mais les trois constructions peuvent augmenter le temps réel. Cette expérience de développement ne prouve pas une supériorité générale des redémarrages. Une borne ou une optimalité du partitionnement ne concerne que son pool de tournées, jamais le CVRPTW complet.

### 9.4. Reprise des dix anciens essais défavorables

Chacun des dix essais initialement à au moins 7 % est repris depuis sa propre solution, avec 180 s de HGS supplémentaires, 40 voisins et une nouvelle graine dérivée de la graine initiale. Nous ne remplaçons pas une mauvaise graine par une autre graine favorable : chaque ancien essai possède une reprise identifiée. Son calcul initial et sa reprise sont intégralement comptés.

{markdown_table(recovered[['instance','seed','before','after','previous_total_s','additional_s','total_s']])}

Le cas R2_10_8, graine 2102, passe de **11,021 % à {r['gap_pct']:.3f} %**. Le pire résultat parmi les dix reprises vaut **{recovered.after.max():.3f} %**. La somme des durées supplémentaires mesurées est {info['additional_seconds']:.2f} s, réparties sur six processus lors de l’expérience ; ce cumul n’est pas une durée murale séquentielle observée.

### 9.5. Archive consolidée et limites d’interprétation

Les 462 autres résultats restent inchangés. Après les dix reprises, les 472 solutions de l’archive couvrent toujours les 356 instances : le pire gap est **{info['maximum']:.3f} %**, et {int(flat.gap_pct.lt(7).sum())}/472 essais sont sous 7 %. La moyenne donnant le même poids à chaque instance est **{info['summary']['mean_instance_gap']:.3f} %** ; sur les 60 instances à 1 000 clients, elle est **{info['large_summary']['mean_instance_gap']:.3f} %**.

Il s’agit d’une **archive après reprises ciblées, à budgets différents**, et non d’une nouvelle campagne uniforme de 120 s. Les références v8 à 2,078 % de moyenne et 11,021 % au pire restent accessibles. La baisse du pire gap est réelle et vérifiée, mais son coût supplémentaire doit accompagner le résultat. Les résultats de confirmation du réglage 20/100 constituent une preuve distincte de cette reprise d’archive.

Le profil optionnel `ils_hgs_refined` expose le partage court-ILS/long-HGS. Le script `refine_worst_v9.py` reproduit les reprises expérimentales. Les sources, protocoles, traces et toutes les régressions sont conservés dans `results/worst_v9/`. Le HGS reste celui de PyVRP, attribué à ses auteurs. Le journal d’évolution répertorie cette phase et les décisions prises.

Pour une nouvelle résolution : `python cli.py R2_10_8 --method ils_hgs_refined --seconds 120 --seed 3102`. Le profil web correspondant est **ILS court + HGS (v9)**. Pour reprendre une solution précise : `python scripts/resume_solution_v9.py results/catalog_v8/runs/R2_10_8_2102.json --seconds 180 --neighbors 40 --seed 22102`. Le second exemple ajoute du temps à une solution existante ; il ne représente pas une résolution neuve de 180 s.
'''
    appendix=nbformat.v4.new_notebook(cells=[nbformat.v4.new_markdown_cell('# Réduction des pires gaps CVRPTW — étude v9\n\n'+section)])
    setup="from pathlib import Path\nfrom IPython.display import Image,display\nROOT=next(p for p in [Path.cwd(),*Path.cwd().parents] if (p/'results/worst_v9').exists())\n"
    appendix.cells.append(nbformat.v4.new_code_cell(setup+'\n'.join(f"display(Image(filename=str(ROOT/'livraison/worst_v9_figures/{n}.png')))" for n in ['confirmation','recovery','convergence'])))
    execute(appendix,ROOT/'notebooks/Reduction_Pires_Gaps_V9.ipynb')
    path=ROOT/'notebooks/Livrable_Final_CVRPTW.ipynb';nb=nbformat.read(path,4)
    reference=next((c.source.split('## Références',1)[1] for c in nb.cells
        if c.metadata.get('worst_v9') and c.cell_type=='markdown' and c.source.startswith('## Références')),None)
    nb.cells=[c for c in nb.cells if not c.metadata.get('worst_v9')]
    for cell in nb.cells:
        if cell.cell_type=='markdown' and '## Références' in cell.source:
            body,reference=cell.source.split('## Références',1);cell.source=body.rstrip()
        if cell.cell_type=='markdown':
            cell.source=re.sub(r'\n<!-- WORST_V9_BEGIN -->.*?<!-- WORST_V9_END -->\n','\n',cell.source,flags=re.S)
            cell.source=cell.source.replace('Le résultat final mesuré est','Le résultat de la campagne de référence est')
    note=f'\n<!-- WORST_V9_BEGIN -->\n**Actualisation v9.** Dans le livrable, les sections 1 à 8 décrivent la campagne de référence. La section 9 présente les nouveaux essais : après dix reprises ciblées avec un budget supplémentaire, le pire gap de l’archive est {info["maximum"]:.3f} %. Les anciens résultats et leurs budgets restent identifiés. Le nouveau profil à 120 s est accessible avec `--method ils_hgs_refined` et dans le web « ILS court + HGS (v9) ».\n<!-- WORST_V9_END -->\n'
    nb.cells[0].source+=note
    cell=nbformat.v4.new_markdown_cell(section);cell.metadata['worst_v9']=True;nb.cells.append(cell)
    for name in ['confirmation','recovery','convergence']:
        cell=nbformat.v4.new_code_cell(f"display(Image(filename=str(ROOT/'livraison/worst_v9_figures/{name}.png')))")
        cell.metadata.update(worst_v9=True,figure_captions=[dict(confirmation='Validation 20/100 : sept cas, deux nouvelles graines, même budget de 120 s.',
            recovery='Les dix reprises ciblées : chaque temps initial et supplémentaire est compté.',
            convergence='Convergence enregistrée pendant la seule reprise de R2_10_8, graine initiale 2102.')[name]])
        nb.cells.append(cell)
    if reference:
        cell=nbformat.v4.new_markdown_cell('## Références'+reference);cell.metadata['worst_v9']=True;nb.cells.append(cell)
    nb.metadata['report_subtitle']='ILS–HGS — Catalogue complet et réduction des pires écarts'
    execute(nb,path)
    text='\n\n'.join(c.source for c in nb.cells if c.cell_type=='markdown')
    (ROOT/'LIVRABLE_FINAL.md').write_text(text,encoding='utf-8');(ROOT/'docs/LIVRABLE_OPTIMISE_SOURCE.md').write_text(text,encoding='utf-8')
    (ROOT/'docs/REDUCTION_PIRES_GAPS_V9.md').write_text(section,encoding='utf-8')
    flat.to_csv(ROOT/'livraison/ARCHIVE_APRES_REPRISES_V9.csv',index=False)
    page='<meta charset="utf-8"><h1>Archive après dix reprises ciblées — budgets variables</h1>'
    page+=f'<p>472 solutions réalisables ; pire gap {info["maximum"]:.3f} %. Chaque temps initial et supplémentaire est facturé. La campagne de référence reste distincte.</p>'
    page+='<h2>Les dix reprises</h2>'+recovered.to_html(index=False,escape=True)
    page+='<h2>Les 356 instances</h2>'+cases.to_html(index=False,escape=True)
    page+='<h2>Tous les 472 résultats</h2>'+flat.to_html(index=False,escape=True)
    (ROOT/'livraison/ARCHIVE_APRES_REPRISES_V9.html').write_text(page,encoding='utf-8')
    readme=ROOT/'README.md';s=readme.read_text(encoding='utf-8')
    s=re.sub(r'\n<!-- WORST_V9_BEGIN -->.*?<!-- WORST_V9_END -->\n','\n',s,flags=re.S)
    first,rest=s.split('\n',1)
    links='\n[Étude v9](docs/REDUCTION_PIRES_GAPS_V9.md), [archive après reprises](livraison/ARCHIVE_APRES_REPRISES_V9.html), [notebook v9](notebooks/Reduction_Pires_Gaps_V9.ipynb).\n'
    rest=rest.replace(links,'')
    s=first+note+links+rest
    s=s.replace('## Résultats de l’édition courante','## Résultats de la campagne de référence v8')
    s=s.replace('python scripts/validate_delivery_v8.py','python scripts/validate_worst_v9.py')
    s=s.replace('--junitxml=results/catalog_v8/tests.xml','--junitxml=results/worst_v9/tests.xml')
    readme.write_text(s,encoding='utf-8')
    journal=ROOT/'docs/JOURNAL_EVOLUTION_ALGORITHME.md';s=journal.read_text(encoding='utf-8')
    s=re.sub(r'\n<!-- WORST_V9_JOURNAL_BEGIN -->.*?<!-- WORST_V9_JOURNAL_END -->\n','\n',s,flags=re.S)
    s+='\n<!-- WORST_V9_JOURNAL_BEGIN -->\n## Phase v9 — réduction des pires écarts\n\n'+f'Le réglage 20/100 est évalué sur sept cas et deux nouvelles graines : moyenne {new.mean_gap:.3f} %, pire {new.worst_gap:.3f} %, {int(new.under7)}/14 sous 7 %. Les dix anciens essais à au moins 7 % reçoivent chacun 180 s supplémentaires. Leur archive consolidée a un pire gap de {info["maximum"]:.3f} %, à budgets variables. Les essais de 360 s, départs multiples et partitionnement sont également exécutés et documentés dans [l’étude v9](REDUCTION_PIRES_GAPS_V9.md). La campagne v8 reste figée.\n<!-- WORST_V9_JOURNAL_END -->\n'
    journal.write_text(s,encoding='utf-8')
    delivery=f'''# Livraison actuelle — réduction des pires gaps v9

Ouvrir `RAPPORT_CVRPTW.pdf` ou `../notebooks/Livrable_Final_CVRPTW.ipynb`. La section 9 explique le nouveau réglage et les reprises, avec tous les coûts. Le reçu courant est `validation_worst_v9.json`, indiqué par `VALIDATION.json`.

**Référence v8 :** campagne figée de 472 pipelines, maximum 11,021 %. Ses données et tableaux restent conservés.

**Archive après reprises v9 :** les mêmes 472 solutions, dont dix reprises pendant 180 s supplémentaires ; maximum {info['maximum']:.3f} %, moyenne par instance {info['summary']['mean_instance_gap']:.3f} %. Ce sont des budgets variables. Voir `ARCHIVE_APRES_REPRISES_V9.html` et `.csv`.

**Nouveau réglage à 120 s :** 20 s d’ILS puis 100 s de HGS, contrôlé sur sept cas et deux nouvelles graines ; pire gap {new.worst_gap:.3f} %, {int(new.under7)}/14 sous 7 %. Le profil est `ILS court + HGS (v9)` ou `--method ils_hgs_refined`. Ce lot n’est pas un nouveau catalogue complet.

Les essais de 360 s, départs multiples et recombinaison sont dans `../docs/REDUCTION_PIRES_GAPS_V9.md` et `../notebooks/Reduction_Pires_Gaps_V9.ipynb`. Le HGS externe reste attribué à PyVRP. Les anciens reçus correspondent à leurs études historiques.
'''
    (ROOT/'livraison/LIRE_DABORD.md').write_text(delivery,encoding='utf-8')
    for relative in ['docs/GUIDE_ORAL.md','docs/MODIFICATIONS_LIVRABLE_V8.md']:
        path=ROOT/relative;s=path.read_text(encoding='utf-8')
        s=re.sub(r'\n<!-- WORST_V9_GUIDE_BEGIN -->.*?<!-- WORST_V9_GUIDE_END -->\n','\n',s,flags=re.S)
        lines=s.split('\n',1)
        update=f'\n<!-- WORST_V9_GUIDE_BEGIN -->\n## Actualisation v9\n\nLa confirmation à 120 s donne {new.mean_gap:.3f} % de moyenne, {new.worst_gap:.3f} % au pire et {int(new.under7)}/14 sous 7 % avec le partage 20/100. Séparément, les dix reprises de 180 s font passer le maximum de l’archive de 11,021 % à {info["maximum"]:.3f} %. Annoncer le budget supplémentaire avec ce dernier chiffre. Le nouveau reçu courant est `validation_worst_v9.json`. [Détails et limites](REDUCTION_PIRES_GAPS_V9.md). Les paragraphes précédents sur v8 restent le bilan de la campagne de référence.\n<!-- WORST_V9_GUIDE_END -->\n'
        path.write_text(lines[0]+update+'\n'+lines[1],encoding='utf-8')
    print(json.dumps(dict(archive_max=info['maximum'],confirmation_worst=float(new.worst_gap),confirmation_under7=int(new.under7)),indent=2))


if __name__=='__main__':main()
