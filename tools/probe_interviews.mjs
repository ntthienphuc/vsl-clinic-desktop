/* Rehearse the installed package using its opt-in local debugging endpoint. */
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { spawn } from 'node:child_process';
const root = path.resolve(import.meta.dirname, '..');
const out = path.join(root, 'docs/evidence');
const pause = ms => new Promise(r => setTimeout(r, ms));
async function until(fn, timeout=60000) {
  const start=Date.now();
  while (Date.now()-start<timeout) { const value=await fn(); if(value) return value; await pause(100); }
  throw new Error('Timeout');
}
async function connect(target) {
  const socket = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise(r=>socket.addEventListener('open',r,{once:true}));
  let sequence=0; const pending=new Map();
  socket.addEventListener('message',e=>{const m=JSON.parse(e.data); if(pending.has(m.id)){pending.get(m.id)(m);pending.delete(m.id);}});
  async function send(method,params={}) {
    const id=++sequence;const result=new Promise(r=>pending.set(id,r));socket.send(JSON.stringify({id,method,params}));
    let timer;const m=await Promise.race([result,new Promise((_,reject)=>{timer=setTimeout(()=>reject(new Error('CDP timeout: '+method)),15000);})]).finally(()=>clearTimeout(timer));if(m.error)throw new Error(JSON.stringify(m.error));return m.result;
  }
  return {socket,send, async evaluate(expression){const r=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw new Error(JSON.stringify(r.exceptionDetails));return r.result.value;}};
}
const targets=await until(async()=>{try {const a=await(await fetch('http://127.0.0.1:58901/json')).json();return a.filter(p=>p.type==='page').length>=2?a:null;}catch{return null;}});
const doctorTarget=targets.find(p=>new URL(p.url).pathname==='/doctor');
const patientTarget=targets.find(p=>new URL(p.url).pathname==='/patient');
const doctor=await connect(doctorTarget),patient=await connect(patientTarget);
const url=new URL(doctorTarget.url),token=url.searchParams.get('token');
const headers={Authorization:'Bearer '+token,'Content-Type':'application/json'};
async function api(route,body){const r=await fetch(url.origin+'/api'+route,{method:body?'POST':'GET',headers,body:body?JSON.stringify(body):undefined});if(!r.ok)throw new Error(await r.text());return r.json();}
async function python(script,args){return new Promise(resolve=>{const c=spawn(path.join(root,'.venv/Scripts/python.exe'),['-X','utf8',script,'--url',url.origin,'--token',token,...args],{cwd:root,windowsHide:true,stdio:'inherit'});c.on('exit',resolve);});}
const report={scope:'Actual 0.3.6 EXE; fixed reference videos and synthetic Vietnamese audio, not live-user validation.',layouts:[],motionFrames:[]};
try {
  await until(async()=>(await api('/bootstrap')).state.clients.patient>0);
  assert.match(await doctor.evaluate('document.body.innerText'),/Demo 0\.3\.6/u);
  for (const word of ['Thế nào','Bao giờ']) {
    const message=await api('/messages',{text:word,mode:'sign'});
    await until(async()=>{const s=(await api('/diagnostics')).state;return s.playback.status==='playing';});
    await pause(1100);
    const frame=await patient.send('Page.captureScreenshot',{format:'png'});
    const name=word==='Thế nào'?'how':'when';fs.writeFileSync(path.join(out,`interview-motion-${name}.png`),Buffer.from(frame.data,'base64'));
    report.motionFrames.push(await patient.evaluate('window.clinicDiagnostics'));
    await until(async()=>(await api('/diagnostics')).state.messages.find(m=>m.id===message.id).status==='completed');
  }
  report.videoExit=await python('tools/probe_rehearsals.py',['--kit','../App/0.3.6/win-unpacked/demo/HOI_BENH_2026-11-01','--output','docs/evidence/interview-packaged-2026-11-01.json']);
  for (const [role,page] of [['doctor',doctor],['patient',patient]]) {
    for (const [width,height] of [[1280,720],[1920,1080]]) {
      await page.send('Page.bringToFront');
      await page.send('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile:false});await pause(250);
      const layout=await page.evaluate('({width:innerWidth,height:innerHeight,scrollWidth:document.documentElement.scrollWidth,scrollHeight:document.documentElement.scrollHeight})');
      assert.ok(layout.scrollHeight<=height+1 && layout.scrollWidth<=width+1);report.layouts.push({role,...layout});
      const frame=await page.send('Page.captureScreenshot',{format:'png'});fs.writeFileSync(path.join(out,`interview-${role}-${width}.png`),Buffer.from(frame.data,'base64'));
    }
  }
  report.speechExit=await python('tools/probe_rehearsal_speech.py',['--catalog','demo/scenarios-v0.3.6.json','--output','docs/evidence/interview-speech-2026-11-01.json']);
  report.passed=report.videoExit===0&&report.speechExit===0;
  assert.ok(report.passed);
} catch(error){report.error=String(error.stack||error);process.exitCode=1;}
finally {fs.writeFileSync(path.join(out,'interview-runtime-2026-11-01.json'),JSON.stringify(report,null,2));if(process.argv.includes('--quit'))await doctor.evaluate('window.clinicDesktop.quit()');doctor.socket.close();patient.socket.close();console.log(JSON.stringify({passed:report.passed,error:report.error}));}
