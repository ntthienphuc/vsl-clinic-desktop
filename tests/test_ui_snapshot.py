"""UI transport must retain conversation actions without sending model arrays."""
import json
from pathlib import Path

from backend.session import ClinicSession
from backend.text_to_sign import TextPlanner


def test_ui_transport_preserves_words_timing_and_diagnostic_evidence():
    root = Path(__file__).resolve().parents[1]
    words = json.loads((root / 'assets/vocabulary.json').read_text('utf-8'))
    bank = json.loads((root / 'assets/motions/manifest.json').read_text('utf-8'))
    session = ClinicSession(TextPlanner(words), {e['id']: e['duration_ms'] for e in bank['entries']})
    session.send('Bác sĩ', 'sign')
    word = dict(id='patient-1', text='Sốt', uncertain=True,
                predictions=[dict(class_id='W068', gloss='Sốt', score=.8)],
                recognition=dict(policy=dict(disposition='review')),
                metrics=dict(inference_ms=123, generation=2, segment_id='stream:1', stream_id='stream',
                             quality=dict(input_fps=25), logits=[.1] * 100,
                             keypoints=[[.5] * 150] * 50))
    session.current_result = word
    session.messages.append(dict(id='turn-1', role='patient', words=[word]))
    full = session.snapshot(diagnostics=True)
    ui = session.snapshot()
    assert ui['playback'] == full['playback']  # Sign, voice and mouth timing unchanged.
    for key in ('id', 'text', 'uncertain', 'predictions', 'recognition'):
        assert ui['current_result'][key] == full['current_result'][key]
    assert ui['current_result']['metrics'] == dict(inference_ms=123, generation=2,
                                                  segment_id='stream:1', stream_id='stream')
    assert len(json.dumps(ui)) < len(json.dumps(full)) / 2
    assert full['current_result']['metrics']['quality']['input_fps'] == 25
    assert len(full['messages'][-1]['words'][0]['metrics']['keypoints']) == 50
    ui['current_result']['predictions'][0]['gloss'] = 'changed'
    ui['messages'][-1]['words'][0]['uncertain'] = False
    full['current_result']['metrics']['logits'][0] = 99
    assert session.current_result['predictions'][0]['gloss'] == 'Sốt'
    assert session.current_result['uncertain'] is True
    assert session.current_result['metrics']['logits'][0] == .1
