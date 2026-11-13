"""Ajoute la procédure de reproduction sans réécrire les cellules exécutées."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nbformat
from scripts.revision_duree import write_markdown

COMMANDS = r'''## Annexe — Tests rapides pour la soutenance

L'objectif reste la durée totale des tournées (trajets, attentes, services).
La limite de calcul communiquée pour la soutenance est de deux minutes. Les
commandes ci-dessous utilisent seulement cinq secondes par résolution, avec une
seule graine. La limite est souple : un appel natif commencé peut se terminer
après l'échéance. Le temps réel est enregistré. L'installation et le préchauffage
initial ne constituent pas un temps de résolution.

### Installation sur le portable, une seule fois

```powershell
git clone --branch rendu-professeur https://github.com/samberbi/algo-final-cvrptw.git CVRPTW
cd CVRPTW
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip check
```

Dans VS Code, ouvrir ce dossier et sélectionner le noyau `.venv`. Le livrable
courant est `notebooks/Livrable_Final_CVRPTW.ipynb` ; les anciens Word/PDF/HTML ne
sont pas synchronisés avec cette révision.

### Vérifier le code et les résultats enregistrés

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q --junitxml=livraison/TESTS_SOUTENANCE.xml
.\.venv\Scripts\python.exe scripts/validate_soutenance.py
```

Le validateur recalcule les contraintes et coûts des solutions enregistrées,
sans relancer les recherches. Le reçu courant est
`livraison/VALIDATION_SOUTENANCE.json` ; `MANIFESTE_SHA256.json` concerne l'édition
précédente. Un test de simulation peut être ignoré si Node.js est absent ; il
reste signalé comme ignoré, jamais comme réussi.

### Choisir des tests courts par famille

C désigne des clients regroupés, R une répartition aléatoire et RC un mélange.
Les types 1 et 2 se distinguent notamment par l'horizon et la capacité ; ils ne
désignent pas le nombre de clients. Les six exemples suivants ont 100 clients.

```powershell
# C1 et C2 : deux résolutions, clients regroupés
.\.venv\Scripts\python.exe scripts/test_instances.py --instances C101 C201 --seconds 5 --label rapide_C

# R1 et R2 : deux résolutions, clients dispersés
.\.venv\Scripts\python.exe scripts/test_instances.py --instances R101 R201 --seconds 5 --label rapide_R

# RC1 et RC2 : deux résolutions, clients mixtes
.\.venv\Scripts\python.exe scripts/test_instances.py --instances RC101 RC201 --seconds 5 --label rapide_RC

# Alternative : les six familles en une seule commande, six résolutions seulement
.\.venv\Scripts\python.exe scripts/test_instances.py --instances C101 C201 R101 R201 RC101 RC201 --seconds 5 --label rapide_6_familles

# C1 et C2 à 1 000 clients : deux résolutions seulement
.\.venv\Scripts\python.exe scripts/test_instances.py --instances C1_10_6 C2_10_2 --seconds 5 --label rapide_1000
```

Choisir les commandes souhaitées ; il n'est pas nécessaire de toutes les lancer.
Pour refaire un test, changer `--label` : les dossiers existants sont refusés
pour préserver les résultats. Le profil par défaut `duration_refined` associe
nos constructions, notre orchestration et notre partitionnement à la recherche
locale **externe PyVRP**. Il ne lance pas les longues continuations HGS.

Pour tester notre ILS sans optimisation PyVRP sur un seul cas :

```powershell
.\.venv\Scripts\python.exe scripts/test_instances.py --instances C101 --method ils --seconds 5 --label rapide_ils
```

Pour l'ILS, la construction s'ajoute au budget de recherche. Un seul essai permet
de vérifier le fonctionnement ; il ne suffit pas pour classer les méthodes.

### Lire les résultats

Chaque commande affiche la progression et les temps réels. Le dossier
`results/local/<label>/` contient `RESULTATS.csv` (faisabilité, durée de la
solution, durée du témoin, écart signé, véhicules, temps réel), les JSON des
tournées et erreurs éventuelles, ainsi que `BILAN.json`, `protocol.json` et les
sources exécutées. Le temps du lot inclut démarrage et préchauffage.

L'écart compare la durée au plan témoin réévalué ; il ne prouve pas un écart à
l'optimum temporel. Ces tests courts ne garantissent pas un écart sous 6 % et ne
remplacent pas une étude statistique. Les meilleurs résultats historiques à
budgets différents restent dans
`results/time_objective/best_duration/COUVERTURE_472_ESSAIS.csv`.
'''


def main():
    target = ROOT/'notebooks/Livrable_Final_CVRPTW.ipynb'
    nb = nbformat.read(target, as_version=4)
    nb.cells = [c for c in nb.cells if not c.metadata.get('soutenance_commands')]
    if not any(c.metadata.get('cpu_completion') for c in nb.cells):
        from scripts.report_cpu_efficiency import add_to_notebook
        add_to_notebook(nb)
    cpu_cell = next(c for c in nb.cells if c.metadata.get('cpu_completion'))
    if 'Priorité de qualité et limite de calcul' not in cpu_cell.source:
        cpu_cell.source += '''

**Priorité de qualité et limite de calcul.** La qualité des solutions reste
prioritaire : l'objectif expérimental est un écart inférieur à +6 % au plan
témoin en durée, avec moins de 120 secondes CPU par instance difficile. Le cache
retenu a donné les mêmes coûts sur les douze paires mesurées. Réduire les budgets
HGS a laissé certains essais au-dessus de 6 % ; ces profils courts ne remplacent
donc pas les reprises longues. Les 58 secondes historiques sont du temps écoulé
cumulé, pas une mesure CPU. Le respect des deux critères doit être vérifié sur
le profil complet et le matériel utilisé. Les commandes de cinq secondes de
l'annexe servent à contrôler le fonctionnement, sans garantir la même qualité.
'''
    if (ROOT/'results/time_objective/quality_cpu_check/summary.json').exists():
        from scripts.report_quality_time import text as quality_text
        marker = '\n\n### Contrôle conjoint qualité–CPU'
        cpu_cell.source = cpu_cell.source.split(marker)[0]+'\n\n'+quality_text()
    for current in nb.cells:
        if current.cell_type == 'markdown':
            current.source = current.source.replace('scripts/valider_duree.py', 'scripts/validate_soutenance.py')
            current.source = current.source.replace('livraison/TESTS.xml', 'livraison/TESTS_SOUTENANCE.xml')
            current.source = current.source.replace('python scripts/validate_soutenance.py\npython -m pytest tests -q --junitxml=livraison/TESTS_SOUTENANCE.xml',
                'python -m pytest tests -q --junitxml=livraison/TESTS_SOUTENANCE.xml\npython scripts/validate_soutenance.py')
    cell = nbformat.v4.new_markdown_cell(COMMANDS)
    cell.metadata['soutenance_commands'] = True
    nb.cells.append(cell)
    if (ROOT/'results/dabia2013/VALIDATION.json').exists():
        from scripts.report_dabia import augment
        augment(nb)
    nbformat.write(nb, target)
    write_markdown(nb)
    report = ROOT/'LIVRABLE_FINAL.md'
    report.write_text(report.read_text(encoding='utf-8').rstrip()+'\n', encoding='utf-8')
    (ROOT/'docs/TESTER_SUR_PORTABLE.md').write_text(COMMANDS, encoding='utf-8')
    readme = ROOT/'README.md'
    text = readme.read_text(encoding='utf-8')
    text = '\n'.join(line for line in text.split('\n') if not line.startswith('La **section 6.12**'))
    text = text.replace('- [Rapport PDF](livraison/RAPPORT_CVRPTW.pdf), [Word pour annotation](livraison/RAPPORT_CVRPTW.docx).',
        '- **Remise actuelle : le notebook ci-dessous.** Les anciens Word/PDF/HTML ne sont pas synchronisés avec cette révision et ne constituent pas la remise actuelle.')
    text = text.replace('python scripts/valider_duree.py', 'python scripts/validate_soutenance.py')
    text = text.replace('python -m pytest tests -q --junitxml=livraison/TESTS.xml',
        'python -m pytest tests -q --junitxml=livraison/TESTS_SOUTENANCE.xml')
    text = text.replace('Le reçu courant est [VALIDATION_DUREE.json](livraison/VALIDATION_DUREE.json), complété par `livraison/TESTS.xml` et `MANIFESTE_SHA256.json`.',
        'Le reçu courant est [VALIDATION_SOUTENANCE.json](livraison/VALIDATION_SOUTENANCE.json), complété par `livraison/TESTS_SOUTENANCE.xml`. `VALIDATION_DUREE.json` et `MANIFESTE_SHA256.json` appartiennent à l’édition antérieure.')
    # Une validation requiert d'abord le XML de tests : l'annexe fait foi pour l'ordre.
    marker = '\n## Version de soutenance : tests sur le portable\n'
    text = text.split(marker)[0]
    text += marker + '\nLes commandes courtes sont dans [TESTER_SUR_PORTABLE.md](docs/TESTER_SUR_PORTABLE.md) et à la fin du notebook : deux cas C1/C2, deux R1/R2, deux RC1/RC2 ou deux cas à 1 000 clients. Une graine et cinq secondes par résolution. Le reçu courant est `livraison/VALIDATION_SOUTENANCE.json`. La section CPU reste informative : la qualité des solutions prime, avec un objectif sous +6 % au témoin en durée et sous 120 secondes CPU par instance difficile. Ces deux critères sont à mesurer séparément. Les tests de cinq secondes ne sont pas le profil de meilleure qualité.\n'
    readme.write_text(text, encoding='utf-8')


if __name__ == '__main__':
    main()
