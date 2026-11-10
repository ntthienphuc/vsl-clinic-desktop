/* Actual Electron/source runtime, offline narration, synthetic audio and fixed sign video. */
const { app, BrowserWindow } = require('electron');
const fs = require('node:fs'), path = require('node:path'), assert = require('node:assert/strict');
const root = path.resolve(__dirname, '..'), output = path.join(root, 'docs/evidence');
process.env.CLINIC_QA = '1'; process.env.CLINIC_QA_PORT = '58898';
app.setPath('userData', path.join(root, 'research/cache/avatar-041-profile'));
app.commandLine.appendSwitch('use-fake-device-for-media-stream');
app.commandLine.appendSwitch('use-file-for-fake-audio-capture', path.join(root, 'research/cache/mic-silence.wav'));
app.commandLine.appendSwitch('remote-debugging-port', '58903');
require('../desktop/main.cjs');
const origin = 'http://127.0.0.1:58898', headers = { Authorization: 'Bearer clinic-test-session', 'Content-Type': 'application/json' };
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
async function until(fn, timeout = 60000) {
  const start = Date.now();
  while (Date.now() - start < timeout) { const result = await fn(); if (result) return result; await delay(80); }
  throw new Error('Timed out: ' + fn.toString().slice(0, 150));
}
async function api(route, body) {
  const r = await fetch(origin + '/api' + route, { method: body === undefined ? 'GET' : 'POST', headers, body: body === undefined ? undefined : JSON.stringify(body) });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}
