/* Integration checks in actual Electron; same helper runs source and EXE. */
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';

export async function checkModeUx({doctor,patient,api,state,until,delay,output,report}) {
 const click=async(page,label)=>{
  const find=`(()=>{const label=${JSON.stringify(label)};return label?[...document.querySelectorAll('button')].find(b=>b.textContent.trim()===label):document.querySelector('dialog[open] button[aria-label="Đóng cửa sổ"]');})()`;
  // A server event can arrive before the initiating UI promise clears busy.
  // Wait for the actual control instead of racing the React acknowledgement.
  await until(()=>page.eval(`(()=>{const b=${find};return !!b&&!b.disabled;})()`),15000);
  await page.eval(`(${find}).click()`);
 };
 const shot=async(page,name)=>{const s=await page.call('Page.captureScreenshot',{format:'png'});fs.writeFileSync(path.join(output,name+'.png'),Buffer.from(s.data,'base64'));};
 const boot=await api('/bootstrap');
 assert.equal((await state()).recognition.mode,'fusion');
 assert.equal(boot.recognition_catalogs.fusion.length,100);
 assert.equal(boot.recognition_catalogs.sign_only.length,400);
 assert.ok(await patient.eval("[...document.querySelectorAll('.feedback-buttons button')].every(b=>b.disabled)"),'Feedback waits for a doctor message');
 for(const [name,page] of [['doctor',doctor],['patient',patient]]){
  const text=await page.eval('document.body.innerText');
  assert.doesNotMatch(text,/\b(?:Fusion|Sign only|avatar|checkpoint|backend)\b/i,'Plain language on the main screen');
  await shot(page,'minimal-'+name+'-1280');
  for(const [width,height] of [[1920,1080],[800,900]]){
   await page.call('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile:false});await delay(150);
   assert.ok(await page.eval('document.documentElement.scrollWidth<=innerWidth+1'),'No horizontal scrolling');
   await shot(page,`minimal-${name}-${width}`);
  }
  await page.call('Emulation.setDeviceMetricsOverride',{width:1280,height:720,deviceScaleFactor:1,mobile:false});
 }
 assert.match(await patient.eval("document.querySelector('.recognition-mode-options button[aria-pressed=true]').innerText"),/Ký hiệu \+ khẩu hình/);
 await click(doctor,'Camera và tùy chọn');
 for(const mode of ['manual','auto']){
  await doctor.eval(`(()=>{const el=document.querySelector('select[aria-label="Gửi lời nói của bác sĩ"]');Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype,'value').set.call(el,${JSON.stringify(mode)});el.dispatchEvent(new Event('change',{bubbles:true}));})()`);
  await until(async()=>(await state()).conversation.mode===mode);
 }
 await shot(doctor,'minimal-options');
 await click(doctor,'Xóa nội dung và bắt đầu lại');
 await until(()=>doctor.eval("document.querySelector('dialog[open] h2')?.textContent==='Bắt đầu cuộc trao đổi mới?'"));
 const beforeCancel=(await state()).session_id;
 await click(doctor,'Tiếp tục trao đổi');
 assert.equal((await state()).session_id,beforeCancel);
 report.checks.minimalPlainLanguageResponsiveSettingsAndCancel=true;
 await click(patient,'Xem 100 từ');
 await until(()=>patient.eval('document.querySelectorAll("[data-testid=patient-vocabulary] > div").length===100'));
 await shot(patient,'vocabulary-fusion');
 await patient.eval("(()=>{const el=document.querySelector('input[aria-label=\"Tìm từ người bệnh\"]');Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(el,'bac si');el.dispatchEvent(new Event('input',{bubbles:true}));})()");
 await until(()=>patient.eval("document.querySelectorAll('[data-testid=patient-vocabulary] > div').length===1"));
 assert.equal(await patient.eval("document.querySelector('[data-testid=patient-vocabulary] strong').textContent"),'Bác sĩ');
 await click(patient,'');
 report.checks.defaultFusion100=true;

 await click(doctor,'Câu khám bệnh');
 await until(()=>doctor.eval('document.querySelectorAll(".clinic-phrase-list button").length===24'));
 await shot(doctor,'quick-phrases-all');
 await click(doctor,'Điều dưỡng');
 assert.equal(await doctor.eval('document.querySelectorAll(".clinic-phrase-list button").length'),6);
 await shot(doctor,'quick-phrases-nursing');
 const before=(await state()).messages.length;
 await doctor.eval("[...document.querySelectorAll('.clinic-phrase-list button')].find(b=>b.querySelector('strong').textContent==='Y tá đo nhiệt độ.').click()");
 await until(()=>doctor.eval("document.querySelector('textarea').value==='Y tá đo nhiệt độ.'"));
 assert.equal((await state()).messages.length,before,'Choosing a phrase must not send without review');
 await until(()=>doctor.eval("[...document.querySelectorAll('button')].some(b=>b.textContent.trim()==='Gửi người bệnh'&&!b.disabled)"));
 await click(doctor,'Gửi người bệnh');
 await until(async()=>{const n=await patient.eval('window.clinicDiagnostics.narration');return n?.speaking&&Object.values(n.mouth).some(v=>v>.01);});
 assert.equal((await state()).messages.at(-1).text,'Y tá đo nhiệt độ.');
 await until(async()=>(await state()).playback.status==='completed');
 report.checks.quickPhrases24ReviewThenRealAvatarVoiceMouth=true;
 await click(patient,'Tôi đã hiểu');
 await until(async()=>(await state()).messages.at(-1)?.text==='Tôi đã hiểu');
 await click(patient,'Xin giải thích lại');
 await until(async()=>(await state()).messages.at(-1)?.text==='Vui lòng giải thích lại');
 await assert.rejects(()=>api('/messages',{text:'Uống thuốc hai viên.',mode:'sign'}));
 const textOnly=await api('/messages',{text:'Uống thuốc hai viên.',mode:'text'});
 await until(()=>patient.eval("document.querySelector('.doctor-caption')?.textContent.includes('Uống thuốc hai viên.')"));
 assert.equal((await state()).messages.at(-1).mode,'text');
 report.checks.patientFeedbackAndUnsupportedMeaningPreserved=true;
 await api('/session/reset',{});

 // Change engine during an active VSL100 sign. The same session must survive,
 // the old partial word must not appear, and the source menu must remap.
 await api('/conversation/configure',{mode:'manual',source:{kind:'demo',demo_id:'mm100:W068'}});
 await api('/conversation/start',{});
 await until(async()=>(await state()).capture.status==='signing');
 const oldGeneration=(await state()).capture.generation;
 const started=Date.now();
 await patient.eval("document.querySelectorAll('.recognition-mode-options button')[1].click()");
 await until(async()=>{const s=await state();return s.recognition.mode==='sign_only'&&!s.recognition.switching&&s.capture.generation>oldGeneration;});
 report.modeSwitch={fusionToSignMs:Date.now()-started,oldGeneration,newGeneration:(await state()).capture.generation};
 assert.equal((await state()).conversation.status,'active');
 assert.match((await state()).conversation.source.demo_id,/^sign400:/);
 await until(()=>patient.eval("document.querySelector('.recognition-mode-summary button').textContent.includes('400')"));
 await click(patient,'Xem 400 từ');
 await until(()=>patient.eval('document.querySelectorAll("[data-testid=patient-vocabulary] > div").length===400'));
 await shot(patient,'vocabulary-sign400');await click(patient,'');
 await click(doctor,'Camera và tùy chọn');
 await until(()=>doctor.eval("document.querySelector('.recognition-mode-options button[aria-pressed=true]').textContent.includes('400')"));
 await shot(doctor,'source-sign400');await click(doctor,'');
 await api('/capture/stop',{});
 await delay(250);
 assert.ok(!(await state()).messages.flatMap(m=>m.words??[m]).some(w=>w.metrics?.generation===oldGeneration));
 report.checks.liveModeSwitchSharedDictionarySourceAndOldResultFence=true;

 // Legacy recognition + readout actually run, with its native label namespace.
 const legacy=boot.recognition_catalogs.sign_only.find(w=>w.label==='Đau'&&w.demo);
 assert.ok(legacy,'Bundled legacy pain fixture');
 const gen=(await api('/capture/start',{kind:'demo',demo_id:legacy.id})).generation;
 const word=await until(async()=>{const s=await state();return s.capture.generation===gen&&s.current_result?s.current_result:null;});
 assert.equal(word.predictions[0].model_id,legacy.model_id);
 assert.equal(word.recognition.actual_mode,'sign_only');
 if(word.uncertain)await api('/confirm',{message_id:word.id,text:legacy.label});
 await until(async()=>(await doctor.eval('window.clinicDiagnostics.patientVoice??[]')).some(e=>e.type==='playing'&&e.message_id===word.id));
 report.legacyWord={word,reviewed:word.uncertain};
 await until(async()=>(await state()).capture.status==='ended');
 report.checks.sign400RealRecognitionAndVoice=true;

 // Switch back while a second legacy capture is running. End must fence both.
 await api('/capture/start',{kind:'demo',demo_id:legacy.id});
 await until(async()=>(await state()).capture.status==='signing');
 await patient.eval("document.querySelectorAll('.recognition-mode-options button')[0].click()");
 await until(async()=>{const s=await state();return s.recognition.mode==='fusion'&&!s.recognition.switching&&s.capture.status!=='idle';});
 assert.match((await state()).conversation.source.demo_id,/^mm100:/);
 await until(()=>patient.eval("document.querySelector('.recognition-mode-summary button').textContent.includes('100')"));
 await api('/conversation/stop',{});await delay(1800);
 assert.equal((await state()).messages.length,0);
 assert.equal((await state()).current_result,null);
 assert.equal((await state()).recognition.mode,'fusion');
 report.checks.returnFusionAndEndFencesBothEngines=true;
 console.log(JSON.stringify({modeUx:true,modeSwitch:report.modeSwitch,legacyReviewed:word.uncertain}));
}
