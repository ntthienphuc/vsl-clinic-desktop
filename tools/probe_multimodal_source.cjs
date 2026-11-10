/* Real Electron/React/WebGL, real multimodal worker, fixed video and synthetic ASR. */
const { app, BrowserWindow } = require('electron');
const fs = require('node:fs'), path = require('node:path'), assert = require('node:assert/strict');
const root = path.resolve(__dirname, '..');
const output = path.join(root, '../Organization/MultimodalIntegration_2026-11-09/source-ui');
fs.mkdirSync(output, {recursive:true});
process.env.CLINIC_QA = '1'; process.env.CLINIC_QA_PORT = '58910';
app.setPath('userData', path.join(output, 'profile'));
app.commandLine.appendSwitch('use-fake-device-for-media-stream');
app.commandLine.appendSwitch('use-file-for-fake-audio-capture', path.join(root, 'research/cache/mic-silence.wav'));
app.commandLine.appendSwitch('remote-debugging-port', '58911');
require('../desktop/main.cjs');
const origin = 'http://127.0.0.1:58910';
const headers = {Authorization:'Bearer clinic-test-session','Content-Type':'application/json'};
const delay = ms => new Promise(r=>setTimeout(r,ms));
async function until(fn, timeout=90000) {
  const start=Date.now();
  while(Date.now()-start<timeout) { const value=await fn(); if(value)return value; await delay(80); }
  throw Error('Timed out: '+fn.toString().slice(0,160));
}
async function api(route,body) {
  const r=await fetch(origin+'/api'+route,{method:body===undefined?'GET':'POST',headers,body:body===undefined?undefined:JSON.stringify(body)});
  if(!r.ok)throw Error(await r.text());return r.json();
}
const state=async()=>(await api('/diagnostics')).state;
const report={scope:'0.5.0 source Electron windows; real fusion/checkpoints/video; silent fake mic and prerecorded synthetic speech. No live webcam participant.',checks:{},timings:[]};
void app.whenReady().then(async()=>{
  let socket;
  try {
    await until(async()=>{try{return (await state()).clients.patient>0;}catch{return false;}});
    const windows=BrowserWindow.getAllWindows();
    const doctor=windows.find(w=>new URL(w.webContents.getURL()).pathname==='/doctor');
    const patient=windows.find(w=>new URL(w.webContents.getURL()).pathname==='/patient');
    doctor.setTitle('VSL Clinic · Bác sĩ · QA 0.5.0');
    patient.setTitle('VSL Clinic · Người bệnh · QA 0.5.0');
    const d=js=>doctor.webContents.executeJavaScript(js), p=js=>patient.webContents.executeJavaScript(js);
    await until(async()=>await p("window.clinicDiagnostics?.mouthExpressions?.includes('aa')"));
    for(const [width,height] of [[1280,720],[1920,1080]]) {
      for(const w of [doctor,patient]) {
        w.setContentSize(width,height); await delay(200);
        const layout=await w.webContents.executeJavaScript('({w:innerWidth,h:innerHeight,sh:document.documentElement.scrollHeight,sw:document.documentElement.scrollWidth})');
        assert.ok(layout.sh<=layout.h+1&&layout.sw<=layout.w+1,JSON.stringify(layout));
      }
    }
    report.checks.layout720p1080p=true;
    doctor.setContentSize(1280,720);patient.setContentSize(1280,720);
    await until(async()=>(await api('/diagnostics')).model.worker.status==='ready');
    await api('/conversation/configure',{mode:'auto',source:{kind:'demo',demo_id:'mm100:W068'}});
    await api('/conversation/start',{});
    const seen=await until(async()=>{const s=await state();return s.current_result?s:null;});
    report.firstRecognition=seen.current_result;
    report.captureAtFirstRecognition=seen.capture;
    assert.equal(seen.current_result.text,'Sốt');
    assert.equal(seen.current_result.uncertain,false);
    assert.equal(seen.current_result.predictions[0].model_id,null);
    assert.equal(seen.current_result.recognition.actual_mode,'fusion');
    assert.equal(seen.patient_turn.status,'streaming');
    await until(async()=>(await d('window.clinicDiagnostics?.patientVoice??[]')).some(e=>e.type==='playing'&&e.text==='Sốt'));
    report.timings.push(seen.current_result.metrics);
    report.patientVoice=await d('window.clinicDiagnostics.patientVoice');
    report.checks.feverRealFusionToIncrementalTextVoice=true;
    await until(async()=>(await state()).capture.status==='ended');
    await until(async()=>(await state()).messages[0]?.status==='candidate');
    const words=await d('window.clinicDiagnostics.patientVoice');
    assert.equal(words.filter(e=>e.type==='playing'&&e.text==='Sốt').length,1);
    report.checks.turnFinalizationDoesNotRepeatVoice=true;
    await api('/messages',{text:'Bạn có đau bụng không? Vui lòng ngồi nghỉ nhé.',mode:'sign'});
    await until(async()=>{const n=await p('window.clinicDiagnostics.narration');return n.speaking&&Object.values(n.mouth).some(v=>v>.01);});
    const narration=await p('window.clinicDiagnostics.narration');
    report.narrationSample=narration;
    assert.match(await d('document.querySelector(".live-speech-status").innerText'),/Đang phát giọng/u);
    report.checks.avatarVoiceMouthAndMicGuard=true;
    let playback=(await state()).playback;
    await api('/playback',{action:'pause',playback_id:playback.id});
    await delay(250);
    assert.equal((await p('window.clinicDiagnostics.narration')).speaking,false);
    assert.ok(Object.values((await p('window.clinicDiagnostics.narration')).mouth).every(v=>v===0));
    await api('/playback',{action:'resume',playback_id:playback.id});
    await until(async()=>(await state()).playback.status==='playing');
    await api('/capture/start',{kind:'demo',demo_id:'mm100:W068'});
    await until(async()=>(await state()).playback.pause_reason==='patient_reply');
    await delay(200);
    assert.equal((await p('window.clinicDiagnostics.narration')).speaking,false);
    report.checks.realFusionReplyYieldsAvatar=true;
    await until(async()=>(await state()).capture.status==='ended');
    await api('/playback',{action:'stop',playback_id:(await state()).playback.id});
    await until(async()=>/Đang nghe bác sĩ/u.test(await d('document.querySelector(".live-speech-status").innerText')));
    report.checks.micRecovers=true;
    await d("Array.from(document.querySelectorAll('.live-speech-status button')).find(b=>b.textContent==='Tắt micro').click()");
    await delay(300);
    socket=new WebSocket(origin.replace('http','ws')+'/ws/speech?live=true&token=clinic-test-session');
    const events=[];socket.addEventListener('message',e=>events.push(JSON.parse(e.data)));
    await until(()=>{const e=events.find(e=>e.type==='error');if(e)throw Error(e.message);return events.some(e=>e.type==='ready');});
    const pcm=fs.readFileSync(path.join(root,'research/cache/avatar-041-doctor.pcm'));
    const audio=Buffer.concat([Buffer.alloc(16000),pcm,Buffer.alloc(192000)]);
    for(let i=0;i<audio.length;i+=3200){socket.send(audio.subarray(i,i+3200));await delay(100);}
    await until(()=>events.some(e=>e.type==='transcript'));
    const transcripts=events.filter(e=>e.type==='transcript');
    assert.equal(transcripts.length,1);assert.equal(transcripts[0].delivery.status,'sent');
    report.speech=transcripts;report.checks.syntheticASRStillSendsOnce=true;
    socket.send(JSON.stringify({action:'finish'}));await delay(200);socket.close();
    await until(async()=>(await state()).playback.status==='completed');
    // End during active capture + avatar voice, then wait beyond the old video.
    await api('/messages',{text:'Bạn có đau bụng không?',mode:'sign'});
    await api('/capture/start',{kind:'demo',demo_id:'mm100:W068'});
    await until(async()=>(await state()).capture.status==='signing');
    await api('/conversation/stop',{});
    await delay(6000);
    const ended=await state();
    assert.equal(ended.messages.length,0);assert.equal(ended.current_result,null);
    assert.equal(ended.conversation.status,'idle');
    assert.equal((await p('window.clinicDiagnostics.narration')).speaking,false);
    assert.equal((await d('window.clinicDiagnostics.patientVoice')).at(-1)?.type!=='playing',true);
    report.checks.endFencesLateFusionAndVoice=true;
    fs.writeFileSync(path.join(output,'doctor.png'),(await doctor.webContents.capturePage()).toPNG());
    fs.writeFileSync(path.join(output,'patient.png'),(await patient.webContents.capturePage()).toPNG());
    report.passed=true;
  } catch(error) { report.error=error.stack;report.passed=false;console.error(error.stack); }
  finally {
    socket?.close();
    try { report.finalDiagnostics=await api('/diagnostics'); } catch {}
    fs.writeFileSync(path.join(output,'REPORT.json'),JSON.stringify(report,null,2));
    console.log(JSON.stringify({passed:report.passed,checks:report.checks,error:report.error},null,2));
    app.quit();
  }
});
