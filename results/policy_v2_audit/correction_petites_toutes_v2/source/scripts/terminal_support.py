"""Catalogue, contrôles et affichage communs aux commandes utilisateur.

Les références sont lues après recherche. Aucune solution de notre méthode
n'entre dans le dénominateur d'un écart. Les plans publics et OR-Tools sont
étiquetés séparément ; les valeurs Phonin non certifiées ne sont pas utilisées.
"""
from pathlib import Path
from datetime import datetime
import csv
import hashlib
import json
import re
import time
import traceback
from algo.comparison_status import present

ROOT=Path(__file__).resolve().parents[1]
SIZES=[25,50,100,200,400,600,800,1000]
FAMILIES=['C1','C2','R1','R2','RC1','RC2']
METHODS=['size_based','construction','ils','sa','pyvrp','hybrid','refined','refined_no_partition','refined_ils','ortools']
DEFAULT_METHOD='size_based'
METHOD_LABELS={
    'size_based':'Sélection v2 : construction + LS PyVRP + ILS jusqu’à 100 clients, renforcé au-delà',
    'construction':'Construction propre regret-2',
    'ils':'ILS autonome, opérateurs propres',
    'sa':'Recuit autonome, opérateurs propres',
    'pyvrp':'PyVRP/HGS externe seul',
    'hybrid':'ILS propre puis HGS externe PyVRP',
    'refined':'Hybride renforcé : constructions propres, LS PyVRP, partitionnement HiGHS',
    'refined_no_partition':'Renforcé sans partitionnement, LS PyVRP externe',
    'refined_ils':'Renforcé puis ILS propre dans le temps restant',
    'ortools':'Google OR-Tools externe, objectif durée complète'
}


def family(name):
    match=re.match(r'^(RC|C|R)([12])',name)
    if not match:raise ValueError('Famille inconnue : '+name)
    return ''.join(match.groups())


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def catalog():
    main=json.loads((ROOT/'data/manifest.json').read_text())
    rows=[dict(instance=r['instance'],n=r['n'],family=family(r['instance']),
        path='data/instances/'+r['instance']+'.vrp',sha256=main['files'][r['instance']+'.vrp']['sha256'])
        for r in main['reference_instances']]
    small=json.loads((ROOT/'data/static_small/manifest.json').read_text())
    rows += [dict(instance=r['instance'],n=r['n'],family=family(r['instance']),
                  path=r['path'],sha256=r['sha256']) for r in small['files']]
    return sorted(rows,key=lambda r:(r['n'],FAMILIES.index(r['family']),r['instance']))


def select_cases(rows,instances=None,sizes=None,families=None,progressive=False,all_cases=False,limit=None):
    """Une instance par famille/taille par défaut ; catalogue complet sur --all."""
    requested=set(sizes or ([] if instances else SIZES if progressive else [100]))
    selected=[]
    if instances:
        for token in instances:
            if ':' in token:
                name,count=token.upper().split(':');count=int(count)
                candidates=[r for r in rows if r['instance']==name and r['n']==count]
            else:
                candidates=[r for r in rows if r['instance']==token.upper() and (not requested or r['n'] in requested)]
                if not requested:
                    candidates=[r for r in candidates if r['n']==100] or candidates[-1:]
            if not candidates:raise ValueError('Instance/taille absente du catalogue : '+token)
            selected.extend(candidates)
    else:
        allowed=set(families or (['C1'] if progressive else FAMILIES if sizes or all_cases else ['C1']))
        candidates=[r for r in rows if r['n'] in requested and r['family'] in allowed]
        if all_cases:selected=candidates
        else:
            for n in sorted(requested):
                for f in FAMILIES:
                    matched=[r for r in candidates if r['n']==n and r['family']==f]
                    if matched:selected.append(matched[0])
    if families:selected=[r for r in selected if r['family'] in families]
    selected=list({(r['instance'],r['n']):r for r in selected}.values())
    if limit is not None:selected=selected[:limit]
    if not selected:raise ValueError('Sélection vide')
    return selected


def load_case(entry):
    if sha(ROOT/entry['path'])!=entry['sha256']:raise ValueError('Empreinte de l’instance différente du manifeste')
    if entry['n'] in [25,50]:
        from algo.static_small import load
    else:
        from algo.data import load
    ins=load(ROOT/entry['path'])
    if ins.n!=entry['n']:raise ValueError('Nombre de clients incorrect')
    return ins


