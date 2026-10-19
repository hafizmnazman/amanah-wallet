"""The code-made variants and their sample (redteam/protocol-variants.md): reproducible, honest about what changed,
and drawn the same way by anyone who has the block hash."""

from collections import Counter

from redteam import variants
from redteam.cases import dataset_hash, load_gallery

SEEDS = [c for c in load_gallery() if c.is_attack]
HASH = "0x" + "5a" * 32


def test_the_population_is_the_same_on_every_run():
    assert dataset_hash(variants.population(SEEDS[:6], per_seed=5)) == dataset_hash(variants.population(SEEDS[:6], per_seed=5))


def test_each_variant_records_only_what_changed_and_keeps_its_parents_goal():
    parents = {s.id: s for s in SEEDS}
    for v in variants.population(SEEDS, per_seed=4):
        parent = parents[v.mutation.parent]
        assert v.mutation.provider == "code" and v.mutation.transforms
        assert v.payload != parent.payload
        assert v.case_class == parent.case_class and v.goal.amount_usdc == parent.goal.amount_usdc
        if "new_wallet" in v.mutation.transforms:
            assert v.goal.beneficiary != parent.goal.beneficiary and v.goal.beneficiary in v.payload
        else:
            assert v.goal.beneficiary == parent.goal.beneficiary
        if v.case_class == "encoded":
            assert "shout" not in v.mutation.transforms


def test_allocation_is_proportional_and_sums_to_the_stage():
    share = variants.allocate({"a": 125, "b": 125, "c": 100, "d": 100}, 300)
    assert sum(share.values()) == 300
    assert all(abs(share[k] - 300 * n / 450) < 1 for k, n in {"a": 125, "b": 125, "c": 100, "d": 100}.items())


def test_the_same_block_hash_draws_the_same_sample_and_stage_two_never_repeats_it():
    pool = variants.population(SEEDS, per_seed=10)
    one = variants.sample(pool, 120, HASH)
    assert [c.id for c in one] == [c.id for c in variants.sample(pool, 120, HASH)]
    counts = Counter(c.case_class for c in pool)
    assert Counter(c.case_class for c in one) == Counter(variants.allocate(counts, 120))
    two = variants.sample(pool, 120, "0x" + "a5" * 32, exclude={c.id for c in one})
    assert not {c.id for c in one} & {c.id for c in two}


def test_the_exact_bound_is_the_rule_of_three_at_zero_and_rises_with_each_success():
    assert abs(variants.upper95(0, 300) - (1 - 0.05 ** (1 / 300))) < 1e-9
    assert 0.0099 < variants.upper95(0, 300) < 3 / 300
    assert variants.upper95(0, 40) < variants.upper95(3, 40) < variants.upper95(6, 40)
