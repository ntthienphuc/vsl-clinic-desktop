import { useMemo, useState } from 'react';
import { ArrowLeft, BookOpen, ClipboardList, CupSoda, HandHeart, HeartPulse, ListFilter, MessageCircle, Search, Send, Star, Stethoscope, X } from 'lucide-react';
import { t } from '../i18n';
import type { Bootstrap } from '../types';
import rehearsal from '../../demo/scenarios-v0.3.6.json';
import { Dialog } from './Dialog';
import './phrase-library.css';

const common = ['ask-pain', 'nurse-temperature', 'sit-rest', 'doctor-exam', 'ask-abdomen', 'ask-fever', 'drink-water', 'need-help'];
const categories = { 'Hỏi triệu chứng': HeartPulse, 'Khám và đo': Stethoscope, 'Chăm sóc': HandHeart, 'Nhu cầu hằng ngày': CupSoda, 'Hướng dẫn': ClipboardList, 'Giao tiếp': MessageCircle };
const normalize = (value: string) => value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/đ/gi, 'd').toLowerCase();

export function QuickPhrases({ phrases, disabled, onChoose, onClose }: {
  phrases: NonNullable<Bootstrap['quick_phrases']>;
  disabled: boolean;
  onChoose: (text: string, supported: boolean) => void;
  onClose: () => void;
}) {
  const [practice, setPractice] = useState(false);
  const [group, setGroup] = useState('Hay dùng');
  const [query, setQuery] = useState('');
  const search = normalize(query.trim());
  const groups = useMemo(() => [...new Set(phrases.map(p => p.category))], [phrases]);
  const visible = useMemo(() => {
    if (search) return phrases.filter(p => normalize(p.text).includes(search));
    if (group === 'Hay dùng') return common.flatMap(id => phrases.filter(p => p.id === id));
    return group === 'Tất cả' ? phrases : phrases.filter(p => p.category === group);
  }, [phrases, search, group]);

  return <Dialog title={t(practice ? 'Tập trao đổi' : 'Câu mẫu')} onClose={onClose} className="phrase-library-dialog">
    {practice ? <section className="library-practice">
      <button className="text-button" onClick={() => setPractice(false)}><ArrowLeft size={16}/>{t('Câu mẫu')}</button>
      <p className="library-hint">{t('Chọn lời bác sĩ để gửi ngay. Người bệnh có thể ký trả lời bất cứ lúc nào.')}</p>
      {rehearsal.scenarios.map(scenario => <details key={scenario.id}><summary>{t(scenario.title)}<span>{t('{0} bước', scenario.steps.length)}</span></summary><div>{scenario.steps.map((step, index) => <button key={index} disabled={disabled} onClick={() => onChoose(step.doctor, true)}><small>{index + 1}</small><span><strong>{step.doctor}</strong><span>{t('Người bệnh: ')}{step.meaning}</span></span></button>)}</div></details>)}
    </section> : <>
      <div className="library-toolbar">
        <div className="library-search"><Search size={18} aria-hidden="true"/>
          <input autoFocus aria-label={t('Tìm trong thư viện')} placeholder={t('Tìm câu, ví dụ: đau bụng')} type="search" autoComplete="off" name="library-search" value={query} onChange={e => setQuery(e.target.value)}/>
          {query && <button className="icon-button" onClick={() => setQuery('')} aria-label={t('Xóa tìm kiếm')}><X size={16}/></button>}
        </div>
        <label className="phrase-filter"><ListFilter size={16} aria-hidden="true"/><select aria-label={t('Nhóm câu mẫu')} value={search ? 'search' : group} onChange={event => { setGroup(event.target.value); setQuery(''); }}>
          {search && <option value="search">{t('Kết quả tìm kiếm')}</option>}
          {['Hay dùng', ...groups, 'Tất cả'].map(name => <option key={name} value={name}>{t(name)}</option>)}
        </select></label>
      </div>
      <section className="library-results">
        <div className="library-result-heading"><h3>{!search && group === 'Hay dùng' && <Star size={16} aria-hidden="true"/>}{t(search ? 'Kết quả tìm kiếm' : group)}</h3><span role="status">{t('{0} câu', visible.length)}</span></div>
        <p className="library-hint">{t('Chọn một câu để gửi ngay cho người bệnh.')}</p>
        <div className="library-phrase-list">{visible.map(phrase => {
          const Icon = categories[phrase.category as keyof typeof categories] ?? MessageCircle;
          return <button key={phrase.id} disabled={disabled} onClick={() => onChoose(phrase.text, phrase.supported)}>
            <i aria-hidden="true"><Icon size={20}/></i><span>{phrase.text}<small>{t(phrase.supported ? phrase.category : 'Gửi bằng chữ')}</small></span><Send size={15} aria-hidden="true"/>
          </button>;
        })}</div>
        {!visible.length && <div className="library-empty"><Search size={24}/><strong>{t('Chưa tìm thấy câu phù hợp')}</strong><button className="button secondary" onClick={() => { setQuery(''); setGroup('Hay dùng'); }}>{t('Xem câu hay dùng')}</button></div>}
      </section>
      <footer className="phrase-library-footer"><button className="text-button" onClick={() => setPractice(true)}><BookOpen size={16}/>{t('Tập trao đổi')}</button></footer>
    </>}
  </Dialog>;
}
