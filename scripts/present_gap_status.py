"""Publie des statuts et statistiques conditionnelles, sans modifier les mesures."""
from pathlib import Path
import hashlib
import json
import re
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import nbformat
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
from algo.comparison_status import BETTER,EQUAL,POSITIVE,describe_positive,positive_text
from scripts.revision_duree import write_markdown

OUT=ROOT/'results/presentation_status'
FIG=ROOT/'livraison/duree_figures'


def summaries(frame,groups,metric):
    rows=[]
    for keys,g in frame.groupby(groups,dropna=False):
        keys=keys if isinstance(keys,tuple) else (keys,)
        d=describe_positive(g[metric].replace({np.nan:None}).tolist())
        rows.append(dict(zip(groups,keys))|dict(Essais=len(g),Positifs=d['positive_count'],
            References_depassees=d['reference_better_count'],References_egalees=d['equal_count'],
            Non_comparables=len(g)-d['comparisons'],Moyenne_positive_pct=d['positive_mean'],
            Mediane_positive_pct=d['positive_median'],Positifs_superieurs_6=d['above_six']))
    return pd.DataFrame(rows)


def formatted(frame):
    f=frame.copy()
    for column in ['Moyenne_positive_pct','Mediane_positive_pct']:
        if column in f:f[column]=f[column].map(lambda x:positive_text(float(x)) if pd.notna(x) else 'Non applicable')
    return f.to_markdown(index=False)


def save(fig,name):
    fig.savefig(FIG/name,dpi=200,bbox_inches='tight');plt.close(fig)


def status_bars(frame,groups,metric,name,title):
    table=summaries(frame,groups,metric)
    fig,ax=plt.subplots(figsize=(11,4.6))
    x=np.arange(len(table));bottom=np.zeros(len(table))
    for col,label,color in [('References_depassees','Référence dépassée','#006d77'),
                            ('References_egalees','Référence égalée','#83c5be'),
                            ('Positifs','Écart positif','#e29578'),('Non_comparables','Non comparable','#aaaaaa')]:
        ax.bar(x,table[col],bottom=bottom,label=label,color=color);bottom+=table[col]
    labels=table[groups].astype(str).agg(' / '.join,axis=1)
    ax.set_xticks(x,labels,rotation=35,ha='right',fontsize=8)
    ax.set_ylabel('Nombre d’essais / comparaisons du périmètre indiqué')
    ax.set_title(title);ax.legend(fontsize=8);save(fig,name)


def transform_tables(source,exact=False,frames=None):
    """Les moyennes signées ne sont pas renommées moyennes positives."""
    def table(match):
        lines=match.group(0).strip().splitlines()
        if len(lines)<2:return match.group(0)
        header=[c.strip() for c in lines[0].strip('|').split('|')]
        indexes=[];aggregate=[]
        for i,label in enumerate(header):
            low=label.lower()
            isgap=(any(t in low for t in ['écart','ecart','delta','gap_pct','gap (%)']) or
                ('%' in low and any(t in low for t in ['avant moyen','après moyen','prototype moyen','pire après'])))
            if isgap:
                indexes.append(i)
                if any(t in low for t in ['moy','mean','median','delta']) and not exact:aggregate.append(i)
                header[i]=label.replace('(%)','').replace('gap_pct','Comparaison').strip()+' / statut'
        if not indexes:return match.group(0)
        output=['| '+' | '.join(header)+' |','| '+' | '.join(['---']*len(header))+' |']
        for line in lines[2:]:
            values=[c.strip() for c in line.strip('|').split('|')]
            if len(values)!=len(header):return match.group(0)
            for i in indexes:
                try:value=float(values[i].replace(',','.'))
                except ValueError:continue
                if not np.isfinite(value):values[i]='Comparaison non disponible'
                elif exact and value==0:values[i]='Optimum atteint'
                elif values[0] in ['C','R','RC']:
                    values[i]='Voir les effectifs par statut, pas une moyenne globale'
                elif i in aggregate:
                    series=None
                    if frames is not None:
                        instance=values[0];label=match.group(0).splitlines()[0].split('|')[i+1].lower()
                        if source.startswith('### 6.9.'):
                            column=('baseline_pct' if 'avant' in label else 'first_variant_pct' if 'prototype' in label
                                    else 'final_pct' if 'après' in label or 'apres' in label else None)
                            if column:series=frames['paired'].loc[frames['paired'].instance.eq(instance),column]
                        elif source.startswith('### 6.13.') and 'mean_delta' in label:
                            method=values[2] if len(values)>2 else ''
                            frame=frames['fresh']
                            series=frame.loc[frame.campaign.eq('confirmation_ils_v2') & frame.instance.eq(instance)
                                             & frame.method.eq(method),'delta_independent_pct']
                        elif 'mean_delta_reference' in label:
                            series=frames['core'].loc[frames['core'].instance.eq(instance),'delta_reference_pct']
                    if series is not None and len(series):
                        valid=series.dropna();positive=valid[valid.gt(0)]
                        values[i]=(positive_text(float(positive.mean()))+f' % (positifs {len(positive)}/{len(series)})'
                            if len(positive) else f'Aucun écart positif (effectif {len(series)})')
                        if 'Moyenne positive conditionnelle' not in header[i]:
                            header[i]='Moyenne positive conditionnelle — '+header[i]
                    else:values[i]='Voir répartition par statut et statistiques conditionnelles'
                elif value<0:values[i]='Référence dépassée — solution améliorante validée'
                elif value==0:values[i]='Référence égalée — optimalité non démontrée'
                else:values[i]=positive_text(value)+' %'
            output.append('| '+' | '.join(values)+' |')
        output[0]='| '+' | '.join(header)+' |'
        return '\n'.join(output)+'\n'
    return re.sub(r'(?m)(?:^\|[^\n]*\n?){2,}',table,source)


