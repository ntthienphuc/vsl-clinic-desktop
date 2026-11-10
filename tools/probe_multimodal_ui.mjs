/* Actual source/packaged Electron, real fusion, real WebGL/audio, fixed inputs. */
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {createHash} from 'node:crypto';
import {checkModeUx} from './check_mode_ux.mjs';
const root=path.resolve(import.meta.dirname,'..');
const version=JSON.parse(fs.readFileSync(path.join(root,'package.json'),'utf8')).version;
const installedExecutable=process.argv.find(a=>a.startsWith('--executable='))?.slice(13);
const packaged=process.argv.includes('--packaged')||!!installedExecutable;
assert.ok(!packaged||!fs.existsSync(path.join(root,'build/PACKAGING_IN_PROGRESS')),'Wait for packaging to complete before launching EXE verification');
const allFixtures=process.argv.includes('--12');
const repeatOnly=process.argv.includes('--repeat-only');
const originalRepeat=process.argv.includes('--repeat-original');
const runName=process.argv.find(a=>a.startsWith('--run='))?.slice(6)??'';
assert.ok(!runName||/^[a-z0-9-]+$/.test(runName),'Run name must be a simple evidence suffix');
const output=path.join(root,'../Organization/MultimodalIntegration_2026-11-09',(packaged?(allFixtures?'packaged-ui-12':'packaged-ui'):'source-ui-final')+(runName?'-'+runName:''));
fs.mkdirSync(output,{recursive:true});
const report={scope:`${version} ${packaged?'packaged EXE':'source Electron'}; fixed prerecorded samples and synthetic silent/doctor mic; no live person.`,runName,startedAt:new Date().toISOString(),checks:{},trials:[]};
const delay=ms=>new Promise(r=>setTimeout(r,ms));
async function until(fn, timeout=90000) {const start=Date.now();while(Date.now()-start<timeout){const r=await fn();if(r)return r;await delay(80);}throw Error('Timeout: '+fn.toString().slice(0,150));}
const env={...process.env};delete env.ELECTRON_RUN_AS_NODE;delete env.PYTHONPATH;delete env.PYTHONHOME;
// Avoid development Python/FFmpeg from PATH in the packaged test.
if(packaged)env.PATH=process.env.SystemRoot+'\\System32;'+process.env.SystemRoot;
const executable=installedExecutable?path.resolve(installedExecutable):packaged?path.join(root,'../App',version,'win-unpacked/VSL Clinic.exe'):path.join(root,'node_modules/electron/dist/electron.exe');
assert.ok(fs.existsSync(executable),'Application executable is missing: '+executable);
report.executable=executable;
const args=[...(packaged?[]:[root]),'--remote-debugging-port=58914',`--user-data-dir=${path.join(output,'profile')}`,
 '--use-fake-device-for-media-stream',`--use-file-for-fake-audio-capture=${path.join(root,'research/cache/mic-silence.wav')}`];
