"""Contrats CLI : sélection bornée, références non circulaires, coûts et échecs."""
import json
from pathlib import Path
import pytest
from scripts import terminal_support as terminal
from scripts.run_benchmark import parser,replay,selected_methods,completed_comparison,check_environment


def test_default_selection_is_one_c101_not_whole_catalogue():
    rows=terminal.select_cases(terminal.catalog())
    assert [(r['instance'],r['n']) for r in rows]==[('C101',100)]


def test_unambiguous_small_sizes_and_large_instance_inference():
    rows=terminal.catalog()
    assert terminal.select_cases(rows,['C101'],[25])[0]['n']==25
    assert terminal.select_cases(rows,['C1_10_6'])[0]['n']==1000
    assert terminal.select_cases(rows,['C101:50'])[0]['n']==50


def test_progressive_is_eight_cases_not_all_instances():
    rows=terminal.select_cases(terminal.catalog(),progressive=True)
    assert [r['n'] for r in rows]==terminal.SIZES
    assert len(rows)==8


def test_all_six_families_at_100_and_explicit_all():
    rows=terminal.catalog()
    selected=terminal.select_cases(rows,sizes=[100],families=terminal.FAMILIES)
    assert len(selected)==6 and {r['family'] for r in selected}==set(terminal.FAMILIES)
    assert len(terminal.select_cases(rows,sizes=[100],all_cases=True))==56


def test_unknown_instance_does_not_silently_disappear():
    with pytest.raises(ValueError,match='absente'):
        terminal.select_cases(terminal.catalog(),['C101','INCONNUE'])


def test_labels_are_unique_and_cannot_escape_store(tmp_path):
    assert terminal.unique_folder('same',tmp_path).name=='same'
    assert terminal.unique_folder('same',tmp_path).name=='same_2'
    with pytest.raises(ValueError):terminal.unique_folder('../escape',tmp_path)


def test_wrong_announced_cost_and_incomplete_coverage_rejected():
    from tests.test_final_static import example
    ins=example()
    with pytest.raises(ValueError,match='Coût annoncé'):
        terminal.verified_result(ins,dict(routes=[[2,1]],cost=0))
    with pytest.raises(ValueError,match='Contraintes invalides'):
        terminal.verified_result(ins,dict(routes=[[1]],cost=1))


def test_signed_gaps_and_unavailable_certificate_are_preserved():
    record=dict(instance='C101',n=100,family='C1',method='ils',seed=1,valid=True,status='feasible',
        wall_s=1,cpu_s=1,requested_seconds=5,result={'metrics':dict(duration=900,travel=400,waiting=100,vehicles=1)})
    row=terminal.row_from(record,dict(duration=100,type='feasible',source='external',certified=False))
    assert row['delta_reference_pct']==pytest.approx(-10) and row['certified_gap_pct'] is None
    row=terminal.row_from(record,dict(duration=None,type='NON DISPONIBLE',source=None))
    assert row['delta_reference_pct'] is None


def test_cached_reference_is_external_not_own_best_solution():
    entry=next(r for r in terminal.catalog() if r['instance']=='C101' and r['n']==25)
    ref=terminal.find_reference(entry,terminal.load_case(entry),'independent')
    assert ref['duration']==2623.5 and '_ortools_' in ref['source'] and not ref['certified']


def test_cli_aliases_accept_legacy_usage():
    args=parser().parse_args(['--instances','C101','--method','duration_refined','--label','x'])
    assert args.method=='duration_refined'
    args=parser().parse_args(['--instance','C101','--size','25','--methods','ils','refined'])
    assert args.sizes==[25] and args.methods==['ils','refined']


def test_default_executes_initial_and_reinforced_but_explicit_method_stays_single():
    assert selected_methods(parser().parse_args([]))==['ils','size_based']
    assert selected_methods(parser().parse_args(['--method','size_based']))==['size_based']
    assert selected_methods(parser().parse_args(['--method','duration_refined']))==['refined']
    with pytest.raises(ValueError):
        selected_methods(parser().parse_args(['--method','ils','--methods','size_based']))


def test_each_instance_and_seed_is_compared_once_when_both_methods_finish():
    def row(name,method,seed=4101):
        return dict(instance=name,n=100,seed=seed,method=method)
    methods=['ils','size_based'];shown=set()
    first=row('C101','ils');second=row('RC101','size_based')
    other_seed=row('C101','size_based',4102)
    rows=[first,second,other_seed]
    assert completed_comparison(rows,second,methods,shown)==[]
    assert completed_comparison(rows,other_seed,methods,shown)==[]
    finish=row('RC101','ils');rows.append(finish)
    assert completed_comparison(rows,finish,methods,shown)==[second,finish]
    assert completed_comparison(rows,finish,methods,shown)==[]
    finish_c=row('C101','size_based');rows.append(finish_c)
    assert completed_comparison(rows,finish_c,methods,shown)==[first,finish_c]


