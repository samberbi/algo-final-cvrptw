"""Compléments scientifiques : sensibilité OFAT, scénarios et rédaction.

Analyse les mesures conservées, sans modifier les solutions ni relancer le
solveur. Les différentes campagnes restent explicitement séparées.
"""
from pathlib import Path
import hashlib
import json
import math
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import nbformat
import numpy as np
import pandas as pd
from algo.data import load,reference
from algo.verify import verify

FIG=ROOT/'livraison/duree_figures'
BASE=ROOT/'results/time_objective'
COLORS={'C':'#176b89','R':'#b45309','RC':'#128475'}

COMPLEXITY=r'''Le problème de décision associé demande s'il existe une solution réalisable de durée totale au plus B. Nous montrons sa difficulté par une réduction **du TSP vers notre CVRPTW statique**, et non dans le sens inverse.

Considérons une instance du TSP symétrique à m sommets, avec des coûts entiers non négatifs $c_{ij}$ et un seuil B. Un sommet devient le dépôt et les $m-1$ autres deviennent les clients. Nous fixons un seul véhicule, $q_i=1$, $Q=m-1$, des services nuls, et les fenêtres $[0,H]$ avec $H=m\max(1,\max_{i,j}c_{ij})$. Les temps de trajet reprennent exactement les coûts du TSP. Toutes les capacités et fenêtres sont alors non bloquantes pour un circuit hamiltonien ; aucun temps d'attente n'est imposé.

Un circuit du TSP de coût au plus B donne donc une tournée CVRPTW de durée au plus B. Réciproquement, une solution CVRPTW de cette instance doit utiliser son unique véhicule pour visiter tous les clients exactement une fois et revenir au dépôt ; elle décrit un circuit hamiltonien dont le coût est au plus sa durée, donc au plus B. La transformation utilise une matrice de taille quadratique et un horizon de représentation binaire polynomiale. L'optimisation est ainsi **NP-difficile**.

Pour la version de décision à données entières ou rationnelles encodées, une liste de tournées est un certificat de taille polynomiale. Nous vérifions couverture, charges, fenêtres, retours et durée par propagation des horaires au plus tôt. Cette vérification est polynomiale ; la version de décision est donc **NP-complète**. La preuve concerne le problème général statique : elle ne prétend pas démontrer la difficulté de chaque instance particulière ni l'optimalité d'une métaheuristique.
'''

CONTEXT='''**Contexte métier.** Dans le cadre de la réponse de CesiCDP à l'appel de l'ADEME, nous étudions l'organisation de livraisons réalisées par une flotte homogène. Il faut servir les clients dans les créneaux convenus, respecter la charge des camions et limiter le temps total mobilisé. L'enjeu opérationnel est de réduire les trajets et attentes évitables tout en maintenant la faisabilité des livraisons. La durée est notre indicateur d'optimisation ; nous ne calculons pas ici une réduction d'émissions de CO₂, qui nécessiterait un modèle énergétique distinct.'''


def table(frame):
    from scripts.build_duration_delivery import table as render
    return render(frame)


def save(fig,name):
    fig.tight_layout()
    fig.savefig(FIG/(name+'.png'),dpi=160)
    plt.close(fig)


