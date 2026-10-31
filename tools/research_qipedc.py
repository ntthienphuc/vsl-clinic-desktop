"""Produce a reviewable cross-vocabulary table; never merge by numeric ID."""
from pathlib import Path
import hashlib
import json
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT.parents[1] / 'ver 1 - 2025-04-18 - VSL/qipedc_dictionary_4362_records.json'


def folded(text):
    return ' '.join(unicodedata.normalize('NFC', text).casefold().split())


def unaccent(text):
    return ''.join(c for c in unicodedata.normalize('NFD', folded(text)) if not unicodedata.combining(c)).replace('đ', 'd')


def main():
    records = json.loads(SOURCE.read_text(encoding='utf-8-sig'))
    words = json.loads((ROOT / 'assets/vocabulary.json').read_text(encoding='utf-8'))
    labels = [w['label'] for w in words] + ['Tôi', 'Bạn', 'Không', 'Chưa', 'Có', 'Đâu', 'Ngồi', 'Thuốc', 'Bụng', 'Đầu', 'Bệnh nhân', 'Mời']
    matches = []
    for label in labels:
        exact = [r for r in records if folded(r['word']) == folded(label)]
        near = [r for r in records if unaccent(r['word']) == unaccent(label) and r not in exact]
        matches.append({
            'label': label,
            'model_id': next((w['model_id'] for w in words if w['label'] == label), None),
            'exact': [{k: r.get(k) for k in ['word', 'description', 'type', 'tl', 'video_url', 'inferred_region']} for r in exact],
            'accent_candidates_require_review': [{k: r.get(k) for k in ['word', 'description', 'video_url']} for r in near],
        })
    report = {
        'source': str(SOURCE),
        'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        'records': len(records),
        'regional_status': 'The inferred_region column is local inference from filenames, not verified Dong Nai attribution.',
        'decision': 'Keep the original 20-word bank. QIPEDC candidates require sense, movement and regional review before import. No silent vocabulary merge.',
        'matches': matches,
    }
    output = ROOT / 'research/qipedc-crosswalk.json'
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
