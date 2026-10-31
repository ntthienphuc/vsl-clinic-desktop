import { useEffect, useRef, useState } from 'react';
import { ArrowDownLeft, ArrowUpRight, Camera, Check, CheckCircle2, CircleHelp, Hand, MessageSquareText, Plus, Send, X } from 'lucide-react';
import { request } from './api';
import { Conversation, Diagnostics, PlaybackControls } from './components/Shared';
import { SourcePanel, type RunAction } from './components/SourcePanel';
import { LiveSpeechPanel } from './speech/LiveSpeechPanel';
import { ConversationBar } from './components/ConversationBar';
import { Dialog } from './components/Dialog';
import type { Bootstrap, SessionState, TextPlan } from './types';
import rehearsal from '../demo/scenarios-v0.3.4.json';

function RecognitionCard({ state, run, busy }: { state: SessionState; run: RunAction; busy: boolean }) {
  const result = state.current_result;
  const turn = state.patient_turn ?? [...state.messages].reverse().find((item) => item.kind === 'patient_turn');
  const [edited, setEdited] = useState('');
  const liveWords = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const element = liveWords.current;
    if (element) {
      element.scrollTop = element.scrollHeight;
    }
  }, [turn?.id, turn?.words?.length]);
  useEffect(() => {
    setEdited(result?.text ?? '');
  }, [result?.id, result?.text]);
  return <section className="card recognition-card">
    <div className="section-heading"><span className="heading-icon"><ArrowDownLeft size={19} /></span><div><h2>Người bệnh đang nói</h2><p>Ký hiệu được chuyển thành chữ</p></div><span className="soft-tag">Ký hiệu → Chữ</span></div>
    {turn && <div className="live-patient-turn" data-testid="live-patient-turn" aria-live="polite">
      <span className="result-label">{turn.status === 'streaming' ? 'ĐANG NHẬN TỪNG TỪ' : 'LƯỢT VỪA KẾT THÚC'}</span>
      <div className="live-word-list" ref={liveWords}>{turn.words?.map((word) => <span key={word.id} className={word.uncertain ? 'uncertain' : ''} title={word.uncertain ? 'Chưa nhận rõ' : 'Kết quả nhận dạng'}>{word.text}{word.uncertain && ' ?'}</span>)}</div>
      {result?.quality_warning && result.status !== 'confirmed' && <p role="alert">{result.quality_warning}</p>}
      {turn.status === 'streaming' ? <small>{state.capture.status === 'signing' ? 'Người bệnh đang tiếp tục…' : 'Đang chờ ý tiếp theo…'}</small> : turn.reading?.rewritten ? <p><span>Gợi ý diễn đạt:</span> {turn.text}</p> : <small>Đã gom lượt vào nội dung trao đổi.</small>}
    </div>}
    {result ? <details className="word-review"><summary>Đối chiếu từ vừa nhận: <strong>{result.text}</strong></summary>
      <div className={`recognition-result ${result.uncertain ? 'uncertain' : ''}`} data-testid="recognition-result">
        <span className="result-label">{result.status === 'confirmed' ? 'NỘI DUNG ĐÃ XÁC NHẬN' : 'KẾT QUẢ NHẬN DẠNG'}</span>
        <strong>{result.text}</strong>
        <span>{result.status === 'confirmed' ? <><CheckCircle2 size={14} /> Đã đối chiếu cùng người bệnh</> : <><CircleHelp size={14} /> {result.uncertain ? 'Chưa nhận rõ, vui lòng đối chiếu' : 'Vui lòng đối chiếu cùng người bệnh'}</>}</span>
      </div>
      {result.status !== 'confirmed' && <div className="result-review">
        {!!result.context_candidates?.length && <div className="alternative-list"><span>Liên quan câu hỏi vừa gửi</span>{result.context_candidates.map((item) => <button key={item.model_id} title={item.reason} className="word-chip small" onClick={() => setEdited(item.gloss)}>{item.gloss}</button>)}<small>Chọn rồi đối chiếu với người bệnh.</small></div>}
        {(result.predictions?.length ?? 0) > 1 && <details className="result-alternatives"><summary>Gợi ý khác</summary><div className="alternative-list">{result.predictions?.slice(1).map((item) => <button key={item.model_id} className="word-chip small" onClick={() => setEdited(item.gloss)}>{item.gloss}</button>)}</div></details>}
        <div className="confirm-row"><input aria-label="Nội dung xác nhận" value={edited} maxLength={500} onChange={(event) => setEdited(event.target.value)} /><button className="button subtle compact" disabled={busy || !edited.trim()} onClick={() => void run(() => request('/confirm', { message_id: result.id, text: edited }))}><Check size={16} /> Xác nhận</button></div>
      </div>}
    </details> : !turn && <div className="recognition-idle"><span className="idle-symbol"><Hand size={29} strokeWidth={1.4} /></span><strong>{state.conversation.status === 'active' ? 'Đang theo dõi người bệnh' : 'Sẵn sàng lắng nghe'}</strong><p>{state.capture.status === 'no_person' ? 'Đưa mặt, vai và hai tay vào khung hình.' : 'Mỗi từ hiện ngay khi nhận xong. Nghỉ một nhịp dài để kết thúc lượt.'}</p></div>}
  </section>;
}

