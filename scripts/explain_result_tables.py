"""Ajoute des clés de lecture locales sans modifier les mesures ni les solveurs."""
from pathlib import Path
import hashlib
import json
import re
import sys
import unicodedata
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import nbformat
import pandas as pd
from scripts.revision_duree import write_markdown

TABLE=re.compile(r'(?m)(?:^\|[^\n]*\n?){2,}')
START='<!-- LECTURE_TABLE_BEGIN -->'
END='<!-- LECTURE_TABLE_END -->'


def normalized(value):
    return ''.join(c for c in unicodedata.normalize('NFKD',value.lower()) if not unicodedata.combining(c))


def targeted_notes():
    f=pd.read_csv(ROOT/'results/time_objective/outliers10/AVANT_APRES_ESSAIS.csv')
    g=f[f.instance.eq('C1_10_6')]
    assert len(g)==2 and g.valid.all()
    def positive(col):
        values=g.loc[g[col]>0,col]
        assert len(values)==2
        return values.mean()
    return '''**Lecture des colonnes et des étapes de ce tableau.**

- **Instance** : identifiant du jeu de données, avec les mêmes clients et contraintes aux trois étapes. **Clients** : nombre de clients à servir, sans compter le dépôt.
- **Essais** : nombre de couples instance–graine suivis. Une graine fixe les tirages aléatoires pour permettre la reproduction. Une reprise de la même solution avec la même graine n'ajoute pas un essai dans cette colonne ; elle ajoute du temps de calcul.
- **Réalisables** : nombre de ces essais dont la solution finale respecte toutes les contraintes : couverture unique, capacité, fenêtres de début de service, flotte et retour au dépôt avant sa fermeture.
- **Avant — écart positif moyen / statut** : bilan du profil hybride historique du catalogue, avant cette mise au point. Il associait déjà notre code à PyVRP. Cette colonne ne mesure donc pas l'ILS autonome utilisé dans les nouvelles commandes de comparaison.
- **Prototype — écart positif moyen / statut** : bilan du premier profil renforcé en durée, avec constructions Clarke–Wright et insertion séquentielle, recherche locale externe PyVRP et partitionnement de tournées. Son budget total demandé était de dix secondes, après préchauffage, avec mesure des dépassements éventuels.
- **Après — écart positif moyen / statut** : bilan de la meilleure solution observée pour chaque couple instance–graine après les reprises ciblées. Une continuation HGS externe PyVRP n'est retenue que si elle améliore la durée. Lorsque le prototype n'est pas amélioré, les colonnes prototype et après peuvent être identiques. Ce sont des résultats d'archive à budgets variables, distincts du profil actuel `size_based` expliqué plus loin.
- **Pire après / statut** : plus grand écart individuel après optimisation, parmi les essais réalisables et comparables de la ligne. Cette colonne empêche une bonne moyenne de masquer un essai moins bon ; les échecs restent comptés dans la colonne Réalisables.
- **Calcul cumulé moyen (s)** : pour chaque couple instance–graine, somme du temps réel du prototype et des continuations tentées, y compris celles qui n'ont pas amélioré le résultat ; puis moyenne de ces sommes sur les essais de la ligne. Le calcul historique « avant », le préchauffage et le démarrage extérieur à ces chronométrages ne sont pas ajoutés ici. Cette valeur mesure l'effort de mise au point enregistré, et non la durée de livraison ou un temps CPU.

**Sens de la moyenne positive conditionnelle.** À chaque étape, nous calculons l'écart relatif à la durée du même plan témoin réévalué : `100 × (durée solution − durée témoin) / durée témoin`. La durée comprend trajets, attentes, services et retours, avec départs à zéro. La moyenne affichée porte uniquement sur les écarts strictement positifs de cette étape. La mention « positifs m/N » indique que m des N essais contribuent à cette moyenne ; les autres ne sont pas remplacés par une valeur artificielle. Les sous-ensembles peuvent changer entre avant et après : une différence de ces moyennes ne constitue pas automatiquement un gain moyen sur tous les essais.

**Lecture des statuts.** « Aucun écart positif » signifie qu'aucun écart disponible n'est strictement positif ; cela ne démontre pas l'optimalité. « Référence dépassée » signifie que la solution vérifiée a une durée inférieure à celle du comparateur heuristique. « Référence égalée — optimalité non démontrée » signifie que les coûts sont identiques. « Optimum atteint » est réservé aux cas disposant d'une preuve compatible. Une référence insuffisante ou un échec de recherche empêche de chiffrer un gap fiable. Les plans publics ayant été optimisés en distance, leur réévaluation en durée ne leur confère pas une preuve d'optimalité temporelle.

'''+f'''**Exemple réel : C1_10_6.** Cette ligne suit deux graines sur 1 000 clients, avec deux solutions finales réalisables. La moyenne des deux écarts positifs passe de {positive('baseline_pct'):.4f} % avant la mise au point à {positive('first_variant_pct'):.4f} % pour le prototype, puis {positive('final_pct'):.4f} % après les reprises. Le pire résultat final vaut {g.final_pct.max():.4f} %, et l'effort cumulé moyen de cette mise au point est de {g.cumulative_runtime_s.mean():.3f} secondes par couple instance–graine. Il ne s'agit ni du temps d'une livraison ni d'un résultat obtenu sous un budget uniforme de dix secondes.

**Intérêt dans la démonstration.** Ce tableau relie les changements algorithmiques à la qualité des solutions et à l'effort supplémentaire consenti. Il complète les résultats initiaux et prépare le graphique suivant, qui compte aussi les références améliorées et égalées. Les anciennes mesures restent disponibles : le tableau décrit la progression sur les cas ciblés, sans démontrer une supériorité à temps égal ou un gap à l'optimum temporel.
'''