def unique_folder(label=None,store=None):
    store=Path(store or ROOT/'results/local')
    label=label or 'terminal_'+datetime.now().strftime('%Y%m%d_%H%M%S')
    if not re.fullmatch(r'[A-Za-z0-9_-]+',label):raise ValueError('Label : lettres, chiffres, tirets et underscores uniquement')
    suffix=1
    while True:
        folder=store/(label if suffix==1 else f'{label}_{suffix}')
        try:folder.mkdir(parents=True,exist_ok=False);return folder
        except FileExistsError:suffix+=1


def dump(path,value):
    path=Path(path)
    temp=path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
    temp.replace(path)


def verified_result(ins,result):
    """Un coût annoncé est contrôlé avant toute mise en tableau."""
    from algo.verify import verify
    if result.get('routes') is None:return None
    metrics=verify(result['routes'],ins)
    if not metrics['valid']:raise ValueError('Contraintes invalides : '+str(metrics['errors']))
    if result.get('cost') is not None and abs(result['cost']-metrics['duration']/10)>1e-7:
        raise ValueError('Coût annoncé différent de la durée recalculée')
    if abs(metrics['duration']-metrics['travel']-metrics['waiting']-ins.service.sum())>1e-7:
        raise ValueError('Décomposition temporelle incohérente')
    return metrics


def worker(entry,method,seconds,seed,target):
    """Processus isolé : chauffe les noyaux avant de chronométrer la résolution."""
    process_start,process_cpu=time.perf_counter(),time.process_time()
    started=cpu=None
    try:
        ins=load_case(entry)
        from algo.size_policy import selected_method
        effective=selected_method(ins.n) if method=='size_based' else method
        if effective not in ['pyvrp','ortools']:
            from algo.duration import warmup
            warmup()
        if effective.startswith('refined'):
            from algo.iterated import arrays
            from algo.savings import savings_construct
            from algo.sequential import sequential_insert
            # Un petit cas suffit à compiler les mêmes signatures, hors mesure.
            small=load_case(next(r for r in catalog() if r['instance']=='C101' and r['n']==25))
            savings_construct(*arrays(small),small.vehicles,1,0.)
            sequential_insert(*arrays(small),small.vehicles,1,1.,.5,0)
        started,cpu=time.perf_counter(),time.process_time()
        if method=='size_based':
            from algo.size_policy import solve
            result=solve(ins,seed=seed,seconds=seconds)
        elif method=='refined':
            from algo.duration_refine import solve
            result=solve(ins,seed=seed,seconds=seconds)
        else:
            from scripts.benchmark_final_static import evaluate
            result=evaluate(method,ins,seed,seconds,seconds)
        metrics=verified_result(ins,result)
        if metrics is not None:result.update(metrics=metrics,cost=metrics['duration']/10)
        elapsed,used=time.perf_counter()-started,time.process_time()-cpu
        record=dict(result=result,valid=metrics is not None,wall_s=elapsed,cpu_s=used,
                    selected_method=effective,status=result.get('status','error'),timing_scope='solve_and_final_verification')
    except Exception as error:
        record=dict(valid=False,status='error',result=dict(routes=None,status='error',error=repr(error)),
            error=traceback.format_exc(),wall_s=time.perf_counter()-(started or process_start),
            cpu_s=time.process_time()-(cpu if cpu is not None else process_cpu),
            timing_scope='failed_execution_including_initialization_if_needed')
    record.update(instance=entry['instance'],n=entry['n'],family=entry['family'],method=method,seed=seed,
        requested_seconds=seconds,process_wall_s=time.perf_counter()-process_start,
        process_cpu_s=time.process_time()-process_cpu)
    dump(target,record)


