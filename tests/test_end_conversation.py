from copy import deepcopy
import json
from pathlib import Path
import threading

import pytest

from backend.session import ClinicSession
from backend.text_to_sign import TextPlanner
from backend.capture import CaptureEngine

ASSETS = Path(__file__).resolve().parents[1] / 'assets'


@pytest.fixture
def session():
    words = json.loads((ASSETS / 'vocabulary.json').read_text(encoding='utf-8'))
    phrases = json.loads((ASSETS / 'phrases.json').read_text(encoding='utf-8'))
    return ClinicSession(TextPlanner(words, phrases), {word['id']: 1000 for word in words})


def populate(session):
    session.configure_conversation('auto', {'kind': 'demo', 'demo_id': '395'})
    session.start_conversation()
    session.send('Bác sĩ đo nhiệt độ.', 'sign')
    session.send('Cảm ơn.', 'sign')
    session.speech_result({'utterance_id': 'old-mic', 'text': 'Uống thuốc hai viên'}, session.conversation['epoch'])
    session.capture_event({'type': 'capture', 'generation': 7, 'status': 'signing'})
    session.capture_event({'type': 'recognition', 'generation': 7, 'predictions': [{'gloss': 'Mệt', 'model_id': 204, 'score': .9}]})


def test_end_clears_both_windows_and_fences_late_work(session):
    populate(session)
    old_session, old_epoch, old_playback = session.session_id, session.conversation['epoch'], session.playback['id']
    session.stop_conversation(generation=8)
    assert session.session_id != old_session
    assert session.conversation['status'] == 'idle'
    assert session.conversation['mode'] == 'auto'
    assert session.conversation['source']['demo_id'] == '395'
    assert not session.messages and not session.pending and not session.speech_drafts and not session.metrics
    assert session.playback is None and session.current_result is None and session.turns.current is None
    assert session.temporary is None
    session.capture_event({'type': 'recognition', 'generation': 7, 'predictions': [{'gloss': 'Đau', 'score': 1}]})
    session.capture_event({'type': 'capture', 'generation': 7, 'status': 'signing'})
    assert session.speech_result({'utterance_id': 'late', 'text': 'Đau'}, old_epoch) is None
    session.control_playback('replay', old_playback)  # stale renderer controls are ignored
    assert not session.messages and session.capture['status'] == 'idle'


def test_optional_temporary_copy_is_separate_and_never_replayed(session):
    populate(session)
    session.stop_conversation(keep_temporary=True, generation=8)
    saved = deepcopy(session.temporary)
    assert len(saved['messages']) == 3 and len(saved['speech_drafts']) == 1
    assert saved['messages'][0]['status'] == 'cancelled'
    assert saved['messages'][1]['status'] == 'cancelled'
    assert saved['messages'][2]['status'] != 'streaming'
    assert not session.messages and session.playback is None
    summary = session.snapshot()['temporary']
    assert 'messages' not in summary and summary['message_count'] == 3
    session.start_conversation()
    session.send('Uống nước.', 'sign')
    assert session.temporary == saved
    session.reset(generation=9, preserve_temporary=True)
    assert session.temporary == saved and not session.messages
    session.discard_temporary()
    assert session.snapshot()['temporary'] is None


def test_next_end_replaces_or_discards_the_one_temporary_slot(session):
    populate(session)
    session.stop_conversation(True)
    old_id = session.temporary['id']
    session.start_conversation()
    session.send('Cảm ơn', 'text')
    session.stop_conversation(True)
    assert session.temporary['id'] != old_id
    assert len(session.temporary['messages']) == 1
    session.stop_conversation(False)
    assert session.temporary is None
    session.reset()
    assert session.snapshot()['temporary'] is None


def test_stopping_capture_releases_the_last_preview_even_after_eof():
    engine = object.__new__(CaptureEngine)
    engine.control = threading.RLock()
    engine.preview_lock = threading.Lock()
    engine.preview, engine.preview_version, engine.current = b'old-frame', 2, None
    engine.stop()
    assert engine.preview is None and engine.preview_version == 3
