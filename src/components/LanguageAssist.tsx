import { useEffect, useRef, useState } from 'react';
import { MessageSquareText } from 'lucide-react';
import { request } from '../api';
import { Dialog } from './Dialog';

interface Advice {
  text: string;
  suggestions: { text: string; phrase_id: string; projection: string[] }[];
  message: string;
  source: 'none' | 'local-model';
}

export function LanguageAssist({ text, onSelect, disabled = false }: { text: string; onSelect: (text: string) => void; disabled?: boolean }) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [advice, setAdvice] = useState<Advice | null>(null);
  const [error, setError] = useState('');
  const generation = useRef(0);
  useEffect(() => {
    generation.current += 1;
    setOpen(false); setBusy(false); setAdvice(null); setError('');
    return () => { generation.current += 1; };
  }, [text]);
  const find = async () => {
    const current = ++generation.current;
    setOpen(true); setBusy(true); setAdvice(null); setError('');
    try {
      const result = await request<Advice>('/language/suggest', { text });
      if (current === generation.current && result.text === text) setAdvice(result);
    } catch (problem) {
      if (current === generation.current) setError((problem as Error).message);
    } finally {
      if (current === generation.current) setBusy(false);
    }
  };
  return <div className="language-assist">
    <button className="text-button" disabled={disabled || !text.trim() || busy} onClick={() => void find()}><MessageSquareText size={15} /> Tìm cách diễn đạt</button>
    {open && <Dialog title="Gợi ý cách nói với người bệnh" onClose={() => setOpen(false)}>
      <div className="language-original"><small>CÂU GỐC CỦA BẠN</small><p>{text}</p></div>
      {busy && <p role="status">Đang tìm mẫu phù hợp trên máy này… Bạn có thể đóng cửa sổ để tiếp tục trao đổi.</p>}
      {error && <p role="alert">{error}</p>}
      {advice && <>
        <p role="status">{advice.message}</p>
        {advice.suggestions.map((item) => <section className="language-candidate" key={item.phrase_id}>
          <strong>{item.text}</strong><span>{item.projection.join(' → ')}</span>
          <p>Kiểm tra xem có giữ đúng ý, triệu chứng và yêu cầu của bạn không. Chọn câu chỉ điền lại ô nhập; bạn sẽ kiểm tra rồi gửi.</p>
          <button className="button primary compact" onClick={() => { onSelect(item.text); setOpen(false); }}>Dùng câu này để kiểm tra</button>
        </section>)}
      </>}
    </Dialog>}
  </div>;
}