def sensitivity():
    folder=BASE/'sensitivity_controlled'
    protocol=json.loads((folder/'protocol.json').read_text())
    expected={tuple(job) for job in protocol['jobs']}
    seen=set();rows=[];cache={}
    for path in sorted((folder/'runs').glob('*.json')):
        r=json.loads(path.read_text())
        key=(r['instance'],r['seed'],r['configuration'])
        assert key in expected and key not in seen
        seen.add(key)
        row={k:v for k,v in r.items() if k not in ['result']}
        row['source']=path.relative_to(ROOT).as_posix()
        if r['valid']:
            if r['instance'] not in cache:
                ins=load(ROOT/'data/instances'/(r['instance']+'.vrp'))
                rr,_=reference(ROOT/'data/instances'/(r['instance']+'.sol'))
                ref=verify(rr,ins);assert ref['valid']
                cache[r['instance']]=(ins,ref)
            ins,ref=cache[r['instance']]
            checked=verify(r['result']['routes'],ins)
            assert checked['valid'] and r['result']['objective']=='duration'
            assert abs(checked['duration']/10-r['duration'])<1e-7
            assert abs(100*(checked['duration']/ref['duration']-1)-r['delta_reference_pct'])<1e-7
            measured=sum(r[k] for k in ['construction_s','own_ils_s','external_hgs_s','verification_s'])
            assert abs(measured-r['recomposed_total_s'])<1e-7
            initial=json.loads((ROOT/r['initial_source']).read_text())
            prefix=json.loads((ROOT/r['prefix_source']).read_text())
            from scripts.controlled_sensitivity import digest
            assert digest(initial['routes'])==r['initial_sha256']
            assert digest(prefix['routes'])==r['prefix_sha256']
            assert r['result']['neighbor_count']==r['parameters']['neighbors']
            row['effective_hgs_neighbors']=min(r['parameters']['neighbors'],ins.n-1)
            assert abs(prefix['runtime_s']-r['own_ils_s'])<1e-7
            assert abs(initial['info']['seconds']-r['construction_s'])<1e-7
        rows.append(row)
    assert seen==expected,('Campaign incomplete',len(seen),len(expected))
    df=pd.DataFrame(rows)
    good=df[df.valid].copy()
    assert good.groupby(['instance','seed']).initial_sha256.nunique().eq(1).all()
    neighbors=good[good.configuration.isin(['baseline','neighbors_80','neighbors_120'])]
    assert neighbors.groupby(['instance','seed']).prefix_sha256.nunique().eq(1).all()
    baseline=good[good.configuration.eq('baseline')][['instance','seed','duration','own_ils_duration','recomposed_total_s']]
    paired=good.merge(baseline,on=['instance','seed'],suffixes=('','_baseline'),validate='many_to_one')
    paired['paired_duration_change_pct']=100*(paired.duration/paired.duration_baseline-1)
    paired['paired_own_ils_change_pct']=100*(paired.own_ils_duration/paired.own_ils_duration_baseline-1)
    paired['time_change_s']=paired.recomposed_total_s-paired.recomposed_total_s_baseline
    paired['improved']=paired.paired_duration_change_pct.lt(-1e-7)
    paired['worse']=paired.paired_duration_change_pct.gt(1e-7)
    paired['equal']=~(paired.improved|paired.worse)
    summary=paired.groupby('configuration',as_index=False).agg(
        pairs=('seed','size'),instances=('instance','nunique'),
        duration_change_pct=('paired_duration_change_pct','mean'),
        own_ils_change_pct=('paired_own_ils_change_pct','mean'),
        improved=('improved','sum'),equal=('equal','sum'),worse=('worse','sum'),
        mean_total_s=('recomposed_total_s','mean'),time_change_s=('time_change_s','mean'))
    case_means=paired.groupby(['configuration','instance'],as_index=False).paired_duration_change_pct.mean()
    macro=case_means.groupby('configuration').paired_duration_change_pct.mean()
    summary['duration_change_pct']=summary.configuration.map(macro)
    df.to_csv(folder/'TOUS_LES_PROFILS.csv',index=False)
    paired.to_csv(folder/'COMPARAISONS_APPARIEES.csv',index=False)
    summary.to_csv(folder/'SYNTHESE_PARAMETRES.csv',index=False)
    fig,axes=plt.subplots(1,2,figsize=(11,4))
    for ax,names,title in [(axes[0],['tolerance_0','baseline','tolerance_002'],'Tolérance de notre ILS'),
                          (axes[1],['baseline','neighbors_80','neighbors_120'],'Voisins du HGS externe')]:
        values=[paired[paired.configuration.eq(name)].paired_duration_change_pct for name in names]
        labels=['0 %','0,5 %','2 %'] if ax is axes[0] else ['40','80','120']
        ax.boxplot(values,tick_labels=labels,showmeans=True)
        ax.axhline(0,color='#b45309',linestyle='--')
        ax.set(title=title,ylabel='Variation de durée finale vs témoin apparié (%)')
    save(fig,'sensibilite_controlee')
    text=r'''### 6.10. Sensibilité contrôlée : un facteur à la fois

**Question.** Une amélioration obtenue en changeant ensemble le budget, le voisinage et la graine ne permet pas d'isoler le rôle d'un réglage. Nous ajoutons une étude OFAT (*one factor at a time*) sur un profil hybride précisément défini : notre construction regret-2 et notre ILS, suivis du HGS externe PyVRP. Le partitionnement et le constructeur renforcé ne participent pas à cette expérience ; nous ne lui attribuons donc pas les performances du profil `duration_refined`.

**Plan fixé avant exécution.** Six instances sont retenues : C103, R203 et RC103 à 100 clients ; C2_10_10, R1_10_5 et RC2_10_5 à 1 000 clients. Trois nouvelles graines, 8301–8303, donnent dix-huit couples instance–graine. La configuration témoin est une tolérance ILS de 0,5 % et 40 voisins HGS. Nous changeons uniquement la tolérance vers 0 % ou 2 %, ou uniquement le voisinage vers 80 ou 120. Ces cinq configurations produisent 90 profils évalués ; le témoin commun n'est pas compté deux fois.

**Contrôle des départs et des temps.** Chaque profil dispose de deux secondes d'ILS puis deux secondes de HGS, avec les mêmes données, la même graine appariée et un unique cœur CPU. La construction commune est réellement exécutée une fois par couple instance–graine. Les voisins HGS sont comparés à partir du même préfixe ILS enregistré, vérifié par empreinte ; modifier le voisinage ne modifie donc pas son entrée. Quand la tolérance change, le préfixe ILS est recalculé. Les phases communes sont mutualisées, et leur temps mesuré est facturé dans chaque profil. Le total publié est la **somme recomposée de phases réellement chronométrées**, construction et préparation comprises, pas le chronométrage continu de 90 pipelines indépendants. Le temps physique de chaque tâche et les réutilisations sont aussi enregistrés. L'ordre des tâches est mélangé et fixé dans le protocole.

Le réglage de voisins concerne uniquement le HGS externe ; le voisinage de notre ILS reste fixe. PyVRP borne le nombre effectif à $\min(k,n-1)$ : le réglage nominal 120 correspond donc à 99 voisins pour les cas à 100 clients, et à 120 pour les cas à 1 000 clients. Cette valeur effective est conservée dans le tableau individuel.

**Indicateur apparié.** Pour chaque couple, $D=100(T_{\mathrm{réglage}}/T_{\mathrm{témoin\ de\ réglage}}-1)$. Ici le témoin est la configuration algorithmique à 0,5 % / 40 voisins, pas le plan BKS. Un D négatif indique une amélioration. Nous moyennons d'abord les graines de chaque instance, puis les six instances à poids égal. Les écarts aux plans de référence restent dans le fichier individuel sous leur qualification habituelle, distincte d'un gap à l'optimum temporel.

'''
    shown=summary.rename(columns={'configuration':'Réglage','pairs':'Paires','instances':'Instances',
        'duration_change_pct':'Variation durée finale (%)','own_ils_change_pct':'Variation ILS seul (%)',
        'improved':'Meilleurs','equal':'Égaux','worse':'Moins bons','mean_total_s':'Total recomposé (s)'})
    text+=table(shown.drop(columns=['time_change_s']))
    text+='''

![Sensibilité de la durée finale à un réglage modifié isolément.](../livraison/duree_figures/sensibilite_controlee.png)

**Lecture des boîtes.** Chaque boîte rassemble les variations appariées des dix-huit couples instance–graine. Le panneau gauche change la tolérance de notre ILS ; le panneau droit change le voisinage du moteur externe. La ligne zéro représente la configuration témoin, identique à elle-même. Sous zéro, le réglage améliore la durée finale ; au-dessus, il la dégrade. La médiane et la dispersion complètent la moyenne du tableau. Les points extrêmes sont conservés.

**Intérêt et continuité.** Après les optimisations combinées de la section 6.9, cette figure examine un réglage à la fois. Les améliorations et régressions sont comparées au même départ, et les résultats propres à l'ILS sont distingués du résultat après HGS. La dispersion inclut des graines et des instances différentes ; elle n'est pas un intervalle de confiance. Trois graines et six cas ne suffisent pas à établir un meilleur réglage universel. L'effet du budget n'est pas étudié, puisqu'il reste fixe ; nous n'attribuons pas ces résultats aux recherches plus longues de l'archive.
'''
    valid=int(df.valid.sum());failed=len(df)-valid
    text+=f'\n\n**Faisabilité et portée.** {valid}/{len(df)} profils sont réalisables, avec {failed} échecs conservés. Cette campagne est exploratoire, séparée des 646 résolutions initiales et de l’archive des meilleures solutions. Un mauvais résultat au budget court reste publié et n’est pas remplacé par une reprise longue.'
    variants=summary[summary.configuration.ne('baseline')].sort_values('duration_change_pct')
    text+='\n\n**Interprétation mesurée.** '
    for r in variants.itertuples():
        text+=f'Le réglage `{r.configuration}` donne une variation moyenne de {r.duration_change_pct:+.3f} %, avec {r.improved} améliorations, {r.equal} égalités et {r.worse} régressions sur {r.pairs} paires. '
    text+='Ces différences ne justifient pas un changement automatique du profil par défaut : une confirmation sur un lot distinct serait nécessaire.'
    strict=summary[summary.configuration.eq('tolerance_0')].iloc[0]
    text+=f'''\n\n**Attribution du gain.** Avec une tolérance nulle, le coût moyen du préfixe ILS varie ici de {strict.own_ils_change_pct:+.3f} % : il est donc moins bon que celui du témoin avant l'appel externe. Le résultat final après HGS varie de {strict.duration_change_pct:+.3f} %. Cette différence montre une interaction entre le départ produit et la recherche externe ; elle ne démontre pas que notre ILS autonome est meilleur. Les voisins 80/120 ne changent pas ce préfixe, ce que confirment leurs empreintes identiques. Leurs différences finales concernent bien le réglage du HGS sur ces entrées.'''
    (ROOT/'docs/SENSIBILITE_CONTROLEE_DUREE.md').write_text(text+'\n',encoding='utf-8')
    return text,dict(profiles=len(df),feasible=valid,failed=failed,summary=summary.to_dict('records'))


