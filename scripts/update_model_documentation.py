"""Update only the model prose; preserve notebook code, results and user edits."""
from pathlib import Path
import json
import nbformat

ROOT = Path(__file__).resolve().parents[1]
NOTE = (
    '> **Révision du livrable.** La modélisation est explicitée ci-dessous en conservant les contraintes du projet. '
    'Le moteur et les résultats expérimentaux présentés dans la suite sont encore ceux de l’ALNS historique. '
    'Le remplacement demandé par l’enseignante est préparé dans `Proposition_Correction_Sans_ALNS.ipynb` ; '
    'aucun résultat tabou, VNS ou nouveau recuit n’est annoncé à ce stade.\n\n'
)


def replace_model(text, fragment):
    start = text.index('### 1.4.')
    end = text.index('### 1.5.', start)
    return text[:start] + fragment + '\n\n' + text[end:]


def revision_note(text):
    if '> **Révision du livrable.**' in text:
        return text
    pos = text.index('## Introduction')
    return text[:pos] + NOTE + text[pos:]


def main():
    fragment = (ROOT / 'docs/MODELISATION_CVRPTW_CORRIGEE.md').read_text(encoding='utf-8').strip()
    for relative in ['docs/LIVRABLE_SOURCE.md', 'LIVRABLE_FINAL.md']:
        path = ROOT / relative
        text = revision_note(replace_model(path.read_text(encoding='utf-8'), fragment))
        path.write_text(text, encoding='utf-8', newline='\r\n')
    path = ROOT / 'notebooks/Livrable_Final_CVRPTW.ipynb'
    nb = json.loads(path.read_text(encoding='utf-8'))
    code_before = json.dumps([c for c in nb['cells'] if c['cell_type'] == 'code'], sort_keys=True)
    changed = 0
    for cell in nb['cells']:
        if cell['cell_type'] != 'markdown':
            continue
        text = ''.join(cell.get('source', []))
        if '### 1.4.' in text:
            text = replace_model(text, fragment)
            changed += 1
        if '## Introduction' in text:
            text = revision_note(text)
        cell['source'] = text.splitlines(keepends=True)
    assert changed == 1
    assert json.dumps([c for c in nb['cells'] if c['cell_type'] == 'code'], sort_keys=True) == code_before
    nbformat.validate(nb)
    path.write_text(json.dumps(nb, ensure_ascii=False, indent=1) + '\n', encoding='utf-8', newline='\r\n')
    proposal = ROOT / 'docs/PROPOSITION_CORRECTION_SANS_ALNS.md'
    text = proposal.read_text(encoding='utf-8')
    start, end = text.index('## 3.'), text.index('## 4.')
    text = (text[:start] + '## 3. PLNE adapté au projet et intégré au livrable\n\n' +
            fragment.split('\n', 1)[1].lstrip() + '\n\n' + text[end:])
    proposal.write_text(text, encoding='utf-8', newline='\n')
    parts = text.split('\n## ')
    nb = nbformat.v4.new_notebook(cells=[nbformat.v4.new_markdown_cell(parts[0])] +
                                 [nbformat.v4.new_markdown_cell('## ' + part) for part in parts[1:]])
    nbformat.validate(nb)
    nbformat.write(nb, ROOT / 'notebooks/Proposition_Correction_Sans_ALNS.ipynb')
    print('Modélisation synchronisée dans le livrable, sa source et les notebooks.')
    print('Les cellules de code et les résultats du notebook principal sont conservés.')


if __name__ == '__main__':
    main()
