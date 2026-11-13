"""Vérifie les compléments documentaires et les preuves de l'étude contrôlée."""
from pathlib import Path
import hashlib
import json
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import nbformat
import pandas as pd


def main():
    folder=ROOT/'results/time_objective/sensitivity_controlled'
    protocol=json.loads((folder/'protocol.json').read_text())
    profiles=pd.read_csv(folder/'TOUS_LES_PROFILS.csv')
    paired=pd.read_csv(folder/'COMPARAISONS_APPARIEES.csv')
    expected={tuple(job) for job in protocol['jobs']}
    assert set(zip(profiles.instance,profiles.seed,profiles.configuration))==expected
    assert len(profiles)==90 and profiles.valid.all() and len(paired)==90
    assert profiles.groupby(['instance','seed']).size().eq(5).all()
    assert profiles.groupby(['instance','seed']).initial_sha256.nunique().eq(1).all()
    subset=profiles[profiles.configuration.isin(['baseline','neighbors_80','neighbors_120'])]
    assert subset.groupby(['instance','seed']).prefix_sha256.nunique().eq(1).all()
    for name,expected_hash in protocol['source_hashes'].items():
        assert hashlib.sha256((folder/'source'/name).read_bytes()).hexdigest()==expected_hash,name
    manifest=json.loads((ROOT/'data/manifest.json').read_text())
    for name in protocol['instances']:
        for ext in ['.vrp','.sol']:
            file=name+ext
            assert hashlib.sha256((ROOT/'data/instances'/file).read_bytes()).hexdigest()==manifest['files'][file]['sha256']
    features=pd.read_csv(ROOT/'results/time_objective/scenario_analysis/CARACTERISTIQUES_INSTANCES.csv')
    assert len(features)==356 and features.instance.nunique()==356
    assert set(features.family)=={'C1','C2','R1','R2','RC1','RC2'}
    assert features.groupby('n').size().to_dict()=={100:56,200:60,400:60,600:60,800:60,1000:60}
    assert features.waiting_share.between(0,1).all()
    assert features.mean_capacity_fill.between(0,1+1e-7).all()
    # La nouvelle étude ne doit pas remplacer les mesures des meilleures tournées.
    old_receipt=json.loads((ROOT/'results/time_objective/outliers10/VALIDATION_OPTIMISATION_DUREE.json').read_text())
    old_csv=ROOT/'results/time_objective/outliers10/AVANT_APRES_ESSAIS.csv'
    assert hashlib.sha256(old_csv.read_bytes()).hexdigest()==old_receipt['result_csv_sha256']
    nb=nbformat.read(ROOT/'notebooks/Livrable_Final_CVRPTW.ipynb',as_version=4)
    nbformat.validate(nb)
    codes=[c for c in nb.cells if c.cell_type=='code']
    assert len(codes)==16 and all(c.execution_count is not None for c in codes)
    assert not any(o.output_type=='error' for c in codes for o in c.outputs)
    for c in nb.cells:
        assert not any(ch in c.source for ch in ['\x08','\x0c','\r'])
    report=(ROOT/'LIVRABLE_FINAL.md').read_text(encoding='utf-8')
    assert report.count('### 6.10.')==1 and report.count('### 6.11.')==1
    assert 'NP-complète' in report and 'Pourquoi fixer le départ à zéro' in report
    images=re.findall(r'!\[[^\n]*\]\(([^)]+)\)',report)
    for path in images:assert (ROOT/path).is_file(),path
    summary=dict(validated=True,scope='Controlled study and reporting additions; no new full-catalogue benchmark',
        sensitivity_profiles=90,sensitivity_feasible=90,instances=6,seeds=3,configurations=5,
        actual_constructions=len(list((folder/'initials').glob('*.json'))),
        actual_ils_prefixes=len(list((folder/'prefixes').glob('*.json'))),actual_hgs_calls=90,
        time_convention=protocol['total_time_kind'],scenario_instances=356,scenario_families=6,
        figures=len(images),missing_figures=0,notebook_code_cells=16,notebook_errors=0,
        prior_best_results_unchanged=True)
    (folder/'VALIDATION_ETUDE.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
