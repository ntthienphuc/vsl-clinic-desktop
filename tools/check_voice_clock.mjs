/* A compositor pause must not suppress an entire short narration cue. */
import assert from 'node:assert/strict';

export async function checkIndependentVoiceClock({api,state,patient,until,report}) {
 await api('/session/reset',{});
 await patient.eval(`(()=>{
  const original=window.requestAnimationFrame.bind(window);
  window.__voiceClockFault={original,from:Infinity,until:Infinity,holds:[]};
  window.requestAnimationFrame=callback=>original(time=>{
   const fault=window.__voiceClockFault,now=Date.now();
   if(fault&&now>=fault.from&&now<fault.until){
    const hold={started_at:now,released_at:null};fault.holds.push(hold);
    setTimeout(()=>{hold.released_at=Date.now();callback(performance.now());},fault.until-now+10);
   }else callback(time);
  });
 })()`);
 try {
  await api('/messages',{text:'Bác sĩ đo nhiệt độ.',mode:'sign'});
  const playback=await until(async()=>{const p=(await state()).playback;return p?.status==='playing'?p:null;});
  assert.equal(playback.audio_cues.length,3);
  const cue=playback.audio_cues[1];
  const from=playback.started_at_ms+(cue.start_ms-playback.elapsed_ms-120)/playback.rate;
  const to=playback.started_at_ms+(cue.end_ms-playback.elapsed_ms+120)/playback.rate;
  await patient.eval(`Object.assign(window.__voiceClockFault,{from:${from},until:${to}})`);
  await until(async()=>(await state()).playback.status==='completed');
  const observation=await patient.eval(`({holds:window.__voiceClockFault.holds,events:window.clinicDiagnostics.narration.events})`);
  const events=observation.events.filter(e=>e.type==='playing'&&e.cycle===playback.id+':'+playback.iteration);
  report.independentVoiceClock={input:playback.text,cues:playback.audio_cues,events,holds:observation.holds,
   scope:'Only requestAnimationFrame callbacks were delayed across a complete cue. JavaScript timers and the real HTMLAudio playback engine remained active. This does not simulate a fully blocked OS or JavaScript thread.'};
  assert.equal(events.length,3,'Every real audio start survives a compositor pause');
  events.forEach((e,i)=>{
   assert.equal(e.entry_id,playback.audio_cues[i].entry_id);
   assert.equal(e.gloss_index,i);
   assert.ok(Math.abs(e.timeline_ms-playback.audio_cues[i].start_ms)<180,'Independent voice stays on the shared timeline');
  });
  assert.ok(observation.holds.some(h=>h.started_at<events[1].at_ms&&h.released_at>events[1].at_ms
    &&h.released_at-h.started_at>cue.duration_ms),'A real word began while rendering was held across its full cue');
  report.checks.voiceClockSurvivesCompositorPause=true;
 } finally {
  await patient.eval(`(()=>{const fault=window.__voiceClockFault;if(fault)window.requestAnimationFrame=fault.original;delete window.__voiceClockFault;})()`);
  await api('/session/reset',{});
 }
}
