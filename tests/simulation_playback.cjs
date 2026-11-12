// Exercise the delivered animation script with a minimal DOM/canvas substitute.
const vm = require('node:vm');
const fs = require('node:fs');
const assert = require('node:assert/strict');
const html = fs.readFileSync(0, 'utf8');
const script = html.match(/<script>([\s\S]*)<\/script>/)[1];
const nodes = new Map();
function element() {
  return {style:{}, textContent:'', value:'0', checked:true, children:[], events:{},
    append(node){this.children.push(node)},
    replaceChildren(){this.children=[]},
    addEventListener(name, handler){this.events[name]=handler},
    getBoundingClientRect(){return {width:600,height:430}},
    getContext(){return new Proxy({}, {get:(_, name)=>()=>{}})}};
}
const get = id => {
  if(!nodes.has(id)) nodes.set(id,element());
  return nodes.get(id);
};
get('speed').value='1';
let nextFrame;
const context=vm.createContext({console, document:{getElementById:get, createElement:element},
  window:{devicePixelRatio:1}, ResizeObserver:class{observe(){}},
  requestAnimationFrame:callback=>{nextFrame=callback}});
vm.runInContext(script, context);
const read = expression=>vm.runInContext(expression,context);
assert.equal(read('state(data.vehicles[0],4).position[0]'),4);
assert.equal(read('state(data.vehicles[0],8).kind'),'Attente');
assert.equal(read('state(data.vehicles[0],15).kind'),'Service');
assert.equal(read('state(data.vehicles[0],19.9).done.length'),0);
assert.equal(read('state(data.vehicles[0],20).done.length'),1);
assert.equal(read('state(data.vehicles[0],25).kind'),'Service');
assert.equal(read('state(data.vehicles[0],29).destination'),0);
assert.equal(read('state(data.vehicles[0],34).kind'),'Rentré');
get('play').events.click();
nextFrame(0);nextFrame(100);
assert.equal(read('time'),2);
get('speed').value='2';nextFrame(200);
assert.equal(read('time'),6);
get('play').events.click();nextFrame(300);
assert.equal(read('time'),6); // Pause prevents advancement.
get('time').events.input({target:{value:'500'}});
assert.equal(read('time'),17);
assert.equal(read('playing'),false);
assert.ok(get('capacity-check').textContent.includes('5,0 / 6,0'));
assert.ok(get('next-check').textContent.includes('[15,0 ; 25,0]'));
assert.ok(get('windows-check').textContent.includes('1 / 1'));
assert.equal(get('stops').children[0].children[1].textContent,'Service');
read('data.vehicles[0].stops[0].late=14; draw()');
assert.ok(get('windows-check').className.includes('bad'));
assert.equal(get('stops').children[0].children[8].textContent,'VIOLATION');
read('data.vehicles[0].stops[0].late=25; data.capacity=4; draw()');
assert.ok(get('capacity-check').textContent.includes('VIOLATION'));
read('data.capacity=6; draw()');
get('time').events.input({target:{value:'1000'}});
assert.equal(get('delivered').textContent,'2 / 2');
assert.equal(get('returned').textContent,'1 / 1');
assert.ok(get('depot-check').textContent.includes('Retour réalisé'));
assert.ok(get('capacity-check').textContent.includes('0,0 / 6,0'));
get('reset').events.click();
assert.equal(read('time'),0);
assert.equal(get('delivered').textContent,'0 / 2');
console.log('Lecture, pause, vitesse, curseur, attentes, services et retour vérifiés.');
