"""The last check before the submission email (plan tasks E4 and E6, and plan section 12).

    python scripts/presubmit.py                    # every offline check
    python scripts/presubmit.py --links            # also open every external link in the README
    python scripts/presubmit.py --verify           # also run verify.py on every executed payout (needs RPC_URL)
    python scripts/presubmit.py --readme docs/submission-readme.md    # before it is merged into README.md

Each check prints pass, FAIL or todo. A todo is a step no script can check, such as making the repository
public; it never fails the run. The exit code is 1 when any check fails. Relative links resolve from the
repository root, where the README is published, whichever file --readme names.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))

DASHES = re.compile(f"[{chr(0x2013)}{chr(0x2014)}]")  # en and em dash, written as code points
FILL = "[[fill"
# The plan's own E4 command holds the two characters it searches for.
DASH_EXEMPT = {"IMPLEMENTATION_PLAN.md"}
TEXT_SUFFIXES = {".md", ".py", ".ts", ".tsx", ".js", ".mjs", ".cjs", ".sol", ".json", ".jsonl", ".yaml", ".yml",
                 ".sh", ".txt", ".html", ".css", ".toml", ".ini", ".cfg", ".csv", ".example", ".gitignore"}
E3_DOCS = ["docs/technical-documentation.md", "docs/security-self-assessment.md", "redteam/protocol.md"]
EVIDENCE = ["evidence/transactions.csv", "evidence/action-log.jsonl", "evidence/demo-summary.json",
            "evidence/amanah-evidence-pack.zip", "contracts/deployments/84532.json",
            "contracts/broadcast/Deploy.s.sol/84532/run-latest.json"]
RESULTS = ["redteam/results/final/report.md", "redteam/results/final/summary.json",
           "redteam/results/final/manifest.json"]
ARMS = ("S1", "S2", "S3", "S4", "S5")
DECK_SLIDES = 11
SCENARIOS = [str(n) for n in range(1, 17)]
MANUAL = [
    "The repository is public, and every link opens from a logged-out browser (E6).",
    "The README names no feature that did not ship (E4).",
    "The video is under 5 minutes, in English with captions, and opens with the split-screen attack (E5).",
    "The deck is exported as PDF and PPTX, and the video and deck links in the README open (E5).",
    "The lanes are merged into main in the order A, B, C, D, E, and main holds what was tested.",
    "The files are attached or on OneDrive, and the email is sent before Tuesday 20:00 (E6).",
]


@dataclass
class Check:
    name: str
    status: str  # "pass", "FAIL" or "todo"
    detail: str = ""

    def line(self) -> str:
        return f"{self.status:<5} {self.name}" + (f": {self.detail}" if self.detail else "")


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, check=True).stdout


def tracked() -> list[str]:
    return [p for p in git("ls-files", "-z").split("\0") if p]


def is_tracked(path: str) -> bool:
    return subprocess.run(["git", "ls-files", "--error-unmatch", path], cwd=REPO, capture_output=True).returncode == 0


# Markers and dashes


def fill_markers(paths: list[str]) -> Check:
    found = {}
    for path in paths:
        file = REPO / path
        if file.exists():
            count = file.read_text().count(FILL)
            if count:
                found[path] = count
    if not found:
        return Check("no [[fill markers", "pass", ", ".join(paths))
    return Check("no [[fill markers", "FAIL", ", ".join(f"{p} has {n}" for p, n in found.items()))


def dash_lines(text: str) -> int:
    return sum(1 for line in text.splitlines() if DASHES.search(line))


def dashes(files: list[str]) -> Check:
    found = {}
    for path in files:
        file = REPO / path
        if path in DASH_EXEMPT or not (file.suffix in TEXT_SUFFIXES or file.name in TEXT_SUFFIXES) or not file.is_file():
            continue
        try:
            count = dash_lines(file.read_text())
        except UnicodeDecodeError:
            continue
        if count:
            found[path] = count
    if not found:
        return Check("no em or en dashes in tracked text files", "pass")
    shown = ", ".join(f"{p} ({n} lines)" for p, n in sorted(found.items())[:8])
    return Check("no em or en dashes in tracked text files", "FAIL", shown + (" and more" if len(found) > 8 else ""))


# Links


def slug(heading: str) -> str:
    """GitHub's anchor for a heading: rendered text, lower case, punctuation dropped, spaces to hyphens."""
    text = re.sub(r"`([^`]*)`", r"\1", heading)
    text = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("*", "")
    text = re.sub(r"(?<!\w)_(.+?)_(?!\w)", r"\1", text)
    text = re.sub(r"[^\w\- ]", "", text.strip().lower())
    return text.replace(" ", "-")


