/* Static browser edition of the RallyScope Dash prototype.
   Reads the same full source CSV and applies the same score-validity rules. */
'use strict';
const DATA_URL = 'https://raw.githubusercontent.com/SahilMotyar/bwf-match-data/main/matches.csv';
const DISCIPLINES = ['MS', 'WS', 'MD', 'WD', 'XD'];
const NAMES = {MS:"Men's singles",WS:"Women's singles",MD:"Men's doubles",WD:"Women's doubles",XD:"Mixed doubles"};
const COLOR = {purple:'#57068c',violet:'#7548b4',lavender:'#ab88d8',muted:'#697184',grid:'#eae4f1'};
const NS = 'http://www.w3.org/2000/svg';
const state = {all:[],start:2007,end:2026,disciplines:new Set(DISCIPLINES),tiers:new Set(),selection:null,sourceRows:0};

function parseCSV(source){
  const rows=[]; let row=[],field='',quoted=false;
  for(let i=0;i<source.length;i++){
    const c=source[i];
    if(quoted){if(c==='"'&&source[i+1]==='"'){field+='"';i++;}else if(c==='"')quoted=false;else field+=c;}
    else if(c==='"')quoted=true;
    else if(c===','){row.push(field);field='';}
    else if(c==='\n'){row.push(field.replace(/\r$/,''));rows.push(row);row=[];field='';}
    else field+=c;
  }
  if(field||row.length){row.push(field.replace(/\r$/,''));rows.push(row);}
  return rows;
}

function scoreMetrics(raw,winner){
  if(!raw)return null;
  const score=raw.replace(/,/g,' ').replace(/\s+/g,' ').trim();
  if(!/^\d{1,2}-\d{1,2}(?: \d{1,2}-\d{1,2}){1,2}$/.test(score))return null;
  const games=score.split(' ').map(g=>g.split('-').map(Number));
  if(games.length<2||games.length>3)return null;
  let wins1=0,wins2=0,margin=0;
  for(const [a,b] of games){
    const hi=Math.max(a,b),lo=Math.min(a,b);
    if(a===b||lo<0||hi>30||hi<21||(hi-lo<2&&!(hi===30&&lo===29)))return null;
    if(a>b)wins1++;else wins2++;
    margin+=Math.abs(a-b);
  }
  if(!((winner===1&&wins1===2&&wins2<=1)||(winner===2&&wins2===2&&wins1<=1)))return null;
  const openingLoser=games[0][0]<games[0][1]?1:2;
  return {deciding:games.length===3,comeback:openingLoser===winner,openingLoser,margin:margin/games.length};
}

function prepare(rows){
  const header=rows[0]||[];
  const required=['date','discipline','tier','team1','team2','winner','score'];
  if(required.some(f=>!header.includes(f)))throw Error('The source CSV is missing required columns.');
  const ix=Object.fromEntries(required.map(f=>[f,header.indexOf(f)]));
  const all=[];
  for(let i=1;i<rows.length;i++){
    const r=rows[i];if(!r||r.length<7)continue;
    const year=Number((r[ix.date]||'').slice(0,4));
    const discipline=(r[ix.discipline]||'').trim();
    const tier=(r[ix.tier]||'').trim();
    const a=(r[ix.team1]||'').trim(),b=(r[ix.team2]||'').trim();
    const winner=Number(r[ix.winner]);
    if(!Number.isInteger(year)||year<1900||year>2100||!DISCIPLINES.includes(discipline)||!a||!b||a===b)continue;
    const m=scoreMetrics(r[ix.score],winner);if(!m)continue;
    const sideA=a<=b?a:b,sideB=a<=b?b:a;
    const winnerName=winner===1?a:b;
    all.push({year,discipline,tier,a,b,loser:m.openingLoser===1?a:b,
      comeback:m.comeback,deciding:m.deciding,margin:m.margin,
      rivalryId:discipline+'::'+sideA+'::'+sideB,sideA,sideB,sideAWon:winnerName===sideA});
  }
  return all;
}

