"""Original diagrams and plots; all experimental charts read measured records."""
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})


def save(fig,path):
    fig.tight_layout();fig.savefig(path,dpi=160,bbox_inches='tight');plt.close(fig)


def boxes(path,labels,title,loop=False):
    fig,ax=plt.subplots(figsize=(10,2.6));ax.axis('off')
    width=.85/len(labels)
    for i,(heading,body) in enumerate(labels):
        x=.02+i/len(labels)
        ax.add_patch(FancyBboxPatch((x,.2),width,.53,boxstyle='round,pad=.01',facecolor='#e9f0f7',edgecolor='#355977'))
        ax.text(x+width/2,.58,heading,ha='center',va='center',fontsize=10,weight='bold')
        ax.text(x+width/2,.39,body,ha='center',va='center',fontsize=8)
        if i<len(labels)-1:ax.annotate('',xy=(x+1/len(labels)-.005,.47),xytext=(x+width+.01,.47),arrowprops={'arrowstyle':'->','color':'#355977'})
    if loop:
        ax.annotate('',xy=(.1,.12),xytext=(.89,.12),xycoords='axes fraction',
            arrowprops={'arrowstyle':'->','connectionstyle':'arc3,rad=-.08','color':'#355977'})
        ax.text(.5,.01,'Répéter jusqu’au budget ; retourner le meilleur résultat réalisable',ha='center',fontsize=8)
    ax.set_title(title,weight='bold');save(fig,path)


def diagrams(out):
    out.mkdir(parents=True,exist_ok=True)
    boxes(out/'algorithm.png',[
        ('Construire','Regret-2\nDépart réalisable'),('Détruire','Retirer plusieurs\nclients'),('Réparer','Regret-2/3\nContraintes strictes'),
        ('Décider','Recuit + archive\nAdapter les poids')], 'Une boucle de recherche, deux états : courant et meilleur conservé',loop=True)
    boxes(out/'repair.png',[
        ('Tournées','[1, 2, 3]\n[4, 5, 6]'),('Retrait','[1, 3]  [4, 6]\nRéserve : {2, 5}'),
        ('Insertions','Comparer les coûts\net les horaires'),('Candidate','Tous les clients\nVérifier puis accepter')],
        'Illustration du mécanisme : aucune solution partielle n’est publiée')
    boxes(out/'representation.png',[
        ('Données','Demandes, services\nfenêtres, matrice'),('Solution','[[1, 3], [2, 4]]\nDépôt implicite'),
        ('Évaluation','Charge + horaires\ndistance + attente')], 'Des données au trajet puis à sa vérification')
    fig,axes=plt.subplots(1,3,figsize=(10,2.8))
    moves=[('Relocate','A : 1 → [2] → 3\nB : 4 → 5','A : 1 → 3\nB : 4 → [2] → 5'),
        ('Swap','A : 1 → [2] → 3\nB : 4 → [5] → 6','A : 1 → [5] → 3\nB : 4 → [2] → 6'),
        ('2-opt*','A : 1 → 2 | 3 → 4\nB : 5 → 6 | 7 → 8','A : 1 → 2 → 7 → 8\nB : 5 → 6 → 3 → 4')]
    for ax,(title,before,after) in zip(axes,moves):
        ax.axis('off');ax.set_title(title,color='#224d6a',weight='bold')
        ax.text(.5,.78,before,ha='center',va='center',fontsize=10)
        ax.annotate('',xy=(.5,.39),xytext=(.5,.6),arrowprops={'arrowstyle':'->'})
        ax.text(.5,.22,after,ha='center',va='center',fontsize=10)
    fig.suptitle('Exemples de transformations ; les horaires sont contrôlés après le mouvement',fontsize=10)
    save(fig,out/'moves.png')
    fig,ax=plt.subplots(figsize=(7,3))
    delta=np.linspace(0,30,200)
    for t in [2,10,20]:ax.plot(delta,np.exp(-delta/t),label=f'T = {t}')
    ax.set(xlabel='Dégradation du coût Δ',ylabel='Probabilité d’acceptation',ylim=(0,1.03),title='Le refroidissement réduit l’acceptation des détours')
    ax.legend();ax.grid(alpha=.2);save(fig,out/'acceptance.png')
    fig,ax=plt.subplots(figsize=(8,2.5))
    ax.broken_barh([(0,8)],(0,1),facecolors='#3c79a4',label='Trajet')
    ax.broken_barh([(8,7)],(0,1),facecolors='#e4a845',label='Attente')
    ax.broken_barh([(15,5)],(0,1),facecolors='#499b70',label='Service')
    ax.axvspan(15,25,color='#8ac4a0',alpha=.15);ax.axvline(15,color='#499b70',linestyle='--');ax.axvline(25,color='#b94a48',linestyle='--')
    ax.text(19,1.1,'Fenêtre de début de service [15 ; 25]',ha='center',fontsize=9)
    ax.set(xlim=(0,30),ylim=(-.1,1.6),yticks=[],xlabel='Temps (exemple illustratif)',title='Arriver à 8, attendre jusqu’à 15, servir de 15 à 20')
    ax.legend(loc='upper left',ncol=3,fontsize=8);save(fig,out/'schedule.png')
    fig,ax=plt.subplots(figsize=(8,3))
    sizes=[100,200,400,600,800,1000];initial=np.array([5,6,8,10,12,15]);extra=np.array([0,0,5,5,5,5]);last=np.array([0,0,0,0,0,5])
    ax.bar(range(6),initial,label='Recherche initiale',color='#347e94')
    ax.bar(range(6),extra,bottom=initial,label='Intensification',color='#e0a54a')
    ax.bar(range(6),last,bottom=initial+extra,label='Seconde passe à 1 000',color='#b26c39')
    for i,t in enumerate(initial+extra+last):ax.text(i,t+.25,str(t),ha='center',fontsize=9)
    ax.set_xticks(range(6),sizes);ax.set(xlabel='Clients',ylabel='Secondes nominales',ylim=(0,29),title='Budgets de recherche déclarés, hors chargement et préchauffage')
    ax.legend(fontsize=8);save(fig,out/'budgets.png')


