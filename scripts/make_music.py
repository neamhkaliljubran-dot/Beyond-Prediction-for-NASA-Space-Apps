"""Generate an original, synthesised rendering of J. S. Bach, Prelude in C major, BWV 846
(bars 1-8). The composition is in the public domain; this recording is generated
from scratch by this script (no third-party audio), so it carries no recording rights.

Output: assets/audio/bach_prelude_c_bwv846_synth.wav (mono, 22.05 kHz, 16-bit).
"""

from __future__ import annotations

import wave
from pathlib import Path

import numpy as np

SR = 22050
SIXTEENTH = 0.25                      # seconds; ~60 quarter notes per minute
OUT = Path(__file__).resolve().parent.parent / "assets" / "audio" / "bach_prelude_c_bwv846_synth.wav"

# Each bar: an 8-note figure (MIDI numbers) played twice.
BARS = [
    [60, 64, 67, 72, 76, 67, 72, 76],   # C
    [60, 62, 69, 74, 77, 69, 74, 77],   # Dm7/C
    [59, 62, 67, 74, 77, 67, 74, 77],   # G7/B
    [60, 64, 67, 72, 76, 67, 72, 76],   # C
    [60, 64, 69, 76, 81, 69, 76, 81],   # Am/C
    [60, 62, 66, 69, 74, 66, 69, 74],   # D7/C
    [59, 62, 67, 74, 79, 67, 74, 79],   # G/B
    [59, 60, 64, 67, 72, 64, 67, 72],   # Cmaj7/B
]


def tone(midi: int, dur: float) -> np.ndarray:
    f = 440.0 * 2 ** ((midi - 69) / 12)
    t = np.arange(int(SR * dur)) / SR
    env = np.exp(-t * 2.6) * (1 - np.exp(-t * 300))            # soft attack, piano-like decay
    partials = sum(a * np.sin(2 * np.pi * f * k * t) for k, a in [(1, 1.0), (2, 0.35), (3, 0.12), (4, 0.05)])
    return env * partials


def main() -> None:
    notes = [n for bar in BARS for n in bar * 2]
    ring = 1.6                                                    # notes overlap like a sustain pedal
    total = len(notes) * SIXTEENTH + 4.0
    y = np.zeros(int(SR * total))
    for i, n in enumerate(notes):
        s = int(i * SIXTEENTH * SR)
        x = tone(n, ring)
        y[s:s + len(x)] += x
    s = int(len(notes) * SIXTEENTH * SR)                          # closing C major chord
    for n in (48, 60, 64, 67, 72):
        x = tone(n, 3.8)
        y[s:s + len(x)] += 0.8 * x
    y *= 0.35 / np.max(np.abs(y))                                 # gentle level (about -9 dBFS)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(OUT), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((y * 32767).astype("<i2").tobytes())
    print(f"wrote {OUT} ({OUT.stat().st_size / 1e6:.2f} MB, {total:.1f} s)")


if __name__ == "__main__":
    main()