const state = async () => (await api('/diagnostics')).state;
const report = { scope: 'Actual 0.4.1 source Electron windows, real offline WAV playback and mouth animation. Synthetic speech and prerecorded sign video; not human pilot validation.', checks: {}, samples: [] };
void app.whenReady().then(async () => {
  try {
    await until(async () => { try { return (await state()).clients.patient > 0; } catch { return false; } }, 90000);
    const doctor = BrowserWindow.getAllWindows().find(w => new URL(w.webContents.getURL()).pathname === '/doctor');
    const patient = BrowserWindow.getAllWindows().find(w => new URL(w.webContents.getURL()).pathname === '/patient');
    doctor.setTitle('VSL Clinic · Bác sĩ · QA 0.4.1'); patient.setTitle('VSL Clinic · Người bệnh · QA 0.4.1');
    patient.setContentSize(1280, 720); doctor.setContentSize(1280, 720);
    const view = js => patient.webContents.executeJavaScript(js);
    const doctorView = js => doctor.webContents.executeJavaScript(js);
    await until(async () => await view("!!window.clinicDiagnostics?.mouthExpressions?.includes('aa')"));
    for (const window of [doctor, patient]) {
      const layout = await window.webContents.executeJavaScript('({w:innerWidth,h:innerHeight,scroll:document.documentElement.scrollHeight,width:document.documentElement.scrollWidth})');
      assert.ok(layout.scroll <= layout.h + 1 && layout.width <= layout.w + 1, JSON.stringify(layout));
    }
    report.checks.layout720p = true;
    await api('/messages', { text: 'Bạn có đau bụng không? Vui lòng ngồi nghỉ nhé.', mode: 'sign' });
    await until(async () => { const n = await view('window.clinicDiagnostics?.narration'); return n?.speaking && Object.values(n.mouth).some(v => v > .01); });
    let current = (await state()).playback;
    const active = await view('window.clinicDiagnostics');
    assert.ok(Object.values(active.narration.mouth).some(n => n > .01));
    assert.ok(active.mouthExpressions.includes('aa'));
    report.checks.actualSoundAndMouth = true;
    report.samples.push(active.narration);
    await api('/playback', { action: 'pause', playback_id: current.id });
    await delay(300);
    const paused = await view('window.clinicDiagnostics.narration');
    assert.equal(paused.speaking, false); assert.ok(Object.values(paused.mouth).every(v => v === 0));
    const clock = paused.audioTimeMs; await delay(400);
    assert.equal((await view('window.clinicDiagnostics.narration')).audioTimeMs, clock);
    report.checks.pauseFreezesAudioAndMouth = true;
    await api('/playback', { action: 'speed', playback_id: current.id, rate: .75 });
    await api('/playback', { action: 'resume', playback_id: current.id });
    await until(async () => (await view('window.clinicDiagnostics.narration')).speaking);
    await api('/avatar/voice', { enabled: false }); await delay(200);
    assert.equal((await view('window.clinicDiagnostics.narration')).speaking, false);
    await api('/avatar/voice', { enabled: true });
    report.checks.mute = true;
    await api('/playback', { action: 'speed', playback_id: current.id, rate: 1 });
    await api('/playback', { action: 'replay', playback_id: current.id });
    await until(async () => (await state()).playback?.iteration === 1 && (await view('window.clinicDiagnostics.narration')).speaking);
    for (let i = 0; i < 12; i++) {
      const sample = await view('window.clinicDiagnostics.narration');
      if (sample.speaking) report.samples.push({ driftMs: sample.driftMs, audioTimeMs: sample.audioTimeMs });
      await delay(80);
    }
    assert.ok(report.samples.filter(s => s.driftMs !== undefined).every(s => Math.abs(s.driftMs) < 260));
    await until(async () => (await state()).playback?.status === 'completed');
    report.checks.replaySpeedAndCompletion = true;
    await api('/session/reset', {});

    // Record the real avatar canvas and actual media-element audio together.
    await view(`(async () => {
      const canvas = document.querySelector('.avatar-canvas canvas');
      const context = new AudioContext(); await context.resume();
      const destination = context.createMediaStreamDestination();
      const originalPlay = HTMLMediaElement.prototype.play;
      const wired = new WeakSet();
      HTMLMediaElement.prototype.play = function() {
        if (this instanceof HTMLAudioElement && !wired.has(this)) {
          const source = context.createMediaElementSource(this);
          source.connect(context.destination); source.connect(destination); wired.add(this);
        }
        return originalPlay.call(this);
      };
      const originalStream = canvas.captureStream(30);
      const sourceVideo = document.createElement('video'); sourceVideo.srcObject = originalStream; sourceVideo.muted = true;
      await originalPlay.call(sourceVideo);
      const presentation = document.createElement('canvas'); presentation.width = 1280; presentation.height = 720;
      const ctx = presentation.getContext('2d');
      let drawing = true, frame;
      const draw = () => {
        if (!drawing) return;
        ctx.fillStyle = '#edf3f1'; ctx.fillRect(0,0,1280,720);
        const height = 620, width = height * canvas.width / canvas.height;
        ctx.drawImage(sourceVideo, (1280-width)/2, 40, width, height);
        ctx.fillStyle = '#174c42'; ctx.font = 'bold 25px Segoe UI'; ctx.textAlign = 'center';
        ctx.fillText('VSL Clinic · Ký hiệu và giọng nói',640,35);
        ctx.fillStyle = '#ffffff'; ctx.fillRect(100,651,1080,55);
        ctx.fillStyle = '#173c35'; ctx.font = '24px Segoe UI';
        const event = [...(window.clinicDiagnostics?.narration?.events ?? [])].reverse().find(e=>e.type==='playing');
        ctx.fillText(event?.text ?? 'Đang chuẩn bị lời bác sĩ…',640,686);
        frame=requestAnimationFrame(draw);
      }; draw();
      const stream = presentation.captureStream(30);
      destination.stream.getAudioTracks().forEach(track => stream.addTrack(track));
      const recorder = new MediaRecorder(stream, {mimeType:'video/webm;codecs=vp8,opus',videoBitsPerSecond:2500000});
      const chunks=[]; recorder.ondataavailable=e=>{if(e.data.size)chunks.push(e.data);};
      window.finishAvatarRecording=()=>new Promise(resolve=>{
        recorder.onstop=async()=>{
          const bytes=new Uint8Array(await new Blob(chunks).arrayBuffer());
          let binary='';for(let i=0;i<bytes.length;i+=16384)binary+=String.fromCharCode(...bytes.subarray(i,i+16384));
          HTMLMediaElement.prototype.play=originalPlay;
          drawing=false; cancelAnimationFrame(frame);
          stream.getTracks().forEach(t=>t.stop()); originalStream.getTracks().forEach(t=>t.stop()); sourceVideo.srcObject=null;
          await context.close(); resolve(btoa(binary));
        };recorder.stop();
      }); recorder.start(250);
    })()`);
    await api('/messages', { text: 'Bạn có đau bụng không? Vui lòng ngồi nghỉ nhé. Cảm ơn.', mode: 'sign' });
    await until(async () => (await state()).playback?.status === 'completed');
    await delay(250);
    const video = await view('window.finishAvatarRecording()');
    const videoPath = path.join(root, '../Demo/AVATAR_GIONG_NAM_0.4.1.webm');
    fs.mkdirSync(path.dirname(videoPath), { recursive: true });
    fs.writeFileSync(videoPath, Buffer.from(video, 'base64'));
    report.video = videoPath;
    report.checks.recordedActualAudioAndAvatar = fs.statSync(videoPath).size > 50000;

    await api('/session/reset', {});
    await api('/conversation/configure', { mode: 'auto', source: { kind: 'demo', demo_id: '395' } });
    await api('/conversation/start', {});
    await until(async () => (await state()).capture.status === 'ended');
    await until(async () => (await doctorView('window.clinicDiagnostics?.patientVoice ?? []')).some(e => e.type === 'ended'), 30000);
    report.patientVoice = await doctorView('window.clinicDiagnostics.patientVoice');
    report.checks.patientVideoToImmediateVoice = report.patientVoice.some(e => e.type === 'playing');
    await api('/messages', { text: 'Bạn có đau bụng không? Vui lòng ngồi nghỉ nhé.', mode: 'sign' });
    await until(async () => (await state()).playback?.status === 'playing');
    await api('/capture/start', { kind: 'demo', demo_id: '395' });
    await until(async () => (await state()).playback?.pause_reason === 'patient_reply');
    report.checks.realPatientReplyPausesAvatar = true;
    await until(async () => (await state()).capture.status === 'ended');
    await api('/playback', { action: 'stop', playback_id: (await state()).playback.id });
    await until(async () => await doctorView("Array.from(document.querySelectorAll('.live-speech-status button')).some(b=>b.textContent==='Tắt micro')"));
    await doctorView("Array.from(document.querySelectorAll('.live-speech-status button')).find(b=>b.textContent==='Tắt micro').click()");
    await delay(300);
    const socket = new WebSocket(origin.replace('http', 'ws') + '/ws/speech?live=true&token=clinic-test-session');
    const events = [];
    socket.addEventListener('message', e => events.push(JSON.parse(e.data)));
    await until(() => { const error = events.find(e => e.type === 'error'); if (error) throw Error(error.message); return events.some(e => e.type === 'ready'); });
    const pcm = fs.readFileSync(path.join(root, 'research/cache/avatar-041-doctor.pcm'));
    const audio = Buffer.concat([Buffer.alloc(16000), pcm, Buffer.alloc(192000)]);
    for (let i = 0; i < audio.length; i += 3200) { socket.send(audio.subarray(i, i + 3200)); await delay(100); }
    await until(() => events.some(e => e.type === 'transcript'));
    const transcript = events.filter(e => e.type === 'transcript');
    assert.equal(transcript.length, 1, 'one utterance and six seconds of silence must not generate extras');
    assert.equal(transcript[0].delivery.status, 'sent', JSON.stringify(transcript));
    report.speech = transcript; report.checks.syntheticSpeechAutoAvatar = true;
    socket.send(JSON.stringify({ action: 'finish' })); await delay(300); socket.close();
    await until(async () => (await state()).playback?.status === 'completed');
    await api('/conversation/stop', {});
    await delay(300);
    assert.equal((await state()).messages.length, 0);
    assert.equal((await view('window.clinicDiagnostics.narration')).speaking, false);
    report.checks.endClearsAndStops = true;
    fs.writeFileSync(path.join(output, 'avatar-041-source.json'), JSON.stringify(report, null, 2));
    console.log(JSON.stringify({ checks: report.checks, video: report.video, speech: report.speech.map(e=>e.text) }, null, 2));
    // Keep the simulation open for visual inspection; microphone/camera are off.
    await api('/messages', { text: 'Bạn có đau bụng không? Vui lòng ngồi nghỉ nhé.', mode: 'sign' });
  } catch (error) {
    report.error = error.stack;
    fs.writeFileSync(path.join(output, 'avatar-041-source-failed.json'), JSON.stringify(report, null, 2));
    console.error(error.stack);
  }
});
