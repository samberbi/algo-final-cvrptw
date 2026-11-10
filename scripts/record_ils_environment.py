"""Record actual installed packages and the most recent completed pytest log."""
from pathlib import Path
import importlib.metadata as metadata
import json,platform,re
import psutil
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/revision_ils'
packages=['numpy','pandas','scipy','matplotlib','vrplib','psutil','numba','nbformat','nbclient','ipykernel','nbconvert','jupyter-client','pytest','python-docx','pymupdf','tabulate']
versions={name:metadata.version(name) for name in packages}
environment={'Python':platform.python_version(),'OS':platform.platform(),'Processeur':platform.processor(),
             'Cœurs physiques':psutil.cpu_count(logical=False),'Processeurs logiques':psutil.cpu_count(),
             'RAM (Gio)':round(psutil.virtual_memory().total/2**30,1),'Versions':versions,
             'Streamlit':metadata.version('streamlit'),'Plotly':metadata.version('plotly')}
(OUT/'environment.json').write_text(json.dumps(environment,indent=2,ensure_ascii=False),encoding='utf-8')
(ROOT/'requirements-lock.txt').write_text('# Direct dependencies actually validated on Python '+platform.python_version()+'\n'+'\n'.join(k+'=='+v for k,v in versions.items())+'\n',encoding='utf-8')
log=(OUT/'tests.log').read_bytes().decode('utf-16' if (OUT/'tests.log').read_bytes().startswith(b'\xff\xfe') else 'utf-8')
summary=re.findall(r'\d+ passed[^\n]*',log)[-1].strip()
(OUT/'test_validation.json').write_text(json.dumps({'summary':summary,'command':'python -m pytest -q --disable-warnings','log':'results/revision_ils/tests.log'},indent=2))
print(summary)
