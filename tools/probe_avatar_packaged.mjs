import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
const root = path.resolve(import.meta.dirname, '..');
const delay = ms => new Promise(r => setTimeout(r, ms));
const report = { scope: 'Actual Windows EXE 0.4.1; bundled audio, real renderer and prerecorded sign input. Fake silent microphone; not live-person validation.', checks: {} };
const sockets = [];
async function until(fn, timeout = 60000) {
  const start = Date.now();
  while (Date.now() - start < timeout) { const result = await fn(); if (result) return result; await delay(80); }
  throw Error('Timed out: ' + fn.toString().slice(0,160));
}
async function connect(target) {
  const socket = new WebSocket(target.webSocketDebuggerUrl); sockets.push(socket);
  await new Promise(resolve=>socket.addEventListener('open',resolve,{once:true}));
  let sequence=0; const pending=new Map();
  socket.addEventListener('message',e=>{const p=JSON.parse(e.data);if(pending.has(p.id)){pending.get(p.id)(p);pending.delete(p.id);}});
  return async expression=>{
    const id=++sequence; let timer;
    const response=new Promise((resolve,reject)=>{pending.set(id,resolve);timer=setTimeout(()=>reject(Error('CDP timeout')),15000);});
    socket.send(JSON.stringify({id,method:'Runtime.evaluate',params:{expression,returnByValue:true,awaitPromise:true}}));
    const r=await response.finally(()=>clearTimeout(timer));
    if(r.error||r.result.exceptionDetails)throw Error(JSON.stringify(r));
    return r.result.result.value;
  };
}
try {
  const pages = await until(async()=>{try{const p=await(await fetch('http://127.0.0.1:58904/json')).json();return p.some(t=>t.url.includes('/patient?'))?p:null;}catch{return null;}});
  const doctorPage=pages.find(t=>t.url.includes('/doctor?')), patientPage=pages.find(t=>t.url.includes('/patient?'));
  const doctor=await connect(doctorPage), patient=await connect(patientPage), url=new URL(doctorPage.url);
  const headers={Authorization:'Bearer '+url.searchParams.get('token'),'Content-Type':'application/json'};
  const api=async(route,body)=>{const r=await fetch(url.origin+'/api'+route,{method:body===undefined?'GET':'POST',headers,body:body===undefined?undefined:JSON.stringify(body)});if(!r.ok)throw Error(await r.text());return r.json();};
  const state=async()=>(await api('/diagnostics')).state;
  assert.equal((await(await fetch(url.origin+'/healthcheck')).json()).version,'0.4.1');
  await until(async()=>await patient("window.clinicDiagnostics?.mouthExpressions?.includes('aa')"));
  const bank=await(await fetch(url.origin+'/assets/avatar-voice/manifest.json')).json();
  assert.equal(bank.entries.length,132);
  for(const entry of bank.entries) {
    const wav=Buffer.from(await(await fetch(url.origin+'/assets/avatar-voice/'+entry.file)).arrayBuffer());
    assert.equal(crypto.createHash('sha256').update(wav).digest('hex'),entry.sha256);
  }
  report.checks.bundled132Voices=true;
  await api('/session/reset',{});
  await api('/conversation/configure',{mode:'auto',source:{kind:'demo',demo_id:'395'}});
  await api('/conversation/start',{});
  await until(async()=>(await state()).capture.status==='ended');
  await until(async()=>(await doctor('window.clinicDiagnostics?.patientVoice ?? []')).some(e=>e.type==='ended'));
  const words=await doctor('window.clinicDiagnostics.patientVoice');
  assert.deepEqual(words.filter(e=>e.type==='playing').map(e=>e.text),['Đồng ý']);
  report.patientVoice=words;report.checks.realSignToTextAndVoice=true;
  await until(async()=>/Đang nghe bác sĩ/u.test(await doctor('document.querySelector(".live-speech-status").innerText')));
  await api('/messages',{text:'Y tá đo nhiệt độ.',mode:'sign'});
  await until(async()=>{const n=await patient('window.clinicDiagnostics.narration');return n.speaking&&Object.values(n.mouth).some(v=>v>.01);});
  assert.match(await doctor('document.querySelector(".live-speech-status").innerText'),/Đang phát giọng/u);
  report.checks.micProtectedDuringNarration=true;
  await until(async()=>/Đang nghe bác sĩ/u.test(await doctor('document.querySelector(".live-speech-status").innerText')) && (await state()).playback.status==='playing');
  report.checks.micResumesDuringSilentSigning=true;
  await until(async()=>(await state()).playback.status==='completed');
  await api('/messages',{text:'Bạn có đau bụng không? Vui lòng ngồi nghỉ nhé.',mode:'sign'});
  await until(async()=>(await state()).playback.status==='playing');
  await api('/capture/start',{kind:'demo',demo_id:'395'});
  await until(async()=>(await state()).playback.pause_reason==='patient_reply');
  report.checks.clearPatientReplyYieldsAvatar=true;
  await delay(200);
  assert.equal((await patient('window.clinicDiagnostics.narration')).speaking,false);
  report.checks.yieldStopsAvatarSound=true;
  await until(async()=>(await state()).capture.status==='ended');
  await api('/playback',{action:'stop',playback_id:(await state()).playback.id});
  await until(async()=>/Đang nghe bác sĩ/u.test(await doctor('document.querySelector(".live-speech-status").innerText')));
  await doctor("Array.from(document.querySelectorAll('.live-speech-status button')).find(b=>b.textContent==='Tắt micro').click()");
  await delay(300);
  const socket=new WebSocket(url.origin.replace('http','ws')+'/ws/speech?live=true&token='+url.searchParams.get('token'));sockets.push(socket);
  const events=[];socket.addEventListener('message',e=>events.push(JSON.parse(e.data)));
  await until(()=>{const e=events.find(e=>e.type==='error');if(e)throw Error(e.message);return events.some(e=>e.type==='ready');});
  const pcm=fs.readFileSync(path.join(root,'research/cache/avatar-041-doctor.pcm'));
  const audio=Buffer.concat([Buffer.alloc(16000),pcm,Buffer.alloc(192000)]);
  for(let i=0;i<audio.length;i+=3200){socket.send(audio.subarray(i,i+3200));await delay(100);}
  await until(()=>events.some(e=>e.type==='transcript'));
  const transcripts=events.filter(e=>e.type==='transcript');assert.equal(transcripts.length,1);assert.equal(transcripts[0].delivery.status,'sent');
  report.speech=transcripts;report.checks.bundledASRAutoSendsOnce=true;
  socket.send(JSON.stringify({action:'finish'}));await delay(300);socket.close();
  await until(async()=>(await state()).playback.status==='completed');
  await api('/conversation/stop',{});await delay(300);
  assert.equal((await state()).messages.length,0);assert.equal((await patient('window.clinicDiagnostics.narration')).speaking,false);
  report.checks.endCancelsEverything=true;
  fs.writeFileSync(path.join(root,'docs/evidence/avatar-041-packaged.json'),JSON.stringify(report,null,2));
  console.log(JSON.stringify(report.checks,null,2));
} catch(error) {
  report.error=error.stack;
  fs.writeFileSync(path.join(root,'docs/evidence/avatar-041-packaged-failed.json'),JSON.stringify(report,null,2));
  console.error(error.stack);process.exitCode=1;
} finally { sockets.forEach(s=>s.close()); }
