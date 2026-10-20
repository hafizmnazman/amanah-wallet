"""Cuts the voiced demo video: the recorded clips, Hafiz's and Khaidhir's voices, the captions from the script.

    python docs/video/dialogue.py --raw DIR --voice DIR --work DIR [--takes FILE] [--out FILE] [--plan]
                                  [--metamask FILE --metamask-span a,b[;c,d] --metamask-mark name=seconds ...]

The words come from docs/video/script-v2.md and the moments the picture must reach from docs/video/cues.yaml. The
voice folder holds one recording per line and take, named ID-NAME-TAKE (02.5-hafiz-1.m4a), or one per act and
speaker (03-khaidhir-1.m4a) with two seconds of silence between the lines, which is split on the silence. Each
chosen take is trimmed, filtered and brought to -16 LUFS, then transcribed (docs/video/transcribe.py) for the time
of every word.

Each act is the clips of its chapter (docs/video/cut.py's CLIPS, act N being chapter N + 1), cut as the silent cut
does: the middle of every wait goes. Then the lines are laid down one after another, and for each cue the picture
is brought to its moment just before the word is said. When the picture is early it keeps more of a wait it had
cut, or holds a frame a moment after the last cue's moment; when it is late, the voice waits, before the line or
at the widest pause inside it. The band under the picture (docs/video/band.cjs) carries the speaker who is talking,
the line as written in the script with its stressed words in gold, and where the shot was made; each voice's
waveform runs under its name. A refusal in the attacks gets its stamp. H.264 1080p30 and a 720p copy, AAC, and the
captions as an .srt.
"""

from __future__ import annotations

import argparse
import array
import difflib
import json
import re
import shutil
import subprocess
import sys
import wave
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cut  # noqa: E402  the silent cut's clips, waits and ffmpeg helpers
import yaml  # noqa: E402

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
LEAD = 0.15          # the moment shows this long before its word
HOLD_AT = 2.0        # a hold comes this long after the last cue's moment, once the pointer has settled
VOICE_LEAD, VOICE_TAIL = 0.5, 0.7
WAIT_HEAD, WAIT_TAIL = 0.8, 1.1   # of a cut wait, the seconds kept after it starts and before its result
GAP_TURN, GAP_SAME = 0.3, 0.5   # between two speakers' lines, and between two lines of one speaker
CAPTION_KEEP = 1.0   # a caption stays up across a shorter silence
ROW, CHUNK = 60, 118  # characters in a caption row, and in the two rows of one caption
STAMP_FOR = 1.8
SPEAKERS = {"H": "hafiz", "K": "khaidhir"}
CARDS = {"1", "2", "7b", "8", "9"}   # the recorder's title cards (CARD_VIEW)
TAIL_KEEP = 3.0      # seconds of picture kept after an act's last moment once the voice is done
AUDIO = (".m4a", ".wav", ".mp3", ".aac", ".ogg", ".opus", ".flac", ".webm", ".caf", ".mp4")
PROMPT = "Amanah, Claude, Qwen, Kimi, Ipoh, USDC, MetaMask, Base Sepolia, FISCO BCOS, zakat, trustee, re-check"
# Who refused, for take 3, which recorded no stamps: every attack there was refused by the planner
STAMP_FALLBACK = {"chairman": ("Stopped by the planner", "planner"), "data": ("Stopped by the planner", "planner"),
                  "admin": ("Stopped by the planner", "planner"), "letter": ("Flagged by the reader", "reader")}
NUMBERS = {"one": "1", "two": "2", "three": "3", "ten": "10", "eleven": "11", "twelve": "12", "seventeen": "17",
           "forty-four": "44", "fortyfour": "44"}


# The script


@dataclass
class Line:
    id: str
    act: int
    speaker: str
    flag: str
    text: str                      # as written: **stress**, / and // pauses
    audio: Path | None = None      # the cleaned voice, 48 kHz mono
    duration: float = 0.0
    words: list[dict] = field(default_factory=list)  # the transcript's words, with times in the cleaned file
    start: float = 0.0             # on the act's timeline
    pauses: list[tuple[float, float]] = field(default_factory=list)  # (time in the file, seconds of silence added)

    @property
    def plain(self) -> str:
        return re.sub(r"\s+", " ", re.sub(r"\*\*|/+", " ", self.text)).strip()

    def at(self, t: float) -> float:
        """A time in the file, on the act's timeline."""
        return self.start + t + sum(d for p, d in self.pauses if p <= t)

    @property
    def end(self) -> float:
        return self.at(self.duration)


def parse_script(path: Path) -> list[Line]:
    out, act = [], -1
    for raw in path.read_text(encoding="utf-8").splitlines():
        if raw.startswith("## "):
            act = int(raw[3:5])
            continue
        m = re.match(r"^- (\d\d\.\d+) ([HK])(?: \(([^)]*)\))?: (.*)$", raw)
        if m:
            out.append(Line(m[1], act, m[2], (m[3] or "").lower(), m[4].strip()))
    return out


