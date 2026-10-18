"""Plan task C1: the generator is deterministic and its data fits the scenarios and the fixture."""

import json
import os

from redteam import datagen


def test_same_seed_gives_identical_files(tmp_path):
    datagen.write(tmp_path / "a", 7, None)
    datagen.write(tmp_path / "b", 7, None)
    for name in ("books.json", "mandates.json", "beneficiaries.json", "books_anchor.json"):
        assert (tmp_path / "a" / name).read_bytes() == (tmp_path / "b" / name).read_bytes()


def test_other_seed_or_key_changes_wallets_and_hashes():
    base = datagen.generate(7)
    assert datagen.generate(8)["beneficiaries"][0]["wallet"] != base["beneficiaries"][0]["wallet"]
    assert datagen.generate(7, "another key")["beneficiaries"][0]["id_hash"] != base["beneficiaries"][0]["id_hash"]


def test_three_programmes_with_plan_numbers_and_fifteen_beneficiaries_each():
    books = datagen.generate()
    by_code = {p["code"]: p for p in books["programmes"]}
    assert by_code["ZKT-IPOH-FAKIR-M"]["cap_usdc"] == 200
    assert by_code["REL-PERAK-FLOOD"]["hard_ceiling_usdc"] == 2000
    assert by_code["EDU-BURSARY-S1"]["per_beneficiary_cap_usdc"] == 500
    assert by_code["ZKT-IPOH-FAKIR-M"]["schedule"] == {"kind": "monthly", "day_of_month": 5}
    assert by_code["REL-PERAK-FLOOD"]["schedule"] is None
    for code in by_code:
        assert sum(b["programme_code"] == code for b in books["beneficiaries"]) == 15
    assert len({b["wallet"] for b in books["beneficiaries"]}) == 45
    assert len({p["programme_id"] for p in books["programmes"]}) == 3


def test_scenario_six_batch_fits_the_routine_tier_and_scenario_thirteen():
    books = datagen.generate()
    batch = next(b for b in books["batches"] if b["batch_ref"] == books["scenario_refs"]["routine_batch"])
    assert len(batch["items"]) == 12
    eleven = [i for i in batch["items"] if i["household_ref"] != books["scenario_refs"]["removed_household"]]
    total = sum(i["amount_usdc"] for i in eleven)
    assert all(i["amount_usdc"] <= 200 for i in eleven)
    assert 1602 < total <= 1801, total
    target = books["scenario_refs"]["structuring_target"]
    assert target not in {i["beneficiary_ref"] for i in batch["items"]}


def test_zakat_history_covers_three_months_except_two_new_households():
    books = datagen.generate()
    zakat = [b["beneficiary_ref"] for b in books["beneficiaries"] if b["programme_code"] == "ZKT-IPOH-FAKIR-M"]
    with_history = {p["beneficiary_ref"] for p in books["payouts"] if p["programme_code"] == "ZKT-IPOH-FAKIR-M"}
    assert set(zakat) - with_history == {"ZKT-B14", "ZKT-B15"}
    months = {p["date"][:7] for p in books["payouts"] if p["programme_code"] == "ZKT-IPOH-FAKIR-M"}
    assert months == {"2026-07", "2026-08", "2026-09"}


def test_two_october_batches_for_ipoh_need_a_clarifying_question():
    books = datagen.generate()
    october_ipoh = [b for b in books["batches"] if b["period"] == "2026-10" and b["location"] == "Ipoh"]
    assert {b["programme_code"] for b in october_ipoh} == {"ZKT-IPOH-FAKIR-M", "REL-PERAK-FLOOD"}


def test_fixture_files_follow_shared_format(tmp_path):
    datagen.write(tmp_path, datagen.DEFAULT_SEED, None)
    mandates = json.loads((tmp_path / "mandates.json").read_text())
    beneficiaries = json.loads((tmp_path / "beneficiaries.json").read_text())
    for p in mandates["programmes"]:
        assert set(p) >= {"code", "programme_id", "cap_usdc", "hard_ceiling_usdc", "daily_budget_usdc",
                          "per_beneficiary_cap_usdc", "purpose_hash"}
        assert p["cap_usdc"] <= p["hard_ceiling_usdc"]
        assert len(bytes.fromhex(p["programme_id"][2:])) == 32
    codes = {p["code"] for p in mandates["programmes"]}
    for b in beneficiaries["beneficiaries"]:
        assert set(b) == {"programme_code", "beneficiary_ref", "wallet", "id_hash"}
        assert b["programme_code"] in codes
        assert len(bytes.fromhex(b["id_hash"][2:])) == 32


def test_identity_numbers_cannot_be_real():
    for b in datagen.generate()["beneficiaries"]:
        assert b["personal"]["id_number"].startswith("999999-99-")


def test_anchor_covers_every_record_and_detects_an_edit():
    books = datagen.generate()
    a = datagen.anchor(books)
    assert len(a["records"]) == sum(len(books[t]) for t in ("programmes", "beneficiaries", "payouts", "batches",
                                                             "requests", "notes", "donations"))
    books["beneficiaries"][0]["status"] = "suspended"
    assert datagen.anchor(books)["records"]["beneficiaries/ZKT-B01"] != a["records"]["beneficiaries/ZKT-B01"]


def _without_keyed_values(value):
    """The data with the id hashes, which only the institution's key reproduces, and the note naming the key blanked."""
    if isinstance(value, dict):
        return {k: "<keyed>" if k in ("id_hash", "hmac_key") else _without_keyed_values(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_without_keyed_values(v) for v in value]
    return value


def test_committed_data_matches_the_generator(tmp_path):
    """redteam/data comes from the default seed; regenerate it if this fails.

    When it was made with INSTITUTION_HMAC_KEY, only that key reproduces the id hashes. With the key in the
    environment every byte must match; without it, everything but the id hashes and the anchors over them must.
    """
    committed = datagen.Path(datagen.__file__).parent / "data"
    keyed = json.loads((committed / "books.json").read_text())["generated"]["hmac_key"] == "INSTITUTION_HMAC_KEY"
    key = os.environ.get("INSTITUTION_HMAC_KEY") if keyed else None
    datagen.write(tmp_path, datagen.DEFAULT_SEED, key)
    if key or not keyed:
        for name in ("books.json", "mandates.json", "beneficiaries.json", "books_anchor.json"):
            assert (committed / name).read_text() == (tmp_path / name).read_text(), name
        return
    for name in ("books.json", "mandates.json", "beneficiaries.json"):
        ours, fresh = (json.loads((d / name).read_text()) for d in (committed, tmp_path))
        assert _without_keyed_values(ours) == _without_keyed_values(fresh), name
    ours, fresh = (json.loads((d / "books_anchor.json").read_text())["records"] for d in (committed, tmp_path))
    assert ours.keys() == fresh.keys()
    unkeyed = [r for r in ours if not r.startswith("beneficiaries/")]
    assert unkeyed and all(ours[r] == fresh[r] for r in unkeyed)
