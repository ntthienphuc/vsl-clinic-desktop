/* DevTools-only QA input. Never shipped or imported by the application.
 * Inject after loading an isolated local QA session, then reload to remove.
 * Uses the real getUserMedia -> AudioWorklet -> WebSocket -> frozen ASR path.
 * The sole replacement is the physical microphone, fed from synthetic audio.
 */
(function installSpeechFixture(clips) {
  const NativeSocket = window.WebSocket;
  const originalGetUserMedia = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
  const events = [];
  let context;
  let destination;
  let source;
  window.WebSocket = class extends NativeSocket {
    constructor(...args) {
      super(...args);
      if (String(args[0]).includes('/ws/speech')) {
        this.addEventListener('message', (event) => {
          events.push({ time_ms: performance.now(), ...JSON.parse(event.data) });
        });
      }
    }
  };
  navigator.mediaDevices.getUserMedia = async (constraints) => {
    if (!constraints.audio || constraints.video) {
      throw new Error('QA only supplies a synthetic microphone');
    }
    if (context && context.state !== 'closed') {
      await context.close();
    }
    context = new AudioContext({ sampleRate: 16000 });
    destination = context.createMediaStreamDestination();
    await context.resume();
    return destination.stream;
  };
  window.clinicSpeechQA = {
    events,
    plays: [],
    async play(name, noiseSeconds = 0) {
      if (!context || context.state === 'closed') {
        throw new Error('Start the conversation first');
      }
      if (source) {
        source.stop();
      }
      const bytes = Uint8Array.from(atob(clips[name]), (char) => char.charCodeAt(0));
      const speech = await context.decodeAudioData(bytes.buffer);
      const buffer = context.createBuffer(1, speech.length + Math.round(noiseSeconds * 16000), 16000);
      const samples = buffer.getChannelData(0);
      samples.set(speech.getChannelData(0));
      let seed = 7321;
      let low = 0;
      let previous = 0;
      for (let index = speech.length; index < samples.length; index += 1) {
        seed = (1664525 * seed + 1013904223) >>> 0;
        const noise = seed / 2147483648 - 1;
        low = 0.75 * low + 0.25 * noise;
        const filtered = low - previous;
        previous = 0.98 * previous + 0.02 * low;
        samples[index] = 0.012 * filtered * (1 + 0.8 * Math.sin(2 * Math.PI * 3 * index / 16000));
      }
      source = context.createBufferSource();
      source.buffer = buffer;
      source.connect(destination);
      await context.resume();
      source.start();
      const record = { name, start_ms: performance.now(), speech_ms: speech.duration * 1000, noiseSeconds, duration_ms: buffer.duration * 1000, sample_rate: context.sampleRate };
      this.plays.push(record);
      return record;
    },
    async dispose() {
      if (source) {
        source.stop();
      }
      if (context && context.state !== 'closed') {
        await context.close();
      }
      navigator.mediaDevices.getUserMedia = originalGetUserMedia;
      window.WebSocket = NativeSocket;
    },
  };
})
