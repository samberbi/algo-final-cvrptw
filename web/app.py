"""Run with: python -m streamlit run web/app.py"""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import plotly.express as px
import streamlit as st

from web import charts
from web.experiments import (PROFILES, campaign_path, catalog, create_campaign,
                             frame, launch, list_campaigns, make_protocol, progress,
                             read_json, records, statistics, stop)

st.set_page_config(page_title='CVRPTW · Laboratoire', page_icon='🚚', layout='wide')
st.markdown('''<style>
.stApp {background: #f6f8fb;}
[data-testid="stSidebar"] {background: #101e35;}
[data-testid="stSidebar"] * {color: #e8eff8;}
[data-testid="stMetric"] {background: white; padding: 16px; border-radius: 12px; border: 1px solid #e2e8f0;}
.block-container {padding-top: 2rem;}
</style>''', unsafe_allow_html=True)

st.sidebar.title('CVRPTW')
st.sidebar.caption('LABORATOIRE D’EXPÉRIMENTATION')
page = st.sidebar.radio('Navigation', ['Vue d’ensemble', 'Nouvelle expérience', 'Mes campagnes', 'Résultats historiques'])
st.sidebar.divider()
st.sidebar.write('**Objectif : distance minimale**')
st.sidebar.caption('Référence DIMACS · fenêtres strictes · capacité et flotte maximale respectées')
st.sidebar.caption('Les calculs tournent sur cet ordinateur. Les campagnes continuent si la page est fermée.')


@st.cache_data
def historical(source):
    path = ROOT / 'results/report' / ('mille_executions.csv' if source == 'Extension · 1 000 runs' else 'etude_principale_80.csv')
    df = pd.read_csv(path)
    if 'id' in df:
        df = df.rename(columns={'id': 'run'})
    df['profile'] = 'Historique publié'
    df['valid'] = df['status'].eq('feasible') if 'status' in df else True
    if 'status' not in df:
        df['status'] = 'feasible'
    return df


def display_metrics(df, expected=None):
    if df.empty:
        st.info('Aucun essai terminé pour le moment.')
        return
    valid = df['valid'].astype(bool)
    gaps = df.loc[valid, 'gap_pct'].dropna()
    cols = st.columns(5)
    cols[0].metric('Essais terminés', f'{len(df)}' + (f' / {expected}' if expected else ''))
    cols[1].metric('Réalisables', f'{int(valid.sum())} / {len(df)}')
    cols[2].metric('Gap moyen', f'{gaps.mean():.3f} %' if len(gaps) else '—')
    cols[3].metric('Sous 5 %', f'{int((valid & df.gap_pct.lt(5)).sum())} / {len(df)}')
    cols[4].metric('Sous 7 %', f'{int((valid & df.gap_pct.lt(7)).sum())} / {len(df)}')
    st.caption(f'Moyenne arithmétique des gaps sur {len(gaps)} essais réalisables avec BKS, '
               f'parmi {len(df)} essais terminés. Chaque run a le même poids. Les échecs restent dans le tableau.')


def downloads(df, summary, prefix):
    a, b = st.columns(2)
    a.download_button('Télécharger les runs · CSV', df.to_csv(index=False).encode('utf-8-sig'),
                      file_name=prefix + '_runs.csv', mime='text/csv', key=prefix + '_runs')
    b.download_button('Télécharger les statistiques · CSV', summary.to_csv(index=False).encode('utf-8-sig'),
                      file_name=prefix + '_stats.csv', mime='text/csv', key=prefix + '_stats')


def analysis(df, key):
    if df.empty:
        return
    summary = statistics(df)
    st.subheader('Statistiques par instance et configuration')
    st.caption('std_gap : écart-type entre répétitions, en points de pourcentage (non défini avec un seul essai). '
               'Les seuils sont strictement inférieurs à 5 % et 7 %.')
    st.dataframe(summary, hide_index=True, width='stretch')
    if df['gap_pct'].notna().any():
        left, right = st.columns(2)
        by = 'profile' if df['profile'].nunique() > 1 else 'instance'
        left.plotly_chart(charts.distribution(df, by), width='stretch', key=key + '_box')
        right.plotly_chart(charts.gap_bars(summary), width='stretch', key=key + '_bar')
        st.plotly_chart(charts.finish(px.scatter(df, x='runtime_s', y='gap_pct', color='profile',
                                                 hover_data=['instance', 'seed']),
                                      'Temps de calcul et qualité', 'Temps de recherche (s)', 'Gap (%)'),
                        width='stretch', key=key + '_scatter')
    st.subheader('Tous les essais, y compris les échecs')
    st.dataframe(df, hide_index=True, width='stretch')
    downloads(df, summary, key)