def tokens(text: str) -> list[str]:
    """Words for matching the script against the transcript: lower case, no punctuation, numbers as digits."""
    t = re.sub(r"\*\*|/+", " ", text.lower()).replace("’", "'")
    t = re.sub(r"(\d),(\d{3})", r"\1\2", t)
    t = re.sub(r"\b(three|eleven) hundred\b", lambda m: {"three": "300", "eleven": "1100"}[m[1]], t)
    t = re.sub(r"\btwo thousand\b", "2000", t)
    out = []
    for w in re.findall(r"[\w'一-鿿-]+", t):
        w = w.strip("-'")
        if not w:
            continue
        out.append(NUMBERS.get(w, w.replace("-", "")))
    return out


# The voices


def choose_takes(voice: Path, takes: Path | None) -> dict[str, Path]:
    """The recording for each line and speaker ("02.5-H"), or for each act and speaker ("03-K"), the take picked
    in takes.md or the first."""
    picked = {}
    if takes and takes.exists():
        for m in re.finditer(r"^\s*(\d\d(?:\.\d+)?)\s*:\s*(\d+)", takes.read_text(encoding="utf-8"), re.M):
            picked[m[1]] = int(m[2])
    found: dict[str, dict[int, Path]] = {}
    for f in sorted(voice.iterdir()):
        m = re.match(r"^(\d\d(?:\.\d+)?)[-_ ]([a-z]+)[-_ ](\d+)$", f.stem, re.I)
        if not m or f.suffix.lower() not in AUDIO:
            continue
        who = "H" if m[2].lower().startswith("h") else "K" if m[2].lower().startswith("k") else None
        if who is None:
            continue
        found.setdefault(f"{m[1]}-{who}", {})[int(m[3])] = f
    return {key: by_take.get(picked.get(key.split("-")[0], 0)) or by_take[min(by_take)] for key, by_take in found.items()}


def ffmpeg_stderr(tools: cut.Tools, argv: list[str]) -> str:
    return subprocess.run([tools.ffmpeg, "-hide_banner", "-nostats", "-y", *argv], cwd=tools.work, check=True,
                          capture_output=True, text=True, encoding="utf-8", errors="replace").stderr


TRIM = ("silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.12,areverse,"
        "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.12,areverse,highpass=f=80")


def clean(tools: cut.Tools, src: Path, out: Path, ss: float | None = None, to: float | None = None) -> None:
    """Trimmed of the silence around it, a high-pass for handling noise, two-pass loudness to -16 LUFS."""
    span = (["-ss", f"{ss:.3f}"] if ss is not None else []) + (["-to", f"{to:.3f}"] if to is not None else [])
    err = ffmpeg_stderr(tools, [*span, "-i", tools.path(src), "-af", f"{TRIM},loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json",
                                "-f", "null", "-"])
    m = json.loads(err[err.rindex("{"):err.rindex("}") + 1])
    measured = (f"measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}:"
                f"measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    tools.run([*span, "-i", tools.path(src), "-af", f"{TRIM},loudnorm=I=-16:TP=-1.5:LRA=11:{measured},aresample=48000",
               "-ac", "1", "-c:a", "pcm_s16le", tools.path(out)])


def silences(tools: cut.Tools, src: Path) -> list[tuple[float, float]]:
    err = ffmpeg_stderr(tools, ["-i", tools.path(src), "-af", "silencedetect=noise=-38dB:d=1.2", "-f", "null", "-"])
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", err)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", err)]
    return list(zip(starts, ends))


def wav_length(p: Path) -> float:
    with wave.open(str(p), "rb") as w:
        return w.getnframes() / w.getframerate()


