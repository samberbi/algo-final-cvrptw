"""Interface de la version en durée ; les références ne sont pas des optimums temps."""
from pathlib import Path
import json
import pandas as pd
import plotly.express as px
import streamlit as st
import streamlit.components.v1 as components
from algo.data import load
from algo.verify import verify
from web import charts
from web.simulation import timeline, simulation_html
from web.constraint_views import audit_frames
from web.experiments import ROOT, PROFILES, catalog, make_protocol, create_campaign, launch, list_campaigns, records, progress, stop, read_json, campaign_path


def show_record(item):
    result=item['result'];name=item.get('instance') or item['job']['instance']
    if not item.get('valid'):
        st.error(result.get('reason',item.get('error','Essai non réalisable')));return
    ins=load(ROOT/'data/instances'/(name+'.vrp'));checked=verify(result['routes'],ins)
    cols=st.columns(4)
    for col,label,value in zip(cols,['Clients','Durée cumulée (u.t.)','Attente (u.t.)','Calcul (s)'],
                               [str(ins.n),f"{checked['duration']/10:.2f}",f"{checked['waiting']/10:.2f}",f"{result['runtime_s']:.2f}"]):
        col.metric(label,value)
    st.caption('Départ à zéro ; durée = trajets + attentes + services. Le temps de calcul est mesuré séparément en secondes.')
    ref=item['reference_duration']
    st.write(f"Plan témoin : {ref:.2f} u.t. ; écart relatif : {100*(result['cost']/ref-1):+.3f} %. Ce témoin est issu d’une BKS distance, réévaluée en durée ; son optimalité en temps n’est pas établie.")
    tabs=st.tabs(['Simulation','Tournées','Horaires','Vérifier toutes les contraintes','Convergence'])
    data=timeline(ins,result['routes'])
    with tabs[0]:components.html(simulation_html(data),height=800,scrolling=True)
    with tabs[1]:st.plotly_chart(charts.routes_map(ins,result['routes']),width='stretch')
    with tabs[2]:st.plotly_chart(charts.gantt(charts.schedule_frame(ins,checked,result['routes'])),width='stretch')
    with tabs[3]:
        clients,routes=audit_frames(data)
        st.success('Solution contrôlée : couverture, capacité, fenêtres et retour au dépôt.')
        st.dataframe(clients,width='stretch');st.dataframe(routes,width='stretch')
    with tabs[4]:st.plotly_chart(charts.convergence(result,ref),width='stretch')


def simulation():
    st.title('CVRPTW — simulation des solutions en durée')
    source=st.radio('Source',['Catalogue en durée','Mes campagnes'])
    if source=='Catalogue en durée':
        paths=sorted((ROOT/'results/time_objective/catalogue/runs').glob('*.json'))
        names=sorted({p.stem.rsplit('_',2)[0] for p in paths})
        if not names:st.info('Aucun essai enregistré. Lancer une expérience.');return
        name=st.selectbox('Instance',names)
        selected=[p for p in paths if p.stem.rsplit('_',2)[0]==name]
        path=st.selectbox('Exécution',selected,format_func=lambda p:p.stem)
        show_record(read_json(path))
    else:
        ids=[i for i in list_campaigns() if read_json(campaign_path(i)/'protocol.json')['objective']=='duration']
        if not ids:st.info('Aucune campagne en durée.');return
        identifier=st.selectbox('Campagne',ids)
        items=records(identifier)
        if items:show_record(st.selectbox('Exécution',items,format_func=lambda r:f"{r['job']['instance']} / {r['job']['seed']} / {r['job']['profile']}"))


