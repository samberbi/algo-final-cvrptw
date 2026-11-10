"""Verified route playback, with a self-contained browser animation."""
import json

from algo.verify import verify


def timeline(ins, routes):
    checked = verify(routes, ins)
    if not checked['valid']:
        raise ValueError('Tournées irréalisables : ' + '; '.join(checked['errors']))
    active = [list(r) for r in routes if r]
    vehicles = []
    for number, (route, detail) in enumerate(zip(active, checked['routes']), 1):
        segments, clock, previous = [], 0., 0
        for stop in detail['schedule']:
            client = stop['client']
            for kind, start, end, origin, destination in [
                ('Trajet', clock, stop['arrival'], previous, client),
                ('Attente', stop['arrival'], stop['start'], client, client),
                ('Service', stop['start'], stop['finish'], client, client),
            ]:
                if end > start:
                    segments.append(dict(kind=kind, start=start / 10, end=end / 10,
                                         origin=origin, destination=destination))
            clock, previous = stop['finish'], client
        if detail['duration'] > clock:
            segments.append(dict(kind='Trajet', start=clock / 10, end=detail['duration'] / 10,
                                 origin=previous, destination=0))
        vehicles.append(dict(id=number, route=route, segments=segments,
                             stops=[dict(client=s['client'], arrival=s['arrival'] / 10,
                                         start=s['start'] / 10, finish=s['finish'] / 10,
                                         early=float(ins.early[s['client']]) / 10,
                                         late=float(ins.late[s['client']]) / 10,
                                         demand=float(ins.demand[s['client']])) for s in detail['schedule']],
                             end=detail['duration'] / 10, load=detail['load'],
                             waiting=detail['waiting'] / 10))
    return dict(name=ins.name, coordinates=ins.xy.tolist(), vehicles=vehicles, clients=ins.n,
                end=max((v['end'] for v in vehicles), default=0.),
                distance=checked['distance'] / 10, capacity=ins.capacity,
                horizon=ins.horizon / 10, fleet=ins.vehicles)


def simulation_html(data):
    encoded = json.dumps(data, ensure_ascii=False, allow_nan=False).replace('<', '\\u003c')
    return TEMPLATE.replace('__SIMULATION_DATA__', encoded)


