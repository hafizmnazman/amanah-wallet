"""Decision E-38: after the one history rewrite of decision E-18, point every commit cited in a tracked file at its new hash.

    python scripts/rehash_refs.py --map .git/filter-repo/commit-map --dry-run    # lists what would change
    python scripts/rehash_refs.py --map .git/filter-repo/commit-map              # rewrites the files

git filter-repo rewrites the hashes in commit messages but not in file contents, so a README that cites the red
team's protocol commit would point at a commit that no longer exists. The commit map filter-repo writes lists each
old commit beside its new one. A token of 7 to 12 hex digits that is not part of a longer hex string, does not
follow 0x, and is the prefix of exactly one old commit is replaced by the new commit's prefix of the same length.
Every other token is left alone. Records keep the hash they were written with: data files (JSON, JSONL and CSV,
such as each red-team manifest and Foundry's broadcast records) are not touched, and the map is committed as
docs/commit-map.txt so that any hash in them can be looked up. Run it after the rewrite and before the seal, since
the seal hashes the files.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TOKEN = re.compile(r"(?<![0-9a-fA-Fx])([0-9a-f]{7,12})(?![0-9a-fA-F])")
DELETED = "0" * 40
RECORDS = (".json", ".jsonl", ".csv")
SAVED_MAP = REPO / "docs" / "commit-map.txt"


def load_map(path: Path) -> dict[str, str]:
    """old full hash -> new full hash, from filter-repo's commit-map (a header line, then "old new" per commit)."""
    commits = {}
    for line in path.read_text().splitlines():
        parts = line.split()
        if len(parts) == 2 and len(parts[0]) == 40 and parts[0] != "old":
            commits[parts[0]] = parts[1]
    return commits


def rewrite(text: str, commits: dict[str, str]) -> tuple[str, list[tuple[str, str]]]:
    """Replace each cited commit with its new hash at the same length; return the text and what changed."""
    changes = []

    def swap(match: re.Match) -> str:
        token = match.group(1)
        found = [old for old in commits if old.startswith(token)]
        if len(found) != 1 or commits[found[0]] in (DELETED, found[0]):
            return token
        new = commits[found[0]][: len(token)]
        changes.append((token, new))
        return new

    return TOKEN.sub(swap, text), changes


def is_reference_file(relative: str) -> bool:
    """Prose and code cite commits; data files record them and keep what they recorded."""
    return not relative.endswith(RECORDS) and not relative.startswith("contracts/broadcast/")


def tracked_text_files() -> list[Path]:
    names = subprocess.run(["git", "ls-files", "-z"], cwd=REPO, capture_output=True, check=True).stdout.split(b"\0")
    files = []
    for name in filter(None, names):
        if not is_reference_file(name.decode()):
            continue
        path = REPO / name.decode()
        if path.is_file() and not path.is_symlink() and b"\0" not in path.read_bytes()[:8192]:
            files.append(path)
    return files


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python scripts/rehash_refs.py", description=__doc__.split("\n\n")[0])
    parser.add_argument("--map", type=Path, required=True, help="the commit-map that git filter-repo wrote")
    parser.add_argument("--dry-run", action="store_true", help="list the changes and write nothing")
    args = parser.parse_args(argv)

    commits = load_map(args.map)
    if not commits:
        raise SystemExit(f"{args.map} lists no commits")
    total = 0
    for path in tracked_text_files():
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        new_text, changes = rewrite(text, commits)
        if not changes:
            continue
        total += len(changes)
        pairs = sorted(set(changes))
        print(f"{path.relative_to(REPO)}: " + ", ".join(f"{old} -> {new}" for old, new in pairs))
        if not args.dry_run:
            path.write_text(new_text, encoding="utf-8")
    if not args.dry_run:
        lines = [f"{old} {new}" for old, new in sorted(commits.items()) if new not in (old, DELETED)]
        SAVED_MAP.write_text("# Commits before and after the one history rewrite of decision E-18: old new.\n"
                             "# Records such as the red-team manifests keep the old hash; look it up here.\n"
                             + "\n".join(lines) + "\n")
        print(f"saved the map of {len(lines)} commits to {SAVED_MAP.relative_to(REPO)}")
    print(f"{total} reference{'s' if total != 1 else ''} {'would change' if args.dry_run else 'changed'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
