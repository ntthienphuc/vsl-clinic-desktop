import { useEffect, useState } from 'react';
import { BookOpen } from 'lucide-react';
import { request } from '../api';
import type { Bootstrap, SessionState, RecognitionMode } from '../types';
import type { RunAction } from './SourcePanel';
import { Dialog } from './Dialog';

const fold = (text: string) => text.normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/đ/gi, 'd').toLocaleLowerCase('vi');

export function RecognitionModePanel({ bootstrap, state, run, disabled }: {
  bootstrap: Bootstrap; state: SessionState; run: RunAction; disabled: boolean;
}) {
  const mode = state.recognition?.mode ?? 'fusion';
  const switching = state.recognition?.switching;
  const words = bootstrap.recognition_catalogs[mode];
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState('');
  useEffect(() => setSearch(''), [mode]);
  const choose = (next: RecognitionMode) => {
    if (next !== mode) void run(() => request('/recognition/mode', { mode: next }));
  };
  const filtered = words.filter(word => fold(word.label).includes(fold(search.trim())));
  return <section className="recognition-mode-panel" aria-label="Chế độ nhận ký hiệu">
    <div className="recognition-mode-options" role="group" aria-label="Chọn cách nhận ký hiệu">
      <button aria-pressed={mode === 'fusion'} className={mode === 'fusion' ? 'selected' : ''}
        disabled={disabled || switching} onClick={() => choose('fusion')}>
        <strong>Ký hiệu + khẩu hình</strong><span>100 từ · Cần thấy rõ miệng</span>
      </button>
      <button aria-pressed={mode === 'sign_only'} className={mode === 'sign_only' ? 'selected' : ''}
        disabled={disabled || switching} onClick={() => choose('sign_only')}>
        <strong>Chỉ ký hiệu</strong><span>400 từ · Không cần khẩu hình</span>
      </button>
    </div>
    <div className="recognition-mode-summary">
      <span role="status">{switching ? 'Đang đổi chế độ…' : state.recognition?.status === 'loading' || state.recognition?.status === 'not_started'
        ? 'Đang chuẩn bị nhận dạng…' : mode === 'fusion' ? 'Giữ rõ mặt và hai tay.' : 'Giữ rõ vai và hai tay.'}</span>
      <button className="text-button" onClick={() => setOpen(true)}><BookOpen size={15} /> Xem {words.length} từ</button>
    </div>
    {open && <Dialog title={`Từ có thể nhận · ${words.length} từ`} onClose={() => setOpen(false)}>
      <p className="picker-help">{mode === 'fusion' ? 'Ký hiệu + khẩu hình' : 'Chỉ ký hiệu'}: tìm từ bạn muốn diễn đạt. Bạn không cần nói thành tiếng.</p>
      <input className="vocabulary-search" aria-label="Tìm từ người bệnh" placeholder="Tìm từ, có thể gõ không dấu…" value={search} onChange={e => setSearch(e.target.value)} />
      <p role="status">{filtered.length} từ phù hợp</p>
      <div className="recognition-vocabulary" data-testid="patient-vocabulary">{filtered.map(word =>
        <div key={word.id}><strong>{word.label}</strong><small>{word.category}</small></div>)}</div>
      {!filtered.length && <p>Không có từ này trong bộ đang chọn. Bạn có thể nhập chữ hoặc nhờ bác sĩ hỗ trợ.</p>}
    </Dialog>}
  </section>;
}
