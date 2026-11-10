"""Retrieve all 356 VRPTW instances and verify all published BKS, never code."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import concurrent.futures,hashlib,json,time,urllib.request
from algo.data import load,reference
from algo.verify import verify


def fetch(url):
    for attempt in range(4):
        try:
            request=urllib.request.Request(url,headers={'User-Agent':'CVRPTW-academic-benchmark'})
            with urllib.request.urlopen(request,timeout=35) as f:return f.read()
        except Exception:
            if attempt==3:raise
            time.sleep(attempt+1)


def main():
    data=ROOT/'data';folder=data/'instances';folder.mkdir(exist_ok=True)
    tree=json.loads((data/'repository_tree.json').read_text())
    revision=tree['revision']
    paths=[r['path'] for r in tree['subtree']['tree'] if r['path'].endswith(('.vrp','.sol'))]
    assert len([p for p in paths if p.endswith('.vrp')])==356
    def one(path):
        name=Path(path).name
        assert '..' not in Path(path).parts and ':' not in path
        target=folder/name
        url=f'https://raw.githubusercontent.com/PyVRP/Instances/{revision}/VRPTW/{path}'
        if not target.exists():target.write_bytes(fetch(url))
        return name,dict(url=url,sha256=hashlib.sha256(target.read_bytes()).hexdigest())
    files={}
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        for i,(name,record) in enumerate(pool.map(one,paths)):
            files[name]=record
            if i%60==0:print('Files:',i+1,'/',len(paths),flush=True)
    refs=[]
    for path in sorted(folder.glob('*.vrp')):
        ins=load(path);routes,cost=reference(path.with_suffix('.sol'));checked=verify(routes,ins)
        assert checked['valid'] and abs(checked['distance']/10-cost)<1e-6,(path.name,checked['errors'],checked['distance']/10,cost)
        refs.append(dict(instance=path.stem,n=ins.n,reference_distance=cost,
            reference_vehicles=checked['vehicles'],fleet_limit=ins.vehicles,validated=True))
    manifest=dict(repository='https://github.com/PyVRP/Instances',revision=revision,
        convention='DIMACS floor(10 * original Euclidean edge); times and distance in tenths; distance-only objective',
        files=files,reference_instances=refs)
    (data/'manifest.json').write_text(json.dumps(manifest,indent=2))
    (data/'LICENSE_repository.txt').write_bytes(fetch(f'https://raw.githubusercontent.com/PyVRP/Instances/{revision}/LICENSE'))
    print('Validated references:',len(refs),flush=True)


if __name__=='__main__':main()
