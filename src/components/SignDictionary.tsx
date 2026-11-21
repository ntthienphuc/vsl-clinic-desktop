import { lazy, memo, Suspense, useEffect, useMemo, useState } from 'react';
import { ArrowRight, ChevronLeft, ChevronRight, Search, X } from 'lucide-react';
import { t, useInterfaceLanguage } from '../i18n';
import type { Bootstrap } from '../types';
import './sign-dictionary.css';

const DictionaryPreview = lazy(() => import('../avatar/DictionaryPreview').then(m => ({ default: m.DictionaryPreview })));
const fold = (value: string) => value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/đ/gi, 'd').toLowerCase();
const PAGE_SIZE = 36;

export const SignDictionary = memo(function SignDictionary({ bootstrap, onUse }: { bootstrap: Bootstrap; onUse: (word: string) => void }) {
  useInterfaceLanguage();
  const [query, setQuery] = useState(''), [category, setCategory] = useState('Tất cả'), [page, setPage] = useState(0);
  const [selected, setSelected] = useState(bootstrap.vocabulary.find(w => w.label === 'Bụng')?.id ?? bootstrap.vocabulary[0]?.id);
  const index = useMemo(() => [...bootstrap.vocabulary].sort((a,b) => a.label.localeCompare(b.label, 'vi')).map(word => ({ ...word, search: fold(word.label) })), [bootstrap.vocabulary]);
  const categories = useMemo(() => ['Tất cả', ...new Set(index.map(w => w.category))], [index]);
  const results = useMemo(() => index.filter(w => (category === 'Tất cả' || category === w.category) && w.search.includes(fold(query.trim()))), [index, query, category]);
  const word = index.find(w => w.id === selected);
  const pages = Math.max(1, Math.ceil(results.length / PAGE_SIZE));
  useEffect(() => { setPage(0); }, [query, category]);
  return <section className="sign-dictionary" aria-label={t('Từ điển ký hiệu')}>
    <div className="dictionary-browser">
      <div className="dictionary-heading"><div><h2>{t('Tìm một ký hiệu')}</h2><p>{t('{0} từ có sẵn, dùng khi không có Internet.', index.length)}</p></div></div>
      <div className="dictionary-search"><Search size={19} aria-hidden="true"/><input type="search" name="sign-dictionary-search" aria-label={t('Tìm ký hiệu')} placeholder={t('Nhập từ, không cần gõ dấu…')} value={query} onChange={e => setQuery(e.target.value)} autoComplete="off"/>{query && <button className="icon-button" aria-label={t('Xóa tìm kiếm')} onClick={() => setQuery('')}><X size={18}/></button>}</div>
      <label className="dictionary-category">{t('Nhóm từ')}<select value={category} onChange={e => setCategory(e.target.value)}>{categories.map(c => <option key={c} value={c}>{t(c)}</option>)}</select></label>
      <p className="dictionary-count" role="status">{t('{0} kết quả', results.length)}</p>
      <div className="dictionary-word-list" aria-label={t('Danh sách ký hiệu')}>
        {results.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE).map(w => <button key={w.id} className={w.id === selected ? 'selected' : ''} aria-pressed={w.id === selected} onClick={() => setSelected(w.id)}><span>{w.label}</span><ChevronRight size={16} aria-hidden="true"/></button>)}
        {!results.length && <div className="dictionary-empty"><strong>{t('Chưa tìm thấy từ phù hợp')}</strong><p>{t('Thử một từ ngắn hơn hoặc chọn nhóm khác.')}</p><button className="text-button" onClick={() => { setQuery(''); setCategory('Tất cả'); }}>{t('Xem tất cả')}</button></div>}
      </div>
      {pages > 1 && <div className="dictionary-pagination"><button className="icon-button" aria-label={t('Trang trước')} disabled={page === 0} onClick={() => setPage(p => p - 1)}><ChevronLeft size={18}/></button><span>{t('Trang {0} / {1}', page + 1, pages)}</span><button className="icon-button" aria-label={t('Trang sau')} disabled={page + 1 >= pages} onClick={() => setPage(p => p + 1)}><ChevronRight size={18}/></button></div>}
    </div>
    <div className="dictionary-viewer">
      {word && <><div className="dictionary-selected-heading"><div><p>{t(word.category)}</p><h2>{word.label}</h2></div><button className="button secondary" onClick={() => onUse(word.label)}>{t('Thêm vào lời bác sĩ')}<ArrowRight size={17}/></button></div>
        <Suspense fallback={<p className="dictionary-loading" role="status">{t('Đang mở ký hiệu…')}</p>}><DictionaryPreview id={word.id} avatarUrl={bootstrap.avatar_url} entries={bootstrap.bank.entries}/></Suspense>
        <p className="dictionary-footnote">{t('Chọn từ để xem riêng. Thêm vào lời bác sĩ khi muốn dùng trong cuộc trao đổi.')}</p></>}
    </div>
  </section>;
});
