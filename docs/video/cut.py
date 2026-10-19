"""Cuts the demo video from the clips docs/video/record.cjs recorded and Hafiz's voice-over.

    python docs/video/cut.py --raw DIR --work DIR [--voice DIR] [--take 4=2] [--metamask FILE --metamask-span 12,58.5]
                             [--out amanah-demo.mp4] [--srt docs/video/amanah-demo.srt] [--ffmpeg PATH] [--plan]

The recorder saves each clip as Chrome's screencast frames with the times they were drawn, and the cut first builds
the clip from them at 30 frames a second, so a mark's time is the clip's time. Each clip is 1920 by 960. Under it the
cut puts a 120-pixel band with the captions and, on the right, where the shot was made. Every wait the recorder marked (a model, a block, a timeout) keeps its first second and the moment before
the result; the middle goes. A chapter runs as long as its voice-over: when the voice needs longer, the frame is held
just after each result appears. The voice is trimmed of the silence around it and normalised (loudnorm), and the
captions also go to an .srt. H.264, 1080p, 30 frames a second, AAC.

The voice-over files are chN-takeK.m4a (docs/video-script.md); without them the chapters run at the recorded pace,
silent, which is how the cut is checked before the voice exists. Windows' ffmpeg works from WSL: the paths it is given
are converted with wslpath, so --work must then be on a Windows drive (/mnt/c/...).
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Clip, the band's note of where the shot was made, the voice-over chapter it belongs to
# A key ending in "r" is the same tab as the key before it, from its "return" mark: chapter 5 leaves the officer's
# tab at "switch" for the trustee's queue (5b) and comes back to it.
LOCAL = "Local test chain · live models"
CLIPS = [("1", "Local test chain", 1), ("2", "", 2), ("3", LOCAL, 3), ("4", LOCAL, 4), ("5", LOCAL, 5),
         ("5b", LOCAL, 5), ("5r", LOCAL, 5), ("6", LOCAL, 6), ("6m", "Base Sepolia · MetaMask", 6), ("7a", "", 7),
         ("7b", "Base Sepolia", 7), ("8", "", 8), ("9", "", 9)]
METAMASK_CAPTION = "A real signature in MetaMask, on Base Sepolia."
# Marks that are not moments to hold on
NOT_MOMENTS = {"start", "end", "caption", "note", "wait", "go", "skip", "resume", "sign-click", "switch", "return"}
WAIT_HEAD, WAIT_TAIL, WAIT_MIN = 1.0, 1.3, 2.8
HOLD_AFTER = 0.9
VOICE_LEAD, VOICE_TAIL = 0.3, 0.7
W, H, BAND, FPS = 1920, 960, 120, 30
NAVY, GOLD, MUTED = "0x0B1F4B", "0xD8A521", "0x9FB0D6"
DEFAULT_FFMPEG = ("/mnt/c/Users/abdul/AppData/Local/Microsoft/WinGet/Packages/"
                  "Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-8.1-full_build/bin/ffmpeg.exe")
FONTS = [("/mnt/c/Windows/Fonts/seguisb.ttf", "/mnt/c/Windows/Fonts/segoeui.ttf"),
         ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")]


@dataclass
class Piece:
    clip: str
    src: Path
    a: float
    b: float
    moment: bool = False  # ends just after a result appeared, so the frame can be held there
    hold: float = 0.0
    screen: bool = False  # a screen capture, fitted into 1920 by 960


@dataclass
class Chapter:
    n: int
    pieces: list[Piece] = field(default_factory=list)
    lines: list[tuple[str, float, str, str]] = field(default_factory=list)  # clip, source time, kind, text
    voice: Path | None = None
    voice_length: float = 0.0

    @property
    def length(self) -> float:
        return sum(p.b - p.a + p.hold for p in self.pieces)

    def at(self, clip: str, t: float) -> float:
        """A clip's source time on the chapter's timeline; a time inside a dropped wait lands where it resumes."""
        out = 0.0
        for p in self.pieces:
            if p.clip == clip and t < p.b:
                return out + max(0.0, t - p.a)
            out += p.b - p.a + p.hold
        return out


def first(marks: list[dict], label: str) -> float:
    return next(m["t"] for m in marks if m["label"] == label)


def kept(marks: list[dict], start: str, stop: str) -> list[tuple[float, float]]:
    """From `start` to `stop`, less the middle of every wait longer than WAIT_MIN and all of every skip (a page
    loading, say, which is no part of the story)."""
    t0, t1 = first(marks, start), first(marks, stop)
    spans, at, opened, skipped = [], t0, None, None
    for m in marks:
        if m["label"] == "wait":
            opened = m["t"]
        elif m["label"] == "go" and opened is not None:
            a, b = max(opened + WAIT_HEAD, at), min(m["t"] - WAIT_TAIL, t1)
            if m["t"] - opened > WAIT_MIN and a < b:
                spans.append((at, a))
                at = b
            opened = None
        elif m["label"] == "skip":
            skipped = m["t"]
        elif m["label"] == "resume" and skipped is not None:
            a, b = max(skipped, at), min(m["t"], t1)
            if a < b:
                spans.append((at, a))
                at = b
            skipped = None
    spans.append((at, t1))
    return [(a, b) for a, b in spans if b - a > 0.05]


def pieces(clip: str, src: Path, marks: list[dict], start: str, stop: str) -> list[Piece]:
    """The kept spans, cut again just after each moment so the frame can be held there."""
    t1 = first(marks, stop)
    moments = sorted(m["t"] + HOLD_AFTER for m in marks if m["label"] not in NOT_MOMENTS and m["t"] + HOLD_AFTER < t1)
    out = []
    for a, b in kept(marks, start, stop):
        cuts = [t for t in moments if a + 0.2 < t < b - 0.2]
        edges = [a, *cuts, b]
        out += [Piece(clip, src, edges[i], edges[i + 1], moment=i < len(cuts)) for i in range(len(edges) - 1)]
    out[-1].moment = True
    return out


def two_lines(text: str, width: int = 64) -> str:
    """A long caption on two lines, broken at the space nearest the middle. Up to 64 characters fit on one line
    between the band's left edge and the note on its right."""
    if len(text) <= width:
        return text
    spaces = [i for i, c in enumerate(text) if c == " "]
    i = min(spaces, key=lambda s: abs(s - len(text) / 2))
    return text[:i] + "\n" + text[i + 1:]