const child=spawn(executable,args,{cwd:output,env,windowsHide:true,stdio:['ignore',fs.openSync(path.join(output,'stdout.log'),'w'),fs.openSync(path.join(output,'stderr.log'),'w')]});
let desktopExitedAt=null;child.once('exit',()=>{desktopExitedAt=Date.now();});
const sockets=[];let doctor, patient, api, state, browserSocket;
async function connect(target) {
 const s=new WebSocket(target.webSocketDebuggerUrl);sockets.push(s);
 await new Promise((resolve,reject)=>{s.addEventListener('open',resolve,{once:true});s.addEventListener('error',reject,{once:true});});
 let sequence=0;const pending=new Map();
 s.addEventListener('message',e=>{const r=JSON.parse(e.data);if(pending.has(r.id)){pending.get(r.id)(r);pending.delete(r.id);}});
 const call=async(method,params={})=>{const id=++sequence;let timer;const p=new Promise((resolve,reject)=>{pending.set(id,resolve);timer=setTimeout(()=>reject(Error('CDP timeout '+method)),15000);});s.send(JSON.stringify({id,method,params}));const r=await p.finally(()=>clearTimeout(timer));if(r.error)throw Error(JSON.stringify(r));return r.result;};
 return {call,eval:async(expression)=>{const r=await call('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error(JSON.stringify(r));return r.result.value;}};
}
try {
 const pages=await until(async()=>{try{const p=await(await fetch('http://127.0.0.1:58914/json')).json();return p.some(t=>t.url.includes('/patient?'))?p:null;}catch{return null;}});
 const dpage=pages.find(t=>t.url.includes('/doctor?')),ppage=pages.find(t=>t.url.includes('/patient?'));
 doctor=await connect(dpage);patient=await connect(ppage);
 const url=new URL(dpage.url),token=url.searchParams.get('token');
 const headers={Authorization:'Bearer '+token,'Content-Type':'application/json'};
 api=async(route,body)=>{const r=await fetch(url.origin+'/api'+route,{method:body===undefined?'GET':'POST',headers,body:body===undefined?undefined:JSON.stringify(body)});if(!r.ok)throw Error(await r.text());return r.json();};
 state=async()=>(await api('/diagnostics')).state;
 assert.equal((await(await fetch(url.origin+'/healthcheck')).json()).version,version);
 await until(async()=>await patient.eval("window.clinicDiagnostics?.mouthExpressions?.includes('aa')"));
 report.graphics=await patient.eval("(()=>{const gl=document.querySelector('canvas').getContext('webgl2');const ext=gl.getExtension('WEBGL_debug_renderer_info');return {renderer:ext?gl.getParameter(ext.UNMASKED_RENDERER_WEBGL):gl.getParameter(gl.RENDERER),vendor:gl.getParameter(gl.VENDOR)};})()");
 await until(async()=>{const m=(await api('/diagnostics')).model;assert.notEqual(m.worker.status,'error',JSON.stringify(m));return m.worker.status==='ready';});
 report.worker=(await api('/diagnostics')).model;
 for(const [width,height] of [[1280,720],[1920,1080]])for(const page of [doctor,patient]){
  await page.call('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile:false});await delay(200);
  const l=await page.eval('({w:innerWidth,h:innerHeight,sh:document.documentElement.scrollHeight,sw:document.documentElement.scrollWidth})');assert.ok(l.sh<=l.h+1&&l.sw<=l.w+1,JSON.stringify(l));
 }
 for(const page of [doctor,patient])await page.call('Emulation.setDeviceMetricsOverride',{width:1280,height:720,deviceScaleFactor:1,mobile:false});
 report.checks.layout720p1080p=true;
 if(process.argv.includes('--modes'))await checkModeUx({doctor,patient,api,state,until,delay,output,report});
 await api('/conversation/configure',{mode:'auto',source:{kind:'demo',demo_id:'mm100:W068'}});
 await api('/conversation/start',{});
 if(allFixtures||repeatOnly)await api('/capture/stop',{});
 let yielded=0, autoWords=0, newWords=0, reviewDone=false;
 const ids=['W068','W066','W069','W072','W082','W093'];
 const cases=repeatOnly?[]:allFixtures?JSON.parse(fs.readFileSync(path.join(root,'../Organization/MultimodalIntegration_2026-11-09/capture/PLAN.json'),'utf8')).clips:ids.map(class_id=>({class_id}));
 report.fixturePlan=repeatOnly?'Focused repeated VSL100 word: identity, policy, audio, ASR and End; not a new 12-clip sweep.':allFixtures?'Same prespecified 12 VSL100 clips with mouth pixels: Học validation + Huy test, T01/C1; fixed fold01/seed17; no threshold tuning.':'Six staged VSL100 Huy test examples.';
 for(const [i,fixture] of cases.entries()){
  const cid=fixture.class_id;let targetGeneration;
  if(i){await api('/messages',{text:'Bạn có đau bụng không? Vui lòng ngồi nghỉ nhé.',mode:'sign'});await until(async()=>{const n=await patient.eval('window.clinicDiagnostics.narration');return n.speaking&&Object.values(n.mouth).some(v=>v>.01);});
   assert.match(await doctor.eval('document.querySelector(".live-speech-status").innerText'),/Đang phát giọng/u);
   report.checks.avatarVoiceMouthAndMicGuard=true;
   if(i===1){
    const playback=(await state()).playback;
    await api('/playback',{action:'pause',playback_id:playback.id});await delay(250);
    const n=await patient.eval('window.clinicDiagnostics.narration');assert.equal(n.speaking,false);assert.ok(Object.values(n.mouth).every(v=>v===0));
    await api('/playback',{action:'resume',playback_id:playback.id});await until(async()=>(await state()).playback.status==='playing');
    report.checks.manualPauseResumeStopsSoundAndMouth=true;
   }
  }
  if(allFixtures){
   const file=path.join('E:/Paper/MultiModel Paper/Data_Labeling_20261104/delivery/VSL100_REVIEWED_20261106_r3',fixture.video_path);
   const bytes=fs.readFileSync(file);assert.equal(createHash('sha256').update(bytes).digest('hex'),fixture.sha256);
   const form=new FormData();form.append('file',new Blob([bytes],{type:'video/mp4'}),'fixture.mp4');
   const response=await fetch(url.origin+'/api/capture/upload',{method:'POST',headers:{Authorization:'Bearer '+token},body:form});const body=await response.json();assert.ok(response.ok,JSON.stringify(body));targetGeneration=body.generation;
  }else if(i){targetGeneration=(await api('/capture/start',{kind:'demo',demo_id:'mm100:'+cid})).generation;}
  const s=await until(async()=>{const s=await state();return s.current_result&&(targetGeneration===undefined||s.capture.generation===targetGeneration)?s:null;});const word=s.current_result;
  assert.equal(word.predictions[0].model_id,null);assert.equal(word.recognition.actual_mode,'fusion');
  assert.equal(s.patient_turn.status,'streaming');
  const trial={expected:cid,fixture,word,capture:s.capture,atResultPlayback:s.playback};report.trials.push(trial);
  if(!word.uncertain){
   assert.equal(word.predictions[0].class_id,cid,'Wrong committed word');autoWords++;if(['W068','W069','W072','W082'].includes(cid))newWords++;
   await until(async()=>(await doctor.eval('window.clinicDiagnostics?.patientVoice??[]')).some(e=>e.type==='playing'&&e.message_id===word.id));
   if(i){assert.equal(s.playback.pause_reason,'patient_reply');yielded++;await delay(200);assert.equal((await patient.eval('window.clinicDiagnostics.narration')).speaking,false);}
  }else{
   assert.ok(!(await doctor.eval('window.clinicDiagnostics?.patientVoice??[]')).some(e=>e.type==='playing'&&e.message_id===word.id));
   if(!reviewDone){
    await until(()=>doctor.eval("!!document.querySelector('.word-review[open] input[aria-label=\"Nội dung xác nhận\"]')"));
    await doctor.eval("(()=>{const el=document.querySelector('input[aria-label=\"Nội dung xác nhận\"]');Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(el,'Mệt');el.dispatchEvent(new Event('input',{bubbles:true}));})()");
    await until(()=>doctor.eval("[...document.querySelectorAll('.confirm-row button')].some(b=>!b.disabled)"));
    assert.ok(await doctor.eval("(()=>{const row=document.querySelector('.confirm-row').getBoundingClientRect();const card=document.querySelector('.recognition-card').getBoundingClientRect();return row.top>=card.top&&row.bottom<=card.bottom&&row.bottom<=innerHeight;})()"),'Review input and confirmation must be visible without scrolling');
    const reviewShot=await doctor.call('Page.captureScreenshot',{format:'png'});fs.writeFileSync(path.join(output,'word-review.png'),Buffer.from(reviewShot.data,'base64'));
    await doctor.eval("document.querySelector('.confirm-row button').click()");
    await until(async()=>(await doctor.eval('window.clinicDiagnostics?.patientVoice??[]')).some(e=>e.type==='playing'&&e.message_id===word.id&&e.text==='Mệt'));
    reviewDone=true;trial.correctionApplied=true;report.checks.reviewCorrectionUsesCorrectVoice=true;
   }
  }
  await until(async()=>(await state()).capture.status==='ended');
  await until(async()=>(await state()).patient_turn===null);
  trial.voice=await doctor.eval('window.clinicDiagnostics?.patientVoice??[]');
  trial.paint=(await api('/diagnostics')).metrics.filter(e=>e.message_id===word.id&&e.event==='doctor_result_painted');
  assert.equal(trial.voice.filter(e=>e.type==='playing'&&e.message_id===word.id).length,word.uncertain&&!trial.correctionApplied?0:1);
  const playback=(await state()).playback;if(playback)await api('/playback',{action:'stop',playback_id:playback.id});
  console.log(JSON.stringify({sample:cid,recognized:word.text,committed:!word.uncertain,policy:word.recognition.policy,quality:word.metrics.quality.input_fps}));
  fs.writeFileSync(path.join(output,'PROGRESS.json'),JSON.stringify(report,null,2));
 }
 if(!repeatOnly)assert.ok(autoWords>=2&&newWords>=1&&yielded>=1,JSON.stringify({autoWords,newWords,yielded}));
 report.counts={trials:cases.length,autoWords,newWords,yielded};
 if(!repeatOnly){report.checks.realFusionIncrementalWordsVoiceAndReview=true;report.checks.noRepeatWhenTurnEnds=true;report.checks.realPatientReplyYieldsAvatar=true;}
 const repeatedFile=path.join(root,'../Organization/MultimodalIntegration_2026-11-09',
  originalRepeat?'fusion_explore/repeat-original-vsl100.mp4':'stress/repeat-two-fever.mp4');
 report.repeatFixture={file:repeatedFile,sourceEncodingPreserved:originalRepeat,repeatOnly};
 const form=new FormData();form.append('file',new Blob([fs.readFileSync(repeatedFile)],{type:'video/mp4'}),'repeat-two-fever.mp4');
 const upload=await fetch(url.origin+'/api/capture/upload',{method:'POST',headers:{Authorization:'Bearer '+token},body:form});const uploadBody=await upload.json();assert.ok(upload.ok,JSON.stringify(uploadBody));
 const firstRepeat=await until(async()=>{const s=await state();return s.capture.generation===uploadBody.generation&&s.current_result?s:null;});
 assert.notEqual(firstRepeat.capture.status,'ended');assert.equal(firstRepeat.current_result.text,'Sốt');
 report.repeat={first:firstRepeat.current_result,firstCapture:firstRepeat.capture,originalDecisions:[],qaConfirmations:0};
 async function verifyRepeatedReadout(word){
  report.repeat.originalDecisions.push({id:word.id,text:word.text,uncertain:word.uncertain,recognition:word.recognition});
  if(word.uncertain){
   assert.ok(!(await doctor.eval('window.clinicDiagnostics?.patientVoice??[]')).some(e=>e.type==='playing'&&e.message_id===word.id));
   await api('/confirm',{message_id:word.id,text:'Sốt'});report.repeat.qaConfirmations++;
  }
  await until(async()=>(await doctor.eval('window.clinicDiagnostics?.patientVoice??[]')).some(e=>e.type==='playing'&&e.message_id===word.id));
  assert.notEqual((await state()).patient_turn,null,'Readout must occur before turn grouping');
 }
 await verifyRepeatedReadout(firstRepeat.current_result);
 assert.notEqual((await state()).capture.status,'ended','First word must be read while the repeated-word stream continues');
 const secondRepeat=await until(async()=>{const s=await state();return s.capture.generation===uploadBody.generation&&s.current_result&&s.current_result.id!==firstRepeat.current_result.id?s:null;});
 assert.equal(secondRepeat.current_result.text,'Sốt');
 await verifyRepeatedReadout(secondRepeat.current_result);
 await until(async()=>(await state()).capture.status==='ended');await until(async()=>(await state()).patient_turn===null);
 const repeated=(await state()).messages.flatMap(x=>x.words??[]).filter(w=>w.recognition?.segment_id?.startsWith(firstRepeat.current_result.recognition.segment_id.split(':')[0]+':'));
 assert.deepEqual(repeated.map(w=>[w.text,w.uncertain]),[['Sốt',false],['Sốt',false]]);
 const repeatVoice=await doctor.eval('window.clinicDiagnostics?.patientVoice??[]');
 for(const w of repeated)assert.equal(repeatVoice.filter(e=>e.message_id===w.id&&e.type==='playing').length,1);
 report.repeat.words=repeated;report.repeat.voice=repeatVoice.filter(e=>repeated.some(w=>w.id===e.message_id));
 report.checks.sameStreamRepeatedWordSpokenOnceEachBeforeTurnEnd=true;
 // A closed-set recognizer may require review on a repeated word. Record that
 // separately; identity/voice/lifecycle checks must respect the real policy.
 await until(async()=>/Đang nghe bác sĩ/u.test(await doctor.eval('document.querySelector(".live-speech-status").innerText')));
 await doctor.eval("Array.from(document.querySelectorAll('.live-speech-status button')).find(b=>b.textContent==='Tắt micro').click()");await delay(300);
 const speech=new WebSocket(url.origin.replace('http','ws')+'/ws/speech?live=true&token='+token);sockets.push(speech);const ev=[];speech.addEventListener('message',e=>ev.push(JSON.parse(e.data)));
 await until(()=>{const err=ev.find(e=>e.type==='error');if(err)throw Error(err.message);return ev.some(e=>e.type==='ready');});
 if(process.argv.includes('--modes')){
  // Fixed electrical noises through the real packaged WebSocket/VAD/ASR path.
  // Not room recordings or a claim of speaker identification.
  const negative=Buffer.alloc(8*16000*2);let seed=73;
  for(let i=0;i<8*16000;i++){
   seed=(Math.imul(seed,1664525)+1013904223)>>>0;
   const seconds=i/16000;
   const value=seconds<2?0:seconds<4?((seed/4294967296)*2-1)*.04:seconds<6?Math.sin(i*2*Math.PI*60/16000)*.05:(i%8000<120?((seed/4294967296)*2-1)*.18:0);
   negative.writeInt16LE(Math.round(value*32767),i*2);
  }
  for(let i=0;i<negative.length;i+=3200){speech.send(negative.subarray(i,i+3200));await delay(100);}
  await delay(1000);assert.equal(ev.filter(e=>e.type==='transcript').length,0);
  report.speechNegative={seconds:8,kinds:['silence','hiss','hum','keyboard-like impulses'],transcripts:0};
  report.checks.realSpeechSocketRejectsSyntheticNoise=true;
 }
 const audio=Buffer.concat([Buffer.alloc(16000),fs.readFileSync(path.join(root,'research/cache/avatar-041-doctor.pcm')),Buffer.alloc(192000)]);
 for(let i=0;i<audio.length;i+=3200){speech.send(audio.subarray(i,i+3200));await delay(100);}
 await until(()=>ev.some(e=>e.type==='transcript'));report.speech=ev.filter(e=>e.type==='transcript');assert.equal(report.speech.length,1);assert.equal(report.speech[0].delivery.status,'sent');
 speech.send(JSON.stringify({action:'finish'}));await delay(200);speech.close();report.checks.realBundledASRSendsOnce=true;
 await until(async()=>(await state()).playback.status==='completed');
 for(const [name,page] of [['doctor-conversation',doctor],['patient-conversation',patient]]){const s=await page.call('Page.captureScreenshot',{format:'png'});fs.writeFileSync(path.join(output,name+'.png'),Buffer.from(s.data,'base64'));}
 await api('/messages',{text:'Bạn có đau bụng không?',mode:'sign'});await api('/capture/start',{kind:'demo',demo_id:'mm100:W068'});
 await until(async()=>(await state()).capture.status==='signing');await api('/conversation/stop',process.argv.includes('--modes')?{keep_temporary:true}:{});await delay(6000);
 const ended=await state();assert.equal(ended.messages.length,0);assert.equal(ended.current_result,null);assert.equal(ended.conversation.status,'idle');assert.equal((await patient.eval('window.clinicDiagnostics.narration')).speaking,false);
 report.checks.endFencesFusionAndAudio=true;
 if(process.argv.includes('--modes')){
  const saved=await api('/session/temporary');assert.ok(saved.messages.length>0);
  assert.equal((await state()).playback,null);
  await api('/session/temporary/discard',{});assert.equal(await api('/session/temporary'),null);
  assert.equal((await state()).messages.length,0);
  report.checks.temporaryHistoryNeverReplaysAndDiscards=true;
 }
 for(const [name,page] of [['doctor',doctor],['patient',patient]]){const s=await page.call('Page.captureScreenshot',{format:'png'});fs.writeFileSync(path.join(output,name+'.png'),Buffer.from(s.data,'base64'));}
 report.passed=true;
}catch(error){report.error=error.stack;report.passed=false;process.exitCode=1;console.error(error.stack);}
finally{
 try{report.finalDiagnostics=await api('/diagnostics');}catch{}
 fs.writeFileSync(path.join(output,'REPORT.json'),JSON.stringify(report,null,2));
 console.log(JSON.stringify({passed:report.passed,checks:report.checks,counts:report.counts,error:report.error}));
 const shutdownStarted=Date.now();
 try{await doctor?.eval('void window.clinicDesktop.quit()');}catch{}
 sockets.forEach(s=>s.close());
 const exitStarted=Date.now();
 while(child.exitCode===null&&child.signalCode===null&&Date.now()-exitStarted<35000)await delay(100);
 report.shutdownMs=(desktopExitedAt??Date.now())-shutdownStarted;
 if(child.exitCode===null&&child.signalCode===null){child.kill();report.shutdownForced=true;}
 report.desktopExit=child.exitCode;
 const workerPid=report.worker?.worker?.pid;
 let workerStillAlive=false;
 if(workerPid){try{process.kill(workerPid,0);workerStillAlive=true;}catch(error){if(error.code!=='ESRCH')throw error;}}
 report.workerExited=!!workerPid&&!workerStillAlive;
 const desktopLog=fs.readFileSync(path.join(output,'profile/clinic-engine.log'),'utf8');
 report.engineGracefulExit=/engine exit 0, signal null/.test(desktopLog)&&!desktopLog.includes('graceful shutdown timed out');
 report.checks.cleanDesktopEngineAndWorkerExit=report.desktopExit===0&&!report.shutdownForced&&report.workerExited&&report.engineGracefulExit;
 if(!report.checks.cleanDesktopEngineAndWorkerExit){report.passed=false;process.exitCode=1;}
 fs.writeFileSync(path.join(output,'REPORT.json'),JSON.stringify(report,null,2));
 console.log(JSON.stringify({cleanExit:report.checks.cleanDesktopEngineAndWorkerExit,desktopExit:report.desktopExit,workerExited:report.workerExited,engineGracefulExit:report.engineGracefulExit,shutdownMs:report.shutdownMs}));
}
