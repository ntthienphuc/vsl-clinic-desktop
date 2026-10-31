import { useCallback, useEffect, useRef, useState } from 'react';
import { token } from '../api';

type Phase = 'idle' | 'loading' | 'permission' | 'listening' | 'finishing';

interface Recording {
  id: number;
  socket: WebSocket;
  context: AudioContext;
  stream?: MediaStream;
  source?: MediaStreamAudioSourceNode;
  processor?: AudioWorkletNode;
  timer?: ReturnType<typeof setTimeout>;
  started: number;
  finishing: boolean;
  ready: boolean;
}

export function useDictation(sessionId: string, live = false) {
  const active = useRef<Recording | null>(null);
  const generation = useRef(0);
  const alive = useRef(true);
  const [phase, setPhase] = useState<Phase>('idle');
  const [draft, setDraft] = useState('');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [delivery, setDelivery] = useState('');
  const [uncertain, setUncertain] = useState(false);
  const [level, setLevel] = useState(0);
  const [seconds, setSeconds] = useState(0);
  const [decoding, setDecoding] = useState(false);
  const [latency, setLatency] = useState<number | null>(null);
  const [devices, setDevices] = useState<MediaDeviceInfo[]>([]);
  const [deviceId, setDeviceId] = useState('');

  const releaseAudio = useCallback((run: Recording) => {
    run.stream?.getTracks().forEach((track) => track.stop());
    run.source?.disconnect();
    run.processor?.disconnect();
    if (run.processor) {
      run.processor.port.onmessage = null;
    }
    if (run.context.state !== 'closed') {
      void run.context.close().catch(() => undefined);
    }
  }, []);

  const stop = useCallback((cancel: boolean) => {
    const run = active.current;
    active.current = null;
    generation.current += 1;
    if (run) {
      clearTimeout(run.timer);
      releaseAudio(run);
      if (cancel && run.socket.readyState === WebSocket.OPEN) {
        run.socket.send(JSON.stringify({ action: 'cancel' }));
      }
      run.socket.close();
    }
    if (alive.current) {
      setPhase('idle');
      setLevel(0);
      setDecoding(false);
    }
  }, [releaseAudio]);

  const fail = useCallback((message: string) => {
    stop(true);
    if (alive.current) {
      setError(message);
    }
  }, [stop]);

  const finish = useCallback(() => {
    const run = active.current;
    if (!run || run.finishing) {
      return;
    }
    if (!run.processor) {
      stop(true);
      return;
    }
    run.finishing = true;
    setPhase('finishing');
    clearTimeout(run.timer);
    // The worklet sends its final PCM packet before this acknowledgement.
    run.processor.port.postMessage('finish');
    run.timer = setTimeout(() => fail('Chưa xử lý xong lời nói. Kiểm tra phần chữ đã có rồi thử lại.'), 30000);
  }, [fail, stop]);

  const start = useCallback(async () => {
    if (active.current) {
      return;
    }
    setError('');
    setNotice('');
    setDelivery('');
    setDraft('');
    setUncertain(false);
    setLatency(null);
    setSeconds(0);
    setPhase('loading');
    const id = ++generation.current;
    let run: Recording | null = null;
    try {
      if (!navigator.mediaDevices?.getUserMedia) {
        throw new Error('Không truy cập được micro trong cửa sổ này. Hãy mở ứng dụng VSL Clinic.');
      }
      const context = new AudioContext({ sampleRate: 16000, latencyHint: 'interactive' });
      const socket = new WebSocket(`${location.protocol === 'https:' ? 'wss:' : 'ws:'}//${location.host}/ws/speech?token=${encodeURIComponent(token)}&live=${live}`);
      run = { id, socket, context, started: performance.now(), finishing: false, ready: false };
      active.current = run;
      const recording = run;
      const valid = () => alive.current && active.current === recording && generation.current === id;
      run.timer = setTimeout(() => fail('Bộ nhận giọng nói chưa sẵn sàng. Hãy thử lại.'), 30000);
      socket.onmessage = (event) => {
        if (!valid()) {
          return;
        }
        const message = JSON.parse(event.data);
        if (message.type === 'error') {
          fail(message.message);
        } else if (message.type === 'ready' && !recording.ready) {
          recording.ready = true;
          setPhase('permission');
          clearTimeout(recording.timer);
          recording.timer = setTimeout(() => fail('Chưa mở được micro. Hãy cho phép micro cho ứng dụng hoặc chọn lại thiết bị rồi thử lại.'), 45000);
          void (async () => {
            const stream = await navigator.mediaDevices.getUserMedia({
              audio: {
                channelCount: 1,
                echoCancellation: true,
                noiseSuppression: true,
                autoGainControl: false,
                ...(deviceId ? { deviceId: { exact: deviceId } } : {}),
              },
              video: false,
            });
            if (!valid()) {
              stream.getTracks().forEach((track) => track.stop());
              return;
            }
            recording.stream = stream;
            if (context.sampleRate !== 16000) {
              throw new Error('Thiết bị âm thanh không hỗ trợ chế độ nhận giọng nói 16 kHz.');
            }
            await context.audioWorklet.addModule('/audio/pcm-worklet.js');
            if (!valid()) {
              return;
            }
            const processor = new AudioWorkletNode(context, 'clinic-pcm');
            const source = context.createMediaStreamSource(stream);
            recording.processor = processor;
            recording.source = source;
            processor.port.onmessage = (audio) => {
              if (!valid()) {
                return;
              }
              if (audio.data.pcm) {
                if (socket.readyState !== WebSocket.OPEN || socket.bufferedAmount > 64000) {
                  fail('Kết nối micro bị chậm. Hãy kiểm tra nội dung và nói lại ý còn thiếu.');
                  return;
                }
                socket.send(audio.data.pcm);
                setLevel(Math.min(1, audio.data.level * 8));
                setSeconds(Math.floor((performance.now() - recording.started) / 1000));
              }
              if (audio.data.finished) {
                releaseAudio(recording);
                setLevel(0);
                socket.send(JSON.stringify({ action: 'finish' }));
              }
            };
            source.connect(processor);
            // The worklet writes no output, so microphone audio is never echoed.
            processor.connect(context.destination);
            await context.resume();
            if (!valid()) {
              return;
            }
            recording.started = performance.now();
            clearTimeout(recording.timer);
            if (!live) {
              recording.timer = setTimeout(finish, 85000);
            }
            stream.getAudioTracks().forEach((track) => {
              track.onended = () => {
                if (valid() && !recording.finishing) {
                  fail('Micro đã ngắt kết nối. Hãy chọn lại thiết bị.');
                }
              };
            });
            setPhase('listening');
            const available = await navigator.mediaDevices.enumerateDevices();
            if (valid()) {
              setDevices(available.filter((item) => item.kind === 'audioinput'));
            }
          })().catch((problem: Error) => {
            if (valid()) {
              fail(problem.name === 'NotAllowedError' ? 'Chưa được phép dùng micro. Cho phép micro trong Windows rồi thử lại.' : problem.message);
            }
          });
        } else if (message.type === 'decoding') {
          setNotice('');
          setDecoding(true);
        } else if (message.type === 'speech_rejected') {
          setDecoding(false);
          setNotice(message.message);
        } else if (message.type === 'transcript' && message.session_id === sessionId) {
          setNotice('');
          setDelivery(message.delivery?.status ?? '');
          setDraft((previous) => live ? message.text : `${previous} ${message.text}`.trim());
          setUncertain((previous) => previous || message.uncertain || message.cut_at_limit);
          setLatency(message.decode_ms + message.queue_ms + message.endpoint_audio_ms);
          setDecoding(false);
        } else if (message.type === 'finished') {
          stop(false);
        }
      };
      socket.onerror = () => {
        if (valid()) {
          fail('Chưa kết nối được bộ giọng nói trên máy.');
        }
      };
      socket.onclose = () => {
        if (valid()) {
          fail('Micro đã dừng trước khi hoàn tất. Kiểm tra phần chữ đã nhận.');
        }
      };
      await context.resume();
    } catch (problem) {
      if (generation.current === id) {
        fail((problem as Error).message);
      }
    }
  }, [deviceId, fail, finish, live, releaseAudio, sessionId, stop]);

  useEffect(() => {
    alive.current = true;
    setPhase('idle');
    setLevel(0);
    setDecoding(false);
    setDraft('');
    setError('');
    setNotice('');
    setDelivery('');
    setUncertain(false);
    return () => {
      alive.current = false;
      stop(true);
    };
  }, [sessionId, stop]);

  return {
    phase, draft, setDraft, error, notice, delivery, uncertain, level, seconds, latency, decoding,
    devices, deviceId, setDeviceId, start, finish,
    cancel: stop,
    active: phase !== 'idle',
  };
}
