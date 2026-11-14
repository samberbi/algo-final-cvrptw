"""Convergence observée et cartes des tournées, depuis les JSON de chaque essai."""
from pathlib import Path
import argparse
import html
import json
import math
import sys
import time
import webbrowser

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def trace_points(record):
    """Aucune interpolation de progrès ou de température non enregistrée."""
    result=record.get('result') or {}
    points=[dict(p) for p in result.get('trace',[]) if 'elapsed_s' in p and 'best' in p]
    continuation=result.get('continuation')
    offset=result.get('continuation_started_s')
    if continuation and offset is not None:
        points.extend(dict(p,elapsed_s=float(offset)+p['elapsed_s'])
                      for p in continuation.get('trace',[]) if 'elapsed_s' in p and 'best' in p)
    points=[p for p in points if all(math.isfinite(float(p[k])) for k in ['elapsed_s','best']) and p['elapsed_s']>=0]
    return sorted(points,key=lambda p:p['elapsed_s'])


def draw_map(ax,record,ins,title):
    import matplotlib.pyplot as plt
    from algo.verify import verify
    m=record['measurement'];result=record.get('result') or {}
    if not m['valid'] or result.get('routes') is None:
        ax.text(.5,.5,'Aucune solution réalisable\n'+str(m.get('status','échec')),
                ha='center',va='center',transform=ax.transAxes)
        ax.set_title(title);return
    checked=verify(result['routes'],ins)
    assert checked['valid'] and abs(checked['duration']/10-m['duration'])<1e-7
    routes=result['routes'];palette=plt.get_cmap('turbo')
    for index,route in enumerate(routes):
        nodes=[0]+list(route)+[0];xy=ins.xy[nodes]
        ax.plot(xy[:,0],xy[:,1],color=palette(index/max(1,len(routes)-1)),lw=.8,alpha=.78)
    ax.scatter(ins.xy[1:,0],ins.xy[1:,1],s=5,c='#475569',alpha=.7,zorder=3)
    ax.scatter([ins.xy[0,0]],[ins.xy[0,1]],s=55,c='black',marker='s',zorder=5,label='Dépôt')
    ax.set_title(f"{title}\nDurée {m['duration']:.1f} u.t. · {len(routes)} véhicules")
    ax.set_xlabel('Coordonnée X');ax.set_ylabel('Coordonnée Y');ax.set_aspect('equal',adjustable='box')
    ax.grid(alpha=.15);ax.legend(fontsize=8)