def prepare_voices(lines: list[Line], args: argparse.Namespace, tools: cut.Tools) -> None:
    folder = args.work / "voice"
    folder.mkdir(parents=True, exist_ok=True)
    takes = choose_takes(args.voice, args.takes)
    for line in lines:
        out = folder / f"{line.id}.wav"
        src = takes.get(f"{line.id}-{line.speaker}")
        if src is not None:
            if not out.exists() or out.stat().st_mtime < src.stat().st_mtime:
                clean(tools, src, out)
            line.audio = out
    # One file per act and speaker: split on the silences, in the order of that speaker's lines in the act
    for key, src in takes.items():
        if "." in key.split("-")[0]:
            continue
        act, who = int(key[:2]), key[-1]
        mine = [ln for ln in lines if ln.act == act and ln.speaker == who and ln.audio is None and "optional" not in ln.flag]
        if not mine:
            continue
        gaps = silences(tools, src)
        total = tools.length(src)
        edges = [0.0, *[(a + b) / 2 for a, b in gaps if 0.3 < a and b < total - 0.3], total]
        spans = [(edges[i], edges[i + 1]) for i in range(len(edges) - 1)]
        if len(spans) != len(mine):
            raise SystemExit(f"{src.name}: {len(spans)} parts between silences, but {len(mine)} lines of "
                             f"{SPEAKERS[who]} in act {act:02d}; record one file per line, or leave two clear seconds")
        for line, (a, b) in zip(mine, spans):
            out = folder / f"{line.id}.wav"
            if not out.exists() or out.stat().st_mtime < src.stat().st_mtime:
                clean(tools, src, out, a, b)
            line.audio = out
    def stale(ln: Line) -> bool:
        words = ln.audio.with_suffix(".json")
        return not words.exists() or words.stat().st_mtime < ln.audio.stat().st_mtime

    missing = [ln for ln in lines if ln.audio is not None and stale(ln)]
    if missing:
        chinese = [ln.audio.name for ln in missing if re.search(r"[一-鿿]", ln.text)]
        transcribe = [shutil.which("uv") or str(Path.home() / ".local/bin/uv"), "run", "--quiet", "--with",
                      "faster-whisper==1.1.1", "python", str(HERE / "transcribe.py"), *[str(ln.audio) for ln in missing],
                      "--prompt", PROMPT]
        if chinese:
            transcribe += ["--chinese", *chinese]
        subprocess.run(transcribe, check=True, cwd=REPO)
    for line in lines:
        if line.audio is None:
            continue
        line.duration = wav_length(line.audio)
        line.words = json.loads(line.audio.with_suffix(".json").read_text(encoding="utf-8"))["words"]


def word_times(line: Line) -> list[float]:
    """For each of the script's words, its start in the cleaned file: matched to the transcript where the words
    agree, spread evenly between the matched ones where they do not."""
    script = tokens(line.text)
    heard = [t for w in line.words for t in (tokens(w["word"]) or [""])[:1]]
    starts = [w["start"] for w in line.words]
    times: list[float | None] = [None] * len(script)
    for a, b, n in difflib.SequenceMatcher(None, script, heard, autojunk=False).get_matching_blocks():
        for k in range(n):
            times[a + k] = starts[b + k]
    known = [(i, t) for i, t in enumerate(times) if t is not None]
    if not known:
        return [line.duration * i / max(1, len(script)) for i in range(len(script))]
    out = []
    for i, t in enumerate(times):
        if t is not None:
            out.append(t)
            continue
        left = max(((j, s) for j, s in known if j < i), default=(-1, 0.0))
        right = min(((j, s) for j, s in known if j > i), default=(len(script), line.duration))
        out.append(left[1] + (right[1] - left[1]) * (i - left[0]) / (right[0] - left[0]))
    return out


def cue_time(line: Line, word: str, after: int) -> tuple[int, float]:
    """The first script word at or after index `after` that is the cue, and its start in the file."""
    want = tokens(word)[0]
    script = tokens(line.text)
    for i in range(after, len(script)):
        if script[i] == want or script[i].startswith(want):
            return i, word_times(line)[i]
    raise SystemExit(f"{line.id}: no cue word {word!r} in {line.plain!r}")


# The picture


@dataclass
class Piece:
    clip: str
    src: Path
    a: float
    b: float
    kind: str = "keep"     # keep, wait (its middle; `use` seconds of it are shown) or skip (never shown)
    use: float = 0.0
    hold: float = 0.0
    screen: bool = False

    @property
    def shown(self) -> float:
        return self.b - self.a if self.kind == "keep" else self.use if self.kind == "wait" else 0.0


def build(clip: str, src: Path, marks: list[dict], start: str, stop: str) -> list[Piece]:
    t0, t1 = cut.first(marks, start), cut.first(marks, stop)
    out, at, opened, skipped = [], t0, None, None

    def add(a: float, b: float, kind: str) -> None:
        if b - a > 0.05:
            out.append(Piece(clip, src, a, b, kind))

    for m in marks:
        if m["label"] == "wait":
            opened = m["t"]
        elif m["label"] == "go" and opened is not None:
            a, b = max(opened + WAIT_HEAD, at), min(m["t"] - WAIT_TAIL, t1)
            if m["t"] - opened > cut.WAIT_MIN and a < b:
                add(at, a, "keep"); add(a, b, "wait"); at = b
            opened = None
        elif m["label"] == "skip":
            skipped = m["t"]
        elif m["label"] == "resume" and skipped is not None:
            a, b = max(skipped, at), min(m["t"], t1)
            if a < b:
                add(at, a, "keep"); add(a, b, "skip"); at = b
            skipped = None
    add(at, t1, "keep")
    return out


