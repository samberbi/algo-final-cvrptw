"""Fixed-work comparison: identical moves and outcomes, compilation excluded."""
from pathlib import Path
import sys, json, time
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import pandas as pd
import psutil
from algo import kernels
from algo.cached_local import local_search
from algo.data import load
from algo.iterated import encode, decode, arrays, build_neighbors
from algo.verify import verify


def main():
    psutil.Process().cpu_affinity([psutil.Process().cpu_affinity()[0]])
    rows = []
    for name in ['C1_10_3', 'C2_10_3', 'R1_10_3', 'R2_10_3', 'RC1_10_3', 'RC2_10_3']:
        ins = load(ROOT/'data/instances'/(name+'.vrp'))
        parent = json.loads((ROOT/'results/optimization_v5/portfolio_intensified'/(name+'.json')).read_text())['result']['routes']
        a, lens = encode(parent, ins)
        neighbors = build_neighbors(ins,24)
        enabled = np.ones(4,np.bool_)
        for fn in [kernels.local_search, local_search]:
            fn(a.copy(),lens.copy(),*arrays(ins),neighbors,1,2,0,enabled)
        outputs = {}
        for repeat in range(6):
            order = [('full',kernels.local_search),('cached',local_search)]
            if repeat%2: order.reverse()
            for label, fn in order:
                work, lengths = a.copy(),lens.copy()
                started = time.perf_counter()
                moved, tested = fn(work,lengths,*arrays(ins),neighbors,20,2,repeat,enabled)
                elapsed = time.perf_counter()-started
                routes = decode(work,lengths)
                assert verify(routes,ins)['valid']
                if repeat in outputs:
                    assert outputs[repeat]==routes
                outputs[repeat]=routes
                rows.append(dict(instance=name,repeat=repeat,variant=label,seconds=elapsed,moves=moved,tested=tested))
    out = ROOT/'results/optimization_v6'
    out.mkdir(exist_ok=True)
    frame = pd.DataFrame(rows)
    frame.to_csv(out/'fixed_work.csv',index=False)
    summary = frame.groupby(['instance','variant']).seconds.median().unstack()
    summary['speedup']=summary['full']/summary['cached']
    summary.to_csv(out/'fixed_work_summary.csv')
    print(summary.to_string())


if __name__=='__main__': main()