def follow(identifier):
    state=progress(identifier)
    st.subheader(f"{state['status']} — {state['completed']}/{state['total']}")
    if state['status'] in ('queued','warming','running'):
        if st.button('Arrêter après cet essai'):stop(identifier)
    st.button('Actualiser')
    rows=[]
    for r in records(identifier):
        result=r['result']
        rows.append(dict(instance=r['job']['instance'],graine=r['job']['seed'],méthode=r['job']['profile'],
                         réalisable=r['valid'],durée=result.get('cost'),référence=r['reference_duration'],
                         écart_pct=r.get('delta_reference_pct'),calcul_s=result['runtime_s']))
    if rows:
        df=pd.DataFrame(rows);st.dataframe(df,width='stretch')
        st.download_button('Résultats CSV',df.to_csv(index=False).encode('utf-8-sig'),'resultats_duree.csv')
        st.plotly_chart(px.box(df,x='méthode',y='durée',points='all',title='Durées des essais terminés — u.t.'),width='stretch')


def new_experiment():
    st.title('Lancer des résolutions en durée')
    available=catalog()['instance'].tolist()
    with st.form('duration_campaign'):
        names=st.multiselect('Instances',available,default=['C101'])
        seconds=st.number_input('Budget de recherche par essai (secondes)',min_value=.05,max_value=3600.,value=10.)
        seeds_text=st.text_input('Graines, séparées par des virgules','4101,4102')
        labels=[p for p in PROFILES if PROFILES[p]['method'].startswith('duration_')]
        profiles=st.multiselect('Méthodes',labels,default=['ILS durée + HGS'])
        submitted=st.form_submit_button('Lancer la campagne')
    if submitted:
        try:
            seeds=[int(s.strip()) for s in seeds_text.split(',')]
            protocol=make_protocol(names,seeds,seconds,profiles,name='CVRPTW en durée')
            identifier=create_campaign(protocol);launch(identifier)
            st.session_state['duration_campaign']=identifier
        except (ValueError,OSError) as error:st.error(str(error))
    if 'duration_campaign' in st.session_state:follow(st.session_state['duration_campaign'])


def campaigns():
    st.title('Mes campagnes en durée')
    ids=[i for i in list_campaigns() if read_json(campaign_path(i)/'protocol.json')['objective']=='duration']
    if not ids:st.info('Aucune campagne en durée enregistrée.');return
    follow(st.selectbox('Campagne',ids))


def statistics():
    st.title('Statistiques descriptives — objectif durée')
    folder=ROOT/'results/time_objective/catalogue'
    if not (folder/'core.csv').exists():st.info('Le tableau sera disponible après l’analyse de la campagne.');return
    core=pd.read_csv(folder/'core.csv');cases=pd.read_csv(folder/'instances.csv')
    st.write('Chaque ligne du bilan par instance est la moyenne de ses graines disponibles. Les répétitions ciblées sont analysées séparément.')
    st.dataframe(pd.read_csv(folder/'sizes.csv'),width='stretch')
    st.plotly_chart(px.box(cases,x='n',y='mean_duration',points='all',title='Durée cumulée par instance, par taille — u.t.'),width='stretch')
    st.plotly_chart(px.histogram(cases,x='mean_delta_reference_pct',nbins=25,title='Écarts au plan témoin réévalué en durée — pas des gaps à un optimum temps'),width='stretch')
    st.dataframe(cases,width='stretch')
    st.download_button('Toutes les instances — CSV',cases.to_csv(index=False).encode('utf-8-sig'),'instances_duree.csv')


def render():
    st.set_page_config(page_title='CVRPTW — durée totale',page_icon='🚚',layout='wide')
    st.sidebar.title('CVRPTW — durée totale')
    page=st.sidebar.radio('Navigation',['Simulation','Nouvelle expérience','Mes campagnes','Statistiques du catalogue'])
    st.sidebar.caption('Objectif : somme des durées des tournées, avec attentes et services. Départs à zéro, fenêtres strictes.')
    st.sidebar.caption('Les références distance sont réévaluées en durée ; leur optimalité temporelle n’est pas établie.')
    {'Simulation':simulation,'Nouvelle expérience':new_experiment,'Mes campagnes':campaigns,'Statistiques du catalogue':statistics}[page]()