def general_notes(header,context):
    keys=[normalized(h) for h in header];joined=' '.join(keys)
    if not (any(t in joined for t in ['duree','duration','ecart','delta','moyenne_positive','cpu','calcul',
                                    'references_depassees','q0.25','recherche_s','remplissage','optimum','trajets','attentes'])
            or all(k in keys for k in ['ils','sa','pyvrp'])):return ''
    notes=[]
    identity=[]
    if any(k in ['instance','instances'] for k in keys):identity.append('une instance est un jeu de clients et de contraintes')
    if any(k in ['n','clients'] for k in keys):identity.append('`n` ou Clients compte les clients, dépôt exclu')
    if any(k in ['essais','attempts','runs','resolutions'] for k in keys):identity.append('Essais, `attempts`, `runs` ou résolutions compte les exécutions du périmètre indiqué')
    if any(k in ['realisables','realisable','feasible','faisables'] for k in keys):identity.append('Réalisables, `feasible` ou faisables compte les solutions respectant toutes les contraintes')
    if identity:notes.append('**Périmètre.** '+' ; '.join(identity)+'. Les graines correspondent aux tirages aléatoires ; elles ne sont pas des instances supplémentaires.')
    statistics={
        'mean_duration':'`mean_duration` est la durée moyenne des solutions réalisables',
        'std_duration':'`std_duration` est leur écart-type, qui décrit la dispersion',
        'best_duration':'`best_duration` est la plus petite durée observée, sans preuve d’optimalité',
        'mean':'`mean` est la moyenne', 'median':'`median` est la médiane',
        'std':'`std` est l’écart-type', 'minimum':'`minimum` est la plus petite valeur',
        'maximum':'`maximum` est la plus grande valeur',
        'q0.25':'`q0.25` et `q0.75` sont les premier et troisième quartiles',
        'iqr':'`iqr` est l’écart entre ces quartiles',
        'reference_duration':'`reference_duration` est la durée du plan témoin réévalué',
        'reference':'`reference` est la durée du comparateur indiqué',
        'initial_duration':'`initial_duration` est la durée avant la phase d’amélioration indiquée',
        'reinforced_duration':'`reinforced_duration` est la durée du profil renforcé',
        'duration':'`duration` est la durée totale de la solution',
        'optimum':'`optimum` est le coût optimal établi sur ces petits cas de contrôle',
        'returned':'`returned` est le coût retourné par le solveur'}
    parts=[definition for key,definition in statistics.items() if key in keys]
    if parts:notes.append('**Valeurs.** '+' ; '.join(parts)+'. Les durées de livraison sont exprimées en unités de temps (u.t.) : trajets, attentes, services et retours au dépôt, pour des départs à zéro.')
    if 'trajets' in joined or 'attentes' in joined:
        notes.append('**Composition de la durée.** Trajets additionne les déplacements, retours au dépôt inclus ; attentes mesure le temps avant l’ouverture des fenêtres ; services représente les opérations chez les clients. Ces trois composantes s’additionnent pour former la durée totale. Avant et après désignent les phases précisées dans cette section ; les services restent constants lorsque les mêmes clients sont servis.')
    if 'moyenne_positive' in joined or 'conditionnelle' in joined or 'mediane_positive' in joined:
        notes.append('**Statistiques de comparaison.** La moyenne et la médiane positives portent seulement sur les écarts strictement positifs au plan témoin réévalué en durée. Les effectifs précisent combien d’essais y contribuent ; ce ne sont pas des statistiques globales sur tous les essais. Un pourcentage élevé signifie une durée supérieure au comparateur, dont l’optimalité temporelle n’est pas démontrée.')
    if any(t in joined for t in ['references_depassees','reference_amelioree','references_egalees','reference_egalee','non_comparables','sans_reference','statut']):
        notes.append('**Statuts et effectifs.** Positifs compte les solutions plus coûteuses que le témoin ; référence améliorée ou dépassée signifie un coût inférieur vérifié ; référence égalée signifie un coût identique sans preuve d’optimalité. Non comparables ou sans référence indique l’absence de comparaison compatible. Les colonnes au-dessus de six comptent les dépassements du seuil ; elles ne sont pas des pourcentages moyens.')
    times=[]
    if any(t in joined for t in ['wall','reel','ecoule','calcul','calculation']):times.append('réel, écoulé, `wall_s` et calcul désignent le temps de résolution chronométré en secondes selon le périmètre de la campagne')
    if 'cpu' in joined:times.append('CPU mesure le temps processeur consommé ; un CPU cumulé additionne les processus, et un maximum CPU est le plus grand temps observé')
    if any(t in joined for t in ['requested','budget','recherche_s','reference_s']):times.append('budget, `requested` ou `recherche_s` est une allocation demandée, pas le temps total mesuré ; `reference_s` concerne la recherche du comparateur')
    if times:notes.append('**Temps de calcul.** '+' ; '.join(times)+'. Ces secondes de calcul sont distinctes des durées de livraison en u.t. Une moyenne de temps porte sur le groupe annoncé, et non sur la somme de tout le catalogue.')
    if 'duration_gain_pct' in joined or 'variation duree' in joined or 'gain construction' in joined:
        notes.append('**Variation entre méthodes.** Le gain ILS/renforcé vaut `100 × (durée initiale − durée renforcée) / durée initiale` : positif si le renforcé améliore l’initial, négatif dans le cas inverse. Un gain depuis la construction prend la construction comme point de départ. Les variations de sensibilité suivent la convention annoncée dans leur section. Ces variations ne sont pas les gaps au plan témoin.')
    if 'remplissage' in joined:
        notes.append('**Contraintes.** Q est la capacité d’un véhicule et H l’horizon de fermeture du dépôt. La largeur d’une fenêtre mesure son temps d’ouverture ; fenêtre/H la rapporte à l’horizon. Demande/Q rapporte la demande d’un client à la capacité ; le remplissage décrit la charge utilisée dans les tournées. Les pourcentages décrivent ici des caractéristiques des données, pas des gaps.')
    if 'method' in keys or 'methode' in keys or all(k in keys for k in ['ils','sa','pyvrp']):
        notes.append('**Méthodes.** ILS et SA désignent notre recherche locale itérée et notre recuit simulé ; PyVRP et OR-Tools sont des moteurs externes. Hybrid et les profils renforcés combinent notre code avec les bibliothèques attribuées dans la section. Dans le tableau à une colonne par méthode, les cellules sont les durées moyennes observées sur le lot annoncé.')
    if not notes:return ''
    return '**Clés de lecture de ce tableau.**\n\n'+'\n\n'.join(notes)+'\n'


