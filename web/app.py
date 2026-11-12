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
page = st.sidebar.radio('Navigation', ['Simulation', 'Vue d’ensemble', 'Nouvelle expérience', 'Mes campagnes', 'Résultats historiques'])
st.sidebar.divider()
st.sidebar.write('**Objectif : distance minimale**')
st.sidebar.caption('Référence DIMACS · fenêtres strictes · capacité et flotte maximale respectées')
st.sidebar.caption('Les calculs tournent sur cet ordinateur. Les campagnes continuent si la page est fermée.')


def historical(source):
    if source.startswith('Catalogue complet'):
        data=pd.read_csv(ROOT/'results/catalog_v8/flat.csv')
        data=data.rename(columns={'total_s':'runtime_s','bks':'reference_distance'})
        data['profile']='ILS + HGS (PyVRP)'
        data['status']=data.valid.map({True:'feasible',False:'error'})
        return data
    if source.startswith('Optimisation v6'):
        data=pd.read_csv(ROOT/'results/optimization_v6/validation/flat.csv')
        data['profile']=data['profile'].replace({'baseline':'ILS de référence','combined':'Cache et groupes temporels'})
        return data
    if source.startswith('Optimisation v5'):
        return pd.read_csv(ROOT/'results/optimization_v5/validation/flat.csv')
    if source.startswith('Optimisation v2'):
        path=ROOT/'results/optimization_v2/validation/flat.csv'
        data=pd.read_csv(path)
        data['profile']=data['profile'].replace({'optimized_ils':'ILS optimisée','optimized_sa':'Recuit décomposé'})
        return data
    if source.startswith('ILS / recuit'):
        path = ROOT / 'results/revision_ils/flat.json'
        return pd.read_json(path) if path.exists() else pd.DataFrame()
    return pd.DataFrame()


