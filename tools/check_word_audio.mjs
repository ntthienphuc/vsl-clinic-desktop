import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';

export async function checkWordAudio({api,state,patient,until,report}) {
 await api('/messages',{text:'Bác sĩ đo nhiệt độ.',mode:'sign'});
 const playback=await until(async()=>{const p=(await state()).playback;return p?.status==='playing'?p:null;});
 assert.equal(playback.glosses.length,3);
 const signs=playback.timeline.filter(s=>s.phase==='sign');
 assert.equal(playback.audio_cues.length,signs.length);
 playback.audio_cues.forEach((cue,i)=>{
  assert.equal(cue.entry_id,'w:'+playback.glosses[i].id);
  assert.equal(cue.gloss_index,i);
  assert.equal(cue.start_ms,signs[i].start_ms);
  if(i)assert.ok(playback.audio_cues[i-1].end_ms<=cue.start_ms);
 });
 await until(async()=>(await state()).playback.status==='completed');
 const events=(await patient.eval('window.clinicDiagnostics.narration.events'))
  .filter(e=>e.type==='playing'&&e.cycle===playback.id+':'+playback.iteration);
 assert.equal(events.length,3,'Exactly three real audio starts, one per signed gloss');
 events.forEach((e,i)=>{
  assert.equal(e.entry_id,playback.audio_cues[i].entry_id);
  assert.equal(e.gloss_index,i);
  assert.ok(Math.abs(e.timeline_ms-playback.audio_cues[i].start_ms)<180,'Voice onset near its sign onset');
 });
 report.perSignVoice={input:playback.text,glosses:playback.glosses,cues:playback.audio_cues,events};
 report.checks.threeWordsReadOnTheirOwnAvatarSigns=true;
}

export async function samplePreview(url,ms=6500) {
 const controller=new AbortController();
 const timer=setTimeout(()=>controller.abort(),ms);
 const arrivals=[], hashes=new Set();let pending=Buffer.alloc(0);
 try {
  const response=await fetch(url,{signal:controller.signal});
  assert.ok(response.ok);
  for await(const chunk of response.body){
   pending=Buffer.concat([pending,chunk]);
   while(true){
    const start=pending.indexOf('--frame\r\n');
    const headerEnd=pending.indexOf('\r\n\r\n',Math.max(0,start));
    if(start<0||headerEnd<0)break;
    const length=Number(pending.subarray(start,headerEnd).toString().match(/Content-Length: (\d+)/)?.[1]);
    if(!length||pending.length<headerEnd+4+length)break;
    const jpeg=pending.subarray(headerEnd+4,headerEnd+4+length);
    assert.equal(jpeg[0],255);assert.equal(jpeg[1],216);
    hashes.add(createHash('sha256').update(jpeg).digest('hex'));
    arrivals.push(performance.now());
    pending=pending.subarray(headerEnd+4+length);
   }
   assert.ok(pending.length<1024*1024,'No unbounded preview backlog');
  }
 }catch(error){if(!controller.signal.aborted)throw error;}
 finally{clearTimeout(timer);controller.abort();}
 const gaps=arrivals.slice(1).map((at,i)=>at-arrivals[i]).sort((a,b)=>a-b);
 return {frames:arrivals.length,distinctFrames:hashes.size,
  fps:arrivals.length>1?(arrivals.length-1)*1000/(arrivals.at(-1)-arrivals[0]):0,
  p95GapMs:gaps[Math.floor((gaps.length-1)*.95)]??null,maxGapMs:gaps.at(-1)??null,
  scope:'Real MJPEG transport arrivals with unique JPEG hashes; not display/photon FPS.'};
}
