import { t } from '../i18n';
import type { Message } from '../types';

/** Green identifies the first-ranked result, not a verified clinical statement. */
export function PatientWordResult({ word }: { word: Message }) {
  const alternatives = (word.predictions ?? []).filter(item => item.gloss !== word.text).slice(0, 2);
  return <div className="patient-word-result" data-testid="recognition-result">
    <strong className="patient-top-word"><span className="word-rank" aria-hidden="true">1</span>{word.text}</strong>
    {alternatives.length > 0 && <div className="patient-other-words" aria-label={t('Các kết quả tiếp theo')}>
      {alternatives.map((item, index) => <strong className="patient-alternative-word" key={item.class_id ?? item.model_id ?? item.gloss}>
        <span className="word-rank" aria-hidden="true">{index + 2}</span>{item.gloss}
      </strong>)}
    </div>}
  </div>;
}