class Tools:
    def __init__(self, ffmpeg: str, work: Path):
        self.ffmpeg = ffmpeg
        self.ffprobe = str(Path(ffmpeg).with_name(Path(ffmpeg).name.replace("ffmpeg", "ffprobe")))
        self.windows = ffmpeg.endswith(".exe") and sys.platform.startswith("linux")
        self.work = work
        if self.windows and not str(work.resolve()).startswith("/mnt/"):
            raise SystemExit("--work must be on a Windows drive (/mnt/...) when ffmpeg is Windows' own")

    def path(self, p: Path) -> str:
        if not self.windows:
            return str(p)
        return subprocess.run(["wslpath", "-w", str(p.resolve())], check=True, capture_output=True, text=True).stdout.strip()

    def run(self, argv: list[str]) -> None:
        subprocess.run([self.ffmpeg, "-hide_banner", "-loglevel", "error", "-y", *argv], cwd=self.work, check=True)

    def length(self, p: Path) -> float:
        out = subprocess.run([self.ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                              self.path(p)], check=True, capture_output=True, text=True, cwd=self.work).stdout
        return float(out.strip())


def assemble(folder: Path, entry: dict, tools: Tools) -> tuple[Path, float]:
    """The clip at 30 frames a second, each frame shown from the time it was drawn until the next; and the seconds
    to add to a mark's time to place it on the clip's timeline. Built once per recording."""
    frames = json.loads((folder / "frames.json").read_text(encoding="utf-8"))
    end = entry["t0"] + entry["marks"][-1]["t"] + 0.4
    out = tools.work / f"clip-{folder.name}.mp4"
    if not out.exists() or out.stat().st_mtime < (folder / "frames.json").stat().st_mtime:
        lines = ["ffconcat version 1.0"]
        for (name, ts), (_, after) in zip(frames, [*frames[1:], (None, end)]):
            lines += [f"file {name}", f"duration {max(after - ts, 0.001):.6f}"]
        lines.append(f"file {frames[-1][0]}")
        (folder / "frames.ffconcat").write_text("\n".join(lines) + "\n", encoding="utf-8")
        tools.run(["-f", "concat", "-safe", "0", "-i", tools.path(folder / "frames.ffconcat"),
                   "-vf", f"fps={FPS},format=yuv420p", "-c:v", "libx264", "-preset", "fast", "-crf", "12", out.name])
    return out, entry["t0"] - frames[0][1]


