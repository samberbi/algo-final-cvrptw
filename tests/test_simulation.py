"""Playback must preserve verified travel, waiting, service and return times."""
import numpy as np
import pytest

from algo.model import Instance
from web.simulation import timeline, simulation_html


def example():
    return Instance('exemple', np.array([[0, 0], [8, 0], [4, 3]]),
                    np.array([0, 2, 3]), np.array([0, 50, 40]),
                    np.array([0, 150, 0]), np.array([600, 250, 400]),
                    np.array([[0, 80, 50], [80, 0, 50], [50, 50, 0]]), 6., 2, 600.)


def test_waiting_service_delivery_and_return_are_distinct():
    data = timeline(example(), [[1, 2]])
    v = data['vehicles'][0]
    assert [(s['kind'], s['start'], s['end']) for s in v['segments']] == [
        ('Trajet', 0., 8.), ('Attente', 8., 15.), ('Service', 15., 20.),
        ('Trajet', 20., 25.), ('Service', 25., 29.), ('Trajet', 29., 34.)]
    assert [s['finish'] for s in v['stops']] == [20., 29.]
    assert v['segments'][-1]['destination'] == 0
    assert data['end'] == 34. and data['distance'] == 18.


def test_parallel_vehicles_use_last_return_and_empty_routes_are_ignored():
    data = timeline(example(), [[], [1], [2]])
    assert len(data['vehicles']) == 2
    assert data['end'] == 28.  # 8 + 7 waiting + 5 service + 8 return.
    assert data['end'] != sum(v['end'] for v in data['vehicles'])


def test_invalid_solution_is_not_animated():
    with pytest.raises(ValueError, match='irréalisables'):
        timeline(example(), [[1], [1, 2]])


def test_constraint_evidence_preserves_windows_load_and_duration_components():
    from web.constraint_views import audit_frames
    clients, vehicles = audit_frames(timeline(example(), [[1, 2]]))
    assert clients.fenetre_respectee.all() and vehicles.capacite_respectee.all()
    assert vehicles.retour_respecte.all()
    assert clients.charge_apres_service.tolist() == [3., 0.]
    assert clients.marge_fenetre.tolist() == [10., 15.]
    assert vehicles.iloc[0][['trajet', 'attente', 'service']].sum() == vehicles.iloc[0].retour


def test_window_check_is_about_start_even_when_service_ends_after_closing():
    from dataclasses import replace
    from web.constraint_views import audit_frames
    ins = replace(example(), service=np.array([0, 150, 40]))
    clients, _ = audit_frames(timeline(ins, [[1, 2]]))
    assert clients.iloc[0].fin > clients.iloc[0].fermeture
    assert clients.fenetre_respectee.all()


def test_saved_feasibility_fixtures_supply_complete_constraint_evidence():
    from pathlib import Path
    import json
    from algo.data import load
    from web.constraint_views import audit_frames
    root = Path(__file__).resolve().parents[1]
    files = json.loads((root / 'tests/fixtures/solutions_feasibility.json').read_text())
    assert len(files) == 360
    instances = {}
    for path in files:
        item = path
        name = item['instance']
        if name not in instances:
            instances[name] = load(root / 'data/instances' / (name + '.vrp'))
        data = timeline(instances[name], item['routes'])
        assert all({'early', 'late', 'arrival', 'start', 'finish', 'demand'} <= stop.keys()
                   for vehicle in data['vehicles'] for stop in vehicle['stops']), path.name
        clients, vehicles = audit_frames(data)
        assert len(clients) == data['clients'] and clients.client.nunique() == data['clients']
        assert clients.fenetre_respectee.all(), path.name
        assert vehicles.capacite_respectee.all() and vehicles.retour_respecte.all(), path.name


def test_payload_cannot_close_its_script_element():
    html = simulation_html(dict(name='</script><script>alert(1)</script>'))
    assert '</script><script>alert' not in html
    assert '\\u003c/script>' in html


def test_javascript_playback_controls_and_schedule_boundaries():
    from pathlib import Path
    import shutil
    import subprocess
    node = shutil.which('node')
    if not node:
        pytest.skip('Node.js est nécessaire pour vérifier les contrôles de lecture')
    result = subprocess.run([node, str(Path(__file__).with_name('simulation_playback.cjs'))],
                            input=simulation_html(timeline(example(), [[1, 2]])),
                            text=True, encoding='utf-8', capture_output=True, timeout=15)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize('source,instance',[
    ('Catalogue en durée','R1_10_3'),
    ('Catalogue en durée','R1_10_6'),
    ('Catalogue en durée','R2_10_4'),
    ('Catalogue en durée','R2_10_8'),
])
def test_simulation_page_accepts_a_large_saved_solution(source,instance):
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file('web/app.py', default_timeout=30).run()
    assert not at.exception
    assert at.sidebar.radio[0].value == 'Simulation'
    assert source in at.radio[0].options
    at.radio[0].set_value(source).run()
    at.selectbox[0].select(instance).run()
    assert not at.exception
    assert any(m.label == 'Clients' and m.value == '1000' for m in at.metric)
    assert any('Vérifier toutes les contraintes' == tab.label for tab in at.tabs)
    assert not at.dataframe[0].value.empty
    at.radio[0].set_value('Mes campagnes').run()
    assert not at.exception
