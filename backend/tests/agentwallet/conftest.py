"""A local chain for the tests that need one: anvil on a free port with lane A's fixture deployed."""

from __future__ import annotations

import pytest

from app.agentwallet import devchain
from app.agentwallet.books import Books


@pytest.fixture(scope="session")
def local_chain():
    if not devchain.available():
        pytest.skip("anvil and forge are needed for chain tests")
    with devchain.anvil_fixture() as chain:
        chain.books = Books.load()
        yield chain


@pytest.fixture(autouse=True)
def _isolated_chain(request):
    """Every test that uses the chain starts from the fixture's state: an EVM snapshot is taken before it
    and restored after, so no test depends on what another test spent, paid or raised."""
    if "local_chain" not in request.fixturenames:
        yield
        return
    chain = request.getfixturevalue("local_chain")
    snapshot = chain.snapshot()
    yield
    chain.revert(snapshot)