def when(pieces: list[Piece], src: Path, t: float) -> float:
    """A source time on the act's timeline; a time in a cut part lands where the picture goes on."""
    out = 0.0
    for p in pieces:
        if p.src == src and p.a <= t < p.b:
            return out + (t - p.a if p.kind == "keep" else min(t - p.a, p.use) if p.kind == "wait" else 0.0)
        out += p.shown + p.hold
    last = [i for i, p in enumerate(pieces) if p.src == src]
    if last and t >= pieces[last[-1]].b:
        return sum(p.shown + p.hold for p in pieces[:last[-1] + 1])
    return out


def index_at(pieces: list[Piece], src: Path, t: float) -> int:
    for i, p in enumerate(pieces):
        if p.src == src and p.a <= t < p.b:
            return i
    same = [i for i, p in enumerate(pieces) if p.src == src]
    return same[-1] if same and t >= pieces[same[-1]].b else (same[0] if same else 0)


def split(pieces: list[Piece], i: int, t: float) -> int:
    """Cuts the kept piece i at source time t; returns the index of the piece that ends at t."""
    p = pieces[i]
    if t - p.a < 0.04:
        return i - 1 if i > 0 else i
    if p.b - t < 0.04:
        return i
    pieces[i:i + 1] = [Piece(p.clip, p.src, p.a, t, p.kind, screen=p.screen),
                       Piece(p.clip, p.src, t, p.b, p.kind, hold=p.hold, screen=p.screen)]
    return i


def lengthen(pieces: list[Piece], lo: tuple[Path, float] | None, hi: tuple[Path, float] | None, by: float) -> str:
    """Makes the picture `by` seconds longer between two moments (the act's start and end when None): first with
    more of a wait it had cut, then a frame held a little after the first moment, else just before the second."""
    i = index_at(pieces, *lo) if lo else 0
    j = index_at(pieces, *hi) if hi else len(pieces) - 1
    done = []
    for p in sorted((p for p in pieces[i:j + 1] if p.kind == "wait"), key=lambda p: p.use - (p.b - p.a)):
        more = min(by, p.b - p.a - p.use)
        if more > 0.05:
            p.use += more
            by -= more
            done.append(f"wait +{more:.1f}")
    if by <= 0.05:
        return ", ".join(done)
    # The hold: in the app, HOLD_AT after the first moment (its result on screen, the pointer settled) if that is
    # still before the second; on a title card, whose lines fade in on a timer, just before the second moment
    target = None
    card = lo is not None and pieces[index_at(pieces, *lo)].clip in CARDS
    if lo and not card:
        k = index_at(pieces, *lo)
        t = lo[1] + HOLD_AT
        if pieces[k].kind == "keep" and t < pieces[k].b and (not hi or (pieces[k].src, t) != hi and
                                                             when(pieces, pieces[k].src, t) < when(pieces, *hi) - 0.15):
            target = split(pieces, k, t)
    if target is None and hi:
        k = index_at(pieces, *hi)
        while k > 0 and pieces[k].kind != "keep":
            k -= 1
        p = pieces[k]
        t = min(hi[1], p.b) - 0.05 if p.src == hi[0] else p.b
        target = split(pieces, k, max(p.a + 0.04, t)) if p.kind == "keep" else k
    if target is None:
        target = len(pieces) - 1
    pieces[target].hold += by
    done.append(f"hold +{by:.1f} at {pieces[target].clip} {pieces[target].b:.1f}s")
    return ", ".join(done)


# One act


@dataclass
class Act:
    n: int
    pieces: list[Piece] = field(default_factory=list)
    lines: list[Line] = field(default_factory=list)
    stamps: list[tuple[float, str, str]] = field(default_factory=list)   # timeline time, text, signer
    log: list[str] = field(default_factory=list)

    @property
    def picture(self) -> float:
        return sum(p.shown + p.hold for p in self.pieces)

    @property
    def length(self) -> float:
        voice = max((ln.end for ln in self.lines), default=0.0) + VOICE_TAIL if self.lines else 0.0
        return max(self.picture, voice)


def load_clips(args: argparse.Namespace, tools: cut.Tools) -> tuple[dict[int, Act], dict[str, tuple[Path, list[dict]]]]:
    marks = json.loads((args.raw / "marks.json").read_text(encoding="utf-8"))
    acts: dict[int, Act] = {}
    sources: dict[str, tuple[Path, list[dict]]] = {}
    for clip, _, chapter in cut.CLIPS:
        act = acts.setdefault(chapter - 1, Act(chapter - 1))
        if clip == "6m":
            if not args.metamask:
                continue
            spans = [tuple(float(x) for x in s.split(",")) for s in args.metamask_span.split(";")]
            act.pieces += [Piece(clip, args.metamask, a, b, screen=True) for a, b in spans]
            named = [{"label": "start", "t": spans[0][0]}] + [
                {"label": k, "t": float(v)} for k, v in (m.split("=") for m in args.metamask_mark)]
            sources["6m"] = (args.metamask, named)
            continue
        returning = clip.endswith("r")
        entry = marks.get(f"ch{clip[:-1] if returning else clip}")
        if entry is None:
            continue
        labels = {m["label"] for m in entry["marks"]}
        if returning and "return" not in labels:
            continue
        src, shift = cut.assemble(args.raw / entry["dir"], entry, tools)
        moments = [{**m, "t": m["t"] + shift} for m in entry["marks"]]
        sources[f"ch{clip[:-1] if returning else clip}"] = (src, moments)
        start = "return" if returning else "start"
        stop = ("end" if returning else "switch" if "switch" in labels
                else "sign-click" if clip == "6" and args.metamask else "end")
        act.pieces += build(clip, src, moments, start, stop)
        for m in moments:
            if m["label"] == "stamp" and cut.first(moments, start) <= m["t"] <= cut.first(moments, stop):
                act.stamps.append((m["t"], m.get("text", ""), m.get("who", "planner"), src))  # type: ignore[arg-type]
    return acts, sources


