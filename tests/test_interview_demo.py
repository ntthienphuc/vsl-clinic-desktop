"""Verify interview meaning and the patient model boundary independently of playback."""
import csv
import json
from pathlib import Path

import pytest
from backend.text_to_sign import TextPlanner

ROOT = Path(__file__).resolve().parents[1]


def read(name):
    return json.loads((ROOT / name).read_text(encoding='utf-8'))


@pytest.fixture
def planner():
    return TextPlanner(read('assets/vocabulary.json'), read('assets/phrases.json'), read('assets/semantic_bank.json'))


@pytest.mark.parametrize('text, expected', [
    ('Bạn cảm thấy như thế nào?', ['Cảm thấy', 'Thế nào']),
    ('Bạn đau bụng lúc nào?', ['Bụng', 'Đau', 'Bao giờ']),
    ('Bạn ngủ khi nào?', ['Ngủ', 'Bao giờ']),
    ('Bạn thức dậy vào lúc nào?', ['Thức dậy', 'Bao giờ']),
    ('Bản thức dậy vào lúc nào.', ['Thức dậy', 'Bao giờ']),
    ('Bạn ăn có ngon miệng không?', ['Ăn', 'Ngon miệng']),
])
def test_interview_question_meaning(planner, text, expected):
    result = planner.plan(text)
    assert result['supported']
    assert result['projection'] == expected
    assert result['text'] == text


@pytest.mark.parametrize('text', [
    'Bạn đau bụng bao nhiêu ngày?', 'Bạn bắt đầu đau bụng khi nào?',
    'Bạn ngủ bao nhiêu tiếng?', 'Bạn có bị mất ngủ không?',
    'Bạn không ăn ngon miệng phải không?', 'Bạn sốt 39 độ phải không?',
])
def test_related_but_uncovered_clinical_meaning_stays_blocked(planner, text):
    assert not planner.plan(text)['supported']


def test_every_rehearsal_turn_uses_real_bank_and_unchanged_patient_classes(planner):
    with (ROOT / 'assets/gloss.csv').open(encoding='utf-8', newline='') as f:
        labels = dict(csv.reader(f))
    assert len(labels) == 400
    scenarios = read('demo/scenarios-v0.3.6.json')['scenarios']
    assert len(scenarios) == 2
    for scenario in scenarios:
        assert len(scenario['steps']) >= 10
        for step in scenario['steps']:
            assert planner.plan(step['doctor'])['supported'], step['doctor']
            for identity in step['patient_ids']:
                assert str(identity) in labels
                assert (ROOT / f'assets/samples/{identity:03d}.mp4').is_file()