def plan(args: argparse.Namespace, tools: Tools) -> list[Chapter]:
    marks = json.loads((args.raw / "marks.json").read_text(encoding="utf-8"))
    takes = dict(t.split("=") for t in args.take)
    chapters: dict[int, Chapter] = {}
    for clip, _, n in CLIPS:
        ch = chapters.setdefault(n, Chapter(n))
        if clip == "6m":
            if not args.metamask:
                continue
            spans = [tuple(float(x) for x in span.split(",")) for span in args.metamask_span.split(";")]
            ch.pieces += [Piece(clip, args.metamask, a, b, screen=True) for a, b in spans]
            ch.pieces[-1].moment = True
            ch.lines.append((clip, spans[0][0], "caption", METAMASK_CAPTION))
            continue
        returning = clip.endswith("r")
        entry = marks.get(f"ch{clip[:-1] if returning else clip}")
        if entry is None:
            continue
        labels = {m["label"] for m in entry["marks"]}
        if returning and "return" not in labels:
            continue
        src, shift = assemble(args.raw / entry["dir"], entry, tools)
        moments = [{**m, "t": m["t"] + shift} for m in entry["marks"]]
        start = "return" if returning else "start"
        stop = ("end" if returning else "switch" if "switch" in labels
                else "sign-click" if clip == "6" and args.metamask else "end")
        ch.pieces += pieces(clip, src, moments, start, stop)
        t0, t1 = first(moments, start), first(moments, stop)
        ch.lines += [(clip, m["t"], m["label"], m["text"]) for m in moments
                     if m["label"] in ("caption", "note") and t0 <= m["t"] <= t1]
    for ch in chapters.values():
        if not ch.pieces or not args.voice:
            continue
        take = args.voice / f"ch{ch.n}-take{takes.get(str(ch.n), '1')}.m4a"
        if not take.exists():
            print(f"chapter {ch.n}: no {take.name}, silent")
            continue
        # Trimmed of the silence before and after, a high-pass for handling noise, and normalised
        ch.voice = args.work / f"voice{ch.n}.wav"
        trim = "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.15,areverse"
        tools.run(["-i", tools.path(take), "-af", f"{trim},{trim},highpass=f=80,loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000",
                   "-ac", "2", ch.voice.name])
        ch.voice_length = tools.length(ch.voice)
        extra = ch.voice_length + VOICE_LEAD + VOICE_TAIL - ch.length
        if extra > 0:
            moments = [p for p in ch.pieces if p.moment]
            for p in moments:
                p.hold = extra / len(moments)
    return [chapters[n] for n in sorted(chapters) if chapters[n].pieces]


def tag_spans(ch: Chapter) -> list[tuple[float, float, str]]:
    labels = {clip: tag for clip, tag, _ in CLIPS}
    spans, at = [], 0.0
    for p in ch.pieces:
        length = p.b - p.a + p.hold
        if labels[p.clip]:
            if spans and spans[-1][2] == labels[p.clip] and abs(spans[-1][1] - at) < 1e-6:
                spans[-1] = (spans[-1][0], at + length, labels[p.clip])
            else:
                spans.append((at, at + length, labels[p.clip]))
        at += length
    return spans


def render(ch: Chapter, tools: Tools, work: Path, first_chapter: bool, last_chapter: bool) -> Path:
    total = ch.length
    argv, graph, labels = [], [], []
    for i, p in enumerate(ch.pieces):
        argv += ["-ss", f"{p.a:.3f}", "-t", f"{p.b - p.a:.3f}", "-i", tools.path(p.src)]
        fit = (f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color={NAVY},"
               if p.screen else "")
        hold = f",tpad=stop_mode=clone:stop_duration={p.hold:.3f}" if p.hold > 0.01 else ""
        graph.append(f"[{i}:v]setpts=PTS-STARTPTS,{fit}fps={FPS},setsar=1,format=yuv420p{hold}[p{i}]")
        labels.append(f"[p{i}]")
    band = [f"pad={W}:{H + BAND}:0:0:color={NAVY}", f"drawbox=x=0:y={H}:w={W}:h=3:color={GOLD}:t=fill"]
    timed = sorted(((ch.at(clip, t), kind, text) for clip, t, kind, text in ch.lines), key=lambda x: x[0])
    captions = [(t, text) for t, kind, text in timed if kind == "caption"]
    for i, (t, text) in enumerate(captions):
        end = captions[i + 1][0] if i + 1 < len(captions) else total
        # One drawtext a line: a newline inside the text is drawn as a missing glyph once the text is shaped
        lines = two_lines(text).split("\n")
        boxes = [(H, BAND)] if len(lines) == 1 else [(H + 14, 46), (H + 60, 46)]
        for j, (line, (y, height)) in enumerate(zip(lines, boxes)):
            name = f"cap{ch.n}_{i}_{j}.txt"
            (work / name).write_text(line, encoding="utf-8")
            band.append(f"drawtext=fontfile=caption.ttf:textfile={name}:expansion=none:fontsize=34:fontcolor=white:"
                        f"x=0:y={y}:boxw={W}:boxh={height}:box=1:boxcolor={NAVY}@0.0:text_align=C+M:"
                        f"enable='between(t,{t:.3f},{end:.3f})':alpha='min(1,(t-{t:.3f})/0.25)'")
    for i, (a, b, tag) in enumerate(tag_spans(ch)):
        name = f"tag{ch.n}_{i}.txt"
        (work / name).write_text(tag, encoding="utf-8")
        band.append(f"drawtext=fontfile=tag.ttf:textfile={name}:expansion=none:fontsize=20:fontcolor={MUTED}:"
                    f"x=0:y={H}:boxw={W - 36}:boxh={BAND}:box=1:boxcolor={NAVY}@0.0:text_align=R+M:"
                    f"enable='between(t,{a:.3f},{b:.3f})'")
    if first_chapter:
        band.append("fade=t=in:st=0:d=0.6")
    if last_chapter:
        band.append(f"fade=t=out:st={total - 0.9:.3f}:d=0.9")
    graph.append(f"{''.join(labels)}concat=n={len(labels)}:v=1:a=0," + ",".join(band) + "[v]")
    if ch.voice:
        argv += ["-i", ch.voice.name]
        lead = int(VOICE_LEAD * 1000)
        graph.append(f"[{len(ch.pieces)}:a]adelay={lead}:all=1,apad,atrim=0:{total:.3f}[a]")
    else:
        argv += ["-f", "lavfi", "-t", f"{total:.3f}", "-i", "anullsrc=r=48000:cl=stereo"]
        graph.append(f"[{len(ch.pieces)}:a]atrim=0:{total:.3f}[a]")
    script = work / f"ch{ch.n}.filter"
    script.write_text(";\n".join(graph), encoding="utf-8")
    out = work / f"ch{ch.n}.mp4"
    tools.run([*argv, "-/filter_complex", script.name, "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "medium",
               "-crf", "18", "-pix_fmt", "yuv420p", "-r", str(FPS), "-c:a", "aac", "-b:a", "160k", "-ar", "48000",
               out.name])
    return out


