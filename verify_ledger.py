"""
verify_ledger.py  --  check that the public ledger has not been altered.

Anyone can run this against the public repository. It needs only Python 3 (no
third-party packages):

    git clone https://github.com/<owner>/<repo>
    cd <repo>
    python verify_ledger.py

How it works
  * Every time picks are recorded, ledger/picks.csv gains a block of rows that share one
    snapshot_id. The SHA-256 hash of that block's exact text is recorded in
    ledger/hashes.csv.
  * Each hash is chained to the previous one:
        chain_n = SHA-256( chain_(n-1) + ":" + snapshot_sha256_n )     (chain_0 = "GENESIS")
    so changing, deleting, or reordering ANY past snapshot changes every later chain hash.
  * Each chain hash is also posted to a public Discord channel. Discord stamps the message
    with its own time, which the operator cannot edit. The message id and time are saved in
    hashes.csv (columns discord_message_id, discord_posted_at) so you can look the message up.

This script recomputes everything from picks.csv and compares it with hashes.csv.
Exit code 0 = consistent; 1 = a problem was found.

What it cannot do: it can't prove a snapshot was honest at the time (only that it hasn't
changed since it was hashed), and the Discord timestamps have to be checked in Discord.
"""

import argparse
import csv
import hashlib
import os
import sys

GENESIS = "GENESIS"
HASH_COLS = ["snapshot_id", "n_rows", "snapshot_sha256", "chain_sha256", "discord_message_id", "discord_posted_at"]


def sha256_hex(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def snapshot_hash(lines):
    return sha256_hex("\n".join(lines))


def chain_hash(prev, snap_hash):
    return sha256_hex(f"{prev}:{snap_hash}")


def read_snapshots(picks_path):
    """Return ordered list of (snapshot_id, [raw csv lines]) in file order. Raw text, no parsing,
    so the hash covers the exact bytes people can see in the repository."""
    with open(picks_path, newline="", encoding="utf-8") as f:
        raw = [ln.rstrip("\r\n") for ln in f]
    if not raw:
        return []
    order, blocks = [], {}
    for ln in raw[1:]:  # skip header
        if not ln.strip():
            continue
        sid = next(csv.reader([ln]))[0]
        if sid not in blocks:
            order.append(sid)
            blocks[sid] = []
        blocks[sid].append(ln)
    return [(sid, blocks[sid]) for sid in order]


def read_hashes(hashes_path):
    if not os.path.exists(hashes_path):
        return []
    with open(hashes_path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def verify(ledger_dir):
    picks_path = os.path.join(ledger_dir, "picks.csv")
    snaps = read_snapshots(picks_path) if os.path.exists(picks_path) else []
    recorded = read_hashes(os.path.join(ledger_dir, "hashes.csv"))
    problems, notes = [], []

    rec_by_id = {r["snapshot_id"]: r for r in recorded}
    snap_ids = [s for s, _ in snaps]

    for sid in rec_by_id:
        if sid not in snap_ids:
            problems.append(f"{sid}: hashed snapshot is MISSING from picks.csv (rows deleted?)")

    prev = GENESIS
    unanchored = 0
    for sid, lines in snaps:
        rec = rec_by_id.get(sid)
        if rec is None:
            problems.append(f"{sid}: snapshot in picks.csv has NO hash record (rows added without being anchored)")
            continue
        sh = snapshot_hash(lines)
        ch = chain_hash(prev, sh)
        if sh != rec["snapshot_sha256"]:
            problems.append(f"{sid}: snapshot hash MISMATCH (rows were changed after hashing)")
        if str(len(lines)) != str(rec["n_rows"]):
            problems.append(f"{sid}: row count {len(lines)} != recorded {rec['n_rows']}")
        if ch != rec["chain_sha256"]:
            problems.append(f"{sid}: chain hash MISMATCH (history before this point was changed, or order changed)")
        if not rec.get("discord_message_id"):
            unanchored += 1
        # Continue the chain from the RECORDED value so one break doesn't hide later problems.
        prev = rec["chain_sha256"]

    # order check: recorded order must match file order
    rec_order = [r["snapshot_id"] for r in recorded if r["snapshot_id"] in snap_ids]
    if rec_order != [s for s in snap_ids if s in rec_by_id]:
        problems.append("Snapshot order in hashes.csv differs from picks.csv")

    notes.append(f"{len(snaps)} snapshot(s) in picks.csv, {len(recorded)} in hashes.csv, "
                 f"{len(snaps) - unanchored} anchored to Discord, {unanchored} not anchored.")
    return problems, notes


def main():
    ap = argparse.ArgumentParser(description="Verify the public ledger hash chain.")
    ap.add_argument("--ledger-dir", default="ledger")
    args = ap.parse_args()
    problems, notes = verify(args.ledger_dir)
    for n in notes:
        print(n)
    if problems:
        print("\nPROBLEMS FOUND:")
        for p in problems:
            print("  -", p)
        sys.exit(1)
    print("OK: every snapshot matches its recorded hash and the chain is unbroken.")


if __name__ == "__main__":
    main()
