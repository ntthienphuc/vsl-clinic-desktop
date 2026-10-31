"""Audio boundaries and cancellation, independent of ASR model accuracy."""
import asyncio
import json
from pathlib import Path

import pytest

from backend.speech import FRAME_BYTES, SpeechService, UtteranceSegmenter, stream_dictation


class MarkedVad:
    def is_speech(self, frame, rate):
        assert rate == 16000
        return frame[0] == 1


VOICE = bytes([1, 0]) * (FRAME_BYTES // 2)
SILENCE = bytes(FRAME_BYTES)


def test_vad_short_chunk_boundaries_endpoint_and_silence():
    segmenter = UtteranceSegmenter(MarkedVad())
    frames = [SILENCE] * 20 + [VOICE] * 24 + [SILENCE] * 18
    data = b''.join(frames)
    utterances = []
    for offset in range(0, len(data), 3200):
        utterances.extend(segmenter.feed(data[offset:offset + 3200]))
    assert len(utterances) == 1
    assert utterances[0]['endpoint_audio_ms'] == 576
    assert not utterances[0]['cut_at_limit']
    assert utterances[0]['pcm'].count(VOICE) == 24
    assert segmenter.finish() is None
    assert UtteranceSegmenter(MarkedVad()).feed(SILENCE * 10) == []


def test_stop_keeps_partial_packet_and_ceiling_is_bounded():
    segmenter = UtteranceSegmenter(MarkedVad())
    for _ in range(10):
        assert segmenter.feed(VOICE) == []
    segmenter.feed(VOICE[:100])
    assert segmenter.finish()['pcm'].endswith(VOICE + VOICE[:100])
    result = []
    for _ in range(1200):
        result.extend(segmenter.feed(VOICE))
    assert len(result) == 1
    assert result[0]['cut_at_limit']
    assert result[0]['duration_ms'] == 12000
    assert segmenter.finish() is None
    # A long continuous signal cannot generate another turn without a pause.
    for frame in [SILENCE] * 18 + [VOICE] * 24 + [SILENCE] * 18:
        result.extend(segmenter.feed(frame))
    assert len(result) == 2
    assert not result[1]['cut_at_limit']
    with pytest.raises(ValueError):
        segmenter.feed(b'x')


class Socket:
    def __init__(self):
        self.input = asyncio.Queue()
        self.output = asyncio.Queue()

    async def accept(self):
        pass

    async def close(self, code=1000):
        await self.output.put({'type': 'closed', 'code': code})

    async def receive(self):
        return await self.input.get()

    async def send_json(self, item):
        await self.output.put(item)


class Service:
    active_id = None

    def info(self):
        return {'available': True}

    def prepare(self):
        pass

    async def run(self, function, *args):
        return function(*args)

    def transcribe(self, pcm):
        return {'text': 'Cảm ơn', 'decode_ms': 1, 'audio_ms': 1000, 'uncertain': False}


def test_missing_model_error_is_sent_to_ui():
    async def scenario():
        service = SpeechService(Path('missing-assets'))
        socket = Socket()
        try:
            await asyncio.wait_for(stream_dictation(socket, service, lambda: 'a', lambda x: None), 2)
            packets = []
            while not socket.output.empty():
                packets.append(socket.output.get_nowait())
            assert any(p['type'] == 'error' and 'Thiếu' in p['message'] for p in packets)
            assert service.active_id is None
        finally:
            service.close()
    asyncio.run(scenario())


def test_finish_and_reset_generation_fence(monkeypatch):
    monkeypatch.setattr('backend.speech.SpeechActivity', MarkedVad)

    async def scenario(reset):
        service = Service()
        socket = Socket()
        generation = ['a']
        metrics = []
        task = asyncio.create_task(stream_dictation(socket, service, lambda: generation[0], metrics.append))
        while (await socket.output.get())['type'] != 'ready':
            pass
        for _ in range(10):
            await socket.input.put({'type': 'websocket.receive', 'bytes': VOICE})
        if reset:
            generation[0] = 'b'
        await socket.input.put({'type': 'websocket.receive', 'text': json.dumps({'action': 'finish'})})
        await asyncio.wait_for(task, 2)
        outputs = []
        while not socket.output.empty():
            outputs.append(socket.output.get_nowait())
        transcripts = [p for p in outputs if p['type'] == 'transcript']
        assert len(transcripts) == (0 if reset else 1)
        assert len(metrics) == (0 if reset else 1)
        assert service.active_id is None
    asyncio.run(scenario(False))
    asyncio.run(scenario(True))


def test_decoder_failure_does_not_hang_finish(monkeypatch):
    monkeypatch.setattr('backend.speech.SpeechActivity', MarkedVad)

    class Broken(Service):
        def transcribe(self, pcm):
            raise RuntimeError('decoder failed')

    async def scenario():
        socket = Socket()
        task = asyncio.create_task(stream_dictation(socket, Broken(), lambda: 'a', lambda x: None))
        while (await socket.output.get())['type'] != 'ready':
            pass
        for _ in range(10):
            await socket.input.put({'type': 'websocket.receive', 'bytes': VOICE})
        await socket.input.put({'type': 'websocket.receive', 'text': '{"action":"finish"}'})
        await asyncio.wait_for(task, 2)
        outputs = []
        while not socket.output.empty():
            outputs.append(socket.output.get_nowait())
        assert any(p['type'] == 'error' and 'decoder failed' in p['message'] for p in outputs)
    asyncio.run(scenario())


@pytest.mark.parametrize('mode', ['auto', 'manual'])
def test_live_pause_delivers_before_socket_finish_and_never_duplicates(monkeypatch, mode):
    from backend.session import ClinicSession
    from backend.text_to_sign import TextPlanner
    root = Path(__file__).resolve().parents[1]
    words = json.loads((root / 'assets/vocabulary.json').read_text(encoding='utf-8'))
    phrases = json.loads((root / 'assets/phrases.json').read_text(encoding='utf-8'))
    session = ClinicSession(TextPlanner(words, phrases), {word['id']: 1000 for word in words})
    session.configure_conversation(mode)
    session.start_conversation()
    epoch = session.conversation['epoch']
    monkeypatch.setattr('backend.speech.SpeechActivity', MarkedVad)

    async def scenario():
        socket = Socket()
        task = asyncio.create_task(stream_dictation(
            socket, Service(), lambda: epoch, lambda metric: None,
            live=True, on_transcript=lambda result: session.speech_result(result, epoch)))
        while (await socket.output.get())['type'] != 'ready':
            pass
        for _ in range(2):
            for frame in [VOICE] * 24 + [SILENCE] * 18:
                await socket.input.put({'type': 'websocket.receive', 'bytes': frame})
            while True:
                event = await asyncio.wait_for(socket.output.get(), 2)
                assert event['type'] not in {'error', 'closed'}, event
                if event['type'] == 'transcript':
                    break
            assert event['delivery']['status'] == ('sent' if mode == 'auto' else 'review')
            assert not task.done()  # Pause sends while the live microphone remains open.
        await socket.input.put({'type': 'websocket.receive', 'text': '{"action":"finish"}'})
        await asyncio.wait_for(task, 2)
        assert len(session.messages) == (2 if mode == 'auto' else 0)
        assert len(session.speech_drafts) == (0 if mode == 'auto' else 2)
        identities = [item.get('speech_utterance_id', item['id']) for item in session.messages + session.speech_drafts]
        assert len(set(identities)) == 2
    asyncio.run(scenario())


def test_empty_decoder_result_warns_without_creating_a_draft(monkeypatch):
    monkeypatch.setattr('backend.speech.SpeechActivity', MarkedVad)

    class Empty(Service):
        def transcribe(self, pcm):
            return {'text': '', 'decode_ms': 1, 'audio_ms': 1000, 'uncertain': True}

    async def scenario():
        socket = Socket()
        delivered = []
        task = asyncio.create_task(stream_dictation(socket, Empty(), lambda: 'a', lambda x: None,
                                                     live=True, on_transcript=delivered.append))
        while (await socket.output.get())['type'] != 'ready':
            pass
        for frame in [VOICE] * 24 + [SILENCE] * 18:
            await socket.input.put({'type': 'websocket.receive', 'bytes': frame})
        while True:
            event = await asyncio.wait_for(socket.output.get(), 2)
            assert event['type'] not in {'error', 'transcript'}
            if event['type'] == 'speech_rejected':
                assert 'nói lại' in event['message']
                break
        assert not delivered
        await socket.input.put({'type': 'websocket.receive', 'text': '{"action":"finish"}'})
        await asyncio.wait_for(task, 2)
    asyncio.run(scenario())