function Composer({ bootstrap, state, connected, run, busy }: { bootstrap: Bootstrap; state: SessionState; connected: boolean; run: RunAction; busy: boolean }) {
  const [text, setText] = useState('');
  const [mode, setMode] = useState<'sign' | 'text'>('sign');
  const [picker, setPicker] = useState<'phrases' | 'words' | 'demo' | null>(null);
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('Tất cả');
  const [plan, setPlan] = useState<TextPlan | null>(null);
  const [planning, setPlanning] = useState(false);
  const [planError, setPlanError] = useState('');
  useEffect(() => {
    let valid = true;
    setPlan(null);
    setPlanError('');
    if (!text.trim()) {
      setPlanning(false);
      return;
    }
    setPlanning(true);
    const timer = setTimeout(() => {
      void request<TextPlan>('/text/plan', { text }).then((value) => {
        if (valid) {
          setPlan(value);
        }
      }).catch((error: Error) => {
        if (valid) {
          setPlanError(error.message);
        }
      }).finally(() => {
        if (valid) {
          setPlanning(false);
        }
      });
    }, 120);
    return () => {
      valid = false;
      clearTimeout(timer);
    };
  }, [text]);
  useEffect(() => {
    setText('');
  }, [state.session_id]);
  const canSend = connected && !busy && !!text.trim() && (mode === 'text' || (!planning && !!plan?.supported && plan.text === text.trim()));
  const reviewingSpeech = state.speech_drafts.length > 0 && !text.trim();
  const send = () => {
    if (!canSend) {
      return;
    }
    void run(async () => {
      await request('/messages', { text, mode });
      setText('');
    });
  };
  return <section className="card composer-card">
    <div className="section-heading"><span className="heading-icon"><ArrowUpRight size={19} /></span><div><h2>Nói với người bệnh</h2><p>{state.conversation.mode === 'auto' ? 'Lời nói được gửi sau nhịp ngừng.' : 'Kiểm tra lời nói trước khi gửi.'}</p></div></div>
    <div className="composer-body">
    {!reviewingSpeech && <div className="composer-modes segmented" aria-label="Cách gửi nội dung">
      <button className={mode === 'sign' ? 'selected' : ''} onClick={() => setMode('sign')}><Hand size={16} /> Chữ & ký hiệu</button>
      <button className={mode === 'text' ? 'selected' : ''} onClick={() => setMode('text')}><MessageSquareText size={16} /> Chỉ gửi chữ</button>
    </div>}
    <LiveSpeechPanel state={state} available={bootstrap.speech.available} connected={connected} run={run} />
    {!reviewingSpeech && <div className="composer-input">
      <textarea aria-label="Nội dung gửi người bệnh" placeholder={mode === 'sign' ? 'Nhập câu, ví dụ: Bạn có đau không?' : 'Nhập nội dung cần trao đổi…'} maxLength={500} value={text} onChange={(event) => setText(event.target.value)} onKeyDown={(event) => {
        if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
          event.preventDefault();
          send();
        }
      }} />
      <span className="character-count">{text.length}/500</span>
    </div>}
    {mode === 'sign' && text.trim() && <div className={`plan-status ${plan && !plan.supported ? 'warning' : ''}`} aria-live="polite">
      {planning ? 'Đang chuẩn bị cách thể hiện…' : planError ? planError : plan?.supported ? <><CheckCircle2 size={15} /><span>{plan.clauses.map((clause) => plan.glosses.slice(clause.gloss_start, clause.gloss_end).map((item) => item.label).join(' → ')).join(' / ')}{plan.semantic?.omitted.length ? <small className="semantic-note"> · Bỏ từ đệm: {[...new Set(plan.semantic.omitted.map((item) => item.text))].join(', ')}</small> : null}</span></> : plan ? <><CircleHelp size={16} /><span>{plan.message}{!!plan.unsupported.length && <> Chưa có: <strong>{[...new Set(plan.unsupported.map((item) => item.text))].join(', ')}</strong>.</>}</span></> : null}
    </div>}
    {mode === 'sign' && !!plan?.suggestions.length && <div className="suggestion-panel"><strong>Cách nói gần nghĩa — chỉ chọn nếu đúng ý bạn</strong>{plan.suggestions.map((item) => <button className="word-chip" key={item.text} title={item.reason} onClick={() => setText(item.text)}>{item.text}</button>)}</div>}
    </div>
    {!reviewingSpeech && <div className="composer-actions"><span>{mode === 'sign' ? 'Chữ và ký hiệu' : 'Gửi nguyên văn bằng chữ'}<small>Ctrl + Enter để gửi</small></span><button className="button primary" disabled={!canSend} onClick={send}>Gửi người bệnh <Send size={17} /></button></div>}
    <div className="quick-phrases">
      <button className="button secondary compact" onClick={() => { setSearch(''); setPicker('phrases'); }}><MessageSquareText size={17} /> Chọn câu / từ</button>
      {['Bạn có đau không?', 'Uống nước.'].map((phrase) => <button className="word-chip" key={phrase} onClick={() => { setMode('sign'); setText(phrase); }}>{phrase}</button>)}
    </div>
    <PlaybackControls playback={state.playback} pending={state.pending_count} run={run} />
    {picker && <Dialog title="Câu và từ có sẵn" onClose={() => setPicker(null)}>
      <div className="picker-toolbar">
        <div className="segmented" aria-label="Chọn câu hoặc từ"><button className={picker === 'phrases' ? 'selected' : ''} onClick={() => setPicker('phrases')}>Mẫu câu ({bootstrap.phrases.length})</button><button className={picker === 'words' ? 'selected' : ''} onClick={() => setPicker('words')}>Từ ({bootstrap.vocabulary.length})</button><button className={picker === 'demo' ? 'selected' : ''} onClick={() => { setPicker('demo'); setSearch(''); }}>2 kịch bản demo</button></div>
        <input aria-label="Tìm câu hoặc từ" placeholder="Tìm câu hoặc từ…" value={search} onChange={(event) => setSearch(event.target.value)} />
      </div>
      <p className="picker-help">{picker === 'demo' ? 'Chọn lượt để điền lời bác sĩ. Đợi ký hiệu phát xong, rồi người bệnh trả lời theo video tập trong bộ demo.' : picker === 'phrases' ? 'Chọn một câu, kiểm tra rồi gửi. Có thể ghép nhiều câu bằng dấu chấm.' : 'Chọn từ để thêm vào ô nhập. Chỉ gửi khi app đã có cách thể hiện đầy đủ.'}</p>
      {picker === 'words' && <div className="word-categories">{['Tất cả', ...new Set(bootstrap.vocabulary.map((word) => word.category))].map((name) => <button key={name} className={`word-chip ${category === name ? 'selected' : ''}`} onClick={() => setCategory(name)}>{name}</button>)}</div>}
      {picker === 'demo' ? <div className="rehearsal-picker">{rehearsal.scenarios.map((scenario) => <section key={scenario.id}><h3>{scenario.title}</h3>{scenario.steps.map((step, index) => <button key={index} className="rehearsal-step" onClick={() => { setMode('sign'); setText(step.doctor); setPicker(null); }}><span>{index + 1}</span><div><strong>{step.doctor}</strong><small>Người bệnh: {step.meaning}</small></div></button>)}</section>)}</div> : <div className="picker-list">
        {picker === 'phrases' ? bootstrap.phrases.filter((phrase) => phrase.text.toLocaleLowerCase('vi').includes(search.trim().toLocaleLowerCase('vi'))).map((phrase) => <button className="word-chip" key={phrase.id} onClick={() => { setMode('sign'); setText(phrase.text); setPicker(null); }}>{phrase.text}</button>)
          : bootstrap.vocabulary.filter((word) => (category === 'Tất cả' || category === word.category) && word.label.toLocaleLowerCase('vi').includes(search.trim().toLocaleLowerCase('vi'))).map((word) => <button className="word-chip" key={word.id} onClick={() => { setMode('sign'); setText((previous) => `${previous.trim()} ${word.label}`.trim().slice(0, 500)); setPicker(null); }}><Plus size={15} />{word.label}</button>)}
      </div>}
    </Dialog>}
  </section>;
}