def anchors(markdown: str) -> set[str]:
    found: set[str] = set()
    seen: dict[str, int] = {}
    fenced = False
    for line in markdown.splitlines():
        if line.lstrip().startswith(("```", "~~~")):
            fenced = not fenced
            continue
        if fenced:
            continue
        found.update(re.findall(r"""<a\s+(?:id|name)=["']([^"']+)["']""", line))
        heading = re.match(r"^#{1,6}\s+(.*?)\s*#*\s*$", line)
        if heading:
            base = slug(heading.group(1))
            n = seen.get(base, 0)
            seen[base] = n + 1
            found.add(base if n == 0 else f"{base}-{n}")
    return found


def links(markdown: str) -> list[str]:
    """Every link target in the file, outside code: inline links, images and reference definitions."""
    out = []
    fenced = False
    for line in markdown.splitlines():
        if line.lstrip().startswith(("```", "~~~")):
            fenced = not fenced
            continue
        if fenced:
            continue
        line = re.sub(r"`[^`]*`", "", line)
        out += re.findall(r"\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)", line)
        ref = re.match(r"^\s*\[[^\]]+\]:\s*(\S+)", line)
        if ref:
            out.append(ref.group(1))
    return out


def local_links(readme: str) -> Check:
    path = REPO / readme
    if not path.exists():
        return Check(f"{readme} links and anchors", "FAIL", "the file does not exist")
    text = path.read_text()
    own = anchors(text)
    broken = []
    for target in links(text):
        if re.match(r"^[a-z]+:", target):  # http, https, mailto
            continue
        file, _, anchor = target.partition("#")
        if file:
            dest = (REPO / file).resolve()
            if not dest.exists():
                broken.append(target)
                continue
            if anchor and dest.suffix == ".md" and anchor not in anchors(dest.read_text()):
                broken.append(target)
        elif anchor and anchor not in own:
            broken.append(target)
    if not broken:
        return Check(f"{readme} links and anchors", "pass")
    return Check(f"{readme} links and anchors", "FAIL", f"{len(broken)} broken: " + ", ".join(broken[:8]))


def external_links(readme: str, timeout: float = 10.0) -> Check:
    text = (REPO / readme).read_text()
    urls = sorted({t for t in links(text) if t.startswith(("http://", "https://"))})
    bad = []
    for url in urls:
        request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (amanah presubmit)"})
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                if response.status >= 400:
                    bad.append(f"{url} ({response.status})")
        except urllib.error.HTTPError as exc:
            bad.append(f"{url} ({exc.code})")
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            bad.append(f"{url} ({type(exc).__name__})")
    if not bad:
        return Check(f"{len(urls)} external links in {readme} open", "pass")
    return Check(f"external links in {readme} open", "FAIL", "; ".join(bad[:8]))


# Files a judge needs


def licence() -> Check:
    names = [p.name for p in REPO.iterdir() if p.name.upper().startswith(("LICENSE", "LICENCE", "COPYING"))]
    if names and all(is_tracked(n) for n in names):
        return Check("a licence file at the root", "pass", ", ".join(names))
    return Check("a licence file at the root", "FAIL", "none committed; the licence is still Hafiz's choice")


def committed(name: str, paths: list[str]) -> Check:
    missing = [p for p in paths if not is_tracked(p)]
    if not missing:
        return Check(name, "pass")
    return Check(name, "FAIL", "not committed: " + ", ".join(missing))


