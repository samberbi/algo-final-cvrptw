"""Explain and expose the numerical evidence behind a verified simulation."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from web import charts


def audit_frames(data):
    clients, vehicles = [], []
    for v in data['vehicles']:
        load = v['load']
        for s in v['stops']:
            load -= s['demand']
            clients.append(dict(camion=v['id'], client=s['client'], demande=s['demand'],
                                ouverture=s['early'], fermeture=s['late'], arrivee=s['arrival'],
                                debut=s['start'], fin=s['finish'], attente=s['start']-s['arrival'],
                                marge_fenetre=s['late']-s['start'],
                                fenetre_respectee=s['early']-1e-8 <= s['start'] <= s['late']+1e-8,
                                charge_apres_service=max(0., load)))
        vehicles.append(dict(camion=v['id'], clients=len(v['stops']), charge_depart=v['load'],
                             capacite=data['capacity'], capacite_respectee=v['load'] <= data['capacity']+1e-8,
                             retour=v['end'], fermeture_depot=data['horizon'],
                             marge_retour=data['horizon']-v['end'],
                             retour_respecte=v['end'] <= data['horizon']+1e-8,
                             trajet=sum(s['end']-s['start'] for s in v['segments'] if s['kind']=='Trajet'),
                             attente=v['waiting'],
                             service=sum(s['finish']-s['start'] for s in v['stops'])))
    return pd.DataFrame(clients), pd.DataFrame(vehicles)


def controls(data):
    clients, vehicles = audit_frames(data)
    st.subheader('Preuves numériques sur la tournée complète')
    st.caption('Ces contrôles portent sur le plan complet. Les valeurs « réalisé » dans l’animation suivent son horloge. '
               'Un client est livré à la fin du service ; sa fenêtre porte sur le début du service.')
    coverage = len(clients) == data['clients'] and clients.client.nunique() == data['clients']
    checks = pd.DataFrame([
        dict(contrainte='Tous les clients, exactement une fois', mesure=f"{clients.client.nunique()} / {data['clients']}", respecte=coverage),
        dict(contrainte='Débuts de service dans les fenêtres', mesure=f"{int(clients.fenetre_respectee.sum())} / {len(clients)}", respecte=bool(clients.fenetre_respectee.all())),
        dict(contrainte='Charge de départ ≤ capacité', mesure=f"Maximum {vehicles.charge_depart.max():g} / {data['capacity']:g}", respecte=bool(vehicles.capacite_respectee.all())),
        dict(contrainte='Retour avant fermeture du dépôt', mesure=f"Dernier retour {data['end']:.1f} / {data['horizon']:.1f}", respecte=bool(vehicles.retour_respecte.all())),
        dict(contrainte='Nombre de camions ≤ flotte disponible', mesure=f"{len(vehicles)} / {data['fleet']}", respecte=len(vehicles)<=data['fleet']),
    ])
    if checks.respecte.all():
        st.success('Les cinq contrôles sont satisfaits. La solution a aussi été recalculée par le vérificateur indépendant avant affichage.')
    else:
        st.error('Au moins une contrainte est violée.')
    st.dataframe(checks, hide_index=True, width='stretch')
    st.write('**Charges, retours et marges de chaque camion**')
    st.dataframe(vehicles, hide_index=True, width='stretch')
    st.write('**Fenêtres et horaires de chaque client**')
    st.caption('Une marge de fenêtre faible signifie que le service commence près de la fermeture. '
               'Elle ne représente pas toute la marge disponible sur la suite de la tournée.')
    st.dataframe(clients, hide_index=True, width='stretch')
    st.download_button('Exporter le contrôle des clients · JSON', clients.to_json(orient='records', force_ascii=False, indent=2),
                       file_name=data['name']+'_controle_clients.json', mime='application/json', key='audit_clients')


def graphs(ins, data, result, reference):
    clients, vehicles = audit_frames(data)
    st.subheader('Lire les contraintes sur les graphiques')
    selected = st.selectbox('Camion pour les graphiques détaillés', [v['id'] for v in data['vehicles']])
    v = data['vehicles'][selected-1]
    subset = clients[clients.camion.eq(selected)]
    windows = go.Figure()
    for s in v['stops']:
        label = str(s['client'])
        windows.add_scatter(x=[s['early'], s['late']], y=[label, label], mode='lines',
                            line=dict(color='#cbd5e1', width=12), showlegend=False,
                            hovertemplate=f"Client {label} · fenêtre [{s['early']:.1f} ; {s['late']:.1f}]<extra></extra>")
    for col, label, color, symbol in [('arrivee', 'Arrivée', '#d99526', 'diamond'), ('debut', 'Début du service', '#087e8b', 'circle')]:
        windows.add_scatter(x=subset[col], y=subset.client.astype(str), mode='markers', name=label,
                            marker=dict(color=color, size=9, symbol=symbol))
    windows.update_layout(height=max(330, min(1200, len(subset)*25)))
    st.plotly_chart(charts.finish(windows, 'Fenêtres horaires et débuts de service', 'Temps du benchmark', 'Client'), width='stretch')
    st.info('Le point de début du service doit rester dans la barre grise. Le point d’arrivée peut être à gauche : '
            'le camion attend alors l’ouverture. La contrainte concerne le début, pas la fin du service.')
    remaining = v['load']
    times, loads = [0.], [remaining]
    for s in v['stops']:
        remaining -= s['demand']
        times.append(s['finish']); loads.append(max(0., remaining))
    times.append(v['end']); loads.append(max(0., remaining))
    capacity = go.Figure(go.Scatter(x=times, y=loads, mode='lines+markers', line=dict(shape='hv', color='#087e8b'), name='Charge restante'))
    capacity.add_hline(y=data['capacity'], line_color='#b45309', line_dash='dash', annotation_text='Capacité maximale')
    capacity.update_yaxes(range=[0, data['capacity']*1.12])
    st.plotly_chart(charts.finish(capacity, 'Charge du camion au fil des livraisons', 'Temps du benchmark', 'Quantité à bord'), width='stretch')
    st.caption('La charge est maximale au départ et diminue à la fin de chaque service. Elle doit rester entre zéro et la capacité.')
    returns = go.Figure(go.Bar(x=vehicles.camion.astype(str), y=vehicles.retour, name='Retour au dépôt', marker_color='#087e8b'))
    returns.add_hline(y=data['horizon'], line_color='#b45309', line_dash='dash', annotation_text='Fermeture du dépôt')
    st.plotly_chart(charts.finish(returns, 'Retour au dépôt de tous les camions', 'Camion', 'Temps de retour'), width='stretch')
    duration = go.Figure()
    for col, label, color in [('trajet','Trajet','#64748b'), ('attente','Attente','#f59e0b'), ('service','Service','#0f766e')]:
        duration.add_bar(x=vehicles.camion.astype(str), y=vehicles[col], name=label, marker_color=color)
    duration.update_layout(barmode='stack')
    st.plotly_chart(charts.finish(duration, 'Pourquoi une tournée dure-t-elle ce temps ?', 'Camion', 'Durée'), width='stretch')
    st.caption('Trajets + attentes + services = durée de la tournée, avec départ commun à zéro. La somme des durées diffère de l’heure du dernier retour.')
    st.plotly_chart(charts.convergence(result, reference), width='stretch')
    st.caption('La convergence représente le calcul de la solution avant son animation. Un plateau ne prouve pas l’optimalité. '
               'La référence est une meilleure solution connue en distance.')


def method(root):
    st.subheader('Relier la simulation aux méthodes ILS et recuit')
    st.write('Le solveur calcule d’abord des tournées. La simulation rejoue ensuite leurs horaires vérifiés. '
             'Les mouvements des camions ne représentent pas les itérations de l’optimisation.')
    for filename, caption in [
        ('representation.png', 'Données → tournées → évaluation : l’ordre des clients détermine les horaires calculés.'),
        ('schedule.png', 'Arrivée, attente et service : arriver tôt est permis, commencer avant l’ouverture ne l’est pas.'),
        ('ils.png', 'ILS : construire une fois, perturber, améliorer localement, décider ; conserver le meilleur résultat.'),
        ('sa.png', 'Recuit : proposer un mouvement direct, contrôler sa faisabilité, puis décider de son acceptation.'),
        ('moves.png', 'Recherche locale : déplacements, échanges et échanges de fins de tournées, sous contraintes.'),
        ('temperature.png', 'Recuit : la diminution de température rend les hausses de distance moins probables. Les contraintes restent obligatoires.'),
    ]:
        with st.expander(caption):
            path = root/'livraison/ils_figures'/filename
            if path.exists():
                st.image(str(path), width='stretch')
            else:
                st.info('Schéma en cours de préparation pour la nouvelle édition.')
    st.info('Pour les distributions, moyennes, écarts-types, seuils et comparaisons entre instances, '
            'ouvrir « Résultats historiques ». Pour de nouveaux essais et des ablations, ouvrir « Nouvelle expérience ».')