def new_experiment():
    st.title('Nouvelle expérience')
    st.write('Choisis librement les instances, répétitions et budgets. Chaque essai part d’une nouvelle construction.')
    data = catalog()
    data['family'] = data['instance'].str.extract(r'^(RC|C|R)([12])').agg(''.join, axis=1)
    a, b = st.columns(2)
    sizes = a.multiselect('Nombre de clients', sorted(data.n.unique().tolist()), default=[100])
    families = b.multiselect('Familles', sorted(data.family.unique().tolist()), default=sorted(data.family.unique().tolist()))
    choices = data[data.n.isin(sizes) & data.family.isin(families)]['instance'].tolist()
    all_instances = st.checkbox('Toutes les instances du filtre')
    selected = choices if all_instances else st.multiselect('Instances à résoudre', choices,
                                                           default=[x for x in ['C101'] if x in choices])
    with st.form('campaign_form'):
        name = st.text_input('Nom de l’expérience', 'Ma campagne CVRPTW')
        a, b, c = st.columns(3)
        seconds = a.number_input('Secondes ALNS par run', min_value=.1, max_value=3600., value=5., step=1.)
        repetitions = b.number_input('Répétitions par instance et configuration', min_value=1, max_value=1000, value=3)
        first_seed = c.number_input('Première graine', min_value=0, max_value=2147482647, value=11)
        custom = st.text_input('Graines manuelles (facultatif)', placeholder='11, 22, 33')
        profiles = st.multiselect('Configurations à comparer', list(PROFILES), default=['ALNS complet'])
        polish = st.number_input('Secondes supplémentaires de décomposition par run (0 = désactivée)',
                                 min_value=0., max_value=3600., value=0., step=1.)
        st.caption('Sans adaptation / sans recherche locale / sans recuit : ablations de notre moteur. '
                   'La décomposition est une phase distincte utilisant son propre ALNS complet, '
                   'identique pour toutes les configurations sélectionnées.')
        submitted = st.form_submit_button('Lancer la campagne', type='primary')
    try:
        seeds = [int(s.strip()) for s in custom.split(',') if s.strip()] if custom.strip() else list(range(int(first_seed), int(first_seed + repetitions)))
        protocol = make_protocol(selected, seeds, seconds, profiles, polish, name)
        st.info(f"{protocol['total']} runs = {len(selected)} instances × {len(seeds)} graines × {len(profiles)} configurations. "
                f"Budget nominal séquentiel : {protocol['nominal_search_seconds']/60:.1f} min, hors chargement et compilation.")
        if len(profiles) > 1:
            st.caption('Comparaison sur les mêmes instances, graines et budgets. Les runs sont exécutés séquentiellement.')
        if submitted:
            active = [x for x in list_campaigns() if progress(x)['status'] in {'queued', 'warming', 'running'}]
            if active:
                st.error('Une campagne tourne déjà. Attends sa fin ou demande son arrêt dans « Mes campagnes ».')
                return
            identifier = create_campaign(protocol)
            launch(identifier)
            st.session_state['campaign_id'] = identifier
            st.success('Campagne lancée. Ouvre « Mes campagnes » pour suivre les résultats.')
    except ValueError as exc:
        st.warning(str(exc))


def run_details(items, key):
    st.subheader('Explorer un run')
    labels = {f"#{x['job']['id']} · {x['job']['instance']} · graine {x['job']['seed']} · {x['job']['profile']}": x for x in items}
    label = st.selectbox('Run à visualiser', list(labels), key=key + '_detail')
    item = labels[label]
    result = item['result']
    st.download_button('Télécharger le résultat complet · JSON', json.dumps(item, ensure_ascii=False, indent=2),
                       file_name=f"run_{item['job']['id']}.json", mime='application/json', key=key + '_json')
    if not item['valid']:
        st.error(result.get('reason', result['status']))
        return
    from algo.data import load
    from algo.verify import verify
    ins = load(ROOT / 'data/instances' / (item['job']['instance'] + '.vrp'))
    checked = verify(result['routes'], ins)
    if not checked['valid']:
        st.error('Le contrôle indépendant échoue : ' + '; '.join(checked['errors']))
        return
    st.success(f"Contrôle indépendant réussi : {ins.n} clients couverts une seule fois, capacité, horaires et flotte respectés.")
    a, b, c, d = st.columns(4)
    a.metric('Distance', f"{checked['distance']/10:.1f}")
    b.metric('BKS DIMACS', f"{item['reference_distance']:.1f}")
    c.metric('Gap BKS', f"{item['gap_pct']:.3f} %")
    d.metric('Véhicules', f"{checked['vehicles']} / {ins.vehicles} max")
    st.plotly_chart(charts.convergence(result, item['reference_distance']), width='stretch', key=key + '_trace')
    st.plotly_chart(charts.routes_map(ins, result['routes']), width='stretch', key=key + '_map')
    schedules = charts.schedule_frame(ins, checked, result['routes'])
    if not schedules.empty:
        st.plotly_chart(charts.gantt(schedules), width='stretch', key=key + '_gantt')
    with st.expander('Tournées, charges et horaires détaillés'):
        st.dataframe(pd.DataFrame([dict(vehicle=i+1, clients=' → '.join(map(str, route)), load=detail['load'],
                                         distance=detail['distance']/10, duration=detail['duration']/10,
                                         waiting=detail['waiting']/10)
                                   for i, (route, detail) in enumerate(zip(result['routes'], checked['routes']))]),
                     hide_index=True, width='stretch')
        st.dataframe(schedules, hide_index=True, width='stretch')


