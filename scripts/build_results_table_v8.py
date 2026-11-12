"""Readable, searchable offline table; all cases and repetitions remain visible."""
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import pandas as pd


def main():
    base=ROOT/'results/catalog_v8'
    a=json.loads((base/'analysis.json').read_text(encoding='utf-8'))
    assert a['complete']
    cases=pd.read_csv(base/'instances.csv');runs=pd.read_csv(base/'flat.csv');sizes=pd.read_csv(base/'sizes.csv')
    assert len(cases)==356 and len(runs)==472
    def table(frame,identifier):
        return frame.to_html(index=False,table_id=identifier,escape=True,na_rep='—',
                             float_format=lambda x:f'{x:.3f}'.replace('.',','))
    summary=sizes[['n','instances','attempts','valid','mean_instance_gap','worst_run_gap','mean_total_s']].rename(columns={
        'n':'Clients','instances':'Instances','attempts':'Essais','valid':'Réalisables',
        'mean_instance_gap':'Gap moyen (%)','worst_run_gap':'Pire gap (%)','mean_total_s':'Temps réel moyen (s)'})
    columns={'instance':'Instance','n':'Clients','family':'Famille','attempts':'Essais','valid':'Réalisables',
        'mean_gap':'Gap moyen (%)','std_gap':'Écart-type entre graines','best_gap':'Meilleur gap (%)',
        'worst_gap':'Pire gap (%)','bks':'Distance BKS','mean_distance':'Distance moyenne',
        'best_distance':'Meilleure distance','mean_total_s':'Temps réel moyen (s)'}
    detail=cases.rename(columns=columns)
    cases.to_csv(ROOT/'livraison/INSTANCES_CATALOGUE_V8.csv',index=False)
    raw=runs[['instance','n','seed','bks','cost','vehicles','gap_pct','search_budget_s','total_s','valid','reused']].rename(columns={
        'instance':'Instance','n':'Clients','seed':'Graine','bks':'Distance BKS','cost':'Distance obtenue',
        'vehicles':'Véhicules','gap_pct':'Gap (%)','search_budget_s':'Budget recherche (s)',
        'total_s':'Temps réel (s)','valid':'Réalisable','reused':'Résultat réutilisé'})
    page='''<!doctype html><html lang="fr"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>CVRPTW — Tous les gaps des 356 instances</title><style>
body{font:15px/1.5 system-ui,sans-serif;background:#f4f7fb;color:#17283f;margin:0;padding:24px}
main{max-width:1600px;margin:auto}h1,h2{color:#12365a}nav a{margin-right:20px;color:#125482}
.panel{background:white;border:1px solid #d9e2ed;border-radius:12px;padding:18px;margin:20px 0}
.scroll{overflow:auto;max-height:75vh}table{border-collapse:collapse;width:100%;white-space:nowrap;font-size:13px}
th{background:#183e61;color:white;position:sticky;top:0;z-index:1}th,td{padding:9px 12px;border-bottom:1px solid #e2e8f0;text-align:right}
th:first-child,td:first-child{text-align:left}tbody tr:nth-child(even){background:#f4f7fb}
input,select{font:inherit;padding:8px;border:1px solid #bac9da;border-radius:6px;margin:5px 12px 12px 0}
.good{background:#dff3e8!important;color:#105d3b}.high{background:#fff0d4!important;color:#794a06}.worst{background:#fbe1df!important;color:#8a241f}
.small{font-size:13px;color:#4b6078}</style><main>
<h1>Tous les gaps — 356 instances CVRPTW</h1>
<p>Solution hybride : notre ILS puis le HGS externe de PyVRP 0.12.2, attribué à ses auteurs. Distances et références DIMACS compatibles, données figées.</p>
'''
    full=a['scopes']['catalog_356'];core=a['scopes']['core_116']
    page+=f'<div class="panel"><strong>356 instances · 472 essais · {full["valid"]}/472 réalisables</strong><br>Moyenne par instance : <strong>{full["mean_instance_gap"]:.3f} %</strong>. Moyenne des essais : {full["mean_run_gap"]:.3f} %. Lot 100/1 000 clients : {core["mean_instance_gap"]:.3f} %.</div>'
    page+='''<nav><a href="#sizes">Par taille</a><a href="#instances">Les 356 instances</a><a href="#runs">Les 472 essais</a></nav>
<p class="small">Gap = 100 × (distance obtenue − BKS) / BKS. Chaque instance a le même poids dans la moyenne principale. Deux graines à 100/1 000 clients, une aux tailles intermédiaires. Un écart-type est non défini avec un seul essai. Les temps réels incluent construction et préparation, hors compilation préchauffée.</p>
<section class="panel" id="sizes"><h2>Synthèse par taille</h2><div class="scroll">'''+table(summary,'size-table')+'</div></section>'
    page+='''<section class="panel" id="instances"><h2>Les 356 instances — aucune sélection des bons résultats</h2>
<label>Rechercher <input id="query" placeholder="Ex. R2_10_8" oninput="filterRows()"></label>
<label>Clients <select id="size" onchange="filterRows()"><option value="">Toutes les tailles</option>'''
    page+=''.join(f'<option>{n}</option>' for n in [100,200,400,600,800,1000])
    page+='''</select></label><span id="count"></span>
<p class="small">Couleur du gap moyen : vert sous 6 %, orange à partir de 6 %, rouge à partir de 10 %. Les filtres changent seulement les lignes visibles ; les statistiques publiées ci-dessus portent toujours sur le catalogue complet.</p><div class="scroll">'''+table(detail,'instance-table')+'</div></section>'
    page+='<section class="panel" id="runs"><h2>Les 472 essais individuels</h2><p>Chaque graine, distance, flotte et temps reste visible. Les résultats réutilisés sont identifiés et leur temps est intégralement facturé.</p><div class="scroll">'+table(raw,'run-table')+'</div></section>'
    page+='''<script>
function filterRows(){let q=document.getElementById('query').value.trim().toLowerCase(),n=document.getElementById('size').value,count=0;
document.querySelectorAll('#instance-table tbody tr').forEach(row=>{let show=row.cells[0].textContent.toLowerCase().includes(q)&&(!n||row.cells[1].textContent.trim()===n);row.hidden=!show;if(show)count++;});
document.getElementById('count').textContent=count+' / 356 instances affichées';}
document.querySelectorAll('#instance-table tbody tr').forEach(row=>{let cell=row.cells[5],g=parseFloat(cell.textContent.replace(',','.'));if(Number.isFinite(g))cell.classList.add(g>=10?'worst':g>=6?'high':'good');});filterRows();
</script></main></html>'''
    target=ROOT/'livraison/RESULTATS_CATALOGUE_V8.html'
    target.write_text(page,encoding='utf-8')
    print(target)


if __name__=='__main__':main()
