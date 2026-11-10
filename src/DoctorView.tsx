import { useEffect, useRef, useState } from 'react';
import { ArrowDownLeft, ArrowUpRight, Check, CheckCircle2, CircleHelp, Hand, History, MessageSquareText, Plus, Send, Settings2, Volume2, VolumeX } from 'lucide-react';
import { request } from './api';
import { Conversation, Diagnostics, PlaybackControls } from './components/Shared';
import { SourcePanel, type RunAction } from './components/SourcePanel';
import { RecognitionModePanel } from './components/RecognitionModePanel';
import { QuickPhrases } from './components/QuickPhrases';
import { LiveSpeechPanel } from './speech/LiveSpeechPanel';
import { usePatientVoice } from './speech/usePatientVoice';
import { ConversationBar } from './components/ConversationBar';
import { Dialog } from './components/Dialog';
import { AvatarProgress } from './components/AvatarProgress';
import { TemporaryConversation } from './components/TemporaryConversation';
import { LanguageAssist } from './components/LanguageAssist';
import type { Bootstrap, SessionState, TextPlan } from './types';
import rehearsal from '../demo/scenarios-v0.3.6.json';

function RecognitionCard({ state, run, busy, connected }: { state: SessionState; run: RunAction; busy: boolean; connected: boolean }) {
  const voice = usePatientVoice(state, connected);
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
    <div className="section-heading"><span className="heading-icon"><ArrowDownLeft size={19} /></span><div><h2>Lời người bệnh</h2></div><button className="icon-button" aria-label={voice.enabled ? 'Tắt đọc ký hiệu' : 'Bật đọc ký hiệu'} aria-pressed={voice.enabled} title={voice.enabled ? 'Đang bật giọng đọc tiếng Việt' : 'Bật giọng đọc tiếng Việt'} onClick={voice.toggle}>{voice.enabled ? <Volume2 size={19} /> : <VolumeX size={19} />}</button></div>
    {voice.error ? <small className="patient-voice-error" role="alert">{voice.error}</small> : voice.status && <small className="patient-voice-status" role="status">{voice.status}</small>}
    {turn && <div className="live-patient-turn" data-testid="live-patient-turn" aria-live="polite">
      <span className="result-label">{turn.status === 'streaming' ? 'ĐANG NHẬN TỪNG TỪ' : 'LƯỢT VỪA KẾT THÚC'}</span>
      <div className="live-word-list" ref={liveWords}>{turn.words?.map((word) => <span key={word.id} className={word.uncertain ? 'uncertain' : ''} title={word.uncertain ? 'Chưa nhận rõ' : 'Kết quả nhận dạng'}>{word.text}{word.uncertain && ' ?'}</span>)}</div>
      {result?.quality_warning && result.status !== 'confirmed' && <p role="alert">{result.quality_warning}</p>}
      {turn.status === 'streaming' ? <small>{state.capture.status === 'signing' ? 'Người bệnh đang tiếp tục…' : 'Đang chờ ý tiếp theo…'}</small> : turn.reading?.rewritten ? <p><span>Gợi ý diễn đạt:</span> {turn.text}</p> : <small>Đã gom lượt vào nội dung trao đổi.</small>}
    </div>}
    {result ? <details key={result.id} className="word-review" open={result.uncertain && result.status !== 'confirmed'}><summary>Đối chiếu từ vừa nhận: <strong>{result.text}</strong></summary>
      {result.status === 'confirmed' && <p className="review-confirmed" data-testid="recognition-result"><CheckCircle2 size={14} /> Đã đối chiếu cùng người bệnh</p>}
      {result.status !== 'confirmed' && <div className="result-review">
        <div className="confirm-row"><input aria-label="Nội dung xác nhận" value={edited} maxLength={500} onChange={(event) => setEdited(event.target.value)} /><button className="button subtle compact" disabled={busy || !edited.trim()} onClick={() => void run(() => request('/confirm', { message_id: result.id, text: edited }))}><Check size={16} /> Xác nhận</button></div>
        {!!result.context_candidates?.length && <details className="result-alternatives"><summary>Gợi ý theo câu hỏi</summary><div className="alternative-list">{result.context_candidates.map((item) => <button key={item.class_id ?? item.model_id} title={item.reason} className="word-chip small" onClick={() => setEdited(item.gloss)}>{item.gloss}</button>)}</div></details>}
        {(result.predictions?.length ?? 0) > 1 && <details className="result-alternatives"><summary>Gợi ý khác</summary><div className="alternative-list">{result.predictions?.slice(1).map((item) => <button key={item.class_id ?? item.model_id} className="word-chip small" onClick={() => setEdited(item.gloss)}>{item.gloss}</button>)}</div></details>}
      </div>}
    </details> : !turn && <div className="recognition-idle"><span className="idle-symbol"><Hand size={29} strokeWidth={1.4} /></span><strong>{state.conversation.status === 'active' ? 'Đang theo dõi người bệnh' : 'Sẵn sàng lắng nghe'}</strong><p>{state.capture.status === 'no_person' ? 'Đưa mặt, vai và hai tay vào khung hình.' : 'Mỗi từ hiện ngay khi nhận xong. Nghỉ một nhịp dài để kết thúc lượt.'}</p></div>}
  </section>;
}

