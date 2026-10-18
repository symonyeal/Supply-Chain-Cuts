import {spawn} from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
const root=process.cwd(), brief=path.resolve(root,'../Chokepoint-Lab-brief');
const profile=path.join(brief,'edge-w2-cdp');
const browser=spawn('C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',[
  '--headless=new','--disable-gpu','--no-first-run','--remote-debugging-port=9223',
  `--user-data-dir=${profile}`,'about:blank'],{windowsHide:true,stdio:'ignore'});
const delay=ms=>new Promise(r=>setTimeout(r,ms));
let ws;
try {
  let tabs;
  for(let k=0;k<100;k++){
    try{tabs=await (await fetch('http://127.0.0.1:9223/json')).json();break;}catch{await delay(100);}
  }
  if(!tabs)throw Error('No debugging target');
  ws=new WebSocket(tabs.find(x=>x.type==='page').webSocketDebuggerUrl);
  await new Promise(r=>ws.addEventListener('open',r,{once:true}));
  let i=0;const pending=new Map(),errors=[];
  ws.addEventListener('message',e=>{
    const x=JSON.parse(e.data);
    if(x.id){const p=pending.get(x.id);pending.delete(x.id);x.error?p.reject(x.error):p.resolve(x.result);}
    if(x.method==='Runtime.exceptionThrown')errors.push(x.params.exceptionDetails);
  });
  const call=(method,params={})=>new Promise((resolve,reject)=>{const id=++i;pending.set(id,{resolve,reject});ws.send(JSON.stringify({id,method,params}));});
  const js=async expression=>{
    const r=await call('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});
    if(r.exceptionDetails)throw Error(JSON.stringify(r.exceptionDetails));
    return r.result.value;
  };
  await call('Runtime.enable');await call('Page.enable');
  const reports=[];
  for(const width of [390,1440]){
    await call('Emulation.setDeviceMetricsOverride',{width,height:950,deviceScaleFactor:1,mobile:false});
    await call('Page.navigate',{url:pathToFileURL(path.join(root,'site/index.html')).href});
    for(let k=0;k<100;k++){
      if(await js("!!document.querySelector('#severity-table tbody tr') && typeof Plotly !== 'undefined'"))break;
      await delay(100);
    }
    for(const id of ['cuts','risk','pv','sensitivity','attribution']){
      await js(`document.getElementById('${id}').scrollIntoView()`);await delay(150);
      const result=await js(`({id:'${id}',width:innerWidth,overflow:document.documentElement.scrollWidth>innerWidth,charts:document.querySelectorAll('#${id} .js-plotly-plot').length,rows:document.querySelectorAll('#${id} tbody tr').length})`);
      if(result.overflow)throw Error(JSON.stringify(result));
      reports.push(result);
      if(['cuts','risk','sensitivity'].includes(id)){
        const p=await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});
        fs.writeFileSync(path.join(brief,`w2-${width}-${id}.png`),Buffer.from(p.data,'base64'));
      }
    }
    await js("document.getElementById('scenario-table').scrollIntoView()");await delay(150);
    const shot=await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});
    fs.writeFileSync(path.join(brief,`w2-${width}-scenarios.png`),Buffer.from(shot.data,'base64'));
    for(const [alpha,D,h,s,L] of [['0.5','3','3','0.5','24'],['0.1','6','1','0.1','24'],['0.25','12','0','0','6']]){
      await js(`[['c-alpha','${alpha}'],['c-dj','${D}'],['c-h','${h}'],['c-sigma','${s}'],['c-L','${L}']].forEach(([id,v])=>document.querySelector('#'+id+' [data-v="'+v+'"]').click())`);
      for(const id of ['cuts','pv','attribution']){
        await js(`document.getElementById('${id}').scrollIntoView()`);await delay(100);
      }
      reports.push(await js(`({configuration:'${alpha},${D},${h},${s},${L}',pv:document.getElementById('pv-summary').textContent,attribution:document.getElementById('attr-summary').textContent})`));
    }
  }
  if(errors.length)throw Error(JSON.stringify(errors));
  fs.writeFileSync(path.join(brief,'w2-browser-check.json'),JSON.stringify({errors,reports},null,2));
  console.log(JSON.stringify({errors:errors.length,checks:reports.length}));
}finally{if(ws)ws.close();browser.kill();}
