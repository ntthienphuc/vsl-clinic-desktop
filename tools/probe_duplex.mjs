/* Full duplex integration on actual Electron, VSL100 lip video and synthetic microphone PCM. */
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
const args=Object.fromEntries(process.argv.slice(2).map(s=>s.replace(/^--/,'').split('=')));
const out=path.resolve(args.output);fs.mkdirSync(out,{recursive:true});
const report={scope:'Actual Electron. Bundled VSL100 mouth video, synthetic doctor PCM through browser microphone pipeline. Physical echo cancellation and live human signs are not measured.',checks:{},layouts:[]};
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

try {
 const pages=await(await fetch('http://127.0.0.1:'+args.port+'/json')).json();
 const target=pages.find(p=>p.url.includes('/doctor?'));
 const doctor=await connect(target),patient=await connect(pages.find(p=>p.url.includes('/patient?')));
 const url=new URL(target.url),headers={Authorization:'Bearer '+url.searchParams.get('token'),'Content-Type':'application/json'};
 const api=async(route,body)=>{const r=await fetch(url.origin+'/api'+route,{method:body===undefined?'GET':'POST',headers,body:body===undefined?undefined:JSON.stringify(body)});if(!r.ok)throw Error(await r.text());return r.json();};
 const state=async()=> (await api('/diagnostics')).state;
 await api('/session/reset',{});
 await doctor.call('Page.reload',{ignoreCache:true}); await patient.call('Page.reload',{ignoreCache:true});
 await until(()=>doctor.eval("!!document.querySelector('.composer-card')"));
 await doctor.eval("window.clinicDesktop.setInterfaceLanguage('vi')");
 await until(()=>patient.eval('!!window.clinicDiagnostics?.mouthExpressions'),90000);
 await doctor.eval(`(()=>{
   const original=navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
   const q=window.duplexMic={opens:0,stops:0,constraints:[],original};
   navigator.mediaDevices.getUserMedia=async constraints=>{
     q.opens++;q.constraints.push(constraints);
     const ctx=new AudioContext({sampleRate:16000}),dest=ctx.createMediaStreamDestination();
     const silence=ctx.createConstantSource();silence.offset.value=0;silence.connect(dest);silence.start();
     q.context=ctx;q.destination=dest;await ctx.resume();
     dest.stream.getTracks().forEach(track=>{const stop=track.stop.bind(track);track.stop=()=>{q.stops++;stop();silence.stop();void ctx.close();};});
     return dest.stream;
   };
   q.speak=bytes=>{const ctx=q.context,buffer=ctx.createBuffer(1,bytes.length,16000);buffer.copyToChannel(Float32Array.from(bytes,n=>n/32768),0);const player=ctx.createBufferSource();player.buffer=buffer;player.connect(q.destination);player.start();};
   return true;
 })()`);
 // A phrase click sends once immediately, keeping an unrelated typed draft intact.
 await doctor.eval(`(()=>{const el=document.querySelector('#doctor-message-input');Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype,'value').set.call(el,'Nội dung đang soạn');el.dispatchEvent(new Event('input',{bubbles:true}));document.querySelector('.library-trigger').click();return true;})()`);
 await until(()=>doctor.eval("!!document.querySelector('.library-phrase-list button')"));
 const phrase=await doctor.eval("document.querySelector('.library-phrase-list button > span').childNodes[0].textContent");
 await doctor.eval("(()=>{const button=document.querySelector('.library-phrase-list button');button.click();button.click();return true;})()");
 await until(async()=> (await state()).messages.some(m=>m.role==='doctor'&&m.text===phrase));
 assert.equal((await state()).messages.filter(m=>m.role==='doctor').length,1);
 assert.equal(await doctor.eval("document.querySelector('#doctor-message-input').value"),'Nội dung đang soạn');
 assert.equal(await doctor.eval("!!document.querySelector('dialog[open]')"),false);
 report.checks.quickPhraseOneClickAndDoubleClickDedup=true;
 await api('/session/reset',{});
 await api('/conversation/configure',{mode:'auto',source:{kind:'demo',demo_id:'mm100:W068'}});
 await api('/conversation/start',{});
 await until(()=>doctor.eval("document.querySelector('.live-speech-status strong')?.textContent==='Đang nghe bác sĩ'"),90000);
 await until(async()=> (await state()).capture.status==='ended',90000);
 await until(()=>doctor.eval("(window.clinicDiagnostics?.patientVoice??[]).some(e=>e.type==='ended')"),30000);
 const initialWords=(await state()).messages.filter(m=>m.role==='patient').flatMap(m=>m.words??[]).length;
 const started=Date.now();
 const text='Bác sĩ đo nhiệt độ. Bạn có đau bụng không? Bạn cần nghỉ ngơi không? Uống nước.';
 const first=await api('/messages',{text,mode:'sign'});
 const playing=await until(async()=> {const p=(await state()).playback;return p?.status==='playing'?p:null;});
 await api('/capture/start',{kind:'demo',demo_id:'mm100:W068'});
 report.samples=[];let simultaneous=false,patientVoice=false;
 await until(async()=>{
   const s=await state(),p=s.playback;
   const words=s.messages.filter(m=>m.role==='patient').flatMap(m=>m.words??[]);
   const voice=await doctor.eval('window.clinicDiagnostics?.patientVoice??[]');
   const microphone=await doctor.eval('({opens:duplexMic.opens,stops:duplexMic.stops})');
   const newWords=words.slice(initialWords);
   if(newWords.length && p?.id===playing.id && p.status==='playing') simultaneous=true;
   patientVoice ||= voice.some(e=>e.type==='playing'&&e.recorded_at_ms>=started&&e.text==='Sốt');
   assert.notEqual(p?.status,'paused');assert.equal(microphone.opens,1);assert.equal(microphone.stops,0);
   report.samples.push({at:Date.now()-started,avatar:p?.status,playback:p?.id,patient:newWords.map(w=>w.text),pending:s.pending_count,microphone});
   return simultaneous&&patientVoice;
 },45000);
 report.checks.patientWordsAndVoiceDuringAvatar=simultaneous&&patientVoice;
 report.checks.doctorMicrophoneStaysOpen=true;
 report.microphone=await doctor.eval('({opens:duplexMic.opens,stops:duplexMic.stops,constraints:duplexMic.constraints})');
 assert.equal(report.microphone.constraints[0].audio.echoCancellation,true);
 assert.equal(report.microphone.constraints[0].audio.noiseSuppression,true);
 await doctor.shot('doctor-duplex');await patient.shot('patient-duplex');
 // The doctor can replace their own sentence while the patient keeps signing.
 const raw=fs.readFileSync(path.resolve('research/cache/avatar-041-doctor.pcm'));
 const pcm=Array.from({length:raw.length/2},(_,i)=>raw.readInt16LE(i*2));
 const spokenAt=Date.now();
 await doctor.eval(`duplexMic.speak(${JSON.stringify(pcm)});true`);
 const after=await until(async()=>{const s=await state();return s.playback?.id!==playing.id&&s.playback?.status==='playing'?s:null;},30000);
 const interrupted=after.messages.find(m=>m.id===playing.message_id);
 assert.equal(interrupted.status,'interrupted');
 assert.ok(interrupted.interrupted_elapsed_ms<playing.total_ms);
 assert.equal(after.pending_count,0);
 assert.ok(after.messages.find(m=>m.id===after.playback.message_id).speech_utterance_id);
 report.bargeIn={recognitionAndStartMs:Date.now()-spokenAt,oldTotalMs:playing.total_ms,oldElapsedMs:interrupted.interrupted_elapsed_ms,newText:after.playback.text};
 report.checks.newDoctorSpeechInterruptsImmediately=true;
 await api('/playback',{action:'complete',playback_id:playing.id,iteration:0});
 assert.equal((await state()).playback.id,after.playback.id);
 report.checks.staleCompletionCannotAffectNewSpeech=true;
 await until(()=>patient.eval(`window.clinicDiagnostics?.narration?.events?.some(e=>e.type==='playing'&&e.cycle===${JSON.stringify(after.playback.id+':0')})`));
 assert.equal(await doctor.eval('duplexMic.stops'),0);
 // A text-only interruption must also stop the old audio and mouth motion.
 await api('/messages',{text:'Cảm ơn',mode:'text'});
 await until(()=>patient.eval('window.clinicDiagnostics?.narration?.speaking===false'));
 assert.equal((await state()).playback,null);
 report.checks.textMessageStopsPreviousNarration=true;
 report.doctorSpeech=after.messages.filter(m=>m.speech_utterance_id).map(m=>({text:m.text,id:m.speech_utterance_id,status:m.status}));
 report.patientVoice=await doctor.eval('window.clinicDiagnostics?.patientVoice??[]');
 await api('/conversation/stop',{});await sleep(400);
 assert.equal((await state()).messages.length,0);assert.equal((await state()).playback,null);
 assert.equal(await patient.eval('window.clinicDiagnostics?.narration?.speaking'),false);
 assert.equal(await doctor.eval('duplexMic.stops'),1);
 await doctor.eval('navigator.mediaDevices.getUserMedia=duplexMic.original;true');
 report.checks.endClearsBothStreams=true;report.passed=true;
} catch(error) { report.error=String(error.stack||error);report.passed=false;process.exitCode=1; }
finally { for(const s of sockets)s.close();fs.writeFileSync(path.join(out,'duplex-probe.json'),JSON.stringify(report,null,2));console.log(JSON.stringify({passed:report.passed,checks:report.checks,error:report.error})); }