def display_metrics(df, expected=None):
    if df.empty:
        st.info('Aucun essai terminé pour le moment.')
        return
    valid = df['valid'].astype(bool)
    gaps = df.loc[valid, 'gap_pct'].dropna()
    cols = st.columns(6)
    cols[0].metric('Essais terminés', f'{len(df)}' + (f' / {expected}' if expected else ''))
    cols[1].metric('Réalisables', f'{int(valid.sum())} / {len(df)}')
    cols[2].metric('Gap moyen', f'{gaps.mean():.3f} %' if len(gaps) else '—')
    cols[3].metric('Sous 5 %', f'{int((valid & df.gap_pct.lt(5)).sum())} / {len(df)}')
    cols[4].metric('Sous 6 %', f'{int((valid & df.gap_pct.lt(6)).sum())} / {len(df)}')
    cols[5].metric('Sous 7 %', f'{int((valid & df.gap_pct.lt(7)).sum())} / {len(df)}')
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
        seconds = a.number_input('Secondes de recherche par run', min_value=.1, max_value=3600., value=5., step=1.)
        repetitions = b.number_input('Répétitions par instance et configuration', min_value=1, max_value=1000, value=3)
        first_seed = c.number_input('Première graine', min_value=0, max_value=2147482647, value=11)
        custom = st.text_input('Graines manuelles (facultatif)', placeholder='11, 22, 33')
        profiles = st.multiselect('Configurations à comparer', list(PROFILES), default=['ILS'])
        st.caption('ILS court + HGS (v9) : à 120 s, partage 20 s / 100 s ; '
                   'contrôlé sur les cas difficiles, avec convergence enregistrée. Les temps de préparation s’ajoutent au budget de recherche.')
        st.caption('ILS + HGS (PyVRP) : notre ILS puis un moteur externe attribué à PyVRP. '
                   'Le budget est partagé entre les deux recherches ; construction et préparation sont comptées dans le temps réel en supplément.')
        polish = st.number_input('Secondes supplémentaires de décomposition par run (0 = désactivée)',
                                 min_value=0., max_value=3600., value=0., step=1.)
        st.caption('ILS : perturbation et recherche locale. Recuit : mouvements directs et refroidissement. '
                   'ILS-RVND : mouvements complets, échanges de blocs et perturbations variables. '
                   'ILS-SP : archive de tournées réalisables et partitionnement ; variante expérimentale. '
                   'La décomposition facultative ajoute une phase ILS et un budget distinct ; '
                   'elle est désactivée dans le benchmark principal publié.')
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
    with st.expander('Simuler cette tournée · camions animés'):
        from web.simulation import timeline, simulation_html
        import streamlit.components.v1 as components
        components.html(simulation_html(timeline(ins, result['routes'])), height=850, scrolling=True)
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
    sources=[]
    if (ROOT/'results/optimization_v2/validation/flat.csv').exists():sources.append('Optimisation v2 · 360 trajectoires équilibrées')
    if (ROOT/'results/optimization_v5/validation/flat.csv').exists():sources.append('Optimisation v5 · comparaison appariée à 1 000 clients')
    if (ROOT/'results/optimization_v6/validation/flat.csv').exists():sources.append('Optimisation v6 · confirmation à 1 000 clients')
    if (ROOT/'results/catalog_v8/analysis.json').exists() and read_json(ROOT/'results/catalog_v8/analysis.json').get('complete'):
        sources.append('Catalogue complet v8 · 356 instances, 472 pipelines')
    source = st.selectbox('Campagne publiée', sources,index=len(sources)-1)
    data = historical(source)
    if data.empty:
        st.info('La synthèse de la nouvelle campagne sera disponible à la fin du calcul. Les runs terminés sont déjà simulables.')
        return
    sizes = st.multiselect('Tailles à afficher', sorted(data.n.unique().tolist()), default=sorted(data.n.unique().tolist()))
    choices = sorted(data[data.n.isin(sizes)].instance.unique())
    names = st.multiselect('Instances (vide = toutes les instances des tailles choisies)', choices)
    filtered = data[data.n.isin(sizes)]
    if names:
        filtered = filtered[filtered.instance.isin(names)]
    methods=st.multiselect('Méthodes à afficher',sorted(filtered.profile.unique()),default=sorted(filtered.profile.unique()))
    filtered=filtered[filtered.profile.isin(methods)]
    if source.startswith('Catalogue complet') and len(filtered):
        macro=filtered[filtered.valid].groupby('instance').gap_pct.mean()
        st.info(f'Moyenne donnant le même poids à chaque instance : {macro.mean():.3f} % '
                f'sur {len(macro)} instances représentées. Les métriques suivantes donnent le même poids à chaque essai. '
                'Les tailles 100/1 000 ont deux graines ; les tailles intermédiaires une seule.')
    st.caption('Les filtres changent le périmètre des statistiques affichées. Les deux campagnes restent séparées.')
    display_metrics(filtered)
    analysis(filtered, 'historical')


