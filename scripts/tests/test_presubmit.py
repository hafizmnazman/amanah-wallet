"""The pre-submission gate's own checks, on small files made here."""

import json
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import presubmit  # noqa: E402


def test_slugs_match_the_readme_anchors():
    assert presubmit.slug("7.5 Red-team method and results") == "75-red-team-method-and-results"
    assert presubmit.slug("4. What is new: five contributions") == "4-what-is-new-five-contributions"
    assert presubmit.slug("3.1 `shared/eip712.json`") == "31-sharedeip712json"
    assert presubmit.slug("The **bold** and _quiet_ parts") == "the-bold-and-quiet-parts"
    assert presubmit.slug("joint_failure_planner_auditor") == "joint_failure_planner_auditor"


def test_anchors_skip_code_and_number_repeats():
    text = "# Intro\n```\n# not a heading\n```\n## Notes\n## Notes\n<a id=\"proof\"></a>\n"
    assert presubmit.anchors(text) == {"intro", "notes", "notes-1", "proof"}


def test_links_skip_code_spans_and_fences():
    text = "See [a](docs/a.md#x) and `[b](nowhere.md)`.\n```\n[c](fenced.md)\n```\n[ref]: https://example.org\n"
    assert presubmit.links(text) == ["docs/a.md#x", "https://example.org"]


def test_a_broken_anchor_and_a_missing_file_fail(monkeypatch, tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "a.md").write_text("# Real heading\n")
    (tmp_path / "README.md").write_text("[ok](#top)\n# Top\n[ok](docs/a.md#real-heading)\n[bad](#nowhere)\n"
                                        "[bad](docs/a.md#gone)\n[bad](docs/missing.md)\n[web](https://example.org)\n")
    monkeypatch.setattr(presubmit, "REPO", tmp_path)
    c = presubmit.local_links("README.md")
    assert c.status == "FAIL" and c.detail == "3 broken: #nowhere, docs/a.md#gone, docs/missing.md"


def test_dash_lines_count_both_dashes():
    em, en = chr(0x2014), chr(0x2013)
    assert presubmit.dash_lines(f"plain\nem {em} dash\nen {en} dash\nhyphen - only\n") == 2


def test_fill_markers_are_counted_per_file(monkeypatch, tmp_path):
    (tmp_path / "README.md").write_text("[[fill: a]] and [[fill: b]]\n")
    (tmp_path / "done.md").write_text("nothing left\n")
    monkeypatch.setattr(presubmit, "REPO", tmp_path)
    assert presubmit.fill_markers(["done.md"]).status == "pass"
    c = presubmit.fill_markers(["README.md", "done.md", "absent.md"])
    assert c.status == "FAIL" and c.detail == "README.md has 2"


def test_the_deck_needs_eleven_slides_and_a_pdf(monkeypatch, tmp_path):
    folder = tmp_path / "docs" / "deck"
    folder.mkdir(parents=True)
    monkeypatch.setattr(presubmit, "REPO", tmp_path)

    def pptx(slides: int) -> None:
        with zipfile.ZipFile(folder / "deck.pptx", "w") as z:
            for n in range(1, slides + 1):
                z.writestr(f"ppt/slides/slide{n}.xml", "<p:sld/>")
            z.writestr("ppt/slides/_rels/slide1.xml.rels", "<Relationships/>")

    pptx(10)
    assert presubmit.deck(folder).detail == "deck.pptx has 10 slides; no PDF beside deck.pptx"
    pptx(11)
    (folder / "deck.pdf").write_bytes(b"%PDF-1.7")
    assert presubmit.deck(folder).status == "pass"
    with zipfile.ZipFile(folder / "deck.pptx", "a") as z:
        z.writestr("ppt/notesSlides/notesSlide1.xml", "<a:t>[[fill: S1 %]] of attacks</a:t>")
    assert presubmit.deck(folder).detail == "deck.pptx has 1 [[fill markers; rebuild it with scripts/build_deck.py"


def test_the_demo_summary_must_be_base_sepolia_and_complete(monkeypatch, tmp_path):
    monkeypatch.setattr(presubmit, "REPO", tmp_path)
    path = tmp_path / "demo-summary.json"
    outcomes = [{"scenario": s, "ok": True, "tx_hashes": ["0x" + "ab" * 32]} for s in presubmit.SCENARIOS]
    good = {"network": "base-sepolia", "log_verified": True, "head_anchor_tx": "0x" + "cd" * 32,
            "outcomes": outcomes + [{"scenario": "E1", "ok": True, "tx_hashes": []}]}
    path.write_text(json.dumps(good))
    assert presubmit.demo_summary(path).status == "pass"
    outcomes[6] = {"scenario": "7", "ok": False, "tx_hashes": ["0x" + "ef" * 32]}
    path.write_text(json.dumps({**good, "network": "anvil", "outcomes": outcomes[:15]}))
    c = presubmit.demo_summary(path)
    assert c.status == "FAIL"
    assert c.detail == "network is anvil; no outcome for scenarios 16; failed: 7"


def test_a_scenario_the_live_planner_stopped_needs_no_transaction(monkeypatch, tmp_path):
    # decision E-21: with a live planner, scenarios 8 and 9 can end at the planner, before any signer
    monkeypatch.setattr(presubmit, "REPO", tmp_path)
    path = tmp_path / "demo-summary.json"
    outcomes = [{"scenario": s, "ok": True, "got": "paid", "tx_hashes": ["0x" + "ab" * 32]} for s in presubmit.SCENARIOS]
    outcomes[7] = {"scenario": "8", "ok": True, "got": "the planner refused it", "tx_hashes": []}
    outcomes[8] = {"scenario": "9", "ok": True, "got": "flag True, the planner made no payout", "tx_hashes": []}
    good = {"network": "base-sepolia", "log_verified": True, "head_anchor_tx": "0x" + "cd" * 32, "outcomes": outcomes}
    path.write_text(json.dumps(good))
    c = presubmit.demo_summary(path)
    assert c.status == "pass" and "scenarios 8, 9 stopped at the live planner" in c.detail
    outcomes[9] = {"scenario": "10", "ok": True, "got": "reverted NotAllowlisted", "tx_hashes": []}
    path.write_text(json.dumps(good))
    assert presubmit.demo_summary(path).detail == "no transaction for scenarios 10"