def resolve(ref: str, sources: dict[str, tuple[Path, list[dict]]]) -> tuple[Path, float] | None:
    key, _, label = ref.partition(":")
    if key not in sources:
        return None
    src, moments = sources[key]
    label, _, nth = label.partition("#")
    hits = [m["t"] for m in moments if m["label"] == label]
    k = int(nth) - 1 if nth else 0
    return (src, hits[k]) if len(hits) > k else None


def align(act: Act, cues: dict, sources: dict) -> None:
    """Lays the lines down and brings each cue's moment just before its word (see the module's notes)."""
    at = VOICE_LEAD
    for k, line in enumerate(act.lines):
        if k:
            at += GAP_SAME if line.speaker == act.lines[k - 1].speaker else GAP_TURN
        line.start, line.pauses = at, []
        at = line.end
    prev_mark, prev = None, None   # the last cue's moment, and (line index, word index, file time)
    for k, line in enumerate(act.lines):
        after = 0
        for cue in cues.get(line.id, []):
            refs = cue["mark"] if isinstance(cue["mark"], list) else [cue["mark"]]
            mark = next((m for m in (resolve(r, sources) for r in refs) if m), None)
            if mark is None:
                act.log.append(f"{line.id} {cue['cue']!r}: none of {refs} in this take")
                continue
            i, wt = cue_time(line, str(cue["cue"]), after)
            after = i + 1
            voice, pic = line.at(wt), when(act.pieces, *mark)
            d = (voice - LEAD) - pic
            how = ""
            if d > 0.05:
                how = lengthen(act.pieces, prev_mark, mark, d)
            elif d < -0.05:
                if prev is None or prev[0] != k:
                    shift = -d
                    for later in act.lines[k:]:
                        later.start += shift
                    how = f"line waits {shift:.1f}s"
                else:
                    # Inside the line: the widest gap between the last cue's word and this one
                    times = word_times(line)
                    gaps = [(times[j + 1] - times[j], times[j + 1]) for j in range(prev[1], i)] or [(0, wt)]
                    _, t = max(gaps)
                    line.pauses.append((t - 0.02, -d))
                    for later in act.lines[k + 1:]:
                        later.start += -d
                    how = f"pause {-d:.1f}s inside"
            act.log.append(f"{line.id} {cue['cue']!r} at {mark[1]:.1f}s of {mark[0].stem}: "
                           f"{'on time' if not how else how}")
            prev_mark, prev = mark, (k, i, wt)
    end = max((ln.end for ln in act.lines), default=0.0) + VOICE_TAIL
    if act.lines and end > act.picture + 0.05:
        act.log.append(f"end: {lengthen(act.pieces, prev_mark, None, end - act.picture)}")
    # A picture that runs on after the voice is done ends TAIL_KEEP after the last moment (the end card excepted,
    # whose address and QR code stay up as recorded)
    if act.lines and prev_mark and act.n != 8:
        keep = max(end, when(act.pieces, *prev_mark) + TAIL_KEEP)
        if act.picture > keep + 0.5:
            cut_by = act.picture - keep
            act.log.append(f"end: {cut_by:.1f}s of picture after the voice left out")
            shorten(act.pieces, cut_by)


def shorten(pieces: list[Piece], by: float) -> None:
    """Takes `by` seconds off the end of the picture."""
    while by > 0.01 and pieces:
        p = pieces[-1]
        if p.hold > 0:
            take = min(p.hold, by); p.hold -= take; by -= take
            continue
        take = min(p.shown, by)
        if p.kind == "keep":
            p.b -= take
        elif p.kind == "wait":
            p.use -= take
        by -= take
        if p.shown < 0.05 and p.hold < 0.01:
            pieces.pop()


# Captions and the band


