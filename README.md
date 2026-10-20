# QuantSlate NFL Model - Public Ledger

An append-only record of an NFL spread model's picks, published before kickoff.

**Informational only. Not betting advice. No profit is claimed or implied.**
In our walk-forward backtest the model did not beat the betting market.
This repository exists so anyone can watch its real record.

- Site: https://eflog.github.io/quantslate-public-ledger/
- ledger/picks.csv: every pick, in timestamped snapshots (never edited, only appended)
- ledger/hashes.csv: SHA-256 hash of each snapshot, chained to the previous one
- ledger/results.csv: graded results (rebuilt automatically from the files above)
- verify_ledger.py: checks that nothing has been changed since it was hashed

To verify: clone this repository and run `python verify_ledger.py`.
Each snapshot's hash is also posted to a public Discord channel, whose message
timestamps cannot be edited.
