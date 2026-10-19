# Attempt 1 on Base Sepolia, 19 October 2026

The first Base Sepolia run, on vault `0x2bE8E713B1365E1798267495C21D2b36D78F477D` (`deployment.json`), stopped after scenario 5. Every transaction it sent succeeded (`transactions.csv`): the trustees registered the five machine signers, set the three mandates and added the 45 beneficiaries, and the donor deposited 5,000 tUSDC.

Its checks failed anyway, for two reasons in the chain client that only a public provider shows (decision B-24):
- **Stale reads.** Alchemy spreads requests over several nodes. Reads straight after the writes reached nodes that had not seen them, so the signers read as inactive, the mandates as unset and the deposit as missing.
- **A refused log range.** Alchemy's free plan answers an `eth_getLogs` range over ten blocks with HTTP 400, whose body alone says why. The sentinel's history reader did not recognise it and gave up, so the demo stopped before the first payout.

Both are fixed. The demo then ran on a fresh vault, so that the evidence one folder up holds a single run. This folder is kept as the record of the first attempt.
