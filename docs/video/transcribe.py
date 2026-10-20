"""Transcribes the cut's voice files with the time of every word, so the picture can wait for a word.

    uv run --with faster-whisper==1.1.1 python docs/video/transcribe.py FILE.wav [FILE.wav ...] [--prompt TEXT]

docs/video/cut.py --dialogue runs it on the voice files it has cleaned (trimmed, normalised, 48 kHz mono) whose
transcript is missing, and writes FILE.json beside each: {"file", "duration", "text", "words": [{"word", "start",
"end"}]}. English uses Whisper small.en; a file named in --chinese uses small, which also hears Chinese. The
captions are the script's words, not these: the transcript gives only the times.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def samples(f: Path):
    """The file's audio at 16 kHz as Whisper wants it. The cut's files are 16-bit mono WAV at 48 kHz, so every
    three samples are averaged; reading them here keeps PyAV's decoder (whose newer releases faster-whisper 1.1.1
    cannot open files with) out of the way."""
    import wave

    import numpy as np

    with wave.open(str(f), "rb") as w:
        if w.getsampwidth() != 2 or w.getnchannels() != 1 or w.getframerate() % 16000:
            raise SystemExit(f"{f.name}: expected 16-bit mono WAV at a multiple of 16 kHz")
        step = w.getframerate() // 16000
        x = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float32) / 32768.0
    x = x[: len(x) // step * step]
    return x.reshape(-1, step).mean(axis=1)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("--prompt", default="", help="words to spell as written (names, products)")
    parser.add_argument("--chinese", nargs="*", default=[], help="files whose line has Chinese in it")
    args = parser.parse_args()
    from faster_whisper import WhisperModel

    models: dict[str, WhisperModel] = {}
    for f in args.files:
        name = "small" if f.name in args.chinese or str(f) in args.chinese else "small.en"
        if name not in models:
            models[name] = WhisperModel(name, device="cpu", compute_type="int8")
        segments, info = models[name].transcribe(samples(f), word_timestamps=True, beam_size=5, vad_filter=False,
                                                 initial_prompt=args.prompt or None, condition_on_previous_text=False)
        words, text = [], []
        for s in segments:
            text.append(s.text.strip())
            words += [{"word": w.word.strip(), "start": round(w.start, 3), "end": round(w.end, 3)} for w in s.words or []]
        out = {"file": f.name, "duration": round(info.duration, 3), "text": " ".join(text), "words": words}
        f.with_suffix(".json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"{f.name}: {len(words)} words, {info.duration:.1f} s: {out['text'][:70]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