def simulation_page():
    import streamlit.components.v1 as components
    from algo.data import load
    from web.simulation import timeline, simulation_html

    st.title('Simulation des livraisons')
    st.write('Suis les camions sur leurs tournées : déplacements, attente avant ouverture, service et retour au dépôt.')
    sources=['Mes campagnes']
    if (ROOT/'results/optimization_v2/validation/analysis.json').exists():sources.insert(0,'Optimisation v2')
    if (ROOT/'results/optimization_v5/validation/flat.csv').exists():sources.insert(0,'Optimisation v5')
    if (ROOT/'results/optimization_v6/validation/flat.csv').exists():sources.insert(0,'Optimisation v6')
    if (ROOT/'results/optimization_v6/updated_archive/analysis.json').exists():sources.insert(0,'Archive consolidée v6')
    if (ROOT/'results/catalog_v8/analysis.json').exists() and read_json(ROOT/'results/catalog_v8/analysis.json').get('complete'):
        sources.insert(0,'Catalogue complet v8')
    source = st.radio('Solution à simuler', sources, horizontal=True)
    if source == 'Mes campagnes':
        ids = list_campaigns()
        if not ids:
            st.info('Aucune campagne locale. La simulation est déjà disponible avec les résultats de l’étude principale.')
            return
        identifier = st.selectbox('Campagne à simuler', ids,
                                  format_func=lambda x: read_json(campaign_path(x) / 'protocol.json')['name'] + ' · ' + x)
        candidates = [dict(name=x['job']['instance'], seed=x['job']['seed'],
                           profile=x['job']['profile'], routes=x['result']['routes'],
                           id=x['job']['id'], result=x['result'], reference=x['reference_distance'])
                      for x in records(identifier) if x.get('valid')]
    elif source=='Catalogue complet v8':
        flat=pd.read_csv(ROOT/'results/catalog_v8/flat.csv')
        candidates=[dict(name=row.instance,seed=int(row.seed),profile='ILS + HGS (PyVRP)',
                         id=index,catalog_path=row.source)
                    for index,row in flat[flat.valid].iterrows()]
    elif source=='Optimisation v2':
        candidates=[]
        for path in sorted((ROOT/'results/optimization_v2/validation/runs').glob('*.json')):
            item=read_json(path)
            if item.get('valid'):
                candidates.append(dict(name=item['job']['instance'],seed=item['job']['seed'],
                    profile=item['job']['variant'],routes=item['result']['routes'],id=item['job']['id'],
                    result=item['result'],reference=item['reference_distance']))
    elif source in ('Optimisation v6','Archive consolidée v6'):
        candidates=[]
        refs={r['instance']:r['reference_distance'] for r in read_json(ROOT/'data/manifest.json')['reference_instances']}
        folder=ROOT/('results/optimization_v6/validation/runs' if source=='Optimisation v6' else 'results/optimization_v6/updated_archive')
        for index,path in enumerate(sorted(folder.glob('*_*.json'))):
            stored=read_json(path)
            result=stored.get('result')
            if result and result.get('status')=='feasible':
                candidates.append(dict(name=stored['instance'],seed='multiples' if source=='Archive consolidée v6' else stored['seed'],
                    profile=stored.get('variant','Archive consolidée'),routes=result['routes'],id=index,
                    result=result,reference=refs[stored['instance']],effort_s=stored.get('total_effort_s')))
    elif source == 'Optimisation v5':
        candidates = []
        for index, path in enumerate(sorted((ROOT/'results/optimization_v5/validation/runs').glob('*.json'))):
            item = read_json(path)
            if item.get('valid'):
                candidates.append(dict(name=item['instance'],seed=item['seed'],
                    profile=item['variant'],routes=item['result']['routes'],id=index,
                    result=item['result'],reference=item['result']['cost']/(1+item['gap_pct']/100)))
    else:
        candidates = []
    if not candidates:
        st.info('Aucune solution réalisable terminée à simuler dans cette campagne.')
        return
    left, right = st.columns(2)
    name = left.selectbox('Instance à simuler', sorted({c['name'] for c in candidates}))
    choices = [c for c in candidates if c['name'] == name]
    selected = right.selectbox('Run à simuler', range(len(choices)),
                               format_func=lambda i: f"Graine {choices[i]['seed']} · {choices[i]['profile']} · #{choices[i]['id']}")
    item = choices[selected]
    if 'catalog_path' in item:
        stored=read_json(ROOT/item['catalog_path'])
        item=dict(item,routes=stored['result']['routes'],result=stored['result'],
                  reference=stored['reference_distance'])
    if item.get('effort_s') is not None:
        st.caption(f"Archive de plusieurs recherches : effort cumulé {item['effort_s']:.1f} secondes pour cette instance. Ce n’est pas une résolution indépendante à budget court.")
    if 'file' in item:
        stored = read_json(ROOT/'results/revision_ils/runs'/item['file'])
        item = dict(item, routes=stored['result']['routes'], result=stored['result'],
                    reference=stored['reference_distance'])
    ins = load(ROOT / 'data/instances' / (name + '.vrp'))
    try:
        data = timeline(ins, item['routes'])
    except ValueError as exc:
        st.error(str(exc))
        return
    a, b, c = st.columns(3)
    a.metric('Clients', data['clients'])
    b.metric('Camions', len(data['vehicles']))
    c.metric('Distance de la solution', f"{data['distance']:.1f}")
    from web.constraint_views import controls, graphs, method
    animation, audit, figures, explanation = st.tabs(['Simulation et contrôles en direct', 'Vérifier toutes les contraintes',
                                                      'Graphiques du run', 'Schémas et méthode'])
    with animation:
        components.html(simulation_html(data), height=1150, scrolling=True)
        st.caption('La simulation rejoue une solution vérifiée : elle ne relance pas l’optimisation. '
                   'Les temps sont ceux du benchmark ; les trajets relient ses coordonnées, sans trafic variable.')
    with audit:
        controls(data)
    with figures:
        graphs(ins, data, item['result'], item['reference'])
    with explanation:
        method(ROOT)


