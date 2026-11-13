"""Télécharge six instances TDVRPTW à 25 clients depuis une révision figée.

Les fichiers existants doivent être identiques ; aucune donnée de benchmark
n'est modifiée pour faciliter la résolution.
"""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import hashlib
import json
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
REVISION = '331ec306b7908e0c9a264d1fc1341a938340ab79'
NAMES = ['C101', 'C201', 'R101', 'R201', 'RC101', 'RC201']
BASE = f'https://raw.githubusercontent.com/ANR-MAMUT/MAMUT-routing/{REVISION}/benchmarks/TDVRPTW/Dabia2013/n=25/'


def main():
    folder = ROOT/'data/dabia2013/n25'
    folder.mkdir(parents=True, exist_ok=True)
    jobs = [name+ext for name in NAMES for ext in ['.vrp.json', '.atf.json', '.bks.Duration.json']]
    def fetch(filename):
        url = BASE+filename
        with urllib.request.urlopen(url, timeout=60) as response:
            payload = response.read()
        json.loads(payload)
        path = folder/filename
        if path.exists() and path.read_bytes() != payload:
            raise ValueError(f'Fichier existant différent : {path}')
        if not path.exists():
            path.write_bytes(payload)
        return filename, dict(url=url, sha256=hashlib.sha256(payload).hexdigest(), bytes=len(payload))
    with ThreadPoolExecutor(max_workers=4) as pool:
        files = dict(pool.map(fetch, jobs))
    manifest = dict(repository='https://github.com/ANR-MAMUT/MAMUT-routing', revision=REVISION,
        problem='TDVRPTW', objective='Duration', customers=25, instances=NAMES,
        departures='Optimized per route by canonical checker; not fixed at zero',
        files=files, checker='mamut-routing-lib 0.12.0, td-fold/2',
        provenance='Dabia et al. 2013; Lera-Romero et al. 2020; MAMUT curation',
        license='Upstream curation MIT; original benchmark definitions remain third-party material')
    path = ROOT/'data/dabia2013/manifest.json'
    if path.exists() and json.loads(path.read_text()) != manifest:
        raise ValueError('Manifeste existant différent')
    path.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(f'{len(NAMES)} instances, {len(files)} fichiers, {sum(r["bytes"] for r in files.values())} octets')


if __name__ == '__main__':
    main()