def scenarios():
    folder=BASE/'scenario_analysis';folder.mkdir(exist_ok=True)
    cases=pd.read_csv(BASE/'catalogue/instances.csv')
    runs=pd.read_csv(BASE/'catalogue/core.csv')
    features=[]
    for row in cases.itertuples():
        ins=load(ROOT/'data/instances'/(row.instance+'.vrp'))
        match=re.match(r'^(RC|R|C)([12])',row.instance)
        assert match
        sub=runs[runs.instance.eq(row.instance)]
        original=json.loads((ROOT/sub.iloc[0].source).read_text())
        total_demand=float(ins.demand.sum())
        vehicle_counts=sub.vehicles.to_numpy()
        features.append(dict(instance=row.instance,n=ins.n,geography=match[1],type=int(match[2]),
            family=match[0],capacity=ins.capacity,horizon=ins.horizon/10,
            mean_window_width=float(np.mean(ins.late[1:]-ins.early[1:])/10),
            window_fraction=float(np.mean((ins.late[1:]-ins.early[1:])/ins.horizon)),
            mean_demand_over_Q=float(ins.demand[1:].mean()/ins.capacity),
            capacity_vehicle_lower_bound=math.ceil(total_demand/ins.capacity),
            mean_capacity_fill=float(np.mean(total_demand/(vehicle_counts*ins.capacity))),
            waiting_share=float(row.mean_waiting/row.mean_duration),
            reference_waiting_share=float(original['reference_waiting']/original['reference_duration']),
            service_share=float(row.mean_service/row.mean_duration),
            initial_gain_pct=row.mean_gain_initial_pct,delta_reference_pct=row.mean_delta_reference_pct,
            calculation_s=row.mean_calculation_s,valid=row.valid,attempts=row.attempts))
    df=pd.DataFrame(features)
    geography=df.groupby('geography',as_index=False).agg(instances=('instance','size'),
        delta_reference_pct=('delta_reference_pct','mean'),initial_gain_pct=('initial_gain_pct','mean'),
        waiting_pct=('waiting_share',lambda x:100*x.mean()),reference_waiting_pct=('reference_waiting_share',lambda x:100*x.mean()),
        calculation_s=('calculation_s','mean'))
    families=df.groupby('family',as_index=False).agg(instances=('instance','size'),
        capacity_min=('capacity','min'),capacity_max=('capacity','max'),horizon_min=('horizon','min'),horizon_max=('horizon','max'),
        mean_window_width=('mean_window_width','mean'),window_pct=('window_fraction',lambda x:100*x.mean()),
        demand_over_Q_pct=('mean_demand_over_Q',lambda x:100*x.mean()),
        final_capacity_fill_pct=('mean_capacity_fill',lambda x:100*x.mean()))
    by_size=df.groupby(['geography','n'],as_index=False).agg(instances=('instance','size'),
        delta_reference_pct=('delta_reference_pct','mean'),initial_gain_pct=('initial_gain_pct','mean'),waiting_share=('waiting_share','mean'))
    for name,frame in [('CARACTERISTIQUES_INSTANCES',df),('SYNTHESE_GEOGRAPHIQUE',geography),
                       ('FAMILLES_ET_CONTRAINTES',families),('GEOGRAPHIE_PAR_TAILLE',by_size)]:
        frame.to_csv(folder/(name+'.csv'),index=False)
    fig,axes=plt.subplots(1,2,figsize=(12,3.6))
    fig.suptitle('Campagne initiale : 10 s de recherche, avant les reprises ciblées',fontsize=11)
    for ax,column,title in [(axes[0],'initial_gain_pct','Gain depuis la construction (%)'),
                            (axes[1],'delta_reference_pct','Écart au plan témoin (%)')]:
        matrix=by_size.pivot(index='geography',columns='n',values=column).reindex(['C','R','RC'])
        m=ax.imshow(matrix,cmap='viridis',aspect='auto')
        for i in range(len(matrix)):
            for j in range(len(matrix.columns)):
                span=float(matrix.max().max()-matrix.min().min())
                fraction=(float(matrix.iloc[i,j])-float(matrix.min().min()))/span if span else 0.
                ax.text(j,i,f'{matrix.iloc[i,j]:.1f}',ha='center',va='center',color='black' if fraction>.65 else 'white',fontsize=8)
        ax.set(xticks=range(len(matrix.columns)),xticklabels=matrix.columns,yticks=range(3),yticklabels=matrix.index,
               xlabel='Nombre de clients',title=title)
        fig.colorbar(m,ax=ax,shrink=.8)
    save(fig,'familles_par_taille')
    large=df[df.n.eq(1000)].copy()
    fig,axes=plt.subplots(1,2,figsize=(11,4))
    for geography_name,color in COLORS.items():
        group=large[large.geography.eq(geography_name)]
        axes[0].scatter(100*group.window_fraction,100*group.waiting_share,label=geography_name,color=color,alpha=.75)
        axes[1].scatter(100*group.mean_demand_over_Q,100*group.mean_capacity_fill,label=geography_name,color=color,alpha=.75)
    axes[0].set(xlabel='Largeur moyenne des fenêtres / horizon (%)',ylabel='Part des attentes dans la durée (%)')
    axes[1].set(xlabel='Demande moyenne d’un client / capacité (%)',ylabel='Remplissage moyen des tournées (%)')
    for ax in axes:ax.legend(title='Géographie')
    save(fig,'contraintes_observees')
    associations=dict(instances=len(large),window_waiting_pearson=float(large.window_fraction.corr(large.waiting_share)),
                      demand_fill_pearson=float(large.mean_demand_over_Q.corr(large.mean_capacity_fill)))
    (folder/'ASSOCIATIONS_DESCRIPTIVES.json').write_text(json.dumps(associations,indent=2),encoding='utf-8')
    text=r'''### 6.11. Scénarios géographiques, fenêtres et capacités

**Population comparable.** Cette analyse utilise la campagne initiale à dix secondes de recherche : 356 instances, une observation par instance après moyenne de ses graines. Elle ne mélange pas ces mesures avec l'archive à budgets différents. C désigne les clients groupés, R les clients répartis aléatoirement et RC une organisation mixte. Les six familles C1/C2/R1/R2/RC1/RC2 combinent ces structures et des paramètres temporels et de capacité différents. Nous mesurons les caractéristiques des fichiers originaux, plutôt que supposer que l'indice 2 élargit uniformément toutes les contraintes. Les données ne sont pas modifiées pour construire ces scénarios.

**Indicateurs de difficulté.** Une durée brute plus élevée n'implique pas une mauvaise solution : les nombres de clients et les services diffèrent. Nous examinons aussi le gain par rapport à la construction de la même instance, la part d'attente et le calcul réel. L'écart au témoin reste descriptif : des différences entre familles peuvent venir de la pertinence temporelle variable de leurs références distance, et non seulement de la difficulté intrinsèque.

Le gain depuis la construction est $G=100(T_{\mathrm{construction}}-T_{\mathrm{finale}})/T_{\mathrm{construction}}$. Par exemple, un gain de 19,32 % signifie une diminution de durée de 19,32 % depuis le départ construit ; ce n'est pas un gap de 19,32 % par rapport au BKS. Pour cet indicateur, une valeur positive élevée est une amélioration. La colonne « Écart témoin » utilise une autre référence et doit être interprétée séparément.

'''
    text+=table(geography.rename(columns={'geography':'Géographie','instances':'Instances','delta_reference_pct':'Écart témoin (%)',
        'initial_gain_pct':'Gain construction (%)','waiting_pct':'Part attente (%)',
        'reference_waiting_pct':'Attente témoin (%)','calculation_s':'Calcul moyen (s)'}))
    text+=r'''

![Performances par géographie et par taille dans la campagne initiale.](../livraison/duree_figures/familles_par_taille.png)

**Lecture des cartes de chaleur.** Chaque case représente la moyenne d'instances de la même géographie et de la même taille. Le panneau gauche indique le gain depuis la construction : une valeur positive correspond à une baisse de durée. Le panneau droit indique l'écart au plan témoin : une valeur négative correspond à une durée inférieure à celle du témoin, sans preuve de nouvel optimum temporel. Les deux échelles sont distinctes et leurs couleurs ne doivent pas être comparées directement.

**Intérêt et continuité.** Le tableau global résume les trois géographies ; les cartes séparent ensuite les tailles pour éviter de confondre structure spatiale et nombre de clients. Elles montrent les cas où la recherche améliore beaucoup son départ, ainsi que ceux où le témoin reste meilleur. Cette lecture conduit à examiner les fenêtres et la capacité, qui participent aussi à la faisabilité des mouvements.

**Fenêtres et capacité : définitions mesurées.** La largeur d'une fenêtre est $l_i-e_i$ ; sa moyenne divisée par H donne une ouverture relative à l'horizon. Ce ratio ne mesure ni la position des fenêtres, ni leur compatibilité avec les trajets. Le ratio moyen $q_i/Q$ mesure la part de camion occupée par un client. La borne $\lceil\sum_i q_i/Q\rceil$ donne un minimum de véhicules lié uniquement aux quantités ; les fenêtres peuvent imposer davantage de tournées. Enfin, le remplissage observé est $\sum_i q_i/(mQ)$ pour m véhicules utilisés, puis moyenné sur les graines.

'''
    text+=table(families.rename(columns={'family':'Famille','instances':'Instances','capacity_min':'Q min','capacity_max':'Q max',
        'horizon_min':'H min','horizon_max':'H max','mean_window_width':'Largeur fenêtre moyenne (u.t.)',
        'window_pct':'Fenêtre/H (%)','demand_over_Q_pct':'Demande/Q (%)','final_capacity_fill_pct':'Remplissage (%)'}))
    text+='''

![Fenêtres, attentes et remplissage : observations à 1 000 clients.](../livraison/duree_figures/contraintes_observees.png)

**Lecture des nuages.** Chaque point est une des soixante instances à 1 000 clients, après moyenne de ses graines. À gauche, nous rapprochons l'ouverture relative moyenne des fenêtres de la part d'attente finale. À droite, nous rapprochons la demande relative à la capacité du remplissage effectif. Les couleurs distinguent C, R et RC. La taille et le budget de recherche sont fixes, mais les autres caractéristiques restent différentes.

**Intérêt et limites.** Ces nuages relient les contraintes du modèle au comportement observé. Une capacité élevée autorise certains regroupements sans les garantir ; les horaires peuvent empêcher de remplir un camion. Des fenêtres longues peuvent aussi laisser subsister des attentes selon leur position et l'ordre des visites. Il s'agit d'associations descriptives, pas d'une expérience modifiant une seule contrainte : géographie, services, horizon et demandes peuvent se confondre. Nous ne concluons donc pas à un effet causal isolé de Q ou de la largeur des fenêtres. Les limites de l'approche et les réglages contrôlés de la section précédente complètent cette lecture.
'''
    ordered=geography.sort_values('initial_gain_pct',ascending=False)
    text+='\n\n**Lecture du bilan.** '
    for r in ordered.itertuples():
        text+=f'Pour {r.geography}, le gain moyen depuis la construction vaut {r.initial_gain_pct:.2f} %, la part d’attente {r.waiting_pct:.2f} % et l’écart au témoin {r.delta_reference_pct:+.2f} %. '
    text+='Ces valeurs décrivent la campagne initiale et ses départs ; elles ne classent pas universellement la difficulté des familles. Les tableaux détaillés par taille et famille permettent de revenir aux instances avant de proposer une modification.'
    text+=f'''\n\n**Association et causalité.** Sur les soixante cas à 1 000 clients, la corrélation de Pearson entre ouverture relative des fenêtres et part d'attente vaut {associations['window_waiting_pearson']:.3f}, et celle entre demande relative à Q et remplissage vaut {associations['demand_fill_pearson']:.3f}. Ces associations modestes ne suffisent pas à isoler un effet causal des contraintes. La colonne d'attente du témoin rappelle aussi que les plans de référence n'ont pas été sélectionnés pour minimiser ce temps : leurs écarts de durée peuvent différer fortement selon les familles.'''
    (ROOT/'docs/ANALYSE_SCENARIOS_DUREE.md').write_text(text+'\n',encoding='utf-8')
    return text,dict(instances=len(df),geographies=geography.to_dict('records'),associations=associations)