TEMPLATE = r'''<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{box-sizing:border-box}body{margin:0;font:14px system-ui,sans-serif;color:#17283e;background:#fff}
.panel{border:1px solid #dce5ed;border-radius:16px;overflow:hidden}
.toolbar{display:flex;gap:10px;align-items:center;flex-wrap:wrap;padding:14px;background:#f5f8fc}
button,select{font:inherit;border:1px solid #ccd8e2;border-radius:8px;padding:9px 12px;background:white;color:#17283e;cursor:pointer}
#play{background:#087e8b;color:white;border-color:#087e8b;min-width:110px}
button:focus-visible,select:focus-visible,input:focus-visible{outline:3px solid #00a5ba;outline-offset:2px}
label{display:flex;gap:7px;align-items:center}.metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;padding:12px 14px}
.metric{background:#f5f8fc;border-radius:9px;padding:10px}.metric strong{display:block;font-size:22px;margin-top:3px}
.layout{display:grid;grid-template-columns:minmax(0,1fr) 260px;gap:10px;padding:0 14px 14px}
.map{height:430px;background:#f9fbfd;border:1px solid #e3eaf1;border-radius:12px;position:relative}
canvas{display:block;width:100%;height:100%}.list{max-height:430px;overflow:auto;display:grid;align-content:start;gap:7px}
.truck{border:1px solid #dce5ed;border-left:5px solid;border-radius:9px;padding:9px;background:white}
.truck strong{display:block;margin-bottom:3px}.truck small{display:block;color:#586b7d;margin-top:4px}
.scrubber{padding:0 15px 12px}#time{width:100%;accent-color:#087e8b}.scale{display:flex;justify-content:space-between;color:#607184;font-size:12px}
.legend{display:flex;gap:14px;flex-wrap:wrap;padding:0 15px 12px;color:#52677a;font-size:12px}
.dot{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:4px}
.note{margin:10px 2px;color:#607184;font-size:12px}
.audit{border-top:1px solid #dce5ed;padding:14px}.audit h3{margin:0 0 10px;font-size:17px}
.checks{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:12px}.badge{padding:6px 9px;border-radius:7px;background:#e6f5ee;color:#176644;font-size:12px}
.bad{background:#fff0ec!important;color:#aa3322!important}.inspector{display:flex;align-items:center;flex-wrap:wrap;gap:12px;margin-bottom:10px}
.gauge{height:10px;background:#e3eaf1;border-radius:8px;overflow:hidden;max-width:450px;margin:8px 0}.gauge div{height:100%;background:#087e8b}
.scrolltable{max-height:250px;overflow:auto;border:1px solid #e3eaf1;border-radius:9px;margin-top:12px}
table{width:100%;border-collapse:collapse;font-size:12px;white-space:nowrap}th,td{padding:8px;text-align:left;border-bottom:1px solid #edf1f5}
th{position:sticky;top:0;background:#eef3f8;z-index:1}tr.active{background:#fff5db}tr.done{background:#f0f9f5}
.explain{font-size:12px;color:#52677a;margin:8px 0;line-height:1.5}
@media(max-width:650px){.layout{grid-template-columns:1fr}.list{max-height:150px;grid-template-columns:repeat(2,minmax(0,1fr))}.map{height:340px}.metrics{grid-template-columns:repeat(2,1fr)}}
</style></head><body>
<div class="panel">
 <div class="toolbar">
  <button id="play" type="button">▶ Lecture</button>
  <button id="reset" type="button">↺ Début</button>
  <label>Vitesse <select id="speed" aria-label="Vitesse de simulation">
   <option value=".25">× 0,25</option><option value=".5">× 0,5</option><option value="1" selected>× 1</option>
   <option value="2">× 2</option><option value="5">× 5</option><option value="10">× 10</option><option value="20">× 20</option>
  </select></label>
  <label><input id="paths" type="checkbox" checked>Afficher les tournées</label>
  <span id="message" role="status">Prêt à démarrer</span>
 </div>
 <div class="metrics">
  <div class="metric">Temps simulé<strong id="clock">0,0</strong></div>
  <div class="metric">Livraisons terminées<strong id="delivered">0</strong></div>
  <div class="metric">Camions rentrés<strong id="returned">0</strong></div>
  <div class="metric">Camions en attente<strong id="waiting">0</strong></div>
 </div>
 <div class="layout"><div class="map"><canvas id="map" aria-label="Animation des camions sur les coordonnées de l’instance"></canvas></div><div id="fleet" class="list"></div></div>
 <div class="scrubber"><label for="time">Position dans la tournée</label><input id="time" type="range" min="0" max="1000" step="1" value="0"><div class="scale"><span>Départ du dépôt</span><span id="end"></span></div></div>
 <div class="legend"><span><i class="dot" style="background:#b8c6d3"></i>Client à livrer</span><span><i class="dot" style="background:#11966e"></i>Livré</span><span>■ Dépôt</span><span>Numéro cerclé : camion · halo orange : attente · halo vert : service</span></div>
 <div class="audit">
  <h3>Vérifier les contraintes à cet instant</h3>
  <div class="checks"><span id="coverage-check" class="badge"></span><span id="fleet-check" class="badge"></span><span id="windows-check" class="badge"></span></div>
  <div class="inspector"><label>Camion à inspecter <select id="inspect" aria-label="Camion à inspecter"></select></label><span id="depot-check" class="badge"></span></div>
  <div id="capacity-check"></div><div class="gauge"><div id="load-bar"></div></div>
  <div id="next-check" class="explain"></div>
  <div class="explain">Fenêtre = intervalle autorisé pour le <b>début</b> du service. Arriver avant l’ouverture entraîne une attente. La fin du service peut dépasser la fermeture de cette fenêtre. « Prévu » désigne la tournée complète ; « réalisé » suit l’horloge ci-dessus.</div>
  <div class="scrolltable"><table><thead><tr><th>Client</th><th>État à l’instant t</th><th>Fenêtre [ouverture ; fermeture]</th><th>Arrivée prévue</th><th>Début prévu</th><th>Fin prévue</th><th>Attente</th><th>Demande</th><th>Contrôle du début</th></tr></thead><tbody id="stops"></tbody></table></div>
 </div>
</div>
<p class="note">Lecture des horaires vérifiés · coordonnées de benchmark · × 1 = 20 unités de temps simulé par seconde réelle. Une livraison est terminée à la fin du service.</p>
<script>
const data=__SIMULATION_DATA__;
const colors=['#087e8b','#d17516','#7661b2','#d14f71','#386cb0','#539337','#8e5841','#a47c00'];
const $=id=>document.getElementById(id), canvas=$('map'), ctx=canvas.getContext('2d');
const format=n=>n.toLocaleString('fr-FR',{minimumFractionDigits:1,maximumFractionDigits:1});
let time=0, playing=false, last=null, width=0, height=0;
let inspected=-1, stopRows=[];
const cards=data.vehicles.map((v,i)=>{
 const option=document.createElement('option');option.value=String(i);option.textContent='Camion '+v.id;$('inspect').append(option);
 const card=document.createElement('div');card.className='truck';card.style.borderLeftColor=colors[i%colors.length];
 const title=document.createElement('strong');title.textContent='Camion '+v.id;card.append(title);
 const status=document.createElement('span');card.append(status);
 const detail=document.createElement('small');card.append(detail);$('fleet').append(card);
 return {status,detail};
});
$('end').textContent='Dernier retour : '+format(data.end);
function state(v,t){
 const done=v.stops.filter(s=>s.finish<=t);
 if(t>=v.end)return {position:data.coordinates[0],kind:'Rentré',destination:0,done};
 const s=v.segments.find(s=>s.start<=t&&t<s.end);
 if(!s)return {position:data.coordinates[0],kind:'Au dépôt',destination:0,done};
 const a=data.coordinates[s.origin],b=data.coordinates[s.destination],f=(t-s.start)/(s.end-s.start);
 return {position:s.kind==='Trajet'?[a[0]+f*(b[0]-a[0]),a[1]+f*(b[1]-a[1])]:b,
         kind:s.kind,destination:s.destination,done};
}
function inspectConstraints(states){
 const index=Number($('inspect').value)||0,v=data.vehicles[index];
 if(!v)return;
 if(index!==inspected){
  inspected=index;$('stops').replaceChildren();
  stopRows=v.stops.map(s=>{const row=document.createElement('tr'),cells=[];
   for(let j=0;j<9;j++){const c=document.createElement('td');row.append(c);cells.push(c)}
   $('stops').append(row);return {row,cells};
  });
 }
 const delivered=states[index].done.reduce((sum,s)=>sum+s.demand,0),remaining=v.load-delivered;
 const capacityOK=v.load<=data.capacity+1e-8&&remaining>=-1e-8&&remaining<=data.capacity+1e-8;
 $('capacity-check').textContent='Charge restante : '+format(remaining)+' / '+format(data.capacity)+' · départ : '+format(v.load)+' / '+format(data.capacity)+' — '+(capacityOK?'capacité respectée':'VIOLATION de capacité');
 $('capacity-check').className=capacityOK?'':'bad';
 $('load-bar').style.width=Math.min(100,Math.max(0,100*remaining/data.capacity))+'%';
 $('load-bar').style.background=capacityOK?'#087e8b':'#bb3427';
 const depotOK=v.end<=data.horizon+1e-8;
 $('depot-check').textContent=(time>=v.end?'Retour réalisé : ':'Retour prévu : ')+format(v.end)+' ≤ '+format(data.horizon)+' · '+(depotOK?'dépôt respecté':'RETOUR TARDIF');
 $('depot-check').className='badge'+(depotOK?'':' bad');
 const next=v.stops.find(s=>s.finish>time);
 $('next-check').textContent=next?'Client '+next.client+' : début prévu '+format(next.start)+' dans ['+format(next.early)+' ; '+format(next.late)+'] · marge avant fermeture '+format(next.late-next.start)+'.':'Tous les services de ce camion sont terminés.';
 v.stops.forEach((s,j)=>{
  const status=time>=s.finish?'Livré':time>=s.start?'Service':time>=s.arrival?'Attente':'À venir';
  const valid=s.start>=s.early-1e-8&&s.start<=s.late+1e-8;
  const values=[s.client,status,'['+format(s.early)+' ; '+format(s.late)+']',format(s.arrival),format(s.start),format(s.finish),format(s.start-s.arrival),format(s.demand),valid?(time>=s.start?'Conforme · réalisé':'Conforme · prévu'):'VIOLATION'];
  values.forEach((value,k)=>stopRows[j].cells[k].textContent=String(value));
  stopRows[j].row.className=!valid?'bad':status==='Livré'?'done':status==='Service'||status==='Attente'?'active':'';
 });
 const all=data.vehicles.flatMap(v=>v.stops),started=all.filter(s=>s.start<=time),valid=started.filter(s=>s.start>=s.early-1e-8&&s.start<=s.late+1e-8);
 $('windows-check').textContent='Débuts de service réalisés conformes : '+valid.length+' / '+started.length;
 $('windows-check').className='badge'+(valid.length===started.length?'':' bad');
 const ids=all.map(s=>s.client),coverageOK=ids.length===data.clients&&new Set(ids).size===data.clients&&ids.every(i=>i>=1&&i<=data.clients);
 $('coverage-check').textContent=coverageOK?'Plan : '+data.clients+' clients affectés une seule fois':'VIOLATION de couverture';
 $('coverage-check').className='badge'+(coverageOK?'':' bad');
 $('fleet-check').textContent='Flotte utilisée : '+data.vehicles.length+' / '+data.fleet;
 $('fleet-check').className='badge'+(data.vehicles.length<=data.fleet?'':' bad');
}
const xs=data.coordinates.map(p=>p[0]),ys=data.coordinates.map(p=>p[1]);
const minX=Math.min(...xs),maxX=Math.max(...xs),minY=Math.min(...ys),maxY=Math.max(...ys);
function project(p){
 const scale=Math.min((width-60)/Math.max(1,maxX-minX),(height-60)/Math.max(1,maxY-minY));
 return [width/2+(p[0]-(minX+maxX)/2)*scale,height/2-(p[1]-(minY+maxY)/2)*scale];
}
function draw(){
 ctx.clearRect(0,0,width,height);
 ctx.strokeStyle='#edf1f5';ctx.lineWidth=1;
 for(let x=20;x<width;x+=40){ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,height);ctx.stroke()}
 for(let y=20;y<height;y+=40){ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(width,y);ctx.stroke()}
 if($('paths').checked)data.vehicles.forEach((v,i)=>{
  ctx.strokeStyle=colors[i%colors.length];ctx.globalAlpha=.23;ctx.lineWidth=1.4;ctx.beginPath();
  [0,...v.route,0].forEach((n,j)=>{const [x,y]=project(data.coordinates[n]);j?ctx.lineTo(x,y):ctx.moveTo(x,y)});ctx.stroke();
 });
 ctx.globalAlpha=1;
 const states=data.vehicles.map(v=>state(v,time)),done=new Set(states.flatMap(s=>s.done.map(d=>d.client)));
 data.coordinates.slice(1).forEach((p,i)=>{const [x,y]=project(p);ctx.fillStyle=done.has(i+1)?'#11966e':'#b8c6d3';ctx.beginPath();ctx.arc(x,y,3,0,2*Math.PI);ctx.fill()});
 const [dx,dy]=project(data.coordinates[0]);ctx.fillStyle='#17283e';ctx.fillRect(dx-7,dy-7,14,14);
 ctx.font='bold 11px system-ui';ctx.textAlign='left';ctx.fillText('Dépôt',dx+11,dy-10);
 states.forEach((s,i)=>{
  const [x,y]=project(s.position);
  if(s.kind==='Attente'||s.kind==='Service'){ctx.fillStyle=s.kind==='Attente'?'#f5b64266':'#11966e44';ctx.beginPath();ctx.arc(x,y,16,0,2*Math.PI);ctx.fill()}
  // Returned trucks share the depot; keep its marker legible.
  if(s.kind!=='Rentré'){
   ctx.fillStyle=colors[i%colors.length];ctx.beginPath();ctx.arc(x,y,9,0,2*Math.PI);ctx.fill();ctx.strokeStyle='white';ctx.lineWidth=2;ctx.stroke();
   ctx.fillStyle='white';ctx.font='bold 10px system-ui';ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText(String(i+1),x,y);ctx.textBaseline='alphabetic';
  }
  cards[i].status.textContent=s.kind+(s.kind==='Trajet'?(s.destination?' → client '+s.destination:' → dépôt'):s.kind==='Service'||s.kind==='Attente'?' · client '+s.destination:'');
  const delivered=s.done.reduce((sum,d)=>sum+d.demand,0),v=data.vehicles[i];
  cards[i].detail.textContent=s.done.length+'/'+v.stops.length+' livrés · charge restante '+format(Math.max(0,v.load-delivered))+' / '+format(data.capacity);
 });
 $('clock').textContent=format(time);$('delivered').textContent=done.size+' / '+data.clients;
 $('returned').textContent=states.filter(s=>s.kind==='Rentré').length+' / '+states.length;
 $('waiting').textContent=states.filter(s=>s.kind==='Attente').length;
 $('time').value=data.end?Math.round(time/data.end*1000):0;
 inspectConstraints(states);
}
function setPlaying(value){playing=value;last=null;$('play').textContent=playing?'⏸ Pause':'▶ Lecture';$('message').textContent=time>=data.end?'Toutes les tournées sont terminées':playing?'Simulation en cours':time?'En pause':'Prêt à démarrer'}
$('play').addEventListener('click',()=>{if(time>=data.end)time=0;setPlaying(!playing);draw()});
$('reset').addEventListener('click',()=>{time=0;setPlaying(false);draw()});
$('time').addEventListener('input',e=>{time=Number(e.target.value)/1000*data.end;setPlaying(false);draw()});
$('paths').addEventListener('change',draw);
$('inspect').addEventListener('change',draw);
function resize(){const box=canvas.getBoundingClientRect(),ratio=window.devicePixelRatio||1;width=box.width;height=box.height;canvas.width=Math.round(width*ratio);canvas.height=Math.round(height*ratio);ctx.setTransform(ratio,0,0,ratio,0,0);draw()}
new ResizeObserver(resize).observe(canvas);resize();
function frame(now){if(playing){if(last!==null){time=Math.min(data.end,time+Math.min(.2,(now-last)/1000)*20*Number($('speed').value));if(time>=data.end)setPlaying(false);draw()}last=now}requestAnimationFrame(frame)}
requestAnimationFrame(frame);
</script></body></html>'''
