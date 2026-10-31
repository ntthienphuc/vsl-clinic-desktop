import { useEffect, useRef, useState } from 'react';
import type { Bootstrap, Role, SessionState } from './types';

export const token = new URLSearchParams(location.search).get('token') ?? 'local-development';
export const previewUrl = `/api/preview?token=${encodeURIComponent(token)}`;

export async function request<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(`/api${path}`, {
    method: body === undefined ? 'GET' : 'POST',
    headers: { Authorization: `Bearer ${token}`, ...(body !== undefined ? { 'Content-Type': 'application/json' } : {}) },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const result = await response.json();
  if (!response.ok) {
    throw new Error(typeof result.detail === 'string' ? result.detail : 'Chưa thực hiện được. Vui lòng thử lại.');
  }
  return result as T;
}

export async function uploadVideo(file: File): Promise<void> {
  if (file.size > 100 * 1024 * 1024) {
    throw new Error('Video vượt quá 100 MB.');
  }
  const form = new FormData();
  form.append('file', file);
  const response = await fetch('/api/capture/upload', {
    method: 'POST', headers: { Authorization: `Bearer ${token}` }, body: form,
  });
  if (!response.ok) {
    const result = await response.json();
    throw new Error(result.detail ?? 'Không đọc được video.');
  }
}

export function useClinic(role: Role) {
  const [bootstrap, setBootstrap] = useState<Bootstrap | null>(null);
  const [state, setState] = useState<SessionState | null>(null);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState('');
  const seen = useRef(new Set<string>());
  const receivedAt = useRef(new Map<string, number>());

  useEffect(() => {
    let alive = true;
    let socket: WebSocket | null = null;
    let reconnect: ReturnType<typeof setTimeout> | undefined;
    let retry = 500;
    const accept = (next: SessionState) => {
      if (!alive) {
        return;
      }
      setState(next);
      if (role === 'doctor') {
        for (const message of next.messages.flatMap((item) => item.words ?? [item])) {
          if (message.role !== 'patient' || message.manual || receivedAt.current.has(message.id)) {
            continue;
          }
          receivedAt.current.set(message.id, Date.now());
        }
      }
    };
    const connect = () => {
      if (!alive) {
        return;
      }
      socket = new WebSocket(`${location.protocol === 'https:' ? 'wss:' : 'ws:'}//${location.host}/ws?role=${role}&token=${encodeURIComponent(token)}`);
      socket.onopen = () => {
        if (alive) {
          setConnected(true);
          setError('');
          retry = 500;
        }
      };
      socket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'snapshot') {
          accept(data.state);
        }
      };
      socket.onerror = () => socket?.close();
      socket.onclose = () => {
        if (alive) {
          setConnected(false);
          reconnect = setTimeout(connect, retry);
          retry = Math.min(8000, retry * 1.6);
        }
      };
    };
    const initialize = async () => {
      try {
        const boot = await request<Bootstrap>('/bootstrap');
        if (!alive) {
          return;
        }
        setBootstrap(boot);
        accept(boot.state);
        connect();
      } catch (problem) {
        if (alive) {
          setError((problem as Error).message);
          reconnect = setTimeout(initialize, 2000);
        }
      }
    };
    void initialize();
    return () => {
      alive = false;
      clearTimeout(reconnect);
      socket?.close();
    };
  }, [role]);

  // This effect runs after React has committed the new result to the DOM.
  // A following frame provides a render opportunity; this is not a photon
  // measurement, but it cannot acknowledge an uncommitted setState anymore.
  useEffect(() => {
    if (role !== 'doctor' || !state) {
      return;
    }
    for (const message of state.messages.flatMap((item) => item.words ?? [item])) {
      if (message.role !== 'patient' || message.manual || seen.current.has(message.id)) {
        continue;
      }
      seen.current.add(message.id);
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          void request('/metrics', { event: 'doctor_result_painted', role, message_id: message.id, received_at_ms: receivedAt.current.get(message.id), painted_at_ms: Date.now() }).catch(() => undefined);
        });
      });
    }
  }, [role, state]);

  return { bootstrap, state, connected, error };
}
