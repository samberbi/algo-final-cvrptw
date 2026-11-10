"""Durable campaigns and subprocess launch; never modify published results."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import time
import uuid

import pandas as pd
import psutil

ROOT = Path(__file__).resolve().parents[1]
STORE = ROOT / 'results' / 'local' / 'web'
PROFILES = {
    'ILS': {'method': 'ils'},
    'Recuit simulé': {'method': 'sa'},
}


def now():
    return datetime.now(timezone.utc).isoformat()


def read_json(path):
    for attempt in range(6):
        try:
            return json.loads(Path(path).read_text(encoding='utf-8'))
        except PermissionError:
            # A concurrent replacement can briefly deny a reader on Windows.
            if attempt == 5:
                raise
            time.sleep(.01 * 2**attempt)


def atomic_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, allow_nan=False), encoding='utf-8')
    try:
        for attempt in range(6):
            try:
                os.replace(temporary, path)
                return
            except PermissionError:
                # Windows can briefly lock the destination while the UI reads it.
                if attempt == 5:
                    raise
                time.sleep(.01 * 2**attempt)
    finally:
        temporary.unlink(missing_ok=True)


def catalog():
    return pd.DataFrame(read_json(ROOT / 'data/manifest.json')['reference_instances'])


def campaign_path(identifier, store=STORE):
    if not re.fullmatch(r'[0-9]{8}T[0-9]{6}_[a-f0-9]{12}', identifier):
        raise ValueError('Identifiant de campagne invalide')
    return Path(store) / identifier


def make_protocol(instances, seeds, seconds, profiles, polish_seconds=0, name='Expérience'):
    available = set(catalog()['instance'])
    instances, seeds, profiles = list(instances), list(seeds), list(profiles)
    if not instances or not set(instances) <= available or len(instances) != len(set(instances)):
        raise ValueError('Choisir des instances disponibles et distinctes')
    if not seeds or any(type(s) is not int or not 0 <= s < 2**31 for s in seeds) or len(seeds) != len(set(seeds)):
        raise ValueError('Graines distinctes, entières, entre 0 et 2147483647')
    if not profiles or not set(profiles) <= PROFILES.keys() or len(profiles) != len(set(profiles)):
        raise ValueError('Configuration inconnue ou dupliquée')
    if not math.isfinite(seconds) or not .05 <= seconds <= 3600:
        raise ValueError('Budget de recherche entre 0,05 et 3 600 secondes')
    if not math.isfinite(polish_seconds) or not 0 <= polish_seconds <= 3600:
        raise ValueError('Budget de décomposition entre 0 et 3 600 secondes')
    count = len(instances) * len(seeds) * len(profiles)
    if count > 10000:
        raise ValueError('Limiter une campagne à 10 000 résolutions')
    sources = list((ROOT / 'algo').glob('*.py')) + [ROOT / 'ameliorations/decomposition.py', ROOT / 'web/worker.py']
    jobs = [dict(id=i, instance=instance, seed=seed, profile=profile)
            for i, (instance, seed, profile) in enumerate(
                (a, b, c) for a in instances for b in seeds for c in profiles)]
    return dict(name=str(name).strip()[:100] or 'Expérience', created_at=now(), instances=instances,
                seeds=seeds, profiles=profiles, seconds=float(seconds), polish_seconds=float(polish_seconds),
                objective='distance', convention='DIMACS: floor(10 * euclidean) per edge',
                jobs=jobs, total=count, nominal_search_seconds=count * (seconds + polish_seconds),
                source_sha256={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
                manifest_sha256=hashlib.sha256((ROOT / 'data/manifest.json').read_bytes()).hexdigest())


def create_campaign(protocol, store=STORE):
    identifier = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S') + '_' + uuid.uuid4().hex[:12]
    folder = campaign_path(identifier, store)
    folder.mkdir(parents=True, exist_ok=False)
    atomic_json(folder / 'protocol.json', protocol)
    atomic_json(folder / 'progress.json', dict(status='queued', completed=0, total=protocol['total'], updated_at=now()))
    return identifier


def launch(identifier, store=STORE):
    folder = campaign_path(identifier, store)
    # Exclusive marker prevents double launches from widget reruns or two tabs.
    with (folder / 'LAUNCHED').open('x', encoding='utf-8') as marker:
        marker.write(now())
    env = os.environ.copy()
    env.update({key: '1' for key in ['OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMBA_NUM_THREADS']})
    kwargs = dict(cwd=str(ROOT), env=env, stdin=subprocess.DEVNULL)
    if os.name == 'nt':
        kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs['start_new_session'] = True
    try:
        with (folder / 'worker.log').open('ab') as log:
            process = subprocess.Popen([sys.executable, '-u', '-m', 'web.worker', str(folder.resolve())],
                                       stdout=log, stderr=subprocess.STDOUT, **kwargs)
        atomic_json(folder / 'process.json', dict(pid=process.pid, command_identifier=identifier, launched_at=now()))
        return process.pid
    except Exception as exc:
        atomic_json(folder / 'progress.json', dict(status='error', completed=0, total=read_json(folder / 'protocol.json')['total'],
                                                 error=str(exc), updated_at=now()))
        raise


def progress(identifier, store=STORE):
    folder = campaign_path(identifier, store)
    state = read_json(folder / 'progress.json')
    if state['status'] in {'queued', 'warming', 'running'} and (folder / 'process.json').exists():
        pid = read_json(folder / 'process.json')['pid']
        try:
            process = psutil.Process(pid)
            args = ' '.join(process.cmdline())
            alive = process.is_running() and 'web.worker' in args and identifier in args
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            alive = False
        if not alive:
            state = dict(state, status='interrupted', error='Le processus de calcul est arrêté. Les essais terminés sont conservés.')
    return state


def list_campaigns(store=STORE):
    if not Path(store).exists():
        return []
    return sorted([p.name for p in Path(store).iterdir() if p.is_dir() and (p / 'protocol.json').exists()], reverse=True)


def stop(identifier, store=STORE):
    (campaign_path(identifier, store) / 'STOP').touch()


def records(identifier, store=STORE):
    return [read_json(p) for p in sorted((campaign_path(identifier, store) / 'runs').glob('*.json'))]


def frame(items):
    rows = []
    for item in items:
        result, job = item['result'], item['job']
        rows.append(dict(run=job['id'], instance=job['instance'], n=item['n'], profile=job['profile'], seed=job['seed'],
                         status=result['status'], valid=item.get('valid', False), distance=result.get('cost'),
                         reference_distance=item['reference_distance'], gap_pct=item.get('gap_pct'),
                         vehicles=result.get('vehicles'), runtime_s=result.get('runtime_s'),
                         budget_s=item['budget_s'], reason=result.get('reason', '')))
    return pd.DataFrame(rows)


def statistics(df):
    if df.empty:
        return pd.DataFrame()
    data = df.copy()
    data['feasible'] = data['valid'].astype(bool)
    data['under5'] = data['feasible'] & data['gap_pct'].lt(5)
    data['under7'] = data['feasible'] & data['gap_pct'].lt(7)
    data.loc[~data['feasible'], 'gap_pct'] = float('nan')
    return data.groupby(['instance', 'profile'], dropna=False).agg(
        runs=('status', 'size'), feasible=('feasible', 'sum'), reference=('reference_distance', 'first'),
        mean_gap=('gap_pct', 'mean'), median_gap=('gap_pct', 'median'), std_gap=('gap_pct', 'std'),
        best_gap=('gap_pct', 'min'), worst_gap=('gap_pct', 'max'), under5=('under5', 'sum'), under7=('under7', 'sum'),
        mean_time_s=('runtime_s', 'mean')).reset_index()
