"""After the history rewrite, cited commits point at their new hashes, and nothing else changes."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import rehash_refs  # noqa: E402

OLD = "ffa0490" + "1" * 33
NEW = "1234abc" + "2" * 33
OTHER = "ffa0491" + "3" * 33


def test_a_cited_commit_takes_its_new_hash_at_the_same_length(tmp_path):
    commit_map = tmp_path / "commit-map"
    commit_map.write_text(f"old                                      new\n{OLD} {NEW}\n{OTHER} {'4' * 40}\n")
    commits = rehash_refs.load_map(commit_map)
    assert commits == {OLD: NEW, OTHER: "4" * 40}
    text, changes = rehash_refs.rewrite("protocol `ffa0490`, committed before the run (ffa04901).", commits)
    assert text == "protocol `1234abc`, committed before the run (1234abc2)."
    assert changes == [("ffa0490", "1234abc"), ("ffa04901", "1234abc2")]


def test_hashes_that_are_not_commits_are_left_alone():
    commits = {OLD: NEW, OTHER: "4" * 40}
    text = ("tx 0xffa04901 and sha256 ffa0490ffa0490ffa0490ffa0490ffa0490ffa0490ffa0490ffa0490ffa04901234, "
            "the prefix ffa049 is too short, and ffa049 alone matches two commits")
    assert rehash_refs.rewrite(text, commits) == (text, [])
    assert rehash_refs.rewrite("ffa049f", commits) == ("ffa049f", [])


def test_records_keep_the_hash_they_were_written_with():
    assert rehash_refs.is_reference_file("README.md") and rehash_refs.is_reference_file("redteam/zh.py")
    assert rehash_refs.is_reference_file("redteam/results/final/report.md")
    for record in ("redteam/results/final/manifest.json", "redteam/results/final/results.jsonl",
                   "evidence/transactions.csv", "contracts/broadcast/Deploy.s.sol/84532/run-latest.json"):
        assert not rehash_refs.is_reference_file(record)


def test_a_commit_the_rewrite_dropped_keeps_its_old_hash():
    commits = {OLD: "0" * 40}
    assert rehash_refs.rewrite("see ffa0490", commits) == ("see ffa0490", [])
