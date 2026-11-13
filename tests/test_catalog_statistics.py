"""Statistics must retain failed attempts and distinguish unequal repetition counts."""
import pandas as pd
import pytest
from scripts.statistics_common import summary


def test_instance_mean_does_not_overweight_repeated_easy_cases():
    df=pd.DataFrame([dict(instance='easy',valid=True,gap_pct=0.,total_s=1.),
                     dict(instance='easy',valid=True,gap_pct=0.,total_s=1.),
                     dict(instance='hard',valid=True,gap_pct=12.,total_s=1.)])
    result=summary(df)
    assert result['mean_instance_gap']==6.
    assert result['mean_run_gap']==4.
    assert result['instances']==2 and result['attempts']==3


def test_failures_remain_visible_and_have_no_distance_gap():
    df=pd.DataFrame([dict(instance='ok',valid=True,gap_pct=8.,total_s=1.),
                     dict(instance='failed',valid=False,gap_pct=None,total_s=None)])
    result=summary(df)
    assert result['failures']==1 and result['represented_instances']==1
    assert result['mean_instance_gap']==8. and result['runs_below_6']==0
    assert result['feasible_rate']==pytest.approx(.5)


def test_all_failed_results_do_not_produce_a_zero_mean():
    df=pd.DataFrame([dict(instance='failed',valid=False,gap_pct=None,total_s=None)])
    result=summary(df)
    assert result['mean_instance_gap'] is None and result['mean_run_gap'] is None
    assert result['failures']==1 and result['valid']==0