def measured(out,df,instance_table,records):
    fig,axes=plt.subplots(1,2,figsize=(10,3.8))
    sizes=sorted(df.n.unique())
    groups=[df[(df.n==n)&df.gap_pct.notna()].gap_pct.values for n in sizes]
    axes[0].boxplot(groups,tick_labels=[str(n) for n in sizes],showmeans=True)
    axes[0].axhline(7,color='#bf5b42',ls='--',label='7 %');axes[0].set(xlabel='Clients',ylabel='Gap DIMACS (%)',title='Dispersion de toutes les exécutions réalisables')
    axes[0].legend(fontsize=8)
    axes[1].hist(df.gap_pct.dropna(),bins=25,color='#347e94',edgecolor='white')
    axes[1].axvline(7,color='#bf5b42',ls='--');axes[1].set(xlabel='Gap DIMACS (%)',ylabel='Exécutions',title='Distribution complète, aucun essai écarté')
    save(fig,out/'gaps.png')
    pivot=instance_table.pivot_table(index='family',columns='n',values='mean_gap_pct',aggfunc='mean').reindex(['C1','C2','R1','R2','RC1','RC2'])
    fig,ax=plt.subplots(figsize=(8,3.8));im=ax.imshow(pivot.values,cmap='YlOrRd',aspect='auto',vmin=0)
    for i in range(len(pivot.index)):
        for j in range(len(pivot.columns)):ax.text(j,i,f'{pivot.iloc[i,j]:.2f}',ha='center',va='center',fontsize=9)
    ax.set_xticks(range(len(pivot.columns)),pivot.columns);ax.set_yticks(range(len(pivot.index)),pivot.index)
    ax.set(xlabel='Clients',title='Gap moyen par famille et taille — poids égal par instance')
    fig.colorbar(im,ax=ax,label='Gap (%)');save(fig,out/'families.png')
    fig,axes=plt.subplots(1,2,figsize=(10,3.4))
    for n,g in df.groupby('n'):
        axes[0].scatter(np.full(len(g),n),g.runtime_s,s=12,alpha=.3)
        axes[1].scatter(np.full(len(g),n),g.iterations,s=12,alpha=.3)
    axes[0].set(xlabel='Clients',ylabel='Temps réel (s)',title='Temps mesuré ; budget croissant avec la taille')
    axes[1].set(xlabel='Clients',ylabel='Propositions tentées',title='Propositions de la phase initiale')
    save(fig,out/'scaling.png')
    examples=[]
    for n in [100,1000]:
        eligible=[r for r in records if r['job']['n']==n and r['result']['status']=='feasible']
        examples.append(max(eligible,key=lambda r:r['gap_pct']))
    fig,axes=plt.subplots(1,2,figsize=(10,3.5))
    for ax,r in zip(axes,examples):
        bks=r['job']['reference_distance'];trace=list(r['result']['trace'])
        trace.append(dict(elapsed_s=r['result']['runtime_s'],best=r['result']['cost']))
        times=[v['elapsed_s'] for v in trace];gaps=[100*(v['best']/bks-1) for v in trace]
        ax.step(times,gaps,where='post',color='#347e94');ax.axhline(7,color='#bf5b42',ls='--')
        ax.set(xlabel='Temps de recherche (s)',ylabel='Meilleur gap observé (%)',title=f"{r['job']['instance']} — graine {r['job']['seed']}")
    fig.suptitle('Historique réel des pires essais de chaque taille montrée',fontsize=10);save(fig,out/'convergence.png')
    return examples
