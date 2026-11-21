"""Generate the brief low-level offline cue that precedes an uncertain word."""
from pathlib import Path
import math
import struct
import wave

destination = Path(__file__).resolve().parents[1] / 'public/audio/uncertain-beep.wav'
rate, tone_ms, total_ms = 16000, 90, 120
samples = []
for i in range(rate * total_ms // 1000):
    seconds = i / rate
    envelope = max(0., min(1., seconds / .008, (tone_ms / 1000 - seconds) / .012))
    samples.append(round(32767 * .05 * envelope * math.sin(2 * math.pi * 880 * seconds)))
destination.parent.mkdir(parents=True, exist_ok=True)
with wave.open(str(destination), 'wb') as output:
    output.setparams((1, 2, rate, 0, 'NONE', 'not compressed'))
    output.writeframes(struct.pack('<' + 'h' * len(samples), *samples))
print(destination)