def harmonize(nb,include_experiments=True):
    """Conserve le récit et remplace seulement les passages identifiés."""
    nb.cells=[c for c in nb.cells if not c.metadata.get('reporting_completion')]
    first=nb.cells[0]
    if CONTEXT not in first.source:
        marker='Nous cherchons des tournées'
        assert marker in first.source
        first.source=first.source.replace(marker,CONTEXT+'\n\n'+marker,1)
    old='Le problème généralise le TSP :'
    for cell in nb.cells:
        if cell.cell_type!='markdown':continue
        if cell.source.startswith('## 2. Modélisation'):
            cell.source=(ROOT/'docs/MODELE_DUREE.md').read_text(encoding='utf-8').strip()
        if cell.source.startswith('## 3.') and old in cell.source:
            begin=cell.source.index(old)
            end=cell.source.index('Le PLNE de',begin)
            cell.source=cell.source[:begin]+COMPLEXITY.strip()+'\n\n'+cell.source[end:]
        cell.source=cell.source.replace('la prise en compte d’un trafic dépendant de l’heure demeure une extension non démontrée.',
            'le trafic dépendant de l’heure demandé dans l’énoncé n’est pas traité dans cette version statique.')
        cell.source=cell.source.replace('minimisation de la durée totale d’une tournée ; extension annoncée au trafic horaire.',
            'minimisation de la durée totale et prise en compte annoncée du trafic horaire ; ce dernier point reste non réalisé ici.')
        cell.source=cell.source.replace('tailles plafonnées à 1 000 clients, budget de dix secondes, peu de graines sur la couverture globale',
            'tailles plafonnées à 1 000 clients, dix secondes de recherche dans la campagne initiale et des reprises ciblées plus longues, peu de graines sur la couverture globale')
        if cell.source.startswith('## 7.') and 'sensibilité contrôlée' not in cell.source:
            cell.source=cell.source.replace('Les fichiers `results/time_objective/catalogue/runs/`',
                'Les compléments séparent une sensibilité contrôlée à quatre secondes de recherche et une analyse des scénarios sur les mesures initiales. Les phases mutualisées de la sensibilité ont des temps totaux recomposés ; les reprises d’optimisation conservent leur effort cumulé. Ces études ne prouvent ni un optimum temporel sur les grandes instances ni une généralisation à tous les budgets.\n\nLes fichiers `results/time_objective/catalogue/runs/`')
    if include_experiments:
        sensitivity_text,sensitivity_info=sensitivity()
        scenario_text,scenario_info=scenarios()
        from scripts.revision_duree import insert_before
        cells=[]
        for name,text in [('sensibilite',sensitivity_text),('scenarios',scenario_text)]:
            cell=nbformat.v4.new_markdown_cell(text)
            cell.metadata['reporting_completion']=name
            cells.append(cell)
        anchor='### 6.12.' if any(c.metadata.get('cpu_completion') for c in nb.cells) else '## 7.'
        insert_before(nb,anchor,cells)
        return dict(sensitivity=sensitivity_info,scenarios=scenario_info)
    return {}


def main():
    from scripts.revision_duree import write_markdown
    path=ROOT/'notebooks/Livrable_Final_CVRPTW.ipynb'
    nb=nbformat.read(path,as_version=4)
    codes=[c.source for c in nb.cells if c.cell_type=='code']
    info=harmonize(nb)
    assert codes==[c.source for c in nb.cells if c.cell_type=='code']
    nbformat.validate(nb);nbformat.write(nb,path);write_markdown(nb)
    (BASE/'reporting_completion.json').write_text(json.dumps(info,indent=2),encoding='utf-8')
    print(json.dumps(info,indent=2))


if __name__=='__main__':main()
