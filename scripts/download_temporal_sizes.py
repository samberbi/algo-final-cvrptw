"""Petits lots officiels à tailles croissantes, données jamais redimensionnées."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import argparse
import gzip
import hashlib
import json
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
DABIA_REV = '331ec306b7908e0c9a264d1fc1341a938340ab79'
LERA_REV = '66342e235df79d482b7d95f57f85237eb37aca05'
FAMILIES = ['C1', 'C2', 'R1', 'R2', 'RC1', 'RC2']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sizes', nargs='+', type=int, default=[50, 100])
    parser.add_argument('--families', nargs='+', default=FAMILIES)
    args = parser.parse_args()
    if not set(args.sizes) <= {50,100,200,400,600,800,1000} or not set(args.families) <= set(FAMILIES):
        parser.error('Tailles officielles : 50, 100, 200, 400, 600, 800, 1000')
    for n in sorted(set(args.sizes)):
        family = 'Dabia2013' if n <= 100 else 'Lera2026'
        revision = DABIA_REV if n <= 100 else LERA_REV
        repository = 'ANR-MAMUT/MAMUT-routing' if n <= 100 else 'ANR-MAMUT/MAMUT-routing-TDVRPTW-Lera2026'
        subpath = f'benchmarks/TDVRPTW/Dabia2013/n={n}' if n <= 100 else f'S2/n={n}'
        base = f'https://raw.githubusercontent.com/{repository}/{revision}/{subpath}/'
        folder = ROOT/'data/temporal_sizes'/family/f'n{n}'
        folder.mkdir(parents=True, exist_ok=True)
        entries = []
        for f in args.families:
            name = (f+'01') if n <= 100 else f'Lera-{f}_{n//100}_1-S2'
            def fetch(filename):
                path = folder/filename
                url = base+filename
                with urllib.request.urlopen(url, timeout=60) as response:
                    payload = response.read()
                json.loads(gzip.decompress(payload) if filename.endswith('.gz') else payload)
                if path.exists():
                    assert path.read_bytes() == payload, path
                else:
                    path.write_bytes(payload)
                return dict(path=path.relative_to(ROOT).as_posix(), url=url,
                            sha256=hashlib.sha256(payload).hexdigest(), bytes=len(payload))
            instance_file = fetch(name+'.vrp.json')
            instance = json.loads((ROOT/instance_file['path']).read_text())
            td = instance['td']
            # L'instance désigne le nom exact du fichier annexe, sans hypothèse.
            sidecar = td.get('atf_path') or td.get('categories_path')
            if not sidecar or Path(sidecar).name != sidecar:
                raise ValueError('Annexe relative simple attendue')
            with ThreadPoolExecutor(max_workers=2) as pool:
                files = list(pool.map(fetch, [sidecar, name+'.bks.Duration.json']))
            entry = dict(instance=name, n=n, family=f, benchmark=family,
                         path=instance_file['path'], files=[instance_file,*files])
            entries.append(entry)
            print(f'{family} n={n} {name} : donnees et BKS telechargees', flush=True)
        manifest_path = folder/'manifest.json'
        # Une sélection plus large ajoute des entrées, sans toucher aux précédentes.
        old = json.loads(manifest_path.read_text()) if manifest_path.exists() else dict(entries=[])
        indexed = {r['instance']:r for r in old['entries']}
        for entry in entries:
            if entry['instance'] in indexed:
                assert indexed[entry['instance']] == entry
            indexed[entry['instance']] = entry
        manifest = dict(repository=repository, revision=revision, benchmark=family,
                        scenario='native' if n<=100 else 'S2', n=n,
                        objective='Duration', entries=sorted(indexed.values(), key=lambda r:r['instance']),
                        selection='First numbered instance in each requested family, fixed before outcomes')
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