@st.fragment(run_every='3s')
def follow(identifier):
    folder = campaign_path(identifier)
    state = progress(identifier)
    labels = {'queued': 'En attente', 'warming': 'Compilation / préchauffage', 'running': 'En cours',
              'completed': 'Terminée', 'stopped': 'Arrêtée', 'error': 'Erreur', 'interrupted': 'Interrompue'}
    st.subheader(labels.get(state['status'], state['status']))
    st.progress(state['completed'] / max(1, state['total']), text=f"{state['completed']} / {state['total']} essais terminés")
    current = state.get('current')
    if current and state['status'] == 'running':
        st.caption(f"En cours : {current['instance']} · graine {current['seed']} · {current['profile']}. "
                   'Les graphiques sont actualisés à la fin de chaque run.')
    if state.get('error'):
        st.error(state['error'])
    if state['status'] in {'queued', 'warming', 'running'}:
        if st.button('Arrêter après le run en cours', key=identifier + '_stop'):
            stop(identifier)
        if (folder / 'STOP').exists():
            st.warning('Arrêt demandé. Le run en cours sera enregistré avant l’arrêt.')
    items = records(identifier)
    df = frame(items)
    display_metrics(df, state['total'])
    analysis(df, identifier)
    if items:
        run_details(items, identifier)
    with st.expander('Protocole et journal de calcul'):
        st.json(read_json(folder / 'protocol.json'), expanded=False)
        if (folder / 'worker.log').exists():
            st.code((folder / 'worker.log').read_text(encoding='utf-8', errors='replace')[-10000:] or 'Aucune erreur enregistrée.')


def campaigns():
    st.title('Mes campagnes')
    ids = list_campaigns()
    if not ids:
        st.info('Crée ta première expérience dans « Nouvelle expérience ».')
        return
    selected = st.session_state.get('campaign_id', ids[0])
    identifier = st.selectbox('Campagne', ids, index=ids.index(selected) if selected in ids else 0,
                              format_func=lambda x: read_json(campaign_path(x) / 'protocol.json')['name'] + ' · ' + x)
    st.session_state['campaign_id'] = identifier
    follow(identifier)


def history():
    st.title('Résultats historiques')
    source = st.selectbox('Campagne publiée', ['Extension · 1 000 runs', 'Étude principale · 80 runs'])
    data = historical(source)
    sizes = st.multiselect('Tailles à afficher', sorted(data.n.unique().tolist()), default=sorted(data.n.unique().tolist()))
    choices = sorted(data[data.n.isin(sizes)].instance.unique())
    names = st.multiselect('Instances (vide = toutes les instances des tailles choisies)', choices)
    filtered = data[data.n.isin(sizes)]
    if names:
        filtered = filtered[filtered.instance.isin(names)]
    st.caption('Les filtres changent le périmètre des statistiques affichées. Les deux campagnes restent séparées.')
    display_metrics(filtered)
    analysis(filtered, 'historical')


if page == 'Nouvelle expérience':
    new_experiment()
elif page == 'Mes campagnes':
    campaigns()
elif page == 'Résultats historiques':
    history()
else:
    st.title('Le laboratoire CVRPTW')
    st.write('Lance tes propres expériences, vérifie les solutions et explore leurs résultats.')
    st.subheader('Campagne de couverture · 356 instances')
    display_metrics(historical('Extension · 1 000 runs'))
    st.info('Ces chiffres proviennent de la campagne historique de 1 000 runs. '
            'Tes nouvelles expériences sont enregistrées séparément dans « Mes campagnes ».')
    a, b, c = st.columns(3)
    a.markdown('### 01 · Configurer\nChoisis des instances de 100 à 1 000 clients, tes graines et ton budget de recherche.')
    b.markdown('### 02 · Exécuter\nLe moteur ALNS calcule et le vérificateur contrôle chaque solution avant tout gap.')
    c.markdown('### 03 · Comprendre\nCompare les statistiques, explore les tournées et exporte les tableaux et résultats bruts.')
    st.subheader('Comment lire le gap ?')
    st.latex(r'\mathrm{gap}(\%) = 100\,\frac{D_{\mathrm{solution}}-D_{\mathrm{BKS}}}{D_{\mathrm{BKS}}}')
    st.write('Un gap de 2 % signifie une distance 2 % au-dessus de la meilleure référence publiée dans notre jeu figé. '
             'La flotte est un maximum autorisé, pas un objectif prioritaire. '
             'Les résultats ne se comparent pas directement aux références SINTEF à conventions différentes.')