def demo_summary(path: Path) -> Check:
    name = "the Base Sepolia demo passed every scenario"
    if not path.exists():
        return Check(name, "FAIL", f"{path.relative_to(REPO)} does not exist")
    data = json.loads(path.read_text())
    problems = []
    if data.get("network") != "base-sepolia":
        problems.append(f"network is {data.get('network')}")
    outcomes = {o["scenario"]: o for o in data.get("outcomes", [])}
    missing = [s for s in SCENARIOS if s not in outcomes]
    failed = [s for s, o in outcomes.items() if not o["ok"]]
    # A live planner can refuse before any signer, so nothing is sent (decision E-21); run_demo.py says so in "got"
    stopped = [s for s in SCENARIOS if s in outcomes and not outcomes[s]["tx_hashes"] and outcomes[s]["ok"]
               and any(p in outcomes[s].get("got", "") for p in ("the planner refused", "the planner made no payout"))]
    without = [s for s in SCENARIOS if s in outcomes and not outcomes[s]["tx_hashes"] and s not in stopped]
    if missing:
        problems.append("no outcome for scenarios " + ", ".join(missing))
    if failed:
        problems.append("failed: " + ", ".join(failed))
    if without:
        problems.append("no transaction for scenarios " + ", ".join(without))
    if not data.get("log_verified"):
        problems.append("the action log did not verify")
    if not data.get("head_anchor_tx"):
        problems.append("the log head was not anchored")
    if problems:
        return Check(name, "FAIL", "; ".join(problems))
    note = f"; scenarios {', '.join(stopped)} stopped at the live planner, with nothing to send" if stopped else ""
    return Check(name, "pass", f"{len(outcomes)} checks, log head anchored in {data['head_anchor_tx'][:12]}...{note}")


def action_log(path: Path) -> Check:
    from app.agentwallet.evidence import ActionLog

    if not path.exists():
        return Check("the action log's hash chain verifies", "FAIL", f"{path.relative_to(REPO)} does not exist")
    ok, problem = ActionLog.verify(path)
    return Check("the action log's hash chain verifies", "pass" if ok else "FAIL", "" if ok else str(problem))


def deployment_matches(record: Path, summary: Path) -> Check:
    name = "the deployment record names the demo's vault"
    if not record.exists() or not summary.exists():
        return Check(name, "FAIL", "the deployment record or the demo summary is missing")
    vault = json.loads(record.read_text()).get("vault", "")
    used = json.loads(summary.read_text()).get("vault", "")
    if vault and vault.lower() == used.lower():
        return Check(name, "pass", vault)
    return Check(name, "FAIL", f"deployments/84532.json has {vault or 'no vault'}, the demo used {used or 'none'}")


def red_team(results: Path) -> Check:
    name = "the red-team final run covers S1 to S5"
    summary = results / "summary.json"
    if not summary.exists():
        return Check(name, "FAIL", f"{summary.relative_to(REPO)} does not exist")
    text = summary.read_text()
    missing = [arm for arm in ARMS if f'"{arm}"' not in text]
    if missing:
        return Check(name, "FAIL", "no result for " + ", ".join(missing))
    return Check(name, "pass")


def protocol_first(protocol: str, report: str) -> Check:
    """Plan task C6: the protocol is committed before the full run, so its last change precedes the report."""
    name = "the protocol was committed before the final report"
    last_protocol = git("log", "-1", "--format=%H", "--", protocol).strip()
    first_report = git("log", "--diff-filter=A", "--format=%H", "--", report).strip().splitlines()
    if not last_protocol or not first_report:
        return Check(name, "FAIL", "the protocol or the final report is not committed")
    report_commit = first_report[-1]
    before = subprocess.run(["git", "merge-base", "--is-ancestor", last_protocol, report_commit], cwd=REPO).returncode == 0
    if before and last_protocol != report_commit:
        return Check(name, "pass", f"protocol {last_protocol[:10]}, report {report_commit[:10]}")
    return Check(name, "FAIL", f"protocol {last_protocol[:10]} was changed after the report {report_commit[:10]}")