def find_reference(entry,ins,kind='auto'):
    from algo.verify import verify
    missing=dict(duration=None,type='NON DISPONIBLE',source=None,certified=False)
    if kind=='none':return missing
    if kind in ['auto','public'] and entry['n']>=100:
        source=ROOT/'data/instances'/(entry['instance']+'.sol')
        if source.is_file():
            manifest=json.loads((ROOT/'data/manifest.json').read_text())
            if sha(source)!=manifest['files'][source.name]['sha256']:raise ValueError('Témoin public modifié')
            from algo.data import reference
            routes,_=reference(source);m=verify(routes,ins)
            if not m['valid']:raise ValueError('Témoin public irréalisable')
            return dict(duration=m['duration']/10,type='Plan public DISTANCE réévalué en DURÉE, non optimalité temporelle',
                source=source.relative_to(ROOT).as_posix(),certified=False,metrics=m)
    if kind=='public':return missing
    best=None
    # Seulement des résolutions OR-Tools figées, jamais une solution ILS/hybride.
    for folder in sorted((ROOT/'results/final_static').iterdir()):
        protocol=folder/'protocol.json'
        if not protocol.is_file():continue
        info=json.loads(protocol.read_text())
        if info.get('instance_hashes',{}).get(f"{entry['instance']}:{entry['n']}")!=entry['sha256']:continue
        for path in (folder/'runs').glob(f"{entry['instance']}_{entry['n']}_ortools_*.json"):
            record=json.loads(path.read_text());result=record.get('result',{})
            if record.get('method')!='ortools' or result.get('routes') is None:continue
            m=verify(result['routes'],ins)
            if not m['valid']:continue
            if abs(m['duration']/10-result['cost'])>1e-7:raise ValueError('Coût de référence OR-Tools incohérent')
            candidate=dict(duration=m['duration']/10,type='OR-Tools indépendant enregistré, solution réalisable non prouvée optimale',
                source=path.relative_to(ROOT).as_posix(),certified=False,metrics=m)
            if best is None or candidate['duration']<best['duration']:best=candidate
    return best or missing


def row_from(record,reference):
    r=record;metrics=r.get('result',{}).get('metrics',{}) if r['valid'] else {}
    duration=metrics.get('duration',0)/10 if r['valid'] else None
    ref=reference.get('duration')
    delta=100*(duration/ref-1) if duration is not None and ref is not None and ref>0 else None
    row={k:r.get(k) for k in ['instance','family','n','method','selected_method','seed','valid','status','wall_s','cpu_s',
                            'requested_seconds','process_wall_s','process_cpu_s','timing_scope','guard_s']}
    row.update(duration=duration,vehicles=metrics.get('vehicles'),
        travel=metrics.get('travel',0)/10 if r['valid'] else None,
        waiting=metrics.get('waiting',0)/10 if r['valid'] else None,
        service=(metrics.get('duration',0)-metrics.get('travel',0)-metrics.get('waiting',0))/10 if r['valid'] else None,
        reference_duration=ref,reference_type=reference['type'],reference_source=reference.get('source'),
        delta_reference_pct=delta,gap_duree_pct=delta,
        certified_gap_pct=delta if reference.get('certified') and delta is not None else None,
        overrun_s=max(0,r['wall_s']-r['requested_seconds']),error=r.get('error') or r.get('result',{}).get('error'))
    return row


def number(value,suffix='',signed=False):
    if value is None:return 'NON DISPONIBLE'
    return (f'{value:+.4f}' if signed else f'{value:.3f}')+suffix