def stamp(t: float) -> str:
    ms = round(t * 1000)
    return f"{ms // 3_600_000:02d}:{ms // 60_000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--raw", type=Path, required=True, help="the recorder's --out folder, with marks.json")
    parser.add_argument("--work", type=Path, required=True, help="a folder for the chapter files")
    parser.add_argument("--voice", type=Path, help="the folder of chN-takeK.m4a files")
    parser.add_argument("--take", action="append", default=[], help="N=K uses take K for chapter N (default 1)")
    parser.add_argument("--metamask", type=Path, help="Hafiz's screen capture of the MetaMask signature")
    parser.add_argument("--metamask-span", default="0,30", help="the seconds of it to use, a,b[;c,d]")
    parser.add_argument("--out", type=Path, default=Path("amanah-demo.mp4"))
    parser.add_argument("--srt", type=Path, default=Path(__file__).with_name("amanah-demo.srt"))
    parser.add_argument("--ffmpeg", default=shutil.which("ffmpeg") or DEFAULT_FFMPEG)
    parser.add_argument("--plan", action="store_true", help="print each chapter's length and stop")
    args = parser.parse_args(argv)
    args.work.mkdir(parents=True, exist_ok=True)
    tools = Tools(args.ffmpeg, args.work)
    chapters = plan(args, tools)
    for ch in chapters:
        held = sum(p.hold for p in ch.pieces)
        print(f"chapter {ch.n}: {ch.length:5.1f} s ({held:4.1f} s held), voice {ch.voice_length:4.1f} s")
    print(f"total {sum(ch.length for ch in chapters):.1f} s")
    if args.plan:
        return 0
    caption_font, tag_font = next(f for f in FONTS if Path(f[0]).exists())
    shutil.copyfile(caption_font, args.work / "caption.ttf")
    shutil.copyfile(tag_font, args.work / "tag.ttf")
    files, srt, offset = [], [], 0.0
    for i, ch in enumerate(chapters):
        out = render(ch, tools, args.work, i == 0, i == len(chapters) - 1)
        files.append(out)
        timed = sorted(((ch.at(clip, t), text) for clip, t, kind, text in ch.lines), key=lambda x: x[0])
        for j, (t, text) in enumerate(timed):
            end = timed[j + 1][0] if j + 1 < len(timed) else ch.length
            srt.append((offset + t, offset + end, text))
        offset += tools.length(out)
        print(f"chapter {ch.n} cut")
    (args.work / "chapters.txt").write_text("".join(f"file '{f.name}'\n" for f in files), encoding="utf-8")
    tools.run(["-f", "concat", "-safe", "0", "-i", "chapters.txt", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
               "-movflags", "+faststart", tools.path(args.out)])
    args.srt.write_text("\n".join(f"{i}\n{stamp(a)} --> {stamp(b)}\n{text}\n" for i, (a, b, text) in enumerate(srt, 1)),
                        encoding="utf-8")
    print(f"{args.out}: {tools.length(args.out):.1f} s; captions in {args.srt}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