def chunks(text: str) -> list[str]:
    """A line's caption in parts of at most two rows, broken at its pauses: always at a // (unless the part is
    still short), at a / when the part would be too long."""
    groups = [g.strip() for g in text.split("//")]
    out: list[str] = []
    for g in groups:
        phrases = [p.strip() for p in g.split("/") if p.strip()]
        cur = ""
        for p in phrases:
            joined = f"{cur} {p}".strip()
            if cur and len(re.sub(r"\*\*", "", joined)) > CHUNK:
                out.append(cur)
                cur = p
            else:
                cur = joined
        if cur:
            if out and len(re.sub(r"\*\*", "", out[-1])) < 26 and len(re.sub(r"\*\*", "", f"{out[-1]} {cur}")) <= CHUNK:
                out[-1] = f"{out[-1]} {cur}"
            else:
                out.append(cur)
    return out


def rows(chunk: str) -> list[str]:
    plain = re.sub(r"\*\*", "", chunk)
    if len(plain) <= ROW:
        return [chunk]
    spaces = [i for i, c in enumerate(chunk) if c == " " and chunk[:i].count("**") % 2 == 0]
    i = min(spaces, key=lambda s: abs(len(re.sub(r"\*\*", "", chunk[:s])) - len(plain) / 2))
    return [chunk[:i], chunk[i + 1:]]


@dataclass
class Caption:
    a: float
    b: float
    speaker: str
    text: str


def captions(act: Act) -> list[Caption]:
    out: list[Caption] = []
    for line in act.lines:
        times = word_times(line)
        parts, k = chunks(line.text), 0
        for part in parts:
            n = len(tokens(part))
            out.append(Caption(line.at(times[k]) if k < len(times) else line.end, 0.0, line.speaker, part))
            k += n
        out[-len(parts)].a = line.start
        for j in range(len(parts) - 1):
            out[-len(parts) + j].b = out[-len(parts) + j + 1].a
        out[-1].b = line.end + 0.35
    for c, d in zip(out, out[1:]):
        if d.a - c.b < CAPTION_KEEP:
            c.b = d.a
        c.b = min(c.b, d.a)
    return out


def tags(act: Act) -> list[tuple[float, float, str]]:
    labels = {clip: tag for clip, tag, _ in cut.CLIPS}
    spans, at = [], 0.0
    for p in act.pieces:
        length = p.shown + p.hold
        tag = labels.get(p.clip, "")
        if spans and spans[-1][2] == tag:
            spans[-1] = (spans[-1][0], at + length, tag)
        else:
            spans.append((at, at + length, tag))
        at += length
    if spans:
        spans[-1] = (spans[-1][0], max(spans[-1][1], act.length), spans[-1][2])
    return spans


def band_states(act: Act, caps: list[Caption]) -> list[tuple[float, float, dict]]:
    """The band's look over the act: a new state wherever a caption or the shot's tag changes."""
    edges = sorted({0.0, act.length, *[c.a for c in caps], *[c.b for c in caps],
                    *[a for a, _, _ in tags(act)], *[b for _, b, _ in tags(act)]})
    edges = [e for e in edges if 0.0 <= e <= act.length]
    out = []
    for a, b in zip(edges, edges[1:]):
        if b - a < 1 / cut.FPS:
            continue
        mid = (a + b) / 2
        cap = next((c for c in caps if c.a <= mid < c.b), None)
        tag = next((t for x, y, t in tags(act) if x <= mid < y), "")
        state = {"speaker": cap.speaker if cap else None, "rows": rows(cap.text) if cap else [], "tag": tag}
        if out and out[-1][2] == state:
            out[-1] = (out[-1][0], b, state)
        else:
            out.append((a, b, state))
    return out


# Sound


