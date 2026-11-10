/* Electron/real API QA; synthetic speech creates actual review drafts. */
const {app,BrowserWindow}=require('electron');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..'),out=path.join(root,'docs/evidence');
process.env.CLINIC_QA='1';process.env.CLINIC_QA_PORT='58897';
app.setPath('userData',path.join(root,'research/cache/workspace-037-profile'));
app.commandLine.appendSwitch('use-fake-device-for-media-stream');
app.commandLine.appendSwitch('use-file-for-fake-audio-capture',path.join(root,'research/cache/mic-silence.wav'));
require('../desktop/main.cjs');
const origin='http://127.0.0.1:58897',headers={Authorization:'Bearer clinic-test-session'};
const wait=ms=>new Promise(r=>setTimeout(r,ms));
async function until(fn,max=60000){const start=Date.now();while(Date.now()-start<max){const value=await fn();if(value)return value;await wait(70);}throw new Error('Timed out');}
async function api(endpoint,body){const r=await fetch(origin+'/api'+endpoint,{method:body===undefined?'GET':'POST',headers:{...headers,'Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body)});if(!r.ok)throw new Error(await r.text());return r.json();}
async function state(){return(await api('/diagnostics')).state;}
const report={scope:'Real Electron windows/API, real model video and synthetic speech, no human microphone validation.',layouts:[],checks:{}};
void app.whenReady().then(async()=>{
 await until(async()=>{try{return(await api('/bootstrap')).state.clients.patient>0;}catch{return false;}},90000);
 const doctor=BrowserWindow.getAllWindows().find(w=>new URL(w.webContents.getURL()).pathname==='/doctor');
 let patient=BrowserWindow.getAllWindows().find(w=>new URL(w.webContents.getURL()).pathname==='/patient');
 const evaluate=js=>doctor.webContents.executeJavaScript(js);
 await api('/conversation/configure',{mode:'auto',source:{kind:'demo',demo_id:'395'}});await api('/conversation/start',{});
 await until(async()=>{const s=await state();return s.capture.status==='ended'&&!s.patient_turn;});await wait(1000);
 await until(async()=>await evaluate("Array.from(document.querySelectorAll('.live-speech-status button')).some(b=>b.textContent==='Tắt micro')"));
 await evaluate("Array.from(document.querySelectorAll('.live-speech-status button')).find(b=>b.textContent==='Tắt micro').click()");await wait(300);
 const ws=new WebSocket(origin.replace('http','ws')+'/ws/speech?live=true&token=clinic-test-session');
 const events=[];ws.addEventListener('message',e=>events.push(JSON.parse(e.data)));
 await until(()=>{const error=events.find(e=>e.type==='error');if(error)throw new Error(error.message);return events.some(e=>e.type==='ready');});
 const pcm=fs.readFileSync(path.join(root,'research/cache/workspace-unsupported.pcm'));
 const audio=Buffer.concat([Buffer.alloc(16000),pcm,Buffer.alloc(32000)]);
 for(let i=0;i<9;i++){
   for(let offset=0;offset<audio.length;offset+=3200){ws.send(audio.subarray(offset,offset+3200));await wait(100);}
   await until(async()=>(await state()).speech_drafts.length===i+1);
   console.log('Review drafts:',i+1);
 }
 ws.send(JSON.stringify({action:'finish'}));await until(()=>events.some(e=>e.type==='finished'));ws.close();
 assert.equal(events.filter(e=>e.type==='transcript').length,9);report.checks.nineActualDrafts=true;
 for(let i=0;i<6;i++)await api('/messages',{text:i%2?'Người bệnh có thể nghỉ một nhịp rồi tiếp tục.':'Bác sĩ đang hỏi thêm về tình trạng hiện tại.',mode:'text'});
 const message=await api('/messages',{text:'Y tá đo nhiệt độ.',mode:'sign'});
 await until(async()=>(await state()).playback.status==='playing');
 const first=await state();const id=first.playback.id;
 await wait(600);await api('/playback',{action:'pause',playback_id:id});await wait(200);
 const frozen=await evaluate("Number(document.querySelector('[role=progressbar]').getAttribute('aria-valuenow'))");await wait(500);
 assert.equal(await evaluate("Number(document.querySelector('[role=progressbar]').getAttribute('aria-valuenow'))"),frozen);
 report.checks.pauseFrozen=true;
 await api('/playback',{action:'speed',playback_id:id,rate:.5});await api('/playback',{action:'resume',playback_id:id});await wait(700);
 assert.ok(await evaluate("Number(document.querySelector('[role=progressbar]').getAttribute('aria-valuenow'))")>frozen);
 report.checks.resumeAndSpeed=true;
 patient.close();await until(async()=>(await state()).playback.pause_reason==='patient_disconnected');
 assert.match(await evaluate('document.body.innerText'),/Avatar đang tạm dừng/);
 await evaluate('window.clinicDesktop.openPatient()');await until(async()=>(await state()).clients.patient>0);
 patient=BrowserWindow.getAllWindows().find(w=>new URL(w.webContents.getURL()).pathname==='/patient');
 assert.equal((await state()).playback.status,'paused');report.checks.disconnectFrozen=true;
 for(const [width,height]of [[1280,720],[1920,1080]])for(const [role,window]of [['doctor',doctor],['patient',patient]]){
   window.setContentSize(width,height);await wait(300);
   const layout=await window.webContents.executeJavaScript(`(()=>{const box=s=>document.querySelector(s)?.getBoundingClientRect();return {width:innerWidth,height:innerHeight,scrollWidth:document.documentElement.scrollWidth,scrollHeight:document.documentElement.scrollHeight,sidebar:box('.doctor-main')?.width,chat:box('.doctor-aside')?.width,drafts:box('.compact-drafts')?.height};})()`);
   assert.ok(layout.scrollWidth<=width+1&&layout.scrollHeight<=height+1,JSON.stringify(layout));
   if(role==='doctor'){assert.ok(layout.chat>=layout.sidebar*1.6);assert.ok(layout.drafts<125);}
   report.layouts.push({role,...layout});fs.writeFileSync(path.join(out,`workspace-037-${role}-${width}.png`),(await window.webContents.capturePage()).toPNG());
 }
 await evaluate("document.querySelector('.draft-summary').click()");await until(async()=>await evaluate("!!document.querySelector('dialog[open] .speech-review-item')"));
 assert.match(await evaluate("document.querySelector('dialog[open]').innerText"),/Chưa có đủ ký hiệu/);
 assert.ok(await evaluate("Array.from(document.querySelectorAll('dialog[open] button')).find(b=>b.textContent.includes('Gửi ký hiệu')).disabled"));
 await evaluate("document.querySelector('dialog[open] [aria-label=\"Đóng cửa sổ\"]').click()");report.checks.reviewDialog=true;
 await api('/playback',{action:'resume',playback_id:id});
 await until(async()=>(await state()).messages.find(m=>m.id===message.id).status==='completed');
 assert.equal(await evaluate("Number(document.querySelector('[role=progressbar]').getAttribute('aria-valuenow'))"),100);report.checks.completedProgress=true;
 await api('/playback',{action:'replay',playback_id:id});await until(async()=>(await state()).playback.status==='playing');
 assert.ok(await evaluate("Number(document.querySelector('[role=progressbar]').getAttribute('aria-valuenow'))")<25);report.checks.replayRestarted=true;
 const before=await state();await evaluate("document.querySelector('.keep-temporary input').click()");
 await evaluate("Array.from(document.querySelectorAll('.conversation-bar button')).find(b=>b.textContent==='Kết thúc').click()");
 await until(async()=>(await state()).session_id!==before.session_id);await wait(1200);
 const ended=await state();assert.equal(ended.messages.length,0);assert.equal(ended.speech_drafts.length,0);assert.equal(ended.playback,null);assert.equal(ended.current_result,null);assert.equal(ended.capture.status,'idle');
 assert.ok(ended.temporary);assert.equal(ended.temporary.draft_count,9);
 assert.equal(await evaluate("document.querySelector('[aria-label=\"Nội dung gửi người bệnh\"]').value"),'');
 assert.equal(await evaluate("!!document.querySelector('[role=progressbar]')"),false);
 assert.match(await patient.webContents.executeJavaScript('document.body.innerText'),/Lời nhắn của bác sĩ sẽ xuất hiện ở đây/);
 report.checks.endClearsBothScreens=true;
 await evaluate("Array.from(document.querySelectorAll('button')).find(b=>b.textContent===' Bản tạm'||b.textContent.trim()==='Bản tạm').click()");
 await until(async()=>await evaluate("!!document.querySelector('.temporary-conversation .message')"));
 const saved=await api('/session/temporary');assert.equal(saved.speech_drafts.length,9);assert.equal((await state()).messages.length,0);report.checks.temporaryReadOnly=true;
 await evaluate("Array.from(document.querySelectorAll('dialog[open] button')).find(b=>b.textContent==='Xóa bản tạm').click()");await until(async()=>!(await state()).temporary);
 await api('/conversation/start',{});await api('/messages',{text:'Cảm ơn.',mode:'sign'});
 const next=(await state()).session_id;
 assert.equal(await evaluate("document.querySelector('.keep-temporary input').checked"),false);
 await api('/conversation/stop',{});await wait(2000);
 const clean=await state();assert.notEqual(clean.session_id,next);assert.equal(clean.messages.length,0);assert.equal(clean.temporary,null);assert.equal(clean.playback,null);assert.equal(clean.speech_drafts.length,0);
 report.checks.defaultEndDiscards=true;report.passed=true;
 fs.writeFileSync(path.join(out,'workspace-037-source.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report));app.quit();setTimeout(()=>app.exit(0),6000);
}).catch(error=>{report.error=String(error.stack||error);fs.writeFileSync(path.join(out,'workspace-037-source-failed.json'),JSON.stringify(report,null,2));console.error(error);app.quit();setTimeout(()=>app.exit(1),6000);});
