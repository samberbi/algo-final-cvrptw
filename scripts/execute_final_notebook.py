"""Réexécution complète avec le même Python que la commande, sans export PDF/HTML."""
from pathlib import Path
import hashlib
import json
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
import nbformat
from nbclient import NotebookClient
from jupyter_client.manager import AsyncKernelManager
from jupyter_client.kernelspec import KernelSpecManager


def main():
    target=ROOT/'notebooks/Livrable_Final_CVRPTW.ipynb'
    kernel_root=ROOT/'.tools/final_jupyter/kernels'
    spec=kernel_root/'cvrptw-final';spec.mkdir(parents=True,exist_ok=True)
    (spec/'kernel.json').write_text(json.dumps(dict(argv=[sys.executable,'-m','ipykernel_launcher','-f','{connection_file}'],
        display_name='CVRPTW final — Python courant',language='python',env={'PYTHONUTF8':'1'})),encoding='utf-8')
    nb=nbformat.read(target,4)
    manager=AsyncKernelManager(kernel_name='cvrptw-final',kernel_spec_manager=KernelSpecManager(kernel_dirs=[str(kernel_root)]))
    started=time.perf_counter()
    client=NotebookClient(nb,km=manager,timeout=240,resources={'metadata':{'path':str(ROOT/'notebooks')}})
    try:
        client.execute(cleanup_kc=True)
    except Exception:
        failed=ROOT/'results/final_static/NOTEBOOK_EXECUTION_ECHEC.ipynb'
        nbformat.write(nb,failed)
        raise
    nbformat.write(nb,target)
    receipt=dict(executed=True,python=sys.executable,wall_s=time.perf_counter()-started,
        cells=sum(c.cell_type=='code' for c in nb.cells),errors=0,
        notebook_sha256=hashlib.sha256(target.read_bytes()).hexdigest())
    (ROOT/'results/final_static/NOTEBOOK_EXECUTION.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    print(json.dumps(receipt,indent=2))


if __name__=='__main__':main()
