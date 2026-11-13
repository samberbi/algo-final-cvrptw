"""Conserve les archives officielles Solomon 25/50 et des fichiers choisis."""
from pathlib import Path
import hashlib
import io
import json
import urllib.request
import zipfile
import argparse
ROOT = Path(__file__).resolve().parents[1]
NAMES = ['C101','C105','C106','C201','R101','R201','RC101','RC201']


def main():
    root=ROOT/'data/static_small'
    root.mkdir(parents=True,exist_ok=True)
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',choices=['prefix','official'],default='prefix',
        help='prefix : sous-instances standard issues des fichiers officiels n100 déjà vérifiés ; official : archives web')
    args=parser.parse_args()
    if args.source=='prefix':
        import vrplib
        import numpy as np
        files=[]
        for n in [25,50]:
            folder=root/f'n{n}';folder.mkdir(exist_ok=True)
            for name in NAMES:
                source=ROOT/'data/instances'/(name+'.vrp')
                raw=vrplib.read_instance(source)
                services=np.asarray(raw['service_time'])
                if services.ndim==0:services=np.full(len(raw['demand']),services)
                lines=[name,'','VEHICLE','NUMBER CAPACITY',f"{raw['vehicles']} {raw['capacity']}",
                       '', 'CUSTOMER', 'CUST NO. XCOORD. YCOORD. DEMAND READY TIME DUE DATE SERVICE TIME','']
                for i in range(n+1):
                    x,y=raw['node_coord'][i];early,late=raw['time_window'][i]
                    values=[i,x,y,raw['demand'][i],early,late,0 if i==0 else services[i]]
                    lines.append(' '.join(f'{v:g}' for v in values))
                payload=('\n'.join(lines)+'\n').encode()
                target=folder/(name+'.txt')
                if target.exists():assert target.read_bytes()==payload
                else:target.write_bytes(payload)
                files.append(dict(instance=name,n=n,path=target.relative_to(ROOT).as_posix(),
                    sha256=hashlib.sha256(payload).hexdigest(),parent=source.relative_to(ROOT).as_posix(),
                    parent_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                    derivation=f'Standard Solomon prefix: depot plus customer IDs 1..{n}; values unchanged'))
        manifest=dict(source='Standard first-N subinstances derived transparently from pinned official n100 files',
            files=files,archive_download='Dorronsoro archive returned HTTP 403 in this session; no claim of successful download',
            convention='DIMACS truncated tenths, fixed symmetric times, departures zero; original values unchanged')
        (root/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
        print(f'{len(files)} sous-instances standard dérivées et traçables, sans modification des clients')
        return
    files=[]
    for n in [25,50]:
        url=f'https://vrp.dorronsoro.es/data/instances/solomon/solomon_{n}.zip'
        with urllib.request.urlopen(url,timeout=60) as response:payload=response.read()
        archive=root/f'solomon_{n}.zip'
        if archive.exists():assert archive.read_bytes()==payload
        else:archive.write_bytes(payload)
        folder=root/f'n{n}';folder.mkdir(exist_ok=True)
        with zipfile.ZipFile(io.BytesIO(payload)) as z:
            for name in NAMES:
                found=[info for info in z.infolist() if Path(info.filename).stem.upper()==name and not info.is_dir()]
                if len(found)!=1:raise ValueError((name,[i.filename for i in z.infolist()][:10]))
                data=z.read(found[0]);target=folder/(name+'.txt')
                if target.exists():assert target.read_bytes()==data
                else:target.write_bytes(data)
                files.append(dict(instance=name,n=n,path=target.relative_to(ROOT).as_posix(),
                    sha256=hashlib.sha256(data).hexdigest(),url=url,archive_member=found[0].filename,
                    archive_sha256=hashlib.sha256(payload).hexdigest()))
    manifest=dict(source='Dorronsoro VRP Web, official Solomon subinstances',files=files,
        convention='Original bytes preserved; project loader uses DIMACS floor(10*Euclidean), all times x10',
        comparison='Not automatically compatible with full-precision published time costs')
    (root/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(f'{len(files)} sous-instances sauvegardées')


if __name__=='__main__':main()
