"""Native diagrams and measured figures for the rewritten report."""
from pathlib import Path
import shutil
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from algo.data import load
from algo.verify import verify
from scripts.figures import boxes

ROOT=Path(__file__).resolve().parents[1]
FIG=ROOT/'livraison/ils_figures'
COLORS={'ILS':'#147d92','Recuit simulé':'#dc943d','ils':'#147d92','sa':'#dc943d'}
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})


def save(fig,name):
    fig.tight_layout();fig.savefig(FIG/(name+'.png'),dpi=170,bbox_inches='tight');plt.close(fig)


def generate(df,summary,per_instance,per_size,records,sens,scenarios,exact,exact_runs):
    FIG.mkdir(exist_ok=True)
    boxes(FIG/'representation.png', [('Instance','Demandes, fenêtres\ncapacité, flotte, trajets'),('Tournées','Listes ordonnées\ndépôt implicite'),('Contrôle','Couverture, charges\nhoraires, retour')], 'Du problème à une solution vérifiable')
    boxes(FIG/'ils.png',[('Construire','Regret-2\nune fois au départ'),('Perturber','Jusqu’à 4 mouvements\ndirects réalisables'),('Améliorer','Recherche locale\nréalisable et bornée'),('Décider','Tolérance au record\narchive du meilleur')], 'ILS : répéter perturbation, amélioration et décision sous contraintes strictes')
    boxes(FIG/'sa.png',[('Construire','Même départ\nque l’ILS'),('Proposer','Un mouvement direct\nsur des tournées complètes'),('Contrôler','Capacité, horaires\net retour réalisables'),('Accepter','Amélioration ou\nprobabilité de Metropolis')], 'Recuit : répéter proposition, contrôle et acceptation ; conserver le meilleur')
    boxes(FIG/'validation.png',[('Formaliser','PLNE complet\ncontraintes C1–C8'),('Petits cas','HiGHS : optimum\nou borne/statut'),('Grandes instances','ILS / recuit\nrépétitions et budgets'),('Analyser','Gaps, temps\ndispersion et limites')], 'Trois rôles distincts : définir, résoudre exactement, expérimenter')
    shutil.copy2(ROOT/'results/report/figures/moves.png',FIG/'moves.png')
    shutil.copy2(ROOT/'results/report/figures/schedule.png',FIG/'schedule.png')
    fig,(ax,cooling)=plt.subplots(1,2,figsize=(10,3.2))
    delta=np.linspace(0,30,200)
    for t in [2,10,20]:ax.plot(delta,np.exp(-delta/t),label=f'T = {t}')
    ax.set(xlabel='Hausse de distance Δ',ylabel='Probabilité d’acceptation',title='Recuit : plus T diminue, plus les hausses sont rarement acceptées');ax.legend();ax.grid(alpha=.15)
    fractions=np.linspace(0,1,100);cooling.plot(fractions,.005**fractions,color='#dc943d')
    cooling.set(xlabel='Fraction du budget consommée',ylabel='T / T initiale',title='Refroidissement géométrique');cooling.grid(alpha=.15)
    ax.set_title('Acceptation des hausses de coût',fontsize=11)
    save(fig,'temperature')
    for n in sorted(df.n.unique()):
        fig,ax=plt.subplots(figsize=(8,3.6))
        group=[r for r in records if r['job']['n']==n and r['valid']]
        maximum=max(r['result']['runtime_s'] for r in group);grid=np.linspace(0,maximum,160)
        for method,label in [('ils','ILS'),('sa','Recuit simulé')]:
            values=[]
            for r in group:
                if r['job']['method']!=method:continue
                trace=r['result']['trace'];times=np.array([0.]+[p['elapsed_s'] for p in trace])
                costs=np.array([r['result']['initial_cost']]+[p['best'] for p in trace])
                indices=np.clip(np.searchsorted(times,grid,side='right')-1,0,len(times)-1)
                values.append(100*(costs[indices]/r['reference_distance']-1))
            values=np.asarray(values)
            mean=values.mean(axis=0);low,high=np.quantile(values,[.25,.75],axis=0)
            ax.plot(grid,mean,label=label,color=COLORS[label]);ax.fill_between(grid,low,high,alpha=.16,color=COLORS[label])
        ax.axhline(7,color='#ae5541',ls='--',lw=1,label='7 %')
        ax.set(xlabel='Temps réel d’amélioration (s)',ylabel='Meilleur gap (%)',title=f'{n} clients : convergence moyenne et intervalle interquartile')
        ax.grid(alpha=.15);ax.legend();save(fig,f'convergence_{n}')
    for n,title in [(100,'24 instances à 100 clients'),(1000,'Grandes instances à 1 000 clients')]:
        table=per_instance[per_instance.n.eq(n)];names=sorted(table.instance.unique())
        fig,ax=plt.subplots(figsize=(11,4) if n==100 else (7,3.6));x=np.arange(len(names))
        for offset,label in [(-.2,'ILS'),(.2,'Recuit simulé')]:
            g=table[table.profile.eq(label)].set_index('instance').loc[names]
            ax.bar(x+offset,g.mean_gap,width=.38,label=label,color=COLORS[label],yerr=g.std_gap, capsize=2)
        ax.axhline(7,color='#ae5541',ls='--',lw=1)
        ax.set_xticks(x,names,rotation=60 if n==100 else 0,ha='right' if n==100 else 'center')
        ax.set(ylabel='Gap moyen (%)',title=title+' — barres : moyenne ± écart-type')
        ax.legend();save(fig,f'gaps_{n}')
    fig,ax=plt.subplots(figsize=(8,3.6));groups=[];labels=[]
    for n in sorted(df.n.unique()):
        for label in ['ILS','Recuit simulé']:
            groups.append(df[df.n.eq(n)&df.profile.eq(label)].gap_pct.dropna().values);labels.append(str(n)+'\n'+('ILS' if label=='ILS' else 'Recuit'))
    ax.boxplot(groups,labels=labels,showmeans=True);ax.axhline(7,color='#ae5541',ls='--');ax.set(ylabel='Gap (%)',title='Dispersion entre instances et répétitions');save(fig,'dispersion')
    fig,axes=plt.subplots(1,2,figsize=(10,3.4))
    for label,g in df.groupby('profile'):
        axes[0].scatter(g.n,g.runtime_s,s=9,alpha=.25,label=label,color=COLORS[label])
        axes[1].scatter(g.runtime_s,g.gap_pct,s=9,alpha=.25,label=label,color=COLORS[label])
    axes[0].set(xlabel='Clients',ylabel='Temps d’amélioration (s)',title='Temps observés sous budgets imposés')
    axes[1].set(xlabel='Temps d’amélioration (s)',ylabel='Gap (%)',title='Qualité et calcul');axes[0].legend();save(fig,'times')
    pivot=df.pivot(index=['instance','seed'],columns='method',values='gap_pct').dropna()
    fig,ax=plt.subplots(figsize=(6,4));ax.scatter(pivot.sa,pivot.ils,s=13,alpha=.5,color='#147d92')
    top=max(pivot.max())*1.03;ax.plot([0,top],[0,top],ls='--',color='#64748b')
    ax.set(xlabel='Gap du recuit (%)',ylabel='Gap de l’ILS (%)',title='Comparaisons appariées : sous la diagonale, avantage ILS');save(fig,'paired')
    fig,ax=plt.subplots(figsize=(9,3.6));ax.bar(sens.variant,sens.gap,color=['#dc943d' if str(v).startswith('sa') else '#147d92' for v in sens.variant]);ax.tick_params(axis='x',rotation=35)
    ax.set(ylabel='Gap moyen (%)',title='Sensibilité exploratoire — six instances, trois graines, deux secondes');save(fig,'sensitivity')
    fig,(ax,delta_ax)=plt.subplots(2,1,figsize=(9,6),sharex=True);names=list(dict.fromkeys(scenarios.scenario));x=np.arange(len(names))
    for offset,method in [(-.2,'ils'),(.2,'sa')]:
        g=scenarios[scenarios.method.eq(method)].set_index('scenario').loc[names]
        ax.bar(x+offset,100*g.valides/g.runs,.38,label='ILS' if method=='ils' else 'Recuit',color=COLORS[method])
        delta_ax.bar(x+offset,g.distance_change_pct,.38,color=COLORS[method])
    delta_ax.set_xticks(x,names,rotation=30,ha='right');delta_ax.axhline(0,color='#64748b',lw=.7)
    delta_ax.set(ylabel='Variation moyenne de distance (%)',xlabel='Comparaison appariée au scénario original, mêmes instance et graine')
    ax.set(ylabel='Solutions réalisables (%)',ylim=(0,110),title='Changer une contrainte : succès et distance obtenue, sans BKS modifiée');ax.legend();save(fig,'constraints')
    valid=[r for r in records if r['valid'] and r['job']['method']=='ils' and r['n']==100]
    worst=max(valid,key=lambda r:r['gap_pct']);ins=load(ROOT/'data/instances'/(worst['job']['instance']+'.vrp'))
    fig,ax=plt.subplots(figsize=(7,5))
    for route in worst['result']['routes']:
        ids=[0]+route+[0];ax.plot(ins.xy[ids,0],ins.xy[ids,1],'.-',lw=.8)
    ax.scatter(*ins.xy[0],marker='s',s=70,c='black');ax.set_aspect('equal');ax.set(title=f"Cas ILS le plus défavorable à 100 clients : {worst['job']['instance']} / graine {worst['job']['seed']}")
    save(fig,'routes')
    schedule=verify(worst['result']['routes'],ins)['routes'][0]['schedule'][:8]
    fig,ax=plt.subplots(figsize=(8,3.5))
    for row,stop in enumerate(schedule):
        i=stop['client'];ax.plot([ins.early[i]/10,ins.late[i]/10],[row,row],lw=10,color='#d5dfe7')
        ax.plot([stop['arrival']/10,stop['start']/10],[row,row],lw=4,color='#dc943d')
        ax.plot([stop['start']/10,stop['finish']/10],[row,row],lw=4,color='#2f956a')
        ax.scatter(stop['start']/10,row,color='#147d92',s=25,zorder=5)
    ax.set_yticks(range(len(schedule)),[str(s['client']) for s in schedule]);ax.invert_yaxis()
    ax.set(xlabel='Temps du benchmark',ylabel='Client',title='Fenêtres grises, attente orange, service vert, début bleu');save(fig,'windows')
    return worst