def draw_figure(records,ins,path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from scripts.terminal_support import METHOD_LABELS
    by_method={r['measurement']['method']:r for r in records}
    # Le profil initial est bien l'ILS autonome, pas une construction C&W inventée.
    if 'ils' in by_method and 'size_based' in by_method:
        maps=[(by_method['ils'],'ILS initial — résultat final'),
              (by_method['size_based'],'Renforcé hybride — résultat final')]
        maps.extend((r,r['measurement']['method']+' — résultat final') for r in records
                    if r['measurement']['method'] not in ['ils','size_based'])
    else:
        maps=[(r,r['measurement']['method']+' — résultat final') for r in records]
    fig,axes=plt.subplots(1,1+len(maps),figsize=(5*(1+len(maps)),5.3),squeeze=False)
    axis=axes[0,0];colors=plt.get_cmap('tab10');has_trace=False
    for index,record in enumerate(records):
        if not record['measurement']['valid']:continue
        method=record['measurement']['method'];points=trace_points(record);color=colors(index%10)
        if points:
            has_trace=True
            axis.step([p['elapsed_s'] for p in points],[p['best'] for p in points],where='post',
                color=color,lw=1.6,label=method+' : meilleur observé')
            axis.scatter([p['elapsed_s'] for p in points],[p['best'] for p in points],s=5,color=color)
            current=[p for p in points if 'current' in p and math.isfinite(float(p['current']))]
            if current:axis.plot([p['elapsed_s'] for p in current],[p['current'] for p in current],
                color=color,lw=.65,alpha=.35,label=method+' : courant enregistré')
        elif record['measurement']['valid']:
            axis.scatter([record['measurement']['wall_s']],[record['measurement']['duration']],
                color=color,label=method+' : résultat final uniquement')
    if not has_trace:axis.text(.5,.8,'Pas de trace intermédiaire archivée',ha='center',transform=axis.transAxes,fontsize=9)
    axis.set(title='Convergence : points réellement enregistrés',xlabel='Temps écoulé de résolution (s)',
             ylabel='Durée totale (u.t.)')
    axis.grid(alpha=.2)
    if axis.get_legend_handles_labels()[0]:axis.legend(fontsize=7)
    for ax,(record,title) in zip(axes[0,1:],maps):draw_map(ax,record,ins,title)
    first=records[0]['measurement']
    fig.suptitle(f"{first['instance']} · {first['n']} clients · graine {first['seed']}",fontweight='bold')
    fig.text(.015,.025,'Une couleur par tournée ; carré noir : dépôt. Coût = trajets + attentes + services, retours compris.\n'
        'Les paliers relient les observations archivées ; les phases sans trace restent non détaillées. Aucune température inventée.',fontsize=8)
    fig.tight_layout(rect=(0,.09,1,.94));fig.savefig(path,dpi=140);plt.close(fig)


def render(folder,records,open_page=False):
    from scripts.terminal_support import catalog,load_case
    from algo.comparison_status import present
    folder=Path(folder);out=folder/'figures';out.mkdir(exist_ok=True)
    entries={(e['instance'],e['n']):e for e in catalog()}
    groups={}
    for record in records:
        m=record['measurement'];groups.setdefault((m['instance'],m['n'],m['seed']),[]).append(record)
    started=time.perf_counter();sections=[];figures=[]
    for (name,n,seed),group in sorted(groups.items()):
        ins=load_case(entries[name,n]);filename=f'{name}_{n}_{seed}.png'
        draw_figure(group,ins,out/filename);figures.append('figures/'+filename)
        rows=[]
        for record in group:
            m=record['measurement']
            vals=[m['method'],'OUI' if m['valid'] else 'NON',m.get('duration'),m.get('vehicles'),
                present(m.get('duration'),m.get('reference_duration'),valid=m['valid']),m.get('wall_s'),m.get('cpu_s')]
            rows.append('<tr>'+''.join('<td>'+html.escape(f'{v:.4f}' if isinstance(v,float) else str(v) if v is not None else '—')+'</td>' for v in vals)+'</tr>')
        sections.append(f'<section id="{name}_{n}_{seed}"><h2>{html.escape(name)} — {n} clients — graine {seed}</h2>'
            f'<a href="figures/{filename}"><img src="figures/{filename}" alt="Convergence et tournées {html.escape(name)}"></a>'
            '<table><tr><th>Méthode</th><th>Réalisable</th><th>Durée (u.t.)</th><th>Véhicules</th><th>Comparaison au témoin / statut</th><th>Réel (s)</th><th>CPU (s)</th></tr>'
            +''.join(rows)+'</table></section>')
    receipt=dict(figures=figures,groups=len(groups),trials=len(records),render_wall_s=time.perf_counter()-started,
        objective='Complete route duration; fixed zero departures',no_invented_trace_or_temperature=True,
        plotting_outside_solver_timers=True)
    (folder/'GRAPHIQUES.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
    page=folder/'GRAPHIQUES.html'
    page.write_text('<!doctype html><html lang="fr"><meta charset="utf-8"><title>Résultats CVRPTW</title>'
        '<style>body{font:16px system-ui;margin:24px;color:#172033;background:#f4f6fa}section{background:white;padding:18px;margin:22px 0;border-radius:12px}img{width:100%;height:auto}table{border-collapse:collapse;width:100%;font-size:14px}th,td{padding:9px;border:1px solid #ccd3dd;text-align:left}p{max-width:1100px;line-height:1.55}</style>'
        '<h1>Résultats CVRPTW — convergence et tournées</h1>'
        '<p>Les cartes comparent les solutions finales des méthodes affichées. Pour le couple standard, « initial » désigne notre ILS autonome ; « renforcé » intègre la recherche locale et éventuellement le HGS externes PyVRP. Une couleur représente une tournée, et le carré noir le dépôt. Les trajets de retour sont dessinés.</p>'
        '<p>La convergence montre les meilleurs coûts et, lorsqu’ils sont enregistrés, les coûts courants. Les points proviennent des journaux ; aucune température ou trajectoire intermédiaire manquante n’est fabriquée. Une carte spatiale ne suffit pas à prouver la faisabilité horaire : les solutions sont vérifiées par le contrôleur.</p>'
        '<p>L’écart porte sur un plan témoin compatible réévalué en durée, sans preuve d’optimalité temporelle. La génération de ces figures intervient après le lot, hors chronométrage de résolution ; son coût est enregistré séparément dans GRAPHIQUES.json.</p>'
        +''.join(sections)+'</html>',encoding='utf-8')
    if open_page:webbrowser.open(page.resolve().as_uri())
    return page


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--label',required=True);p.add_argument('--open',action='store_true')
    args=p.parse_args()
    if not args.label or any(not(c.isalnum() or c in '_-') for c in args.label):p.error('Label invalide')
    folder=ROOT/'results/local'/args.label;records=[]
    for path in sorted(folder.glob('*.json')):
        record=json.loads(path.read_text(encoding='utf-8'))
        if isinstance(record,dict) and 'measurement' in record:records.append(record)
    if not records:p.error('Aucun essai enregistré sous ce label')
    print(render(folder,records,args.open))


if __name__=='__main__':main()
