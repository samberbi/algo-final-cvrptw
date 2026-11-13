import pytest
from algo.comparison_status import classify,present,describe_positive,positive_text,BETTER,EQUAL,OPTIMAL,MISSING,FAILED


def test_negative_comparator_is_not_modified_or_called_optimal():
    assert classify(95,100)==BETTER
    assert present(95,100)==BETTER


def test_equal_heuristic_does_not_prove_optimality():
    assert classify(100,100)==EQUAL
    assert present(100,100)==EQUAL


def test_verified_exact_optimum_has_a_non_numeric_status():
    assert classify(100,100,certified=True)==OPTIMAL
    assert classify(0,0,certified=True)==OPTIMAL


def test_beating_certified_optimum_blocks_validation():
    with pytest.raises(ValueError,match='Contradiction'):
        classify(99,100,certified=True)


def test_positive_gap_above_six_is_preserved():
    assert present(115,100)=='15.0000 %'


def test_tiny_positive_gap_does_not_round_to_zero():
    value=positive_text(1e-7)
    assert float(value)>0


@pytest.mark.parametrize('value',[-5,0,None])
def test_nonpositive_numbers_cannot_be_formatted_as_positive_gaps(value):
    with pytest.raises(ValueError):positive_text(value)


def test_failed_or_unreferenced_comparisons_remain_distinct():
    assert classify(None,100,valid=False)==FAILED
    assert classify(100,None)==MISSING
    assert classify(1,0)==MISSING


def test_positive_statistics_do_not_hide_denominators_or_cancellation():
    stats=describe_positive([-5,0,5,9,None])
    assert stats['comparisons']==4 and stats['positive_count']==2
    assert stats['positive_mean']==7 and stats['positive_median']==7
    assert stats['reference_better_count']==1 and stats['equal_count']==1 and stats['above_six']==1


def test_console_status_leaves_original_signed_measurement_intact(capsys):
    from scripts.terminal_support import show
    measurement=dict(instance='C101',family='C1',n=100,method='ils',seed=1,valid=True,
        duration=95.,reference_duration=100.,delta_reference_pct=-5.,wall_s=1.,cpu_s=1.)
    show(dict(measurement=measurement,result={}))
    text=capsys.readouterr().out
    assert BETTER in text and '-5.0000 %' not in text
    assert measurement['delta_reference_pct']==-5.