def show(record,show_routes=False):
    r=record['measurement']
    values=[('Instance',r['instance']),('Famille',r.get('family',family(r['instance']))),
        ('Nombre de clients',r.get('n','NON DISPONIBLE')),('Méthode',r['method']+' — '+METHOD_LABELS.get(r['method'],r['method'])),
        ('Moteur exécuté',r.get('selected_method') or r['method']),('Graine',r['seed']),
        ('FAISABILITÉ','OUI' if r['valid'] else 'NON'),('Statut',r.get('status','historique')),
        ('Véhicules utilisés',r.get('vehicles') if r['valid'] else 'NON DISPONIBLE'),
        ('Durée des trajets',number(r.get('travel'),' u.t.')),('Durée des attentes',number(r.get('waiting'),' u.t.')),
        ('Durée des services',number(r.get('service'),' u.t.')),('DURÉE TOTALE',number(r.get('duration'),' u.t.')),
        ('Durée de référence',number(r.get('reference_duration'),' u.t.')),
        ('Type de référence',r.get('reference_type','Plan public distance réévalué en durée')),
        ('Source de référence',r.get('reference_source') or 'NON DISPONIBLE'),
        ('Comparaison à la référence',present(r.get('duration'),r.get('reference_duration'),valid=r['valid'])),
        ('Gap certifié',number(r.get('certified_gap_pct'),' %',True)),
        ('Temps CPU résolution',number(r.get('cpu_s'),' s')),('Temps réel résolution',number(r.get('wall_s'),' s')),
        ('Temps total processus',number(r.get('process_wall_s'),' s')),
        ('Budget demandé',number(r.get('requested_seconds'),' s')),('Garde-fou processus',number(r.get('guard_s'),' s')),
        ('Dépassement budget demandé',number(r.get('overrun_s'),' s')),
        ('Contraintes','VALIDÉES' if r['valid'] else 'NON VALIDÉES')]
    print('\n'+'='*72+'\nTEST CVRPTW\n'+'='*72,flush=True)
    for key,value in values:print(f'{key:28} : {value}',flush=True)
    delta=r.get('delta_reference_pct')
    if delta is not None and delta<0:print('Solution améliorante vérifiée ; référence heuristique dépassée, sans preuve d’optimalité.',flush=True)
    if delta is not None and delta>6:print('Le seuil indicatif de +6 % est dépassé. Valeur réelle conservée.',flush=True)
    if r.get('error'):print('Erreur : '+r['error'],flush=True)
    if show_routes and (record.get('result') or {}).get('routes') is not None:
        metrics=record['result'].get('metrics',{})
        for index,route in enumerate(record['result']['routes'],1):
            print(f'Tournée {index} : 0 -> '+ ' -> '.join(map(str,route))+' -> 0',flush=True)
            if index<=len(metrics.get('routes',[])):
                for visit in metrics['routes'][index-1]['schedule']:
                    print(f"  client {visit['client']}: arrivée {visit['arrival']/10:.2f}, début {visit['start']/10:.2f}, fin {visit['finish']/10:.2f}",flush=True)
                print(f"  retour au dépôt : {metrics['routes'][index-1]['duration']/10:.2f}",flush=True)


def comparison(rows):
    lines=['\nCOMPARAISON — classement en durée réalisable, par instance et graine',
           'Budgets de recherche et temps totaux sont distincts ; échecs non classés.',
           'Instance / n / graine | Méthode | Durée | Faisable | Véhicules | Réel(s) | Budget(s) | Comparaison / statut | Rang']
    keys=sorted({(r['instance'],r.get('n'),r['seed']) for r in rows},key=str)
    for key in keys:
        group=[r for r in rows if (r['instance'],r.get('n'),r['seed'])==key]
        costs=sorted({r['duration'] for r in group if r['valid']})
        for r in sorted(group,key=lambda r:r.get('duration') if r['valid'] else float('inf')):
            rank=str(costs.index(r['duration'])+1) if r['valid'] else '—'
            lines.append(f"{key[0]} / {key[1]} / {key[2]} | {r['method']} | {number(r.get('duration'))} | "
                f"{'OUI' if r['valid'] else 'NON'} | {r.get('vehicles') or '—'} | {number(r.get('wall_s'))} | "
                f"{number(r.get('requested_seconds'))} | {present(r.get('duration'),r.get('reference_duration'),valid=r['valid'])} | {rank}")
        best=[r['method'] for r in group if r['valid'] and r['duration']==costs[0]] if costs else []
        lines.append('Meilleure(s) méthode(s) sur ce cas/essai : '+(', '.join(best) if best else 'aucune solution réalisable'))
        if len(group)==1:lines.append('Une seule méthode exécutée : le rang ne constitue pas un jugement de qualité.')
    return '\n'.join(lines)


def save_tables(folder,records,batch_wall_s):
    rows=[r['measurement'] for r in records]
    fields=sorted({key for row in rows for key in row})
    with (folder/'RESULTATS.csv').open('w',newline='',encoding='utf-8-sig') as stream:
        writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerows(rows)
    summary=dict(completed=len(rows),valid=sum(r['valid'] for r in rows),failed=sum(not r['valid'] for r in rows),
        batch_wall_s=batch_wall_s,resolution_cpu_sum_s=sum(r['cpu_s'] or 0 for r in rows),
        note='Signed gap against feasible reference, not a certified duration optimum. Warmup excluded from solve time but included in process guard.')
    dump(folder/'BILAN.json',summary)
    text=comparison(rows)
    (folder/'SYNTHESE.txt').write_text(text+'\n\n'+json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    return text
