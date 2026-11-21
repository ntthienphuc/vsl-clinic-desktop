"""Requested natural utterances, exact ASR correction scope and packaged SDK exclusions."""
import json
from pathlib import Path

import pytest

from backend.avatar_voice import load_avatar_voice
from backend.session import ClinicSession
from backend.speech_repair import repair_speech
from backend.text_to_sign import TextPlanner
from tools.runtime_package import development_file, runtime_manifest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def planner():
    read = lambda name: json.loads((ROOT / 'assets' / name).read_text('utf8'))
    return TextPlanner(read('vocabulary.json'), read('phrases.json'), read('semantic_bank.json'))


@pytest.mark.parametrize('text,expected', [
    ('Đồng ý nằm nghỉ ngơi', ['Đồng ý', 'Nằm', 'Nghỉ ngơi']),
    ('Đồng ý, nằm nghỉ ngơi.', ['Đồng ý', 'Nằm', 'Nghỉ ngơi']),
    ('Bạn có đồng ý nằm nghỉ không?', ['Đồng ý', 'Nằm', 'Nghỉ ngơi']),
    ('Mời chị nằm nghỉ nhé.', ['Nằm', 'Nghỉ ngơi']),
    ('Bạn có đau mắt không?', ['Đau mắt']),
    ('Chị có bị nhức tai không ạ?', ['Đau tai']),
    ('Bạn cần đi vệ sinh không?', ['Cần', 'Nhà vệ sinh', 'Đi']),
    ('Anh muốn được ăn uống không?', ['Muốn', 'Ăn uống']),
    ('Bác sĩ băng bó rồi y tá đo nhiệt độ.', ['Bác sĩ', 'Băng bó', 'Y tá', 'Nhiệt độ', 'Đo']),
    ('Y tá tiêm.', ['Y tá', 'Tiêm']),
    ('Gọi cấp cứu.', ['Cấp cứu', 'Gọi']),
    ('Bạn hãy viết nhé.', ['Viết']),
    ('Bạn hãy tiếp tục thở nhé.', ['Tiếp tục', 'Thở']),
    ('Bạn muốn nói chuyện không?', ['Muốn', 'Nói chuyện']),
])
def test_spoken_clauses_send_once_and_every_sign_has_audio(planner, text, expected):
    plan = planner.plan(text)
    assert plan['supported'], plan
    assert plan['projection'] == expected
    session = ClinicSession(planner, {w['id']: 1000 for w in planner.words}, voice_bank=load_avatar_voice(ROOT / 'assets'))
    session.start_conversation()
    utterance = {'text': text, 'utterance_id': '064-natural', 'uncertain': False}
    session.speech_result(utterance, session.conversation['epoch'])
    session.speech_result(utterance, session.conversation['epoch'])
    assert len(session.messages) == 1 and not session.speech_drafts
    assert [cue['text'] for cue in session.playback['audio_cues']] == expected
    assert session.messages[0]['text'] == text


@pytest.mark.parametrize('text', ['Đồng ý nằm nghỉ năm phút', 'Bạn tiêm thuốc hai lần',
    'Bạn không đồng ý nằm nghỉ', 'Bạn đi vệ sinh sau khi uống thuốc', 'Y tá không tiêm.',
    'Bạn có đau mắt và đau tai không?', 'Đồng ý năm nghỉ ngơi'])
def test_new_words_never_consume_missing_details(planner, text):
    assert not planner.plan(text)['supported']


def evidence(text, **kwargs):
    return dict(text=text, segments=[{'avg_logprob': -.1, 'no_speech_prob': .01}], **kwargs)


@pytest.mark.parametrize('text', ['Đồng ý năm nghỉ ngơi', 'Mời chị năm nghỉ nhé.', 'Năm nghỉ'])
def test_rest_asr_repair_is_complete_phrase_only(text):
    corrected, metadata = repair_speech(evidence(text))
    assert corrected.casefold().count('nằm nghỉ') == 1
    assert metadata['raw_text'] == text
    assert repair_speech(evidence(text, uncertain=True)) == (text, None)
    assert repair_speech(evidence(text, cut_at_limit=True)) == (text, None)
    assert repair_speech({'text': text}) == (text, None)


@pytest.mark.parametrize('text', ['Năm phút nghỉ ngơi', 'Nghỉ ngơi năm ngày', 'Năm nay nghỉ ngơi',
    'Đồng ý năm nghỉ ngơi hai phút', 'Không năm nghỉ ngơi', 'Năm nghỉ ngơi?', 'Năm viên thuốc'])
def test_number_negation_question_and_duration_untouched(text):
    assert repair_speech(evidence(text)) == (text, None)


def test_runtime_exclusion_retains_inference_and_source_manifest():
    for name in ['multimodal-runtime', 'multimodal-runtime-cpu']:
        source = ROOT / 'build' / name
        original = (source / 'RUNTIME_MANIFEST.json').read_bytes()
        manifest = runtime_manifest(source)
        paths = {r['path'] for r in manifest['files']}
        assert not any(development_file(Path(p)) for p in paths)
        assert 'Lib/site-packages/torch/lib/torch_cpu.dll' in paths
        assert 'Lib/site-packages/torch/__init__.py' in paths
        assert manifest['packaging']['omitted_bytes'] > 600_000_000
        assert (source / 'RUNTIME_MANIFEST.json').read_bytes() == original
        if name == 'multimodal-runtime':
            assert 'Lib/site-packages/torch/lib/torch_cuda.dll' in paths