def test_missing_dependency_explains_active_interpreter_and_static_environment(monkeypatch):
    import importlib.metadata as metadata
    def version(name):
        if name in ['numba','pyvrp','scipy']:raise metadata.PackageNotFoundError(name)
        return 'test-version'
    monkeypatch.setattr(metadata,'version',version)
    with pytest.raises(ValueError) as error:check_environment(['ils','size_based'])
    text=str(error.value)
    assert 'numba' in text and 'pyvrp' in text and 'scipy' in text
    assert '.venv_dabia' in text and 'requirements-reference-final.txt' in text
    assert 'python.exe scripts/test_instances.py' in text


def test_optional_unused_solver_metadata_does_not_block_own_ils(monkeypatch):
    import importlib.metadata as metadata
    def version(name):
        if name in ['pyvrp','scipy','ortools']:raise metadata.PackageNotFoundError(name)
        return 'test-version'
    monkeypatch.setattr(metadata,'version',version)
    result=check_environment(['ils'])
    assert result['numba']=='test-version' and result['pyvrp'] is None


@pytest.mark.parametrize('cost,expected,conclusion',[(90,10,'Renforcé meilleur'),
    (100,0,'Égalité de durée'),(110,-10,'ILS initial meilleur')])
def test_paired_gain_is_separate_from_reference_gap_and_keeps_regressions(cost,expected,conclusion):
    base=dict(instance='manual',n=2,seed=4101,valid=True,wall_s=5,cpu_s=4,
              requested_seconds=5,reference_duration=50,vehicles=1)
    rows=[dict(base,method='ils',duration=100),dict(base,method='size_based',duration=cost)]
    pair=terminal.paired_comparisons(rows)[0]
    assert pair['duration_gain_pct']==pytest.approx(expected)
    assert pair['conclusion']==conclusion
    assert pair['initial_comparison']=='100.0000 %'
    text=terminal.comparison(rows)
    assert 'CPU(s)' in text and 'INITIAL / RENFORCÉ' in text and conclusion in text


def test_failed_pair_has_no_invented_gain_and_csv_is_saved(tmp_path):
    base=dict(instance='manual',n=2,seed=4101,wall_s=1,cpu_s=1,
              requested_seconds=5,reference_duration=100,vehicles=1)
    rows=[dict(base,method='ils',duration=None,valid=False),
          dict(base,method='size_based',duration=90,valid=True)]
    pair=terminal.paired_comparisons(rows)[0]
    assert pair['duration_gain_pct'] is None and 'échec' in pair['conclusion']
    terminal.save_tables(tmp_path,[dict(measurement=r) for r in rows],2)
    assert (tmp_path/'COMPARAISON_INITIAL_RENFORCE.csv').is_file()


def test_failed_results_keep_na_and_are_not_ranked(tmp_path):
    record=dict(instance='R101',family='R1',n=100,method='pyvrp',seed=1,valid=False,
        status='not_found',wall_s=.1,cpu_s=.1,requested_seconds=.1,result=dict(routes=None,status='not_found'))
    row=terminal.row_from(record,dict(duration=100,type='external',source='x',certified=False))
    assert row['duration'] is None and row['delta_reference_pct'] is None
    terminal.save_tables(tmp_path,[dict(measurement=row,result=record['result'])],1)
    assert json.loads((tmp_path/'BILAN.json').read_text())['failed']==1
    assert 'aucune solution' in (tmp_path/'SYNTHESE.txt').read_text(encoding='utf-8')


def test_replay_keeps_existing_files_unchanged(monkeypatch,tmp_path,capsys):
    monkeypatch.setattr('scripts.run_benchmark.ROOT',tmp_path)
    folder=tmp_path/'results/local/saved';folder.mkdir(parents=True)
    row=dict(instance='C101',n=100,family='C1',method='ils',seed=1,valid=False,status='not_found',
        duration=None,wall_s=1,cpu_s=1,requested_seconds=1,delta_reference_pct=None)
    path=folder/'result.json';path.write_text(json.dumps(dict(measurement=row,result=None)))
    before=path.read_bytes()
    replay('saved',show_routes=True)
    assert path.read_bytes()==before and 'LECTURE SEULE' in capsys.readouterr().out
