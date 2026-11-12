"""Graph explanation and editorial consistency; preserves factual attribution."""
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch
import nbformat
from algo.model import Instance
from algo.verify import verify


GRAPH_TEXT = r'''### 1.1. Représentation du problème par un graphe

Nous représentons le réseau de livraison par un graphe orienté complet :

$$G_{phys}=(V_{phys},A_{phys}),\qquad V_{phys}=\{0\}\cup C,\qquad C=\{1,\ldots,n\},$$
$$A_{phys}=\{(i,j)\in V_{phys}\times V_{phys}:i\ne j\}.$$

Le sommet 0 est le dépôt et chaque sommet i de C représente un client. Un client porte trois informations : sa demande $q_i$, son temps de service $s_i$ et sa fenêtre de début de service $[e_i,l_i]$. Chaque arc $(i,j)$ porte une distance $d_{ij}$ et un temps de trajet $c_{ij}$. Le graphe est orienté parce que l’ordre des visites et la propagation des horaires ont un sens. Dans les instances étudiées, les coûts sont symétriques ; les deux arcs opposés existent donc avec les mêmes coûts.

Une tournée est un circuit $0\to i_1\to\cdots\to i_p\to0$. Une solution contient au plus K tournées non vides et répartit les clients entre elles, sans oubli ni doublon. Sa distance est la somme des distances de tous leurs arcs. Les fenêtres ne sont pas représentées par de nouveaux sommets : elles limitent les horaires auxquels un sommet peut être visité.

Pour un client $j\in C$ précédé par le sommet i, nous calculons le début du service au plus tôt :

$$t_j=\max\{e_j,\ t_i+s_i+c_{ij}\},\qquad t_j\le l_j.$$

Le temps de service au dépôt est nul et le départ est fixé à zéro. Si $\mathcal R_k$ désigne la liste des clients de la tournée du véhicule k, la capacité impose $\sum_{i\in\mathcal R_k}q_i\le Q$ ; le retour doit survenir avant H. Le dessin ci-dessous illustre ces notions sur quatre clients. Cet exemple pédagogique est vérifié par le même contrôleur que les benchmarks ; il ne fait pas partie des 472 essais.

La formulation de la section 2 utilise ensuite deux copies du dépôt, o pour le départ et r pour le retour. Elles représentent toujours le même lieu physique. Cette séparation permet d’écrire les horaires de départ et de retour sans imposer une seule variable de temps à deux événements distincts.
'''


NOTATION_TEXT = r'''### 1.2. Lire les notations avant les équations

| Notation | Signification | Nature |
|---|---|---|
| $n,C$ | Nombre de clients et ensemble des clients | Données et ensemble |
| $K,\mathcal K$ | Nombre maximal de véhicules et ensemble de leurs indices | Données et ensemble |
| $Q,H$ | Capacité commune et fermeture du dépôt | Données |
| $q_i,s_i,[e_i,l_i]$ | Demande, service et fenêtre du client i | Données |
| $d_{ij},c_{ij}$ | Distance et temps de trajet de i vers j | Données |
| $x_{ij}^k$ | Le véhicule k utilise-t-il l’arc $(i,j)$ ? | Variable binaire |
| $y_i^k,u_k$ | Affectation du client i et utilisation du véhicule k | Variables binaires |
| $t_i,R_k$ | Début du service chez i et heure de retour du véhicule k | Variables continues |
| $f_{ij}^k$ | Flot artificiel qui garantit la connexion au dépôt | Variable continue auxiliaire |

Nous distinguons le nombre K de l’ensemble $\mathcal K$, et la tournée $\mathcal R_k$ de la variable $R_k$, qui désigne une heure de retour dans les équations du modèle.

La section 2 précise les domaines, l’objectif et chaque contrainte. Les variables de flot ne modélisent pas une marchandise supplémentaire : elles servent à empêcher un cycle de clients isolé du dépôt, même si certains temps tronqués sont nuls.
'''


