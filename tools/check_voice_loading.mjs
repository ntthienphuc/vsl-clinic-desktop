/* Actual media loading delayed beyond the former five-second failure point. */
import assert from 'node:assert/strict';

export async function checkDelayedVoiceLoad({api,state,patient,until,delay,report}) {
 await api('/session/reset',{});
 await patient.eval(`(()=>{
  const Original=window.Audio;const probe={original:Original,timers:[],loads:0};window.__delayedVoiceLoad=probe;
  window.Audio=function(url){
   const audio=new Original();const load=audio.load.bind(audio);let first=true;
   audio.load=()=>{if(!first){load();return;}first=false;probe.loads++;
    probe.timers.push(setTimeout(()=>{audio.src=url;load();},6200));};
   return audio;
  };window.Audio.prototype=Original.prototype;
 })()`);
 try {
  await api('/messages',{text:'Bạn cần nghỉ ngơi không?',mode:'sign'});
  await until(async()=>(await state()).playback?.status==='loading');
  await delay(5200);
  const before=(await state()).playback;
  report.delayedVoiceLoad={statusAt5200ms:before.status,loads:await patient.eval('window.__delayedVoiceLoad.loads')};
  assert.equal(before.status,'loading','A slow clip must not start a silent avatar sequence');
  const playback=await until(async()=>{const p=(await state()).playback;return p?.status==='playing'?p:null;});
  await until(async()=>(await state()).playback.status==='completed');
  const allEvents=await patient.eval('window.clinicDiagnostics.narration.events');
  const events=allEvents.filter(e=>e.type==='playing'&&e.cycle===playback.id+':'+playback.iteration);
  Object.assign(report.delayedVoiceLoad,{prepareMs:playback.started_at_ms-playback.requested_at_ms,cues:playback.audio_cues,events,
   scope:'Delayed only media source assignment by 6.2s; real packaged WAV playback and onplaying events after readiness.'});
  assert.equal(events.length,playback.audio_cues.length);
  assert.ok(report.delayedVoiceLoad.prepareMs>=6000);
  events.forEach((e,i)=>{
   assert.equal(e.entry_id,playback.audio_cues[i].entry_id);
   assert.ok(Math.abs(e.timeline_ms-playback.audio_cues[i].start_ms)<180);
  });
  report.checks.delayedVoiceLoadWaitsBeforePlayback=true;
 } finally {
  await patient.eval(`(()=>{const p=window.__delayedVoiceLoad;if(p){window.Audio=p.original;p.timers.forEach(clearTimeout);}delete window.__delayedVoiceLoad;})()`);
  await api('/session/reset',{});
 }
}
