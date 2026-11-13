"""Synchronise les liens et consignes de l'extension sans refaire la remise."""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]


def replace_section(path, marker, text):
    previous = path.read_text(encoding='utf-8')
    previous = previous.split(marker)[0].rstrip()
    path.write_text(previous+marker+text.rstrip()+'\n', encoding='utf-8')


def main():
    replace_section(ROOT/'README.md', '\n\n## Extension temporelle Dabia2013\n', '''

Le [pilote Dabia2013](docs/EXTENSION_DABIA2013.md), section **6.13 du notebook**,
compare le même objectif `Duration` des deux côtés : trajets, attentes, services,
avec départs optimisés et trajets dépendant de l'heure. C'est un nouveau profil,
distinct du modèle statique à départs nuls décrit plus haut. Les coûts natifs des
deux benchmarks ne sont pas mélangés.

Six instances à **25 clients**, trois graines, cinq secondes par résolution :
**18/18 solutions réalisables et au coût des BKS**, gap moyen/maximal 0 %, CPU
maximal mesuré 5,031 s. Six essais préliminaires sont également conservés. Les
références C101, R201 et RC201 signalent une recertification en attente après
changement d'arithmétique ; le rapport ne revendique pas de nouvelle preuve
d'optimalité. Aucune mesure Dabia à 50/100 clients ou à 1 000 clients n'est annoncée.

**Contribution :** notre insertion séquentielle, ILS, relocate/swap/2-opt/2-opt*,
cache et orchestration ; évaluation des départs optimaux et contrôle fournis
par le moteur externe **MAMUT-routing-lib 0.12.0**. Le HGS statique PyVRP n'est
pas utilisé pour ce pilote.

```powershell
py -3.12 -m venv .venv_dabia
.\\.venv_dabia\\Scripts\\python.exe -m pip install -r requirements-dabia.txt
.\\.venv_dabia\\Scripts\\python.exe -m pytest tests/test_dabia.py -q
.\\.venv_dabia\\Scripts\\python.exe scripts/validate_dabia.py
.\\.venv_dabia\\Scripts\\python.exe scripts/benchmark_dabia.py --instances R201 --seconds 5 --label essai_dabia_R201
```

Le dernier appel résout une seule instance et affiche le gap BKS Duration dans
le terminal. Les relances créent automatiquement un nouveau dossier numéroté.
Pour les six familles : omettre `--instances R201`. Les fichiers sont écrits dans
`results/dabia2013/<label>/`. La validation des résultats fournis est
`results/dabia2013/VALIDATION.json` ; le XML des **16 tests TD réussis** est
`results/dabia2013/tests.xml`. Dans l'environnement historique sans MAMUT,
la suite statique conserve **171 tests réussis** ; le module TD y est explicitement
ignoré et doit être vérifié dans son environnement séparé.
''')
    replace_section(ROOT/'docs/MODELE_DUREE.md', '\n\n## Extension TDVRPTW : départs optimisés\n', r'''

La formulation précédente reste celle des expériences statiques à 100–1 000
clients et du PLNE exact pour petits cas. Le nouveau module `algo/dabia.py`
traite séparément les six instances Dabia2013 à 25 clients décrites dans
[EXTENSION_DABIA2013.md](EXTENSION_DABIA2013.md).

Le départ $D_p$ n'est plus nul et le trajet dépend de l'heure :
$\alpha_{ij}(t)=t+\tau_{ij}(t)$. La récurrence temporelle applique chaque
fonction d'arrivée, puis $B_i=\max(A_i,e_i)$, puis le service $F_i=B_i+s_i$.
L'objectif compatible est $\min\sum_p(R_p-D_p)$, pas $\min\sum_pR_p$.
Le contrôleur externe MAMUT 0.12.0 optimise le départ de chaque ordre proposé.
Capacité, visite unique, flotte et fenêtres restent obligatoires.

Notre PLNE statique n'est pas présenté comme un PLNE exact de ce problème à
fonctions temporelles. Les données et leurs unités natives ne sont pas
converties à la convention DIMACS. Les coûts de BKS en durée sont contrôlés
après recherche et les notes de recertification originales restent visibles.
''')
    replace_section(ROOT/'docs/PRINCIPES_ET_APPLICATION_ALGORITHMES.md', '\n\n## Profil temporel propre Dabia2013\n', '''

`algo/dabia.py` ne réutilise pas le HGS statique pour des fonctions temporelles.
Notre insertion essaie des positions selon leur véritable variation de durée ;
l'ILS explore relocate, swap, 2-opt et 2-opt*, applique des perturbations et des
redémarrages, puis conserve une archive monotone. La bibliothèque externe MAMUT
calcule le coût de chaque ordre avec son départ optimal et vérifie la solution
finale. Le cache est local à l'instance, limité à 60 000 ordres de tournées.
Le coût de référence n'est jamais une entrée de la recherche. Les 18 essais du
pilote et les limites de leur interprétation sont détaillés dans
[EXTENSION_DABIA2013.md](EXTENSION_DABIA2013.md).
''')


if __name__ == '__main__':
    main()