def main():
    path=ROOT/'notebooks/Livrable_Final_CVRPTW.ipynb';nb=nbformat.read(path,4)
    codes=[c.source for c in nb.cells if c.cell_type=='code']
    nb.cells=[c for c in nb.cells if not c.metadata.get('table_reading_sensitivity')]
    guarded=[ROOT/'results/gap_tables/DETAIL_TOUS_LES_ECARTS.csv',ROOT/'results/time_objective/outliers10/AVANT_APRES_ESSAIS.csv']+list((ROOT/'algo').glob('*.py'))
    hashes={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in guarded}
    count=0;targeted=0;cells=[]
    for cell in nb.cells:
        if cell.cell_type!='markdown':cells.append(cell);continue
        source=re.sub(re.escape(START)+r'.*?'+re.escape(END)+r'\s*','',cell.source,flags=re.S)
        sensitivity=source.startswith('### 6.10.')
        extra=[]
        def annotate(match):
            nonlocal count,targeted
            table=match.group(0).rstrip()
            header=[c.strip() for c in table.splitlines()[0].strip('|').split('|')]
            if 'Prototype' in table.splitlines()[0] and 'Calcul cumulé' in table.splitlines()[0]:
                targeted+=1;notes=targeted_notes()
                labels=['Instance','Clients','Essais','Réalisables','Avant — écart positif moyen / statut',
                    'Prototype — écart positif moyen / statut','Après — écart positif moyen / statut',
                    'Pire après / statut','Calcul cumulé moyen (s)']
                lines=table.splitlines();lines[0]='| '+' | '.join(labels)+' |';table='\n'.join(lines)
            else:notes=general_notes(header,cell.metadata)
            if not notes:return match.group(0)
            count+=1
            block=START+'\n'+notes+'\n'+END+'\n\n'
            if sensitivity:extra.append(block);return match.group(0)
            return table+'\n\n'+block
        cell.source=TABLE.sub(annotate,source)
        meta=cell.metadata.get('comparison_render')
        if meta and not sensitivity:
            meta['rendered_sha256']=hashlib.sha256(cell.source.encode()).hexdigest()
        cells.append(cell)
        if extra:cells.append(nbformat.v4.new_markdown_cell(''.join(extra),metadata={'table_reading_sensitivity':True}))
    assert targeted==1
    nb.cells=cells
    assert codes==[c.source for c in nb.cells if c.cell_type=='code']
    assert all(hashlib.sha256(p.read_bytes()).hexdigest()==h for p,h in hashes.items())
    nbformat.validate(nb);nbformat.write(nb,path);write_markdown(nb)
    receipt=dict(annotated_tables=count,detailed_targeted_table=targeted,
        executable_cells_unchanged=True,measured_values_and_algorithms_unchanged=True,
        scope='Editorial column definitions and example from recorded C1_10_6 trials')
    (ROOT/'livraison/LECTURE_TABLEAUX.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    print(json.dumps(receipt,indent=2))


if __name__=='__main__':main()