def slide_count(pptx: Path) -> int:
    with zipfile.ZipFile(pptx) as z:
        return sum(1 for n in z.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", n))


def deck_fills(pptx: Path) -> int:
    """[[fill markers on the slides and in the speaker notes."""
    with zipfile.ZipFile(pptx) as z:
        return sum(z.read(n).decode().count(FILL) for n in z.namelist()
                   if re.fullmatch(r"ppt/(slides|notesSlides)/\w+\.xml", n))


def deck(folder: Path) -> Check:
    name = f"the deck has {DECK_SLIDES} slides, as PPTX and PDF"
    decks = sorted(folder.glob("*.pptx")) if folder.exists() else []
    if not decks:
        return Check(name, "FAIL", f"no .pptx in {folder.relative_to(REPO)}")
    counts = {p.name: slide_count(p) for p in decks}
    wrong = {n: c for n, c in counts.items() if c != DECK_SLIDES}
    pdfs = [p for p in decks if not p.with_suffix(".pdf").exists()]
    marked = {p.name: deck_fills(p) for p in decks}
    problems = ([f"{n} has {c} slides" for n, c in wrong.items()] + [f"no PDF beside {p.name}" for p in pdfs]
                + [f"{n} has {c} [[fill markers; rebuild it with scripts/build_deck.py" for n, c in marked.items() if c])
    if problems:
        return Check(name, "FAIL", "; ".join(problems))
    return Check(name, "pass", ", ".join(counts))


# Secrets and git


def secrets() -> list[Check]:
    checks = []
    leaked = [p for p in tracked() if Path(p).name == ".env" or (Path(p).name.startswith(".env.") and not p.endswith(".example"))]
    checks.append(Check("no .env file is committed", "FAIL" if leaked else "pass", ", ".join(leaked)))
    gitleaks = shutil.which("gitleaks") or next((p for p in (Path.home() / "go/bin/gitleaks",) if p.exists()), None)
    if gitleaks is None:
        checks.append(Check("gitleaks detect", "todo", "gitleaks is not installed here; run it before pushing"))
    else:
        run = subprocess.run([str(gitleaks), "detect", "--no-banner", "--redact"], cwd=REPO, capture_output=True, text=True)
        checks.append(Check("gitleaks detect", "pass" if run.returncode == 0 else "FAIL",
                            "" if run.returncode == 0 else (run.stdout + run.stderr).strip().splitlines()[-1]))
    return checks


def git_state() -> Check:
    dirty = git("status", "--porcelain").strip().splitlines()
    branch = git("rev-parse", "--abbrev-ref", "HEAD").strip()
    if dirty:
        return Check("everything is committed", "FAIL", f"{len(dirty)} uncommitted paths on {branch}")
    upstream = subprocess.run(["git", "rev-parse", "@{u}"], cwd=REPO, capture_output=True, text=True)
    if upstream.returncode != 0:
        return Check("everything is committed and pushed", "FAIL", f"{branch} has no upstream")
    if upstream.stdout.strip() != git("rev-parse", "HEAD").strip():
        return Check("everything is committed and pushed", "FAIL", f"{branch} differs from its upstream")
    return Check("everything is committed and pushed", "pass", branch)


def verify_payouts(csv_path: Path) -> Check:
    run = subprocess.run([sys.executable, str(REPO / "scripts" / "verify.py"), "--csv", str(csv_path)], cwd=REPO,
                         capture_output=True, text=True)
    last = (run.stdout + run.stderr).strip().splitlines()[-1:] or ["no output"]
    return Check("verify.py passes on every executed payout", "pass" if run.returncode == 0 else "FAIL", last[0])


def checks(readme: str, *, with_links: bool = False, with_verify: bool = False) -> list[Check]:
    files = tracked()
    evidence = REPO / "evidence"
    out = [
        fill_markers([readme, *E3_DOCS]),
        dashes(files),
        local_links(readme),
        licence(),
        committed("the Base Sepolia evidence is committed", EVIDENCE),
        demo_summary(evidence / "demo-summary.json"),
        action_log(evidence / "action-log.jsonl"),
        deployment_matches(REPO / "contracts" / "deployments" / "84532.json", evidence / "demo-summary.json"),
        committed("the red-team final run is committed", RESULTS),
        red_team(REPO / "redteam" / "results" / "final"),
        protocol_first("redteam/protocol.md", "redteam/results/final/report.md"),
        deck(REPO / "docs" / "deck"),
        *secrets(),
        git_state(),
    ]
    if with_links:
        out.append(external_links(readme))
    if with_verify:
        out.append(verify_payouts(evidence / "transactions.csv"))
    return out + [Check(item, "todo") for item in MANUAL]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python scripts/presubmit.py", description=__doc__.split("\n\n")[0])
    parser.add_argument("--readme", default="README.md", help="the README to check, relative to the repository")
    parser.add_argument("--links", action="store_true", help="open every external link in the README")
    parser.add_argument("--verify", action="store_true", help="run verify.py on every executed payout")
    args = parser.parse_args(argv)
    results = checks(args.readme, with_links=args.links, with_verify=args.verify)
    for c in results:
        print(c.line())
    failed = sum(c.status == "FAIL" for c in results)
    automated = sum(c.status != "todo" for c in results)
    print(f"{automated - failed} of {automated} checks pass; {len(results) - automated} steps to do by hand")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