function comebackSummary(data,min=10){
  const map=new Map();
  for(const r of data){let v=map.get(r.loser);if(!v){v={name:r.loser,opportunities:0,wins:0};map.set(r.loser,v);}v.opportunities++;if(r.comeback)v.wins++;}
  return [...map.values()].filter(v=>v.opportunities>=min).map(v=>({...v,rate:100*v.wins/v.opportunities}))
    .sort((a,b)=>b.rate-a.rate||b.opportunities-a.opportunities).slice(0,12);
}
function competitionSummary(data){
  const map=new Map(DISCIPLINES.map(d=>[d,{discipline:d,matches:0,deciding:0,margin:0}]));
  for(const r of data){const v=map.get(r.discipline);v.matches++;if(r.deciding)v.deciding++;v.margin+=r.margin;}
  return [...map.values()].filter(v=>v.matches).map(v=>({...v,rate:100*v.deciding/v.matches,avgMargin:v.margin/v.matches}));
}
function rivalrySummary(data){
  const map=new Map();
  for(const r of data){let v=map.get(r.rivalryId);if(!v){v={id:r.rivalryId,discipline:r.discipline,sideA:r.sideA,sideB:r.sideB,meetings:0,sideAWins:0,deciding:0};map.set(r.rivalryId,v);}v.meetings++;if(r.sideAWon)v.sideAWins++;if(r.deciding)v.deciding++;}
  return [...map.values()].filter(v=>v.meetings>=6).map(v=>({...v,parity:100-2*Math.abs(100*v.sideAWins/v.meetings-50)}))
    .sort((a,b)=>b.parity-a.parity||b.meetings-a.meetings).slice(0,120);
}
function svgEl(tag,attrs={},text){const e=document.createElementNS(NS,tag);for(const [k,v] of Object.entries(attrs))e.setAttribute(k,String(v));if(text!==undefined)e.textContent=text;return e;}
function add(parent,tag,attrs={},text){const e=svgEl(tag,attrs,text);parent.appendChild(e);return e;}
function empty(target,message){target.replaceChildren();const p=document.createElement('p');p.className='empty';p.textContent=message;target.appendChild(p);}
function tooltip(node,lines){const tip=document.getElementById('tooltip');node.addEventListener('mouseenter',e=>{tip.textContent=lines.join('\n');tip.hidden=false;moveTip(e);});node.addEventListener('mousemove',moveTip);node.addEventListener('mouseleave',()=>tip.hidden=true);}
function moveTip(e){const tip=document.getElementById('tooltip');tip.style.left=Math.min(e.clientX+14,innerWidth-tip.offsetWidth-10)+'px';tip.style.top=Math.min(e.clientY+14,innerHeight-tip.offsetHeight-10)+'px';}
function selectable(node,label,onSelect,lines){node.classList.add(node.tagName.toLowerCase()==='circle'?'bubble':'bar');node.setAttribute('tabindex','0');node.setAttribute('role','button');node.setAttribute('aria-label',label);node.addEventListener('click',onSelect);node.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();onSelect();}});tooltip(node,lines);}
function chartSvg(target,width,height){target.replaceChildren();const svg=svgEl('svg',{viewBox:`0 0 ${width} ${height}`,role:'img'});target.appendChild(svg);return svg;}