def main():
    audit=json.loads((OUT/'AUDIT.json').read_text());assert audit['validated'] and not audit['errors']
    assert not json.loads((OUT/'ANOMALIES.json').read_text()), 'Audit en échec : publication bloquée'
    rawfile=ROOT/'results/gap_tables/DETAIL_TOUS_LES_ECARTS.csv'
    assert hashlib.sha256(rawfile.read_bytes()).hexdigest()==audit['raw_source_sha256']
    core=pd.read_csv(ROOT/'results/time_objective/catalogue/core.csv')
    repeated=pd.read_csv(ROOT/'results/time_objective/catalogue/repetitions.csv')
    archive=pd.read_csv(ROOT/'results/time_objective/best_duration/COUVERTURE_472_ESSAIS.csv')
    fresh=pd.read_csv(ROOT/'results/final_static/TOUS_LES_ESSAIS.csv')
    core['geo']=core.instance.str.extract(r'^(RC|C|R)',expand=False)
    coverage=summaries(core,['n'],'delta_reference_pct')
    best=summaries(archive,['n'],'best_delta_pct')
    reps=summaries(repeated,['instance','method'],'delta_reference_pct')
    pilots=summaries(fresh[fresh.method.ne('ortools')],['campaign','method'],'delta_independent_pct')
    geo=summaries(core,['geo'],'delta_reference_pct')
    for name,frame in [('COUVERTURE',coverage),('ARCHIVE',best),('REPETITIONS',reps),('PILOTES',pilots)]:
        frame.to_csv(OUT/(name+'_STATUTS.csv'),index=False,encoding='utf-8-sig')
    audited=pd.read_csv(OUT/'AUDIT_COMPARAISONS.csv').set_index('index')
    publication=pd.read_csv(rawfile)
    public_rows=[]
    for i,r in publication.iterrows():
        status=audited.loc[i,'statut'] if i in audited.index else 'Comparaison non disponible ou référence uniquement'
        display=positive_text(float(r.ecart_pct))+' %' if status==POSITIVE else status
        public_rows.append(dict(instance=r.instance,clients=r.n,campagne=r.campagne,methode=r.methode,
            graine=r.graine,duree_solution=r.duree,duree_reference=r.reference_duree,
            comparaison=display,statut=status,source=r.source,type_reference=r.type_reference))
    pd.DataFrame(public_rows).to_csv(OUT/'TABLEAU_PRESENTATION.csv',index=False,encoding='utf-8-sig')
    status_bars(core,['n'],'delta_reference_pct','presentation_statuts_taille.png',
        'Campagne initiale : toutes les comparaisons de couverture, par statut')
    status_bars(core,['geo'],'delta_reference_pct','presentation_statuts_geographie.png',
        'Comparaisons de couverture par géographie — effectifs, pas gaps moyens globaux')
    status_bars(fresh[fresh.campaign.eq('couverture_progressive') & fresh.method.ne('ortools')],['method'],
        'delta_independent_pct','presentation_statuts_pilotes.png','Pilote progressif : statuts par méthode, échecs compris')
    positive=core.loc[core.delta_reference_pct.gt(0),'delta_reference_pct']
    fig,ax=plt.subplots(figsize=(8,4.5))
    ax.hist(positive,bins=12,color='#e29578',edgecolor='white');ax.axvline(6,color='#8a3020',ls='--',label='Seuil indicatif six pour cent')
    ax.set(xlabel='Écart strictement positif au témoin (%)',ylabel='Nombre d’essais',
        title=f'Distribution conditionnelle : {len(positive)} essais positifs sur {len(core)}')
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v,p:f'{v:g}' if v>0 else ''))
    ax.legend();save(fig,'presentation_ecarts_positifs.png')
    paired=pd.read_csv(ROOT/'results/time_objective/outliers10/AVANT_APRES_ESSAIS.csv')
    phases=pd.concat([paired[['baseline_pct']].rename(columns={'baseline_pct':'delta'}).assign(phase='Avant'),
        paired[['final_pct']].rename(columns={'final_pct':'delta'}).assign(phase='Après')])
    status_bars(phases,['phase'],'delta','presentation_optimisation_statuts.png',
        'Lot ciblé : comparaisons avant/après sur les mêmes 43 couples')
    target=ROOT/'notebooks/Livrable_Final_CVRPTW.ipynb';nb=nbformat.read(target,4)
    backup=OUT/'NOTEBOOK_AVANT_PRESENTATION.ipynb'
    if not backup.exists():backup.write_bytes(target.read_bytes())
    maps={
        'livraison/duree_figures/distribution.png':'livraison/duree_figures/presentation_statuts_taille.png',
        'livraison/duree_figures/histogramme.png':'livraison/duree_figures/presentation_ecarts_positifs.png',
        'livraison/duree_figures/familles_par_taille.png':'livraison/duree_figures/presentation_statuts_geographie.png',
        'livraison/duree_figures/optimisation_ciblee.png':'livraison/duree_figures/presentation_optimisation_statuts.png',
        'livraison/figures_final_static/qualite_taille_temps.png':'livraison/duree_figures/presentation_statuts_pilotes.png'}
    # Les cellules de calcul des statistiques de DURÉE sont conservées. Seules
    # les deux cellules affichant les anciens graphiques d'écarts sont repointées.
    for cell in nb.cells:
        if cell.metadata.get('comparison_status_summary'):continue
        if cell.cell_type=='markdown':
            old=cell.metadata.get('comparison_render')
            if old and hashlib.sha256(cell.source.encode()).hexdigest()==old['rendered_sha256']:
                source=old['original_source']
            else:source=cell.source
            original=source
            if source.startswith('# Livrable final'):
                stats=describe_positive(archive.best_delta_pct.tolist())
                block=(f"**Archive actuelle.** {len(archive)} solutions réalisables sur 356 instances, à budgets différents : "
                    f"{stats['reference_better_count']} références dépassées, {stats['equal_count']} références égalées "
                    f"et {stats['positive_count']} écarts positifs. La moyenne conditionnelle des seuls écarts positifs "
                    f"est {positive_text(stats['positive_mean'])} %, avec un maximum de "
                    f"{positive_text(float(archive.best_delta_pct.max()))} %. Ces indicateurs ne certifient pas "
                    "un gap à l’optimum temporel sur toutes les instances. Le tableau des effectifs et les "
                    "mesures originales permettent de vérifier le périmètre de chaque résultat.")
                source=re.sub(r'<!-- RESULTATS_ACTUELS_DUREE_BEGIN -->.*?<!-- RESULTATS_ACTUELS_DUREE_END -->',
                    '<!-- RESULTATS_ACTUELS_DUREE_BEGIN -->\n'+block+'\n<!-- RESULTATS_ACTUELS_DUREE_END -->',source,flags=re.S)
                source=source.replace('les écarts signés restent visibles','les mesures signées restent dans les fichiers d’audit')
                source=source.replace('Les écarts signés restent visibles','Les mesures signées restent dans les fichiers d’audit')
            elif source.startswith('|   Clients |') and 'Écart témoin (%)' in source:
                source=formatted(coverage)
            elif source.startswith('| instance') and '| delta' in source:
                source=formatted(reps)
            elif source.startswith('Les 646 résolutions comprennent'):
                source='''Les 646 résolutions historiques sont réalisables. Le tableau suivant
compte les 472 essais de couverture, séparément des répétitions. Les moyennes
et médianes portent uniquement sur les écarts strictement positifs ; leurs
effectifs sont affichés. Les références dépassées, égalées et les comparaisons
indisponibles restent comptées. Ces moyennes ne représentent pas tous les essais.'''
            elif source.startswith('**Lecture des boîtes par taille.**'):
                source='''**Lecture des statuts par taille.** Chaque barre compte tous les essais
de couverture de cette taille. Les couleurs distinguent les références dépassées,
les références égalées et les écarts positifs. Aucun optimum n'est déduit d'une
égalité avec un témoin heuristique. Les effectifs et les moyennes positives
conditionnelles sont présentés ensemble ; aucune valeur n'est ramenée à zéro.'''
            elif source.startswith("**Lecture de l'histogramme global.**"):
                source='''**Lecture de l'histogramme conditionnel.** Cette distribution porte
seulement sur les écarts strictement positifs des essais de couverture. Le titre
indique leur effectif et l'effectif total ; les autres statuts restent dans la
figure précédente. Les dépassements de six pour cent sont conservés. On ne
présente pas cette distribution filtrée comme celle du catalogue complet.'''
            if not source.startswith('### 6.10.'):
                source=transform_tables(source,exact=('optimum' in source.lower().split('\n')[0] and 'gap_pct' in source),
                    frames=dict(core=core,paired=paired,fresh=fresh))
            # Les pourcentages signés d'origine restent dans l'annexe technique.
            # Les zéros d'écart-type de DURÉE et les coefficients de régression
            # ne sont pas des gaps et ne sont pas modifiés.
            if not source.startswith('### 6.10.'):
                # La sensibilité contient des paramètres nuls et des variations
                # entre variantes : ils ne sont pas des gaps de benchmark.
                source=re.sub(r'(?<![\w.,])[-−]\d+(?:[.,]\d+)?\s*%',
                    '« référence dépassée — comparaison détaillée dans l’audit »',source)
                source=re.sub(r'(?<![\d.,])\+?0(?:[.,]0+)?\s*%',
                    '« référence égalée — optimalité non démontrée »',source)
            if source.startswith('### 6.11.'):
                source=re.sub(r'\*\*Lecture des cartes de chaleur\.\*\*.*?(?=\n\n)',
                    '**Lecture des statuts géographiques.** Les barres comptent les essais de couverture par géographie et par statut. Les caractéristiques de fenêtres et capacité qui suivent restent calculées par instance ; les granularités ne sont pas confondues.',source,flags=re.S)
                source=re.sub(r'\*\*Lecture du bilan\.\*\*.*?(?=\n\n)',
                    '**Lecture du bilan.** Les gains depuis la construction et les parts d’attente restent des indicateurs de durée, distincts des gaps de benchmark. Les comparaisons au témoin sont décrites par les effectifs de chaque statut ci-dessous ; une moyenne signée de toute une géographie n’est pas requalifiée en moyenne positive.\n\n'+formatted(geo),source,flags=re.S)
            if source.startswith('### 6.9.'):
                source=source.replace('La moyenne après optimisation est calculée sur chaque instance du lot ;',
                    'Les moyennes positives sont conditionnelles et leur effectif est indiqué pour chaque instance ;')
                source=re.sub(r'\*\*Lecture du graphique[^\n]*.*?(?=\n\n)',
                    '**Lecture du graphique.** Les deux barres classent les mêmes 43 couples avant et après la reprise, en références dépassées, égalées et écarts positifs. Le tableau des statistiques conditionnelles précise les effectifs ; les coûts et temps originaux sont conservés.',source,flags=re.S)
            if 'qualite_taille_temps.png' in source:
                source=re.sub(r'\*\*Lecture du graphique\.\*\* Le panneau gauche.*?(?=\n\n)',
                    '**Lecture des statuts du pilote.** Chaque barre regroupe les essais d’une méthode dans le seul lot progressif. Les références dépassées et égalées sont comptées ; les échecs restent visibles. Les temps réels restent dans les tableaux de coûts et dans les CSV. Ce graphique ne prétend pas établir une loi de complexité.',source,flags=re.S)
            for a,b in maps.items():source=source.replace(a,b)
            cell.source=source
            cell.metadata['comparison_render']=dict(original_source=original,
                rendered_sha256=hashlib.sha256(source.encode()).hexdigest())
        elif cell.cell_type=='code':
            for a,b in maps.items():
                if a in cell.source:
                    cell.source=cell.source.replace(a,b)
                    cell.outputs=[];cell.execution_count=None
                    if cell.metadata.get('figure_captions'):
                        cell.metadata['figure_captions']=['Présentation par statuts ou distribution conditionnelle des écarts positifs ; voir explication ci-dessous.']
    summary='''### Comparaisons validées : statuts et statistiques conditionnelles

Une référence heuristique peut être dépassée ou égalée sans qu'un optimum
temporel ait été démontré. Ces cas sont affichés par statut. Les coûts réels,
les anciennes comparaisons signées et leur réévaluation indépendante restent
dans `AUDIT_GAPS_FINAL.md` et `results/presentation_status/`.

L'audit a recalculé **1321 comparaisons chiffrées** : **947 références dépassées,
129 égalités et 245 écarts positifs**, sans anomalie de coût ni faisabilité.
Il s'agit d'enregistrements, comprenant des vues d'archive et plusieurs
références d'un même essai, pas d'un nouveau nombre de résolutions.

Les moyennes et médianes ci-dessous sont **conditionnelles aux seuls écarts
positifs comparables**. La colonne Positifs en donne le dénominateur ; les
autres statuts restent explicitement comptés. Elles ne sont jamais présentées
comme des moyennes sur toutes les instances. Les valeurs supérieures au seuil
de six pour cent sont conservées. Aucun coût, contrainte, référence ou réglage
de l'algorithme n'a été détérioré pour changer le signe d'un pourcentage.

**Campagne initiale — 472 essais de couverture.**

'''+formatted(coverage)+'''

**Archive des plans sélectionnés — budgets différents, pas campagne uniforme.**

'''+formatted(best)+'''

**Nouveaux pilotes — comparaison au solveur indépendant du même lot.**

'''+formatted(pilots)+'''

Les autres tableaux signalent « voir répartition par statut » lorsque leur
ancienne colonne était une moyenne signée mélangeant les statuts. Cette
colonne n'est pas rebaptisée moyenne positive. Les valeurs originales sont
conservées dans les CSV techniques. Une égalité à une référence heuristique
n'est jamais étiquetée « Optimum atteint » ; ce statut reste réservé aux
petits cas exacts avec preuve vérifiée. Une contradiction face à un optimum
certifié bloque la validation. La borne inférieure fournit une majoration
du gap, pas sa valeur exacte. Le seuil académique n'est pas certifié pour
tout le catalogue par ces références heuristiques.
'''
    nb.cells=[c for c in nb.cells if not c.metadata.get('comparison_status_summary')]
    index=next(i for i,c in enumerate(nb.cells) if c.source.startswith('## 6.'))
    nb.cells.insert(index+1,nbformat.v4.new_markdown_cell(summary,metadata={'comparison_status_summary':True}))
    nb.metadata['comparison_status_presentation']=1
    nbformat.validate(nb);nbformat.write(nb,target);write_markdown(nb)
    receipt=OUT/'PRESENTATION.json'
    previous=json.loads(receipt.read_text()) if receipt.exists() else {}
    engines=['duration.py','duration_moves.py','duration_refine.py','kernels.py','model.py','verify.py','hgs_tuning.py','route_pool.py']
    hashes={name:hashlib.sha256((ROOT/'algo'/name).read_bytes()).hexdigest() for name in engines}
    if previous.get('unchanged_engine_hashes'):assert hashes==previous['unchanged_engine_hashes']
    receipt.write_text(json.dumps(dict(applied=True,raw_source_sha256=audit['raw_source_sha256'],
        algorithm_changed=False,unchanged_engine_hashes=hashes,positive_means_are_conditional=True,
        source_notebook_backup=str(backup.relative_to(ROOT))),indent=2),encoding='utf-8')
    print('Présentation par statuts appliquée ; mesures originales et algorithmes conservés.')


if __name__=='__main__':main()