function Composer({ bootstrap, state, connected, run, busy }: { bootstrap: Bootstrap; state: SessionState; connected: boolean; run: RunAction; busy: boolean }) {
  const [text, setText] = useState('');
  const [mode, setMode] = useState<'sign' | 'text'>('sign');
  const [picker, setPicker] = useState<'phrases' | 'words' | 'demo' | null>(null);
  const [quickOpen, setQuickOpen] = useState(false);
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
    <div className="section-heading"><span className="heading-icon"><ArrowUpRight size={19} /></span><div><h2>Nói với người bệnh</h2></div></div>
    <div className="composer-body">
    <div className="composer-modes segmented" aria-label="Cách gửi nội dung">
      <button className={mode === 'sign' ? 'selected' : ''} onClick={() => setMode('sign')}><Hand size={16} /> Chữ & ký hiệu</button>
      <button className={mode === 'text' ? 'selected' : ''} onClick={() => setMode('text')}><MessageSquareText size={16} /> Chỉ gửi chữ</button>
    </div>
    <LiveSpeechPanel state={state} available={bootstrap.speech.available} connected={connected} run={run} />
    <div className="quick-phrases">
      <button className="button secondary compact" onClick={() => setQuickOpen(true)}><MessageSquareText size={17} /> Câu khám bệnh</button>
      <button className="text-button" onClick={() => { setSearch(''); setPicker('phrases'); }}>Thêm câu / từ</button>
    </div>
    <div className="composer-input">
      <textarea aria-label="Nội dung gửi người bệnh" placeholder={mode === 'sign' ? 'Nhập câu, ví dụ: Bạn có đau không?' : 'Nhập nội dung cần trao đổi…'} maxLength={500} value={text} onChange={(event) => setText(event.target.value)} onKeyDown={(event) => {
        if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
          event.preventDefault();
          send();
        }
      }} />
      <span className="character-count">{text.length}/500</span>
    </div>
    {mode === 'sign' && text.trim() && <div className={`plan-status ${plan && !plan.supported ? 'warning' : ''}`} aria-live="polite">
      {planning ? 'Đang chuẩn bị ký hiệu…' : planError ? planError : plan?.supported ? <><CheckCircle2 size={15} /><span>Sẵn sàng gửi bằng chữ và ký hiệu.</span></> : plan ? <><CircleHelp size={16} /><span>{plan.message}{!!plan.unsupported.length && <> Chưa thể hiện đầy đủ: <strong>{[...new Set(plan.unsupported.map((item) => item.text))].join(', ')}</strong>.</>}</span></> : null}
    </div>}
    {mode === 'sign' && !!plan?.suggestions.length && <div className="suggestion-panel"><strong>Cách nói gần nghĩa — chỉ chọn nếu đúng ý bạn</strong>{plan.suggestions.map((item) => <button className="word-chip" key={item.text} title={item.reason} onClick={() => setText(item.text)}>{item.text}</button>)}</div>}
    {mode === 'sign' && plan && !plan.supported && <LanguageAssist text={text} onSelect={setText} disabled={!connected || busy} />}
    </div>
    <div className="composer-actions"><span>{mode === 'sign' ? 'Chữ và ký hiệu' : 'Gửi nguyên văn bằng chữ'}<small>Ctrl + Enter để gửi</small></span><button className="button primary" disabled={!canSend} onClick={send}>Gửi người bệnh <Send size={17} /></button></div>
    <PlaybackControls playback={state.playback} pending={state.pending_count} run={run} />
    {quickOpen && <QuickPhrases phrases={bootstrap.quick_phrases ?? []} onClose={() => setQuickOpen(false)} onChoose={(value, supported) => {
      setMode(supported ? 'sign' : 'text'); setText(value); setQuickOpen(false);
    }} />}
    {picker && <Dialog title="Câu và từ có sẵn" onClose={() => setPicker(null)}>
      <div className="picker-toolbar">
        <div className="segmented" aria-label="Chọn câu hoặc từ"><button className={picker === 'phrases' ? 'selected' : ''} onClick={() => setPicker('phrases')}>Mẫu câu ({bootstrap.phrases.length})</button><button className={picker === 'words' ? 'selected' : ''} onClick={() => setPicker('words')}>Từ ({bootstrap.vocabulary.length})</button><button className={picker === 'demo' ? 'selected' : ''} onClick={() => { setPicker('demo'); setSearch(''); }}>Bài tập thử</button></div>
        <input aria-label="Tìm câu hoặc từ" placeholder="Tìm câu hoặc từ…" value={search} onChange={(event) => setSearch(event.target.value)} />
      </div>
      <p className="picker-help">{picker === 'demo' ? 'Chọn lời bác sĩ để tập trao đổi. Đợi ký hiệu phát xong rồi cho người bệnh trả lời.' : picker === 'phrases' ? 'Chọn câu, kiểm tra rồi gửi.' : 'Chọn từ để thêm vào ô nhập.'}</p>
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
  const [temporaryOpen, setTemporaryOpen] = useState(false);
  useEffect(() => { setTemporaryOpen(false); setSourceOpen(false); setResetOpen(false); }, [state.session_id]);
  return <main className="doctor-page">
    <div className="workspace-toolbar"><h1>Trao đổi với người bệnh</h1><div>{state.temporary && <button className="button secondary compact" onClick={() => setTemporaryOpen(true)}><History size={17} /> Xem lại bản tạm</button>}<button className="button secondary compact" onClick={() => setSourceOpen(true)}><Settings2 size={17} /> Camera và tùy chọn</button></div></div>
    <ConversationBar state={state} run={run} busy={busy} connected={connected} />
    <div className="doctor-grid">
      <div className="doctor-main"><Composer key={state.session_id} bootstrap={bootstrap} state={state} connected={connected} run={run} busy={busy} /></div>
      <aside className="doctor-aside">
        <RecognitionCard state={state} run={run} busy={busy} connected={connected} />
        <section className="card conversation-card"><div className="section-heading"><span className="heading-icon"><MessageSquareText size={18} /></span><div><h2>Nội dung trao đổi</h2></div><span className="message-count">{state.messages.length}</span></div><AvatarProgress playback={state.playback} pending={state.pending_count} voiceEnabled={state.avatar_voice_enabled !== false} onVoiceToggle={() => void run(() => request('/avatar/voice', { enabled: state.avatar_voice_enabled === false }))} /><Conversation messages={state.messages} />{state.clients.patient === 0 && <div className="conversation-footer"><span className="status-dot amber" />Mở màn hình người bệnh để xem ký hiệu</div>}</section>
      </aside>
    </div>
    {sourceOpen && <Dialog title="Camera và tùy chọn" onClose={() => setSourceOpen(false)}>
      <label className="conversation-send-option">Gửi lời nói của bác sĩ
        <select aria-label="Gửi lời nói của bác sĩ" value={state.conversation.mode} disabled={busy || !connected} onChange={event => void run(() => request('/conversation/configure', { mode: event.target.value }))}>
          <option value="auto">Tự gửi sau khi nói</option><option value="manual">Kiểm tra trước khi gửi</option>
        </select>
      </label>
      <h3 className="settings-heading">Cách nhận ký hiệu người bệnh</h3>
      <RecognitionModePanel bootstrap={bootstrap} state={state} run={run} disabled={busy || !connected} />
      <SourcePanel key={state.recognition?.mode} words={bootstrap.recognition_catalogs[state.recognition?.mode ?? 'fusion']} capture={state.capture} run={run} busy={busy || !connected || !!state.recognition?.switching} conversation={state.conversation} />
      <Diagnostics state={state} />
      <div className="session-reset-option"><button className="text-button" onClick={() => { setSourceOpen(false); setResetOpen(true); }}>Xóa nội dung và bắt đầu lại</button></div>
    </Dialog>}
    {temporaryOpen && state.temporary && <TemporaryConversation id={state.temporary.id} onClose={() => setTemporaryOpen(false)} run={run} />}
    {resetOpen && <Dialog title="Bắt đầu cuộc trao đổi mới?" onClose={() => setResetOpen(false)}><p>Nội dung hiện tại sẽ được xóa khỏi cả hai màn hình. Camera, micro và ký hiệu đang phát cũng sẽ dừng.</p><div className="dialog-actions"><button className="button secondary" onClick={() => setResetOpen(false)}>Tiếp tục trao đổi</button><button className="button primary" disabled={busy} onClick={() => void run(async () => {
      await request('/session/reset', {});
      setResetOpen(false);
    })}>Bắt đầu phiên mới</button></div></Dialog>}
  </main>;
}
