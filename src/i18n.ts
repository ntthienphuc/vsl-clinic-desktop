import { useSyncExternalStore } from 'react';
import { english } from './i18n/en';

export type InterfaceLanguage = 'vi' | 'en';
const storageKey = 'clinic.interfaceLanguage';
const listeners = new Set<() => void>();
let language: InterfaceLanguage = 'vi';
let revision = 0;
const valid = (value: unknown): value is InterfaceLanguage => value === 'vi' || value === 'en';

function apply(value: unknown) {
  if (!valid(value)) return;
  revision += 1;
  if (language === value) return;
  language = value;
  for (const listener of listeners) listener();
}

if (typeof window !== 'undefined') {
  if (window.clinicDesktop?.getInterfaceLanguage) {
    // The desktop profile survives the random local server port on each launch.
    window.clinicDesktop.onInterfaceLanguageChanged(apply);
    const initialRevision = revision;
    void window.clinicDesktop.getInterfaceLanguage().then(value => {
      if (revision === initialRevision) apply(value);
    }).catch(() => { /* The default Vietnamese UI remains usable. */ });
  } else {
    try { apply(localStorage.getItem(storageKey)); } catch { /* Browser storage may be unavailable. */ }
    window.addEventListener('storage', event => {
      if (event.key === storageKey) apply(event.newValue);
    });
  }
}

export function useInterfaceLanguage() {
  return useSyncExternalStore(
    listener => { listeners.add(listener); return () => { listeners.delete(listener); }; },
    () => language,
    () => 'vi' as InterfaceLanguage,
  );
}

export async function setInterfaceLanguage(next: InterfaceLanguage) {
  if (!valid(next)) throw new Error('Unsupported interface language');
  if (window.clinicDesktop?.setInterfaceLanguage) {
    // The main process persists first, then broadcasts to both windows.
    await window.clinicDesktop.setInterfaceLanguage(next);
  } else {
    localStorage.setItem(storageKey, next);
    apply(next);
  }
}

const escapePattern = (text: string) => text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
const templates = Object.entries(english).filter(([key]) => /\{\d+\}/.test(key)).map(([key, translated]) => ({
  pattern: new RegExp('^' + key.split(/\{\d+\}/).map(escapePattern).join('(.+?)') + '$'),
  translated,
}));

/** Call only for interface strings. Never pass conversation text or sign labels. */
export function t(source: string | null | undefined, ...values: (string | number)[]): string {
  if (!source) return '';
  let result = source;
  if (language === 'en') {
    const trimmed = source.trim();
    let translated = english[trimmed];
    if (translated === undefined && !values.length) {
      for (const template of templates) {
        const match = template.pattern.exec(trimmed);
        if (match) {
          translated = template.translated.replace(/\{(\d+)\}/g, (_key, index: string) => match[Number(index) + 1] ?? '');
          break;
        }
      }
    }
    if (translated !== undefined) {
      const leading = source.match(/^\s*/)?.[0] ?? '';
      const trailing = source.match(/\s*$/)?.[0] ?? '';
      result = leading + translated + trailing;
    }
  }
  return values.length ? result.replace(/\{(\d+)\}/g, (key, index: string) => String(values[Number(index)] ?? key)) : result;
}
