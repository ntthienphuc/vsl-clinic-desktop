/* Actual Electron dictionary/UI behavior. Public words, isolated QA profile. */
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
const args=Object.fromEntries(process.argv.slice(2).map(s=>s.replace(/^--/,'').split('=')));
const out=path.resolve(args.output);fs.mkdirSync(out,{recursive:true});
const report={scope:'Actual Electron source build, isolated public-fixture profile; no clinical/fluent-sign claim',checks:{},layouts:[]};
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
async function until(fn,ms=25000){const start=Date.now();while(Date.now()-start<ms){const r=await fn();if(r)return r;await sleep(120);}throw Error('Timeout '+fn.toString().slice(0,100));}
const sockets=[];
async function connect(page){
 const ws=new WebSocket(page.webSocketDebuggerUrl);sockets.push(ws);await new Promise(r=>ws.addEventListener('open',r,{once:true}));
 let serial=0;const pending=new Map();ws.addEventListener('message',e=>{const m=JSON.parse(e.data);pending.get(m.id)?.(m);});
 async function call(method,params={}){const id=++serial;let timer;const response=new Promise((r,j)=>{pending.set(id,r);timer=setTimeout(()=>j(Error(method)),15000);});ws.send(JSON.stringify({id,method,params}));const m=await response.finally(()=>{pending.delete(id);clearTimeout(timer);});if(m.error)throw Error(JSON.stringify(m.error));return m.result;}
 async function evaluate(expression){const r=await call('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error(JSON.stringify(r.exceptionDetails));return r.result.value;}
 return {call,eval:evaluate,shot:async name=>{const r=await call('Page.captureScreenshot',{format:'png'});fs.writeFileSync(path.join(out,name+'.png'),Buffer.from(r.data,'base64'));}};
}
try{
 const pages=await(await fetch('http://127.0.0.1:'+args.port+'/json')).json();const doctorPage=pages.find(p=>p.url.includes('/doctor?'));
 const doctor=await connect(doctorPage),patient=await connect(pages.find(p=>p.url.includes('/patient?')));
 await doctor.call('Page.reload',{ignoreCache:true});await patient.call('Page.reload',{ignoreCache:true});
 await doctor.call('Page.bringToFront');
 await until(()=>doctor.eval("!!document.querySelector('#workspace-tab-dictionary')"));
 const url=new URL(doctorPage.url),headers={Authorization:'Bearer '+url.searchParams.get('token'),'Content-Type':'application/json'};
 const api=async(route,body)=>{const r=await fetch(url.origin+'/api'+route,{method:body===undefined?'GET':'POST',headers,body:body===undefined?undefined:JSON.stringify(body)});assert.ok(r.ok,route);return r.json();};
 await api('/session/reset',{});await doctor.eval("window.clinicDesktop.setInterfaceLanguage('vi')");
 const before=(await api('/diagnostics')).state.messages.length;
 await doctor.eval("document.querySelector('#workspace-tab-dictionary').click()");
 await until(()=>doctor.eval("!!document.querySelector('.dictionary-stage canvas')"));
 await until(()=>doctor.eval("!document.querySelector('.dictionary-preview-status')"),90000);
 for(const [width,height] of [[1440,1000],[754,850],[570,840],[375,812]]){
  await doctor.call('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile:false});await sleep(100);
  const layout=await doctor.eval("({width:innerWidth,body:document.documentElement.scrollWidth,stage:document.querySelector('.dictionary-stage').getBoundingClientRect().toJSON(),words:document.querySelectorAll('.dictionary-word-list > button').length})");
  assert.ok(layout.body<=width+1,JSON.stringify(layout));assert.ok(layout.stage.height>=180);assert.ok(layout.words<=36);report.layouts.push(layout);await doctor.shot('dictionary-'+width);
 }
 await doctor.call('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false});
 await doctor.eval("document.querySelector('button[aria-label=\"Xem lại\"]').click()");await sleep(200);
 const playing=await doctor.eval("document.querySelector('.dictionary-transport input').value");await sleep(500);const later=await doctor.eval("document.querySelector('.dictionary-transport input').value");
 assert.notEqual(playing,later);report.checks.previewAdvances=true;
 await doctor.eval("document.querySelector('button[aria-label=\"Tạm dừng\"]').click()");await sleep(180);
 const paused=await doctor.eval("document.querySelector('.dictionary-transport input').value");await sleep(300);assert.equal(await doctor.eval("document.querySelector('.dictionary-transport input').value"),paused);report.checks.pause=true;
 await doctor.eval("document.querySelector('button[aria-label=\"Xem lại\"]').click();document.querySelector('.dictionary-angles button').click()");
 const setInput="const el=document.querySelector('[name=\"sign-dictionary-search\"]');Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(el,'nhiet do');el.dispatchEvent(new Event('input',{bubbles:true}));true";
 await doctor.eval(setInput);await until(()=>doctor.eval("document.querySelectorAll('.dictionary-word-list > button').length===1"));
 assert.equal(await doctor.eval("document.querySelector('.dictionary-word-list > button').innerText.trim()"),'Nhiệt độ');
 await doctor.eval("document.querySelector('.dictionary-word-list > button').click()");await until(()=>doctor.eval("!document.querySelector('.dictionary-preview-status')"));
 assert.equal((await api('/diagnostics')).state.messages.length,before);report.checks.previewDoesNotSend=true;
 await doctor.eval("window.clinicDesktop.setInterfaceLanguage('en')");await until(()=>doctor.eval("document.querySelector('.dictionary-heading h2').textContent==='Find a sign'"));
 assert.equal(await doctor.eval("document.querySelector('.dictionary-selected-heading h2').textContent"),'Nhiệt độ');report.checks.languagePreservesVietnameseWord=true;await doctor.shot('dictionary-english');
 await doctor.eval("document.querySelector('.dictionary-selected-heading .button').click()");await until(()=>doctor.eval("document.querySelector('textarea').value==='Nhiệt độ'"));
 assert.equal(await doctor.eval("document.querySelectorAll('.dictionary-stage canvas').length"),0);assert.equal((await api('/diagnostics')).state.messages.length,before);report.checks.appendAndDispose=true;
 await api('/session/reset',{});await until(()=>doctor.eval("document.querySelector('textarea').value===''") );report.checks.resetClearsInsertion=true;
 assert.equal(await patient.eval("document.querySelectorAll('button,input,select,textarea').length"),0);report.checks.patientPassive=true;
 await doctor.eval("window.clinicDesktop.setInterfaceLanguage('vi')");report.passed=true;
}catch(error){report.error=String(error.stack||error);report.passed=false;process.exitCode=1;}
finally{for(const s of sockets)s.close();fs.writeFileSync(path.join(out,'dictionary-probe.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report));}