function drawComeback(data){
  const target=document.getElementById('comeback-chart');
  const contextual=state.selection&&['player','rivalry'].includes(state.selection.type);
  document.getElementById('comeback-subhead').textContent='Recovery win rate after Game 1 loss · '+(contextual?'exploratory small samples':'minimum 10 opportunities');
  const items=comebackSummary(data,contextual?1:10);
  if(!items.length)return empty(target,'No competitor has enough score-valid comeback opportunities under these filters.');
  const w=720,h=390,left=176,right=60,top=12,rowH=27,plotW=w-left-right;
  const svg=chartSvg(target,w,h);
  for(const tick of [0,25,50,75,100]){const x=left+plotW*tick/100;add(svg,'line',{x1:x,y1:top,x2:x,y2:top+12*rowH,class:'grid'});add(svg,'text',{x,y:top+12*rowH+19,'text-anchor':'middle',class:'axis'},String(tick));}
  items.forEach((v,i)=>{
    const y=top+i*rowH,short=v.name.length>23?v.name.slice(0,22)+'…':v.name;
    add(svg,'text',{x:left-9,y:y+17,'text-anchor':'end',class:'axis'},short);
    const bar=add(svg,'rect',{x:left,y:y+3,width:Math.max(1,plotW*v.rate/100),height:20,rx:2,fill:i===0?COLOR.purple:COLOR.lavender});
    selectable(bar,`${v.name}: ${v.rate.toFixed(1)} percent comeback rate`,()=>{state.selection={type:'player',value:v.name};render();},[v.name,`Comeback rate: ${v.rate.toFixed(1)}%`,`Wins: ${v.wins} / opportunities: ${v.opportunities}`]);
    add(svg,'text',{x:Math.min(left+plotW*v.rate/100+6,w-40),y:y+18,class:'value'},v.rate.toFixed(1)+'%');
  });
  add(svg,'text',{x:left+plotW/2,y:h-7,'text-anchor':'middle',class:'axis'},'Comeback success rate (%)');
}
function drawCompetition(data){
  const target=document.getElementById('competition-chart'),items=competitionSummary(data);
  if(!items.length)return empty(target,'No score-valid matches under these filters.');
  const w=720,h=390,left=68,right=26,top=24,bottom=64,plotW=w-left-right,plotH=h-top-bottom;
  const svg=chartSvg(target,w,h),max=Math.max(50,Math.ceil((Math.max(...items.map(v=>v.rate))+12)/10)*10);
  for(let tick=0;tick<=max;tick+=10){const y=top+plotH*(1-tick/max);add(svg,'line',{x1:left,y1:y,x2:w-right,y2:y,class:'grid'});add(svg,'text',{x:left-9,y:y+4,'text-anchor':'end',class:'axis'},tick+'%');}
  DISCIPLINES.forEach((d,i)=>{
    const v=items.find(x=>x.discipline===d),x=left+(i+.5)*plotW/5,barW=75;
    add(svg,'text',{x,y:h-35,'text-anchor':'middle',class:'axis'},d);
    if(!v)return;
    const barH=v.rate/max*plotH,y=top+plotH-barH;
    const bar=add(svg,'rect',{x:x-barW/2,y,width:barW,height:barH,fill:i<2?COLOR.purple:COLOR.lavender});
    selectable(bar,`${NAMES[d]}: ${v.rate.toFixed(1)} percent deciding games`,()=>{state.selection={type:'discipline',value:d};render();},[NAMES[d],`Deciding-game rate: ${v.rate.toFixed(1)}%`,`Deciding matches: ${v.deciding} / ${v.matches}`,`Avg game-point margin: ${v.avgMargin.toFixed(2)}`]);
    add(svg,'text',{x,y:y-8,'text-anchor':'middle',class:'value'},v.rate.toFixed(1)+'%');
  });
  add(svg,'text',{x:w/2,y:h-8,'text-anchor':'middle',class:'axis'},'MS · WS · MD · WD · XD (click to filter)');
  add(svg,'text',{x:16,y:h/2,transform:`rotate(-90 16 ${h/2})`,'text-anchor':'middle',class:'axis'},'Deciding-game rate (%)');
}
function drawRivalries(data){
  const target=document.getElementById('rivalry-chart'),items=rivalrySummary(data);
  if(!items.length)return empty(target,'No rivalry with at least 6 meetings under these filters.');
  const w=1440,h=340,left=74,right=30,top=19,bottom=57,plotW=w-left-right,plotH=h-top-bottom;
  const svg=chartSvg(target,w,h),maxX=Math.max(10,...items.map(v=>v.meetings))+2;
  for(const tick of [0,20,40,60,80,100]){const y=top+plotH*(1-tick/100);add(svg,'line',{x1:left,y1:y,x2:w-right,y2:y,class:'grid'});add(svg,'text',{x:left-10,y:y+4,'text-anchor':'end',class:'axis'},tick+'%');}
  const step=maxX>30?5:2;for(let tick=0;tick<=maxX;tick+=step){const x=left+plotW*tick/maxX;add(svg,'text',{x,y:h-bottom+19,'text-anchor':'middle',class:'axis'},String(tick));}
  for(const v of items){
    const x=left+plotW*v.meetings/maxX,y=top+plotH*(1-v.parity/100),r=Math.max(5,3.5+2.8*Math.sqrt(v.deciding));
    const bubble=add(svg,'circle',{cx:x,cy:y,r,fill:COLOR.violet,'fill-opacity':.64,stroke:COLOR.purple,'stroke-width':.7});
    selectable(bubble,`${v.sideA} versus ${v.sideB}: ${v.meetings} meetings, ${v.parity.toFixed(1)} percent parity`,()=>{state.selection={type:'rivalry',value:v.id};render();},[`${v.sideA} vs. ${v.sideB}`,`Meetings: ${v.meetings}`,`${v.sideA} wins: ${v.sideAWins}`,`Head-to-head parity: ${v.parity.toFixed(1)}%`,`Deciding games: ${v.deciding}`]);
  }
  add(svg,'text',{x:w/2,y:h-6,'text-anchor':'middle',class:'axis'},'Head-to-head meetings (min. 6)');
  add(svg,'text',{x:16,y:h/2,transform:`rotate(-90 16 ${h/2})`,'text-anchor':'middle',class:'axis'},'Rivalry parity (%)');
}
function render(){
  const base=state.all.filter(r=>r.year>=state.start&&r.year<=state.end&&state.disciplines.has(r.discipline)&&state.tiers.has(r.tier));
  let data=base;
  if(state.selection){const s=state.selection;if(s.type==='player')data=base.filter(r=>r.a===s.value||r.b===s.value);else if(s.type==='discipline')data=base.filter(r=>r.discipline===s.value);else if(s.type==='rivalry')data=base.filter(r=>r.rivalryId===s.value);}
  const label=state.selection?`${state.selection.type}: ${state.selection.value.replace(/::/g,' · ')}`:'All players and rivalries';
  document.getElementById('status').textContent=`${data.length.toLocaleString()} matches · ${state.start}–${state.end} · ${label}`;
  drawComeback(data);drawCompetition(data);drawRivalries(data);
}
function setupFilters(){
  const years=[...new Set(state.all.map(r=>r.year))].sort((a,b)=>a-b),lo=document.getElementById('start-year'),hi=document.getElementById('end-year');
  state.start=years[0];state.end=years[years.length-1];
  for(const y of years){lo.add(new Option(y,y));hi.add(new Option(y,y));}lo.value=state.start;hi.value=state.end;
  lo.addEventListener('change',()=>{state.start=Math.min(Number(lo.value),state.end);lo.value=state.start;state.selection=null;render();});
  hi.addEventListener('change',()=>{state.end=Math.max(Number(hi.value),state.start);hi.value=state.end;state.selection=null;render();});
  const dbox=document.getElementById('disciplines');
  for(const d of DISCIPLINES){const label=document.createElement('label'),input=document.createElement('input');input.type='checkbox';input.value=d;input.checked=true;input.addEventListener('change',()=>{if(input.checked)state.disciplines.add(d);else state.disciplines.delete(d);state.selection=null;render();});label.append(input,document.createTextNode(d));label.title=NAMES[d];dbox.appendChild(label);}
  const tiers=[...new Set(state.all.map(r=>r.tier))].sort(),tbox=document.getElementById('tiers');state.tiers=new Set(tiers);
  for(const tier of tiers){const label=document.createElement('label'),input=document.createElement('input');input.type='checkbox';input.value=tier;input.checked=true;input.addEventListener('change',()=>{if(input.checked)state.tiers.add(tier);else state.tiers.delete(tier);state.selection=null;document.querySelector('#tier-menu summary').textContent=state.tiers.size===tiers.length?'All tournament tiers':`${state.tiers.size} of ${tiers.length} tiers`;render();});label.append(input,document.createTextNode(tier||'(Unspecified)'));tbox.appendChild(label);}
  document.getElementById('clear').addEventListener('click',()=>{state.selection=null;render();});
}
async function start(){
  try{
    const response=await fetch(DATA_URL);if(!response.ok)throw Error(`Source download failed (${response.status}).`);
    const rows=parseCSV(await response.text());state.sourceRows=rows.length-1;state.all=prepare(rows);
    document.getElementById('source-count').textContent=state.sourceRows.toLocaleString();
    document.getElementById('valid-count').textContent=state.all.length.toLocaleString();
    document.getElementById('excluded-count').textContent=(state.sourceRows-state.all.length).toLocaleString();
    setupFilters();render();
  }catch(error){document.getElementById('status').textContent=`Could not load the source CSV: ${error.message} Try again, or run the Python version from the repository.`;}
}
if(typeof document!=='undefined')start();
if(typeof module!=='undefined')module.exports={parseCSV,scoreMetrics,prepare,comebackSummary,competitionSummary,rivalrySummary};
