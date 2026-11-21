import { t } from '../i18n';
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
  return <section className="recognition-mode-panel" aria-label={t("Chế độ nhận ký hiệu")}>
    <div className="recognition-mode-options" role="group" aria-label={t("Chọn cách nhận ký hiệu")}>
      <button aria-pressed={mode === 'fusion'} className={mode === 'fusion' ? 'selected' : ''}
        disabled={disabled || switching} onClick={() => choose('fusion')}>
        <strong>{t("Ký hiệu + khẩu hình")}</strong><span>{t("Cần thấy rõ miệng")}</span>
      </button>
      <button aria-pressed={mode === 'sign_only'} className={mode === 'sign_only' ? 'selected' : ''}
        disabled={disabled || switching} onClick={() => choose('sign_only')}>
        <strong>{t("Chỉ ký hiệu")}</strong><span>{t("Không cần khẩu hình")}</span>
      </button>
    </div>
    <div className="recognition-mode-summary">
      <span role="status">{switching ? t("Đang đổi chế độ…") : state.recognition?.status === 'loading' || state.recognition?.status === 'not_started'
        ? t("Đang chuẩn bị nhận dạng…") : mode === 'fusion' ? t("Giữ rõ mặt và hai tay.") : t("Giữ rõ vai và hai tay.")}</span>
      <button className="text-button" onClick={() => setOpen(true)}><BookOpen size={15} /> {t('Xem {0} từ', words.length)}</button>
    </div>
    {open && <Dialog title={t("Từ có thể nhận · {0} từ", words.length)} onClose={() => setOpen(false)}>
      <p className="picker-help">{mode === 'fusion' ? t("Ký hiệu + khẩu hình") : t("Chỉ ký hiệu")}{t(": tìm từ bạn muốn diễn đạt. Bạn không cần nói thành tiếng.")}</p>
      <input className="vocabulary-search" aria-label={t("Tìm từ người bệnh")} placeholder={t("Tìm từ, có thể gõ không dấu…")} value={search} onChange={e => setSearch(e.target.value)} />
      <p role="status">{filtered.length} {t(" từ phù hợp")}</p>
      <div className="recognition-vocabulary" data-testid="patient-vocabulary">{filtered.map(word =>
        <div key={word.id}><strong>{word.label}</strong><small>{t(word.category)}</small></div>)}</div>
      {!filtered.length && <p>{t("Không có từ này trong bộ đang chọn. Bạn có thể nhập chữ hoặc nhờ bác sĩ hỗ trợ.")}</p>}
    </Dialog>}
  </section>;
}
