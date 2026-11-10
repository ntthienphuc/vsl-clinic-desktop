import { useState } from 'react';
import type { Bootstrap } from '../types';
import { Dialog } from './Dialog';

export function QuickPhrases({ phrases, onChoose, onClose }: {
  phrases: NonNullable<Bootstrap['quick_phrases']>;
  onChoose: (text: string, supported: boolean) => void; onClose: () => void;
}) {
  const [group, setGroup] = useState('Tất cả');
  const [query, setQuery] = useState('');
  const normalize = (value: string) => value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/đ/gi, 'd').toLowerCase();
  const visible = phrases.filter(p => (group === 'Tất cả' || p.category === group) && normalize(p.text).includes(normalize(query.trim())));
  return <Dialog title="Câu thường dùng khi khám bệnh" onClose={onClose}>
    <p className="picker-help">Chọn câu để điền vào ô gửi. Kiểm tra đúng ý rồi bấm Gửi người bệnh.</p>
    <input className="vocabulary-search" aria-label="Tìm câu khám bệnh" placeholder="Tìm: khám bệnh, nhiệt độ, đau…" value={query} onChange={e => setQuery(e.target.value)} />
    <div className="quick-phrase-categories" aria-label="Nhóm câu thường dùng">{['Tất cả', ...new Set(phrases.map(p => p.category))].map(name =>
      <button key={name} className={name === group ? 'selected' : ''} aria-pressed={name === group} onClick={() => setGroup(name)}>{name}</button>)}</div>
    <div className="clinic-phrase-list">{visible.map(phrase => <button key={phrase.id} onClick={() => onChoose(phrase.text, phrase.supported)}>
      <strong>{phrase.text}</strong>{!phrase.supported && <span>Gửi bằng chữ</span>}
    </button>)}</div>
    {!visible.length && <p>Chưa có câu phù hợp. Đóng hộp này để nhập lời bạn muốn nói.</p>}
  </Dialog>;
}
