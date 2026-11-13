"""Recentrage idempotent du notebook ; conserve les expériences TD à part."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import nbformat
from scripts.revision_duree import write_markdown


def main():
    target=ROOT/'notebooks/Livrable_Final_CVRPTW.ipynb'
    nb=nbformat.read(target,4)
    td=[c.source for c in nb.cells if c.metadata.get('dabia_extension')]
    if td:
        (ROOT/'docs/EXPLORATION_TD_HORS_PERIMETRE.md').write_text(
            '# Archive exploratoire — hors modèle principal\n\n'
            'Ces expériences à trajets variables et départs optimisés ne valident pas '
            'le modèle statique confirmé le 13 novembre 2026. Le texte ci-dessous '
            'est conservé historiquement ; les lots 50–1000 ultérieurs sont dans '
            '`results/temporal_sizes/` (dont deux échecs de construction).\n\n'+
            '\n\n'.join(td),encoding='utf-8')
    nb.cells=[c for c in nb.cells if not c.metadata.get('dabia_extension')]
    for cell in nb.cells:
        if cell.cell_type!='markdown':continue
        cell.source='\n\n'.join(p for p in cell.source.split('\n\n')
            if not p.startswith('**Extension Dabia2013 validée**')
            and not p.startswith('**Bilan de l’extension temporelle.**'))
        cell.source=cell.source.replace(
            'Les temps de trajet restent statiques ; le trafic dépendant de l’heure demandé dans l’énoncé n’est pas traité dans cette version statique.',
            'Conformément aux hypothèses professorales confirmées, les temps de trajet sont fixes et symétriques. Les fenêtres concernent le début des services.')
        cell.source=cell.source.replace('temps de trajet statiques, tailles plafonnées',
            'absence de preuve d’optimalité en durée sur les grandes tailles, tailles plafonnées')
        cell.source=cell.source.replace('ce dernier point reste non réalisé ici.',
            'le modèle principal suit la confirmation professorale de trajets fixes et symétriques.')
        cell.source=cell.source.replace('ni une consigne explicite de l\'énoncé',
            'et correspond au périmètre professoral confirmé pour cette finalisation')
        cell.source=cell.source.replace('## 2. Modélisation mathématique','## 3. Modélisation mathématique')
        cell.source=cell.source.replace('## 3. Complexité et vérification','## 2. Complexité et vérification')
    # La difficulté du problème précède sa formulation détaillée.
    complexity=next(c for c in nb.cells if c.source.startswith('## 2. Complexité'))
    idx=nb.cells.index(complexity)
    block=nb.cells[idx:idx+3]
    if idx and nb.cells[idx-1].source.startswith('## 3. Modélisation'):
        del nb.cells[idx:idx+3]
        mathidx=next(i for i,c in enumerate(nb.cells) if c.source.startswith('## 3. Modélisation'))
        nb.cells[mathidx:mathidx]=block
    if not any(c.metadata.get('final_static_scope') for c in nb.cells):
        text='''### Périmètre final et compatibilité des références

Les hypothèses retenues sont $c_{ij}=c_{ji}$, sans dépendance à l’heure,
départs à zéro et $\\min\\sum_k R_k$. Un graphe orienté décrit les décisions
de visite même si ses temps de parcours sont symétriques. Les départs et
retours virtuels représentent le même dépôt physique.

Les campagnes historiques restent conservées. Leurs écarts aux plans distance
réévalués sont distincts du nouveau pilote à référence OR-Tools indépendante.
La compatibilité complète des optima Phonin n'est pas établie : nous ne leur
attribuons pas de gaps certifiés. Les variantes à trajets variables et départs
optimisés sont archivées hors du modèle principal.

La vérification des références est décrite dans
`docs/COMPATIBILITE_REFERENCES_STATIQUES.md`. Les résultats négatifs, nuls,
supérieurs à 6 % et les échecs restent visibles ; aucun pourcentage n'est plafonné.
'''
        cell=nbformat.v4.new_markdown_cell(text,metadata={'final_static_scope':True})
        idx=next(i for i,c in enumerate(nb.cells) if c.source.startswith('## 5.'))
        nb.cells.insert(idx+1,cell)
    nbformat.validate(nb)
    nbformat.write(nb,target)
    write_markdown(nb)
    readme=ROOT/'README.md';text=readme.read_text(encoding='utf-8')
    marker='## Extension temporelle Dabia2013'
    if marker in text:
        prefix,tail=text.split(marker,1)
        end=tail.find('\n## ')
        text=prefix+'## Exploration hors périmètre\n\nLes expériences TD sont archivées dans '
        text+='[EXPLORATION_TD_HORS_PERIMETRE.md](docs/EXPLORATION_TD_HORS_PERIMETRE.md). '
        text+='Elles ne valident pas le modèle principal à trajets fixes, symétriques et départs nuls.\n'
        if end>=0:text+=tail[end:]
    readme.write_text(text,encoding='utf-8')
    print('Notebook statique et Markdown sauvegardés ; exploration TD conservée à part.')


if __name__=='__main__':main()
