/* Natural clinic scenarios against the running source/EXE, with real WebGL/audio. */
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';

export async function checkNaturalDialogue({doctor,patient,api,state,until,delay,output,report}) {
 const scenarios=[
  ['Bạn cần nghỉ ngơi không?', ['Cần','Nghỉ ngơi']],
  ['Bạn có cần được nghỉ ngơi không?', ['Cần','Nghỉ ngơi']],
  ['Mời chị ngồi nghỉ. Bạn có cần uống nước không?', ['Ngồi','Nghỉ ngơi','Cần','Nước','Uống']],
  ['Bác sĩ khám bệnh rồi y tá đo nhiệt độ nhé.', ['Bác sĩ','Khám bệnh','Y tá','Nhiệt độ','Đo']],
  ['Bạn có buồn nôn không? Bạn đau bụng bên trái không? Bạn đau tay bên phải không? Mời chị nằm trên giường. Bạn hãy ngồi đợi.',
   ['Buồn nôn','Bụng','Bên trái','Đau','Tay','Bên phải','Đau','Giường','Nằm','Ngồi','Đợi']],
 ];
 report.naturalDialogues=[];
 await api('/session/reset',{});
 await delay(200);
 for(const [text,expected] of scenarios){
  await doctor.eval(`(()=>{const el=document.querySelector('textarea[aria-label="Nội dung gửi người bệnh"]');Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype,'value').set.call(el,${JSON.stringify(text)});el.dispatchEvent(new Event('input',{bubbles:true}));})()`);
  await until(()=>doctor.eval("[...document.querySelectorAll('button')].some(b=>b.textContent.trim()==='Gửi người bệnh'&&!b.disabled)"));
  await doctor.eval("[...document.querySelectorAll('button')].find(b=>b.textContent.trim()==='Gửi người bệnh').click()");
  const playback=await until(async()=>{const p=(await state()).playback;return p?.text===text&&p.status==='playing'?p:null;});
  assert.deepEqual(playback.glosses.map(g=>g.label),expected);
  assert.equal(playback.audio_cues.length,expected.length,'Every sign must have bundled speech');
  assert.equal((await state()).messages.at(-1).text,text,'Original doctor utterance preserved');
  if(text===scenarios[0][0]){
   assert.equal(playback.nonmanual,'question');
   const shot=await patient.call('Page.captureScreenshot',{format:'png'});
   fs.writeFileSync(path.join(output,'natural-need-rest-question.png'),Buffer.from(shot.data,'base64'));
  }
  const row={text,projection:expected,playbackId:playback.id,cues:playback.audio_cues,captured:[]};
  report.naturalDialogues.push(row);
  const novel=new Set(['Buồn nôn','Bên trái','Bên phải','Nằm','Đợi']);
  await until(async()=>{
   const current=await state();
   const n=await patient.eval('window.clinicDiagnostics.narration');
   if(n.speaking&&Object.values(n.mouth).some(v=>v>.01))row.mouthSeen=true;
   const events=n.events.filter(e=>e.type==='playing'&&e.cycle===playback.id+':'+playback.iteration);
   const cue=events.at(-1); const word=cue?expected[cue.gloss_index]:null;
   if(novel.has(word)&&!row.captured.includes(word)){
    const shot=await patient.call('Page.captureScreenshot',{format:'png'});
    fs.writeFileSync(path.join(output,`natural-word-${cue.gloss_index}.png`),Buffer.from(shot.data,'base64'));
    row.captured.push(word);
   }
   if(current.playback.status==='completed'){row.audioEvents=events;row.allEvents=n.events.filter(e=>e.cycle===playback.id+':'+playback.iteration);return true;}return false;
  },90000);
  assert.equal(row.audioEvents.length,expected.length,'One actual audio start for each sign');
  assert.ok(row.mouthSeen,'Real mouth animation observed');
  row.audioEvents.forEach((e,i)=>{
   assert.equal(e.entry_id,playback.audio_cues[i].entry_id);
   assert.ok(Math.abs(e.timeline_ms-playback.audio_cues[i].start_ms)<200,`Sign and voice offset ${e.timeline_ms-playback.audio_cues[i].start_ms}ms at ${expected[i]}`);
  });
 }
 // The model may suggest wording, but must never silently drop a drug dose.
 await assert.rejects(()=>api('/messages',{text:'Bạn uống thuốc hai viên rồi nghỉ ngơi.',mode:'sign'}));
 assert.equal((await api('/text/plan',{text:'Bạn uống thuốc hai viên rồi nghỉ ngơi.'})).supported,false);
 report.checks.naturalDoctorScenariosKeepMeaningVoiceAndMouth=true;
 await api('/session/reset',{});
 await delay(200);
 // Fully understood wording no longer enters a choose/rewrite/confirm cycle.
 // Also exercise the real bundled LLM separately so the fast grammar cannot
 // conceal a missing offline model or runtime in the installer.
 const original='Bạn có cần được nghỉ ngơi không?';
 const resolved=await api('/text/plan',{text:original,mode:'sign'});
 assert.equal(resolved.supported,true);
 assert.equal(resolved.text,original);
 assert.deepEqual(resolved.suggestions,[]);
 assert.equal(resolved.language_assist,undefined,'Known complete sentences must not wait for an LLM');
 const advice=await api('/language/suggest',{text:original});
 assert.equal(advice.source,'local-model');
 assert.ok(advice.suggestions.some(s=>s.text==='Bạn cần nghỉ ngơi không?'));
 report.localLanguage={original,source:advice.source,elapsedMs:advice.elapsed_ms,suggestions:advice.suggestions};
 report.checks.bundledLocalLlmConstrainedRetrieval=true;
 report.checks.completeNaturalWordingNeedsNoSuggestionChoice=true;
 await api('/session/reset',{});
 await delay(200);
}
