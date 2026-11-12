"""Interactive figures in displayed DIMACS units (internal metrics / 10)."""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

COLORS = px.colors.qualitative.Safe


def finish(fig, title, x=None, y=None):
    fig.update_layout(title=title, template='plotly_white', margin=dict(l=20, r=20, t=55, b=30),
                      font=dict(family='Arial', size=13), legend_title_text='')
    if x:
        fig.update_xaxes(title=x)
    if y:
        fig.update_yaxes(title=y)
    return fig


def distribution(df, by='profile'):
    fig = px.box(df.dropna(subset=['gap_pct']), x=by, y='gap_pct', color=by,
                 points='all', hover_data=['instance', 'seed'])
    fig.add_hline(y=5, line_dash='dot', line_color='#0f766e', annotation_text='Cible 5 %')
    fig.add_hline(y=7, line_dash='dash', line_color='#b45309', annotation_text='Cible 7 %')
    return finish(fig, 'Dispersion des gaps à la BKS', 'Configuration' if by == 'profile' else 'Instance', 'Gap (%)')


def gap_bars(summary):
    fig = px.bar(summary, x='instance', y='mean_gap', color='profile', barmode='group',
                 error_y='std_gap', hover_data=['runs', 'feasible', 'best_gap', 'worst_gap'])
    fig.add_hline(y=7, line_dash='dash', line_color='#b45309')
    return finish(fig, 'Gap moyen et écart-type par instance', 'Instance', 'Gap moyen (%)')


def convergence(result, reference):
    trace = pd.DataFrame(result.get('trace', []))
    fig = go.Figure()
    if not trace.empty:
        fig.add_scatter(x=trace['elapsed_s'], y=trace['best'], mode='lines+markers', name='Meilleure distance',
                        line=dict(color='#0f766e', shape='hv'))
    fig.add_hline(y=reference, line_dash='dash', line_color='#b45309', annotation_text='BKS')
    return finish(fig, 'Convergence enregistrée du run', 'Temps de recherche (s)', 'Distance')


def routes_map(ins, routes):
    fig = go.Figure()
    for i, route in enumerate(routes):
        nodes = [0] + route + [0]
        fig.add_scattergl(x=ins.xy[nodes, 0], y=ins.xy[nodes, 1], mode='lines+markers', name=f'Véhicule {i+1}',
                          text=[f'Client {c}' if c else 'Dépôt' for c in nodes],
                          hovertemplate='%{text}<extra>%{fullData.name}</extra>',
                          line=dict(color=COLORS[i % len(COLORS)], width=1.5), marker=dict(size=5))
    fig.add_scatter(x=[ins.xy[0, 0]], y=[ins.xy[0, 1]], mode='markers', name='Dépôt',
                    marker=dict(symbol='star', size=18, color='#0f172a'))
    fig.update_yaxes(scaleanchor='x', scaleratio=1)
    return finish(fig, 'Tournées de la solution vérifiée', 'Coordonnée X', 'Coordonnée Y')


def schedule_frame(ins, checked, routes):
    rows = []
    for i, (detail, route) in enumerate(zip(checked['routes'], routes)):
        clock = 0.
        for entry in detail['schedule']:
            client = entry['client']
            for kind, start, end in [('Trajet', clock, entry['arrival']),
                                     ('Attente', entry['arrival'], entry['start']),
                                     ('Service', entry['start'], entry['finish'])]:
                if end > start:
                    rows.append(dict(vehicle=f'Véhicule {i+1}', client=client, kind=kind, start=start / 10,
                                     end=end / 10, length=(end - start) / 10))
            clock = entry['finish']
        if detail['duration'] > clock:
            rows.append(dict(vehicle=f'Véhicule {i+1}', client=0, kind='Trajet', start=clock / 10,
                             end=detail['duration'] / 10, length=(detail['duration'] - clock) / 10))
    return pd.DataFrame(rows)


def gantt(df):
    fig = go.Figure()
    for kind, color in [('Trajet', '#64748b'), ('Attente', '#f59e0b'), ('Service', '#0f766e')]:
        data = df[df['kind'] == kind]
        fig.add_bar(y=data['vehicle'], x=data['length'], base=data['start'], orientation='h', name=kind,
                    marker_color=color, customdata=data[['client', 'start', 'end']],
                    hovertemplate='Client %{customdata[0]} · %{customdata[1]:.1f} → %{customdata[2]:.1f}<extra>%{fullData.name}</extra>')
    fig.update_layout(barmode='overlay', height=max(350, min(1000, df['vehicle'].nunique() * 24)))
    return finish(fig, 'Horaires : trajets, attentes et services', 'Temps depuis le départ du dépôt', 'Véhicule')
