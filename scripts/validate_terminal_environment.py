"""Conserver et vérifier le lot exécuté dans l'environnement statique local."""
from pathlib import Path,PureWindowsPath
import hashlib
import json
import shutil
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import vrplib
from scripts.audit_gap_status import check
from scripts.terminal_support import paired_comparisons


def main():
    label='verification_env_six_familles'
    out=ROOT/'results/terminal_comparison'/label
    source=ROOT/'results/local'/label
    if source.exists():
        balance=json.loads((source/'BILAN.json').read_text(encoding='utf-8'))
        assert balance['completed']==12,'Attendre la fin des douze résolutions'
        shutil.copytree(source,out,dirs_exist_ok=True)
    rows=[]
    for path in sorted(out.glob('*.json')):
        record=json.loads(path.read_text(encoding='utf-8'))
        if 'measurement' not in record:continue
        row=record['measurement'];assert row['valid']
        own=check(row['instance'],row['n'],record['result']['routes'])
        assert own['valid'] and abs(own['duration']-row['duration'])<1e-7
        reference=check(row['instance'],row['n'],vrplib.read_solution(ROOT/record['reference']['source'])['routes'])
        assert reference['valid'] and abs(reference['duration']-row['reference_duration'])<1e-7
        assert abs(100*(own['duration']/reference['duration']-1)-row['delta_reference_pct'])<1e-7
        rows.append(row)
    assert len(rows)==12
    pairs=paired_comparisons(rows)
    assert len(pairs)==6 and {r['instance'] for r in pairs}=={'C101','C201','R101','R201','RC101','RC201'}
    protocol=json.loads((out/'protocol.json').read_text(encoding='utf-8'))
    # La provenance conserve le chemin de la machine de mesure, même sur un clone.
    assert PureWindowsPath(protocol['python']).parts[-3:]==('.venv','Scripts','python.exe')
    for rel,expected in protocol['sources'].items():
        assert hashlib.sha256((out/'source'/rel).read_bytes()).hexdigest()==expected
    log=(out.parent/'CONSOLE_ENV_SIX_FAMILLES.txt').read_text(encoding='utf-8-sig')
    assert log.count('RÉSULTATS COMPARÉS POUR CETTE INSTANCE ET CETTE GRAINE')==6
    checked=subprocess.run([sys.executable,'-m','pip','check'],capture_output=True,text=True,check=True)
    result=dict(validated=True,python=protocol['python'],instances=6,trials=12,feasible=12,
        paired_comparisons=6,immediate_console_comparisons=6,independently_checked=True,
        protocol_source_hashes_checked=True,packages=protocol['packages'],pip_check=checked.stdout.strip(),
        note='Five seconds requested per method; search/total-soft budget semantics unchanged; no claim of universal superiority')
    (out.parent/'VALIDATION_ENV_STATIQUE.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps(result,indent=2,ensure_ascii=False))


if __name__=='__main__':main()
