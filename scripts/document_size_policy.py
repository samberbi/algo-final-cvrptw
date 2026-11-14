"""Documenter la correction réellement mesurée du profil de test par taille."""
from pathlib import Path
import json
import re
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import nbformat
import pandas as pd
from scripts.revision_duree import write_markdown


def main():
    out=ROOT/'results/policy_v2_audit'
    receipt=json.loads((out/'AUDIT.json').read_text(encoding='utf-8'))
    assert receipt['issues']==0 and receipt['new_small_trials']==72
    frame=pd.read_csv(out/'AVANT_APRES_PETITES.csv')
    assert frame.valid.all() and (frame.duration<=frame.initial_duration+1e-7).all()
    rows=[]
    for n,g in frame.groupby('n'):
        positive=g[g.signed_delta_pct>1e-8]
        rows.append(dict(Clients=n,Essais=len(g),Réalisables=int(g.valid.sum()),
            Référence_améliorée=int((g.signed_delta_pct < -1e-8).sum()),
            Référence_égalée=int((g.signed_delta_pct.abs()<=1e-8).sum()),
            Sans_référence=int(g.signed_delta_pct.isna().sum()),
            Écarts_positifs=len(positive),Au_dessus_de_6=int((g.signed_delta_pct>6).sum()),
            Moyenne_positive_pct=positive.signed_delta_pct.mean() if len(positive) else 'Sans écart positif',
            Réel_moyen_s=g.wall_s.mean()))
    summary=pd.DataFrame(rows)
    summary.to_csv(out/'SYNTHESE_PAR_TAILLE.csv',index=False,encoding='utf-8-sig')
    example=frame[(frame.instance=='RC101') & (frame.n==100)].iloc[0]
    text='''### 6.14. Correction du profil de test : préserver la meilleure durée

Le premier sélecteur utilisait la construction seule jusqu’à 100 clients.
Cette variante rapide était une ablation, mais son emploi par défaut faisait
perdre de la qualité : RC101/100, graine 4101, coûtait 3 335,2 unités de temps
contre 2 991,6 pour le plan public réévalué, soit +11,4855 %. Son rang 1
signifiait seulement qu’une seule méthode avait été lancée.

**La version 2 corrige cette cause algorithmique.** Jusqu’à 100 clients, elle
construit douze candidats regret-2, conserve le meilleur, applique la recherche
locale externe PyVRP avec 40, 80 puis 120 voisins tant que le budget le permet,
puis consacre le temps restant à notre ILS et ses opérateurs propres. Chaque
étape est vérifiée et conserve une durée au plus égale à celle de l’étape
précédente. Les tournées initiales et finales sont archivées pour le contrôler.
Le calcul ne lit aucune référence ni cible de gap. Ce profil est hybride :
la recherche locale PyVRP n’est pas présentée comme notre implémentation.

Au-delà de 100 clients, le profil renforcé fournit d’abord une solution :
constructions propres, recherche locale PyVRP et partitionnement sur un pool
de tournées par HiGHS. Son budget est limité à cinq secondes (ou au budget
demandé s’il est inférieur). Avec plus de deux secondes restantes, une
continuation **HGS externe PyVRP**, à 60 voisins, reçoit cette solution.
Une seconde est réservée à la préparation ; le temps réellement mesuré reste
affiché car cette réserve n’est pas une garantie stricte. Les contraintes et
la durée complète sont revérifiées, et aucune solution moins bonne n’est retenue.
Le seuil dépend uniquement du nombre de clients. Les moteurs historiques,
leurs résultats et la première ablation restent disponibles ; ils ne sont pas
réétiquetés comme des résultats de la version 2.

**Campagne réellement exécutée : 72 essais**, une graine (4101), budget souple
de cinq secondes, deux processus indépendants : les 56 Solomon à 100 clients
et les 16 préfixes disponibles à 25/50 clients. Chaque solution et chaque plan
de référence sont recalculés indépendamment depuis les coordonnées originales,
avec contrôle de couverture, capacité, fenêtres, retour au dépôt et flotte.
Le budget demandé et le temps total mesuré restent distincts.

'''+summary.to_markdown(index=False,floatfmt='.4f')+f'''

Sur RC101/100, la nouvelle durée est **{example.duration:.1f}**, contre
{example.initial_duration:.1f} à la construction : réduction réelle de
{example.improvement:.1f} unités, soit {100*example.improvement/example.initial_duration:.2f} %.
Elle améliore le comparateur heuristique réévalué. Ce résultat ne prouve pas
un optimum temporel et ne reçoit pas un faux écart positif.

La moyenne indiquée est conditionnelle aux seuls écarts strictement positifs :
les autres effectifs sont affichés séparément. Les références sont des plans
publics optimisés en distance puis réévalués en durée, ou des solutions OR-Tools
indépendantes pour les petits préfixes ; aucune n’est déclarée optimum temporel.
Une égalité de coût ne constitue donc pas une preuve d’optimalité.

L’absence de dépassement dans ces 72 essais ne garantit pas le résultat de
toute graine ou de toute grande instance. Les tableaux complets avant/après,
les tournées, les chronologies d’amélioration, les budgets et les sources sont
conservés dans `results/policy_v2_audit/`. Les anciens dépassements restent
consultables dans l’audit ; aucune mesure historique n’est effacée.

```powershell
python scripts/test_instances.py --instances RC101 --seconds 5 --label verification_RC101
python scripts/test_instances.py --all --sizes 25 50 100 --seconds 5 --workers 2 --label correction_petites
python scripts/test_instances.py --instances C2_10_2 C2_10_7 --seconds 60 --label verification_grandes
```

Le moteur réellement exécuté et son attribution sont affichés dans le terminal.
Le garde-fou du processus est de 120 secondes ; les dépassements éventuels du
budget souple restent mesurés, sans plafonnement artificiel.
'''
    large_path=out/'AVANT_APRES_GRANDES_HGS.csv'
    if large_path.exists():
        large=pd.read_csv(large_path)
        table=large[['instance','n','initial_duration','duration','reference','initial_delta_pct','signed_delta_pct','wall_s','cpu_s']]
        text+='''

**Contrôle ciblé à 1 000 clients.** Le profil renforcé fini s’arrêtait après
environ cinq secondes malgré un budget de trente secondes. Sur C2_10_2 et
C2_10_7, nous testons maintenant le pipeline avec un budget de soixante
secondes, graine 4101. Les coûts « avant » sont les solutions initiales
réellement transmises au HGS pendant ces mêmes essais, et non des solutions
choisies après coup. Deux processus ont été utilisés. Le coût et le temps
incluent le profil initial et la continuation ; préparation et contrôle
du processus restent distingués dans les fichiers JSON.

'''+table.to_markdown(index=False,floatfmt='.4f')+'''

Le gain provient d’une exploration HGS supplémentaire sur une population
initialisée avec notre solution réalisable. Il n’est pas attribué à l’ILS
autonome. Cette comparaison montre le bénéfice de cette continuation sur
ces deux cas, avec une augmentation du temps effectivement utilisé ; elle
n’isole pas un avantage à temps de calcul égal. Une seule graine ne démontre
pas la robustesse du résultat sur toutes les instances de grande taille.
'''
    (ROOT/'docs/SELECTION_PAR_TAILLE.md').write_text(text,encoding='utf-8')
    path=ROOT/'notebooks/Livrable_Final_CVRPTW.ipynb';nb=nbformat.read(path,4)
    existing=next((c for c in nb.cells if c.metadata.get('size_policy_summary')),None)
    nb.cells=[c for c in nb.cells if not c.metadata.get('size_policy_summary')]
    cell=nbformat.v4.new_markdown_cell(text,metadata={'size_policy_summary':True})
    if existing is not None:cell.id=existing.id
    nb.cells.insert(next(i for i,c in enumerate(nb.cells) if c.source.startswith('## 7.')),cell)
    old='la construction seule jusqu’à 100 clients'
    new='la construction suivie de la recherche locale PyVRP et de notre ILS jusqu’à 100 clients'
    nb.cells[0].source=nb.cells[0].source.replace(old,new)
    nb.cells[0].source=nb.cells[0].source.replace('et notre profil renforcé au-delà ;','et notre profil renforcé suivi du HGS externe selon le temps restant au-delà ;')
    meta=nb.cells[0].metadata.get('comparison_render')
    if meta:
        meta['original_source']=meta['original_source'].replace(old,new).replace('et notre profil renforcé au-delà ;','et notre profil renforcé suivi du HGS externe selon le temps restant au-delà ;')
    nbformat.validate(nb);nbformat.write(nb,path);write_markdown(nb)
    notice='''## Configuration actuelle des commandes : sélection par taille

Le profil par défaut `size_based` est en version 2 : construction regret-2,
recherche locale **PyVRP externe** puis notre ILS jusqu’à 100 clients ; profil
renforcé puis HGS externe selon le temps restant au-delà. La meilleure durée
est conservée à chaque étape.
Le moteur et les temps mesurés sont affichés et enregistrés. Le choix ne lit
aucun gap. La campagne de 72 essais et ses limites sont documentées dans
[SELECTION_PAR_TAILLE.md](docs/SELECTION_PAR_TAILLE.md).
Pour lancer la construction seule comme ablation : `--method construction`.
Pour forcer le renforcé : `--method refined`. Les anciens résultats restent
conservés et ne représentent pas la nouvelle configuration.

'''
    for doc in [ROOT/'README.md',ROOT/'COMMANDES_TERMINAL.md']:
        body=doc.read_text(encoding='utf-8')
        title='## Configuration actuelle des commandes : sélection par taille'
        if title in body:
            body=re.sub(r'## Configuration actuelle des commandes : sélection par taille\n.*?(?=\n## |\Z)',notice.rstrip(),body,flags=re.S)
        else:
            split=body.find('\n\n');body=body[:split+2]+notice+body[split+2:]
        body=body.replace("Nouveau défaut : construction seule jusqu'à 100 clients, renforcé au-delà",
                          'Défaut v2 : construction + LS PyVRP + ILS jusqu’à 100 clients, renforcé puis HGS au-delà')
        doc.write_text(body,encoding='utf-8')
    print(summary.to_string(index=False))


if __name__=='__main__':main()
