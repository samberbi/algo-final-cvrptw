"""Figures scientifiques haute résolution, issues uniquement des CSV exécutés."""
from pathlib import Path
import json
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np


def save(fig,name):
    out=ROOT/'livraison/figures_final_static';out.mkdir(parents=True,exist_ok=True)
    fig.savefig(out/(name+'.png'),dpi=220,bbox_inches='tight')
    fig.savefig(out/(name+'.svg'),bbox_inches='tight')
    plt.close(fig)


def main():
    paths=[p for p in (ROOT/'results/final_static').glob('*/RESULTATS.csv')
           if p.parent.name!='reference_audit']
    frames=[pd.read_csv(p).assign(campaign=p.parent.name) for p in paths]
    if not frames:raise ValueError('Aucun résultat exécuté disponible')
    data=pd.concat(frames,ignore_index=True)
    fig,ax=plt.subplots(figsize=(9,4.5))
    positions={'o':(0,.5),'1':(1,1),'2':(1,0),'r':(2,.5)}
    for node,(x,y) in positions.items():
        ax.scatter(x,y,s=900,color='#006d77' if node in ['o','r'] else '#e29578',zorder=3)
        ax.text(x,y,node,ha='center',va='center',color='white',size=16,zorder=4)
    for a,b in [('o','1'),('o','2'),('1','r'),('2','r'),('1','2'),('2','1')]:
        ax.annotate('',xy=positions[b],xytext=positions[a],
            arrowprops=dict(arrowstyle='->',shrinkA=24,shrinkB=24,
            connectionstyle='arc3,rad=.13' if {a,b}=={'1','2'} else 'arc3,rad=0',color='#444444'))
    ax.text(1.25,.5,r'$c_{12}=c_{21}$',va='center')
    ax.text(1,-.32,'o et r : deux copies du même dépôt physique',ha='center')
    ax.set(xlim=(-.4,2.4),ylim=(-.5,1.3),title='Décisions orientées, temps fixes et symétriques')
    ax.axis('off');save(fig,'graphe_modele')
    compare=data[(data.method.isin(['refined','refined_ils'])) & data.valid].copy()
    paired=compare.pivot_table(index=['campaign','instance','n','seed'],columns='method',values='duration').dropna()
    if len(paired):
        paired=paired.reset_index()
        paired['gain_pct']=100*(1-paired.refined_ils/paired.refined)
        fig,ax=plt.subplots(figsize=(10,4.8))
        labels=paired.instance+' / '+paired.n.astype(str)+' / '+paired.seed.astype(str)
        ax.bar(np.arange(len(paired)),paired.gain_pct,color=np.where(paired.gain_pct>=0,'#006d77','#c44536'))
        ax.axhline(0,color='black',lw=.8)
        ax.set_xticks(np.arange(len(paired)),labels,rotation=65,ha='right',fontsize=8)
        ax.set_ylabel('Gain de durée par rapport au renforcé (%)')
        ax.set_title('Variante avec ILS propre : gains et régressions conservés')
        save(fig,'ablation_ils')
        paired.to_csv(ROOT/'results/final_static/PAIRES_VARIANTE_ILS.csv',index=False,encoding='utf-8-sig')
    fig,axes=plt.subplots(1,2,figsize=(12,4.5))
    useful=data[data.valid & data.delta_independent_pct.notna() & data.method.ne('construction')
                & data.campaign.eq('couverture_progressive')]
    for method,group in useful.groupby('method'):
        stats=group.groupby('n').agg(delta=('delta_independent_pct','mean'),wall=('wall_s','mean'))
        axes[0].plot(stats.index,stats.delta,'o-',label=method)
        axes[1].plot(stats.index,stats.wall,'o-',label=method)
    axes[0].axhline(6,color='#c44536',ls='--',label='Seuil indicatif +6 %')
    axes[0].set_ylabel('Écart signé moyen à OR-Tools (%)')
    axes[1].set_ylabel('Temps écoulé moyen par résolution (s)')
    for ax in axes:ax.set_xlabel('Nombre de clients');ax.grid(alpha=.2)
    axes[0].legend(fontsize=7,ncol=2)
    fig.suptitle('Pilotes : qualité et temps observés, référence réalisable non optimale')
    save(fig,'qualite_taille_temps')
    data.to_csv(ROOT/'results/final_static/TOUS_LES_ESSAIS.csv',index=False,encoding='utf-8-sig')
    print(json.dumps(dict(records=len(data),figures_directory='livraison/figures_final_static')))


if __name__=='__main__':main()
