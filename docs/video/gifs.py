"""The README's four moments as GIFs, cut from a recorded take by its marks, with the waits left out.

    python docs/video/gifs.py --raw /root/amanah-video/take4 --work /mnt/c/.../gif-work --out .github/readme/gifs

Each GIF is a few spans of one clip around its marks (docs/video/record.cjs), joined, at 10 frames a second and
800 pixels wide. The clips are built from the screencast frames as the cut builds them (docs/video/cut.py).
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cut  # noqa: E402

# name: (chapter, [(mark, seconds before, seconds after), ...])
MOMENTS = {
    "officer-batch": ("ch3", [("plan", 0.3, 2.2), ("confirm-click", 0.9, 0.6), ("paid", 0.5, 2.8)]),
    "attack-refused": ("ch4", [("chairman-ask", 0.6, 1.2), ("chairman", 1.0, 3.0)]),
    "checker-down": ("ch5", [("confirmed", 0.6, 0.6), ("queued", 1.0, 2.6), ("paid", 0.6, 2.6)]),
    "trustee-signs": ("ch6", [("trustee", 0.3, 5.2), ("signed", 1.0, 2.6)]),
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--ffmpeg", default=shutil.which("ffmpeg") or cut.DEFAULT_FFMPEG)
    args = parser.parse_args()
    args.work.mkdir(parents=True, exist_ok=True)
    args.out.mkdir(parents=True, exist_ok=True)
    tools = cut.Tools(args.ffmpeg, args.work)
    marks = json.loads((args.raw / "marks.json").read_text(encoding="utf-8"))
    for name, (chapter, spans) in MOMENTS.items():
        entry = marks[chapter]
        src, shift = cut.assemble(args.raw / entry["dir"], entry, tools)
        at = {m["label"]: m["t"] + shift for m in entry["marks"]}
        argv, graph = [], []
        for i, (label, before, after) in enumerate(spans):
            argv += ["-ss", f"{max(0.0, at[label] - before):.3f}", "-t", f"{before + after:.3f}", "-i", tools.path(src)]
            graph.append(f"[{i}:v]setpts=PTS-STARTPTS,fps=10,scale=800:-1:flags=lanczos[s{i}]")
        joined = "".join(f"[s{i}]" for i in range(len(spans)))
        graph.append(f"{joined}concat=n={len(spans)}:v=1:a=0,split[a][b]")
        graph.append("[a]palettegen=stats_mode=diff:max_colors=128[p]")
        graph.append("[b][p]paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle")
        made = args.work / f"{name}.gif"   # on the Windows drive, where Windows' ffmpeg writes
        tools.run([*argv, "-filter_complex", ";".join(graph), "-loop", "0", made.name])
        out = shutil.copyfile(made, args.out / made.name)
        print(f"{made.name}: {Path(out).stat().st_size / 1e6:.1f} MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