def graph_figure(root):
    xy=np.array([[0.,0.],[1.4,1.8],[3.,1.],[-1.4,1.8],[-3.,1.]])
    distance=np.floor(10*np.sqrt(((xy[:,None,:]-xy[None,:,:])**2).sum(axis=2)))
    ins=Instance('graphe_pedagogique',xy,np.array([0,1,1,1,1]),np.array([0,20,20,20,20]),
                 np.zeros(5),np.full(5,1000.),distance,2.,2,1000.)
    routes=[[1,2],[3,4]]
    checked=verify(routes,ins)
    assert checked['valid'] and checked['vehicles']==2
    out=root/'livraison/catalog_v8_figures';out.mkdir(parents=True,exist_ok=True)
    fig,(ax,note)=plt.subplots(1,2,figsize=(10,4.1),gridspec_kw={'width_ratios':[1.3,1]})
    for i in range(5):
        for j in range(5):
            if i!=j:
                ax.add_patch(FancyArrowPatch(xy[i],xy[j],arrowstyle='-|>',mutation_scale=7,
                    color='#94a3b8',alpha=.18,connectionstyle='arc3,rad=.05',shrinkA=21,shrinkB=21))
    for route,color in zip(routes,['#2563eb','#d97706']):
        sequence=[0,*route,0]
        for i,j in zip(sequence,sequence[1:]):
            ax.add_patch(FancyArrowPatch(xy[i],xy[j],arrowstyle='-|>',mutation_scale=14,
                linewidth=2,color=color,connectionstyle='arc3,rad=.05',shrinkA=21,shrinkB=21))
    ax.scatter(xy[1:,0],xy[1:,1],s=850,facecolor='white',edgecolor='#334155',zorder=4)
    ax.scatter([0],[0],s=900,marker='s',facecolor='#dbeafe',edgecolor='#12365a',zorder=4)
    for i,(x,y) in enumerate(xy):
        ax.text(x,y,str(i),ha='center',va='center',zorder=5,fontweight='bold')
        ax.text(x,y+.36,'Dépôt' if i==0 else f'Client {i}',ha='center',fontsize=9)
    ax.set(xlim=(-3.8,3.8),ylim=(-.6,2.7),title='Graphe complet et deux tournées réalisables')
    ax.set_aspect('equal');ax.axis('off');note.axis('off')
    note.text(0,.96,'Exemple pédagogique, distinct des benchmarks',va='top',weight='bold',fontsize=10)
    note.text(0,.83,'Quatre clients : demande 1, service 2\nFenêtres : [0, 100]\nDeux véhicules au maximum, capacité 2\nFermeture du dépôt : 100',va='top',fontsize=10,linespacing=1.6)
    note.text(0,.48,'Bleu : 0 → 1 → 2 → 0\nOrange : 0 → 3 → 4 → 0\nGris : autres arcs disponibles',va='top',fontsize=10,linespacing=1.6)
    note.text(0,.23,f"Distance totale vérifiée : {checked['distance']/10:.1f}\nDurée cumulée : {checked['duration']/10:.1f}\nAucune surcharge, aucun retard",va='top',fontsize=10,linespacing=1.6)
    fig.tight_layout();fig.savefig(out/'graph_model.png',dpi=180);fig.savefig(out/'graph_model.svg');plt.close(fig)
    proof=dict(purpose='Pedagogical graph, excluded from benchmark counts',routes=routes,
        coordinates=xy.tolist(),demands=ins.demand.tolist(),services=ins.service.tolist(),
        early=ins.early.tolist(),late=ins.late.tolist(),capacity=2.,horizon=1000.,metrics=checked)
    (root/'results/catalog_v8/graph_model_example.json').write_text(json.dumps(proof,indent=2),encoding='utf-8')


def prose_pass(nb):
    replacements={
        'Le sous-ensemble demandé':'Le périmètre complémentaire',
        'le sous-ensemble demandé':'le périmètre complémentaire',
        'Les deux périmètres demandés':'Les deux périmètres étudiés',
        'Pour chaque couple instance/graine':'Pour chaque couple instance–graine',
    }
    for cell in nb.cells:
        if cell.cell_type=='markdown':
            for old,new in replacements.items():cell.source=cell.source.replace(old,new)
    return nb
