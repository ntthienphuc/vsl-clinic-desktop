"""Preview must never block capture or mutate the model's source frame."""
import threading
import time
import numpy as np
from multimodal.preview import LatestPreview


def test_slow_display_transport_is_bounded_and_does_not_block_camera_frames():
    cancel, done, entered, release = [threading.Event() for _ in range(4)]
    sent = []
    def publish(data):
        entered.set()
        release.wait(2)
        sent.append(data)
    display = LatestPreview(publish,cancel,done)
    original = np.full((64,64,3),123,np.uint8)
    display.thread.start()
    display.offer(original,time.perf_counter()*1000)
    assert entered.wait(1)
    start = time.perf_counter()
    for i in range(100):
        display.offer(original,time.perf_counter()*1000)
    assert time.perf_counter()-start < .1
    assert display.frames.qsize()==1 and display.dropped==99
    assert (original==123).all()
    done.set()
    release.set()
    display.thread.join(2)
    assert not display.thread.is_alive()
    assert len(sent)==2
    assert all(jpeg.startswith(b'\xff\xd8') for jpeg in sent)


def test_end_prevents_future_preview_callbacks():
    cancel, done = threading.Event(), threading.Event()
    sent=[]
    display=LatestPreview(sent.append,cancel,done)
    cancel.set()
    display.offer(np.zeros((8,8,3),np.uint8),time.perf_counter()*1000)
    display.thread.start()
    display.thread.join(1)
    assert not display.thread.is_alive() and not sent
