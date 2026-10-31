/* AudioContext performs native resampling to 16 kHz before this processor. */
class ClinicPCMProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.buffer = new Int16Array(1600);
    this.offset = 0;
    this.energy = 0;
    this.recording = true;
    this.port.onmessage = (event) => {
      if (event.data === 'finish') {
        this.recording = false;
        if (this.offset > 0) {
          const tail = this.buffer.slice(0, this.offset);
          this.port.postMessage({ pcm: tail.buffer, level: 0 }, [tail.buffer]);
        }
        this.port.postMessage({ finished: true });
      }
    };
  }

  process(inputs) {
    if (!this.recording) {
      return false;
    }
    const channel = inputs[0]?.[0];
    if (!channel) {
      return true;
    }
    for (let index = 0; index < channel.length; index += 1) {
      const sample = Math.max(-1, Math.min(1, channel[index]));
      this.buffer[this.offset] = Math.round(sample * (sample < 0 ? 32768 : 32767));
      this.energy += sample * sample;
      this.offset += 1;
      if (this.offset === this.buffer.length) {
        const pcm = this.buffer.buffer;
        this.port.postMessage({ pcm, level: Math.sqrt(this.energy / this.offset) }, [pcm]);
        this.buffer = new Int16Array(1600);
        this.offset = 0;
        this.energy = 0;
      }
    }
    return true;
  }
}

registerProcessor('clinic-pcm', ClinicPCMProcessor);
