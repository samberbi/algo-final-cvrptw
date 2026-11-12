"""Apply the final explanation review without modifying measured campaigns."""
from pathlib import Path
import inspect
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import nbformat
from algo.hybrid_reference import solve
from algo.iterated import construct
from algo.direct import walk
from algo.optimized import solve as grouped_solve
from scripts.build_ils_v5_delivery import execute
from scripts.hgs_method_notes import HGS_DETAILS


def main():
    path = ROOT / 'notebooks/Livrable_Final_CVRPTW.ipynb'
    nb = nbformat.read(path, 4)
    if not any(c.metadata.get('final_review_hgs') for c in nb.cells):
        index = next(i for i, c in enumerate(nb.cells) if 'first = ils(' in c.source)
        cell = nbformat.v4.new_markdown_cell(HGS_DETAILS)
        cell.metadata['final_review_hgs'] = True
        nb.cells.insert(index, cell)
    source = inspect.getsource(solve)
    excerpt = source[source.index('    first = ils('):source.index('    elapsed = time.perf_counter()')]
    cell = next(c for c in nb.cells if c.cell_type == 'markdown' and 'first = ils(' in c.source)
    cell.source = re.sub(r'```python\n.*?```', '```python\n' + excerpt.rstrip() + '\n```', cell.source, count=1, flags=re.S)
    # Keep the teaching excerpts identical to the current, commented source.
    move_source = inspect.getsource(walk.py_func)
    group_source = inspect.getsource(grouped_solve)
    excerpts = {
        'def construct(': inspect.getsource(construct),
        'delta = ca - costs[a]': move_source[move_source.index('        delta = ca - costs[a]'):move_source.index('        if not take:\n')],
        'proposal = [': group_source[group_source.index('        proposal = ['):group_source.index('        trace.append(')],
    }
    for marker, snippet in excerpts.items():
        cell = next(c for c in nb.cells if c.cell_type == 'markdown' and marker in c.source)
        cell.source = re.sub(r'```python\n.*?```', lambda m: '```python\n' + snippet.rstrip() + '\n```', cell.source, count=1, flags=re.S)
    execute(nb, path)
    text = '\n\n'.join(c.source for c in nb.cells if c.cell_type == 'markdown')
    for name in ['LIVRABLE_FINAL.md', 'docs/LIVRABLE_OPTIMISE_SOURCE.md']:
        (ROOT / name).write_text(text, encoding='utf-8')
    readme = ROOT / 'README.md'
    text = readme.read_text(encoding='utf-8')
    text = text.replace('Les scripts de construction et de validation v8 sont ceux de l’édition actuelle.',
                        'La campagne v8 reste la référence figée ; la livraison actuelle est contrôlée par `scripts/validate_worst_v9.py`. Les reprises et leurs budgets sont décrits dans la section 9.')
    if 'py -3.12 -m venv .venv' not in text:
        text = text.replace('python -m pip install -r requirements-reference-v7.txt',
                            'py -3.12 -m venv .venv\n.\\.venv\\Scripts\\Activate.ps1\npython -m pip install -r requirements-reference-v7.txt', 1)
    link = '\nLa [revue finale de conformité](docs/REVUE_FINALE_CONFORMITE.md) précise les contrôles réalisés et les exigences restant hors du périmètre démontré.\n'
    if link not in text:
        text += link
    readme.write_text(text, encoding='utf-8')
    journal = ROOT / 'docs/JOURNAL_EVOLUTION_ALGORITHME.md'
    text = journal.read_text(encoding='utf-8')
    if '## Revue finale de livraison' not in text:
        text += '\n## Revue finale de livraison\n\nLa dernière passe explicite la population, les tournois, SREX, la recherche locale et les pénalités du HGS externe, avec les paramètres réellement utilisés. Les extraits sont synchronisés avec le code livré. Les modules d’intégration sont remis en forme et les graines invalides sont rejetées. Ces corrections de présentation et de validation des entrées ne constituent pas un gain numérique mesuré : les campagnes figées et leurs résultats restent inchangés. Voir la [revue de conformité](REVUE_FINALE_CONFORMITE.md).\n'
    journal.write_text(text, encoding='utf-8')
    print('Notebook executed; report sources and final review links updated.')


if __name__ == '__main__':
    main()