if page == 'Simulation':
    simulation_page()
elif page == 'Nouvelle expérience':
    new_experiment()
elif page == 'Mes campagnes':
    campaigns()
elif page == 'Résultats historiques':
    history()
else:
    st.title('Le laboratoire CVRPTW')
    st.write('Lance tes propres expériences, vérifie les solutions et explore leurs résultats.')
    optimized=(ROOT/'results/optimization_v2/validation/flat.csv').exists()
    st.subheader('Validation équilibrée · 36 instances · cinq graines' if optimized else 'ILS contre recuit · 28 instances · 20 graines')
    if optimized:
        current=historical('Optimisation v2')
        chosen=st.radio('Méthode de la synthèse',['ILS optimisée','Recuit décomposé'],horizontal=True)
        display_metrics(current[current.profile.eq(chosen)],180)
        st.info('Douze instances par taille : 100, 200 et 1 000 clients. Chaque taille pèse un tiers dans cette moyenne. '
                'Aux grandes tailles : 25 + 15 secondes, construction séparée ; les résultats historiques restent disponibles.')
    else:
        display_metrics(historical('ILS / recuit · 1 120 runs'), 1120)
        st.info('Étude initiale ILS/recuit ; les campagnes historiques restent disponibles.')
    images=[('v2_convergence.png','Validation v2 : douze grandes instances, cinq graines par méthode ; continuation prévue à 25 secondes.'),
            ('v2_regression.png','Avant/après à budget égal sur C204 et R1_10_1, vingt graines chacun.'),
            ('v2_development.png','Calibration séparée sur les six familles à 1 000 clients.')] if optimized else [('convergence_100.png', 'À 100 clients : gap moyen au fil du calcul ; bande interquartile, pas un intervalle de confiance.'),
                              ('convergence_1000.png', 'À 1 000 clients : même lecture, avec un budget de 25 secondes.'),
                              ('sensitivity.png', 'Sensibilité exploratoire : six instances de développement et trois graines par variante.')]
    for filename,caption in images:
        path = ROOT / ('livraison/optimization_figures' if optimized else 'livraison/ils_figures') / filename
        if path.exists():
            st.image(str(path), width='stretch')
            st.caption(caption)
    a, b, c = st.columns(3)
    a.markdown('### 01 · Configurer\nChoisis des instances de 100 à 1 000 clients, tes graines et ton budget de recherche.')
    b.markdown('### 02 · Exécuter\nLe moteur ILS ou recuit calcule et le vérificateur contrôle chaque solution avant tout gap.')
    c.markdown('### 03 · Comprendre\nCompare les statistiques, explore les tournées et exporte les tableaux et résultats bruts.')
    st.subheader('Comment lire le gap ?')
    st.latex(r'\mathrm{gap}(\%) = 100\,\frac{D_{\mathrm{solution}}-D_{\mathrm{BKS}}}{D_{\mathrm{BKS}}}')
    st.write('Un gap de 2 % signifie une distance 2 % au-dessus de la meilleure référence publiée dans notre jeu figé. '
             'La flotte est un maximum autorisé, pas un objectif prioritaire. '
             'Les résultats ne se comparent pas directement aux références SINTEF à conventions différentes.')