def voice_tracks(act: Act, work: Path) -> dict[str, Path]:
    """The act's voices on its timeline: both together, and each alone for its waveform."""
    rate = 48000
    total = int(act.length * rate) + 1
    tracks = {k: array.array("h", bytes(2 * total)) for k in ("all", "H", "K")}
    for line in act.lines:
        with wave.open(str(line.audio), "rb") as w:
            data = array.array("h", w.readframes(w.getnframes()))
        cuts = [0, *[int(p * rate) for p, _ in sorted(line.pauses)], len(data)]
        for x, y in zip(cuts, cuts[1:]):
            at = int(line.at(x / rate + 1e-6) * rate) if x else int(line.start * rate)
            part = data[x:y][: max(0, total - at)]
            for key in ("all", line.speaker):
                tracks[key][at:at + len(part)] = part
    out = {}
    for key, samples in tracks.items():
        out[key] = work / f"voice-act{act.n:02d}-{key}.wav"
        with wave.open(str(out[key]), "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
            w.writeframes(samples.tobytes())
    return out


# Rendering


def render(act: Act, states: list, stamp_files: list, tools: cut.Tools, work: Path, first: bool, last: bool) -> Path:
    total = act.length
    pad = total - act.picture
    argv, graph, labels = [], [], []
    for i, p in enumerate(act.pieces):
        if p.shown < 0.01 and p.hold < 0.01:
            continue
        span = p.b - p.a if p.kind == "keep" else max(p.use, 0.04)
        argv += ["-ss", f"{p.a:.3f}", "-t", f"{span:.3f}", "-i", tools.path(p.src)]
        n = len(labels)
        fit = (f"scale={cut.W}:{cut.H}:force_original_aspect_ratio=decrease,pad={cut.W}:{cut.H}:(ow-iw)/2:(oh-ih)/2:"
               f"color={cut.NAVY}," if p.screen else "")
        hold = p.hold + (pad if i == len(act.pieces) - 1 and pad > 0.01 else 0.0)
        tail = f",tpad=stop_mode=clone:stop_duration={hold:.3f}" if hold > 0.01 else ""
        graph.append(f"[{n}:v]setpts=PTS-STARTPTS,{fit}fps={cut.FPS},setsar=1,format=yuv420p{tail}[p{n}]")
        labels.append(f"[p{n}]")
    k = len(labels)
    lines = ["ffconcat version 1.0"]
    for a, b, name in states:
        lines += [f"file bands/{name}", f"duration {b - a:.4f}"]
    lines.append(f"file bands/{states[-1][2]}")
    (work / f"band{act.n:02d}.ffconcat").write_text("\n".join(lines) + "\n", encoding="utf-8")
    argv += ["-f", "concat", "-safe", "0", "-i", tools.path(work / f"band{act.n:02d}.ffconcat")]
    voices = voice_tracks(act, work) if act.lines else {}
    graph.append(f"{''.join(labels)}concat=n={len(labels)}:v=1:a=0[pic]")
    graph.append(f"[{k}:v]fps={cut.FPS},format=yuv420p,trim=0:{total:.3f},setpts=PTS-STARTPTS[band]")
    graph.append("[pic][band]vstack=inputs=2[v0]")
    cur, idx = "v0", k + 1
    if voices:
        for who, x in (("H", 118), ("K", cut.W - 118 - 150)):
            colour = "0xD8A521" if who == "H" else "0xF0716B"
            argv += ["-i", tools.path(voices[who])]
            graph.append(f"[{idx}:a]showwaves=s=150x24:mode=cline:rate={cut.FPS}:colors={colour},format=rgba[w{who}]")
            graph.append(f"[{cur}][w{who}]overlay=x={x}:y={cut.H + 86}:shortest=0:eof_action=pass[o{who}]")
            cur, idx = f"o{who}", idx + 1
    for j, (t, name) in enumerate(stamp_files):
        argv += ["-loop", "1", "-t", f"{total:.3f}", "-i", tools.path(work / "bands" / name)]
        y = f"if(lt(t-{t:.3f},0.25),-h+(t-{t:.3f})/0.25*(h+36),36)"
        graph.append(f"[{cur}][{idx}:v]overlay=x=(W-w)/2:y='{y}':enable='between(t,{t:.3f},{t + STAMP_FOR:.3f})'[s{j}]")
        cur, idx = f"s{j}", idx + 1
    fades = []
    if first:
        fades.append("fade=t=in:st=0:d=0.6")
    if last:
        fades.append(f"fade=t=out:st={total - 0.9:.3f}:d=0.9")
    graph.append(f"[{cur}]{','.join(fades) or 'null'},trim=0:{total:.3f},setpts=PTS-STARTPTS[v]")
    if voices:
        argv += ["-i", tools.path(voices["all"])]
        graph.append(f"[{idx}:a]aformat=channel_layouts=stereo,apad,atrim=0:{total:.3f}[a]")
    else:
        argv += ["-f", "lavfi", "-t", f"{total:.3f}", "-i", "anullsrc=r=48000:cl=stereo"]
        graph.append(f"[{idx}:a]atrim=0:{total:.3f}[a]")
    script = work / f"act{act.n:02d}.filter"
    script.write_text(";\n".join(graph), encoding="utf-8")
    out = work / f"act{act.n:02d}.mp4"
    tools.run([*argv, "-/filter_complex", script.name, "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset",
               "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-r", str(cut.FPS), "-c:a", "aac", "-b:a", "160k",
               "-ar", "48000", out.name])
    return out


def srt_time(t: float) -> str:
    ms = round(t * 1000)
    return f"{ms // 3_600_000:02d}:{ms // 60_000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--raw", type=Path, required=True, help="the recorder's --out folder, with marks.json")
    parser.add_argument("--voice", type=Path, required=True, help="the recordings, ID-NAME-TAKE.m4a")
    parser.add_argument("--work", type=Path, required=True, help="a folder for the parts (on /mnt/c with Windows' ffmpeg)")
    parser.add_argument("--takes", type=Path, help="takes.md: '02.5: 2' picks take 2 of line 02.5")
    parser.add_argument("--script", type=Path, default=HERE / "script-v2.md")
    parser.add_argument("--cues", type=Path, default=HERE / "cues.yaml")
    parser.add_argument("--metamask", type=Path, help="Hafiz's screen capture of the MetaMask signature")
    parser.add_argument("--metamask-span", default="0,30", help="the seconds of it to use, a,b[;c,d]")
    parser.add_argument("--metamask-mark", action="append", default=[], help="a moment in it, name=seconds (paid=41.2)")
    parser.add_argument("--out", type=Path, default=Path("amanah-demo.mp4"))
    parser.add_argument("--ffmpeg", default=shutil.which("ffmpeg") or cut.DEFAULT_FFMPEG)
    parser.add_argument("--plan", action="store_true", help="print each act's timing and stop before rendering")
    args = parser.parse_args(argv)
    args.work.mkdir(parents=True, exist_ok=True)
    tools = cut.Tools(args.ffmpeg, args.work)

    lines = parse_script(args.script)
    lines = [ln for ln in lines if not (("with metamask" in ln.flag and not args.metamask)
                                        or ("without metamask" in ln.flag and args.metamask))]
    prepare_voices(lines, args, tools)
    lost = [ln.id for ln in lines if ln.audio is None and "optional" not in ln.flag]
    if lost:
        print(f"no recording for {', '.join(lost)}: those lines are left out")
    lines = [ln for ln in lines if ln.audio is not None]
    cues = yaml.safe_load(args.cues.read_text(encoding="utf-8"))
    acts, sources = load_clips(args, tools)
    for line in lines:
        acts.setdefault(line.act, Act(line.act)).lines.append(line)
    order = [acts[n] for n in sorted(acts) if acts[n].pieces]
    for act in order:
        align(act, cues, sources)
        voice = sum(ln.duration for ln in act.lines)
        print(f"act {act.n:02d}: {act.length:5.1f} s (picture {act.picture:5.1f} s, voice {voice:4.1f} s in "
              f"{len(act.lines)} lines)")
        for entry in act.log:
            print(f"    {entry}")
    print(f"total {sum(a.length for a in order):.1f} s")
    if args.plan:
        return 0

    # The band's drawings, all at once
    bands_dir = args.work / "bands"
    spec = {"out": str(bands_dir), "bands": [], "stamps": []}
    plans = []
    for act in order:
        caps = captions(act)
        states = []
        for j, (a, b, state) in enumerate(band_states(act, caps)):
            name = f"band-{act.n:02d}-{j:03d}.png"
            spec["bands"].append({"name": name, **state})
            states.append((a, b, name))
        stamp_files = []
        found = [(when(act.pieces, src, t), text, who) for t, text, who, src in act.stamps]  # type: ignore[misc]
        if not found and act.n == 3:
            for label, (text, who) in STAMP_FALLBACK.items():
                mark = resolve(f"ch4:{label}", sources)
                if mark:
                    found.append((when(act.pieces, *mark), text, who))
        for j, (t, text, who) in enumerate(sorted(found)):
            name = f"stamp-{act.n:02d}-{j}.png"
            spec["stamps"].append({"name": name, "text": text, "who": who})
            stamp_files.append((t + 0.1, name))
        plans.append((act, caps, states, stamp_files))
    (args.work / "bands.json").write_text(json.dumps(spec, ensure_ascii=False, indent=1), encoding="utf-8")
    subprocess.run(["node", str(HERE / "band.cjs"), str(args.work / "bands.json")], check=True, cwd=REPO,
                   env={**__import__("os").environ, "NODE_PATH": str(REPO / "frontend" / "node_modules")})

    files, srt, offset = [], [], 0.0
    for i, (act, caps, states, stamp_files) in enumerate(plans):
        out = render(act, states, stamp_files, tools, args.work, i == 0, i == len(plans) - 1)
        files.append(out)
        srt += [(offset + c.a, offset + c.b, re.sub(r"\*\*", "", c.text)) for c in caps]
        offset += tools.length(out)
        print(f"act {act.n:02d} cut")
    (args.work / "acts.txt").write_text("".join(f"file '{f.name}'\n" for f in files), encoding="utf-8")
    tools.run(["-f", "concat", "-safe", "0", "-i", "acts.txt", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
               "-movflags", "+faststart", tools.path(args.out)])
    small = args.out.with_name(args.out.stem + "-720p" + args.out.suffix)
    tools.run(["-i", tools.path(args.out), "-vf", "scale=1280:720:flags=lanczos", "-c:v", "libx264", "-preset", "medium",
               "-crf", "21", "-c:a", "copy", "-movflags", "+faststart", tools.path(small)])
    args.out.with_suffix(".srt").write_text(
        "\n".join(f"{i}\n{srt_time(a)} --> {srt_time(b)}\n{t}\n" for i, (a, b, t) in enumerate(srt, 1)), encoding="utf-8")
    print(f"{args.out}: {tools.length(args.out):.1f} s, {small.name}, captions in {args.out.with_suffix('.srt').name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