export function DoctorView({ bootstrap, state, connected, run, busy }: { bootstrap: Bootstrap; state: SessionState; connected: boolean; run: RunAction; busy: boolean }) {
  const [resetOpen, setResetOpen] = useState(false);
  const [sourceOpen, setSourceOpen] = useState(false);
  return <main className="doctor-page">
    <div className="workspace-toolbar"><h1>Trao đổi với người bệnh</h1><div><button className="button secondary compact" onClick={() => setSourceOpen(true)}><Camera size={17} /> Camera / video</button><button className="button secondary compact" onClick={() => setResetOpen(true)}><Plus size={17} /> Cuộc trao đổi mới</button></div></div>
    <ConversationBar state={state} run={run} busy={busy} connected={connected} />
    <div className="doctor-grid">
      <div className="doctor-main"><Composer bootstrap={bootstrap} state={state} connected={connected} run={run} busy={busy} /></div>
      <aside className="doctor-aside">
        <RecognitionCard state={state} run={run} busy={busy} />
        <section className="card conversation-card"><div className="section-heading"><span className="heading-icon"><MessageSquareText size={18} /></span><div><h2>Nội dung trao đổi</h2><p>Phiên hiện tại</p></div><span className="message-count">{state.messages.length}</span></div><Conversation messages={state.messages} /><div className="conversation-footer"><span className={state.clients.patient > 0 ? 'status-dot active' : 'status-dot amber'} />{state.clients.patient > 0 ? 'Màn hình người bệnh đã kết nối' : 'Mở màn hình người bệnh để phát avatar'}</div></section>
      </aside>
    </div>
    {sourceOpen && <Dialog title="Camera, video và kết nối" onClose={() => setSourceOpen(false)}><SourcePanel words={bootstrap.vocabulary} capture={state.capture} run={run} busy={busy} conversation={state.conversation} /><Diagnostics state={state} /></Dialog>}
    {resetOpen && <div className="dialog-backdrop"><section className="dialog" role="dialog" aria-modal="true" aria-labelledby="reset-title"><button className="icon-button dialog-close" aria-label="Đóng" onClick={() => setResetOpen(false)}><X size={20} /></button><h2 id="reset-title">Bắt đầu cuộc trao đổi mới?</h2><p>Nội dung của phiên hiện tại sẽ được xóa khỏi cả hai màn hình. Camera và ký hiệu đang phát cũng sẽ dừng.</p><div className="dialog-actions"><button className="button secondary" onClick={() => setResetOpen(false)}>Tiếp tục phiên này</button><button className="button primary" disabled={busy} onClick={() => void run(async () => {
      await request('/session/reset', {});
      setResetOpen(false);
    })}>Bắt đầu phiên mới</button></div></section></div>}
  </main>;
}
