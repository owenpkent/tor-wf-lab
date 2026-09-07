#!/usr/bin/env python3
"""Download the open OSF files for osf.io/9m8ea into track-a-robustness/data/.

Resumable (HTTP range), skips files already at the manifest size. Priority
files first so the two-axis closed-world run can start before the full 10.6 GB
has landed. Verification is a separate step, see verify_osf.py.

Exits non-zero if any file this run was asked for did not end up at its manifest
size, so `make data` fails instead of handing a truncated .npz to a trainer.

The two sha512 listings are always fetched, whatever patterns are given: they
are a few kilobytes each, and without them verify_osf.py has nothing to check
a filtered download against.
"""
import json, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
MANIFEST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "osf-manifest.json")

LISTINGS = ("pre-conflux/pre-sha512sum.txt", "post-conflux/post-sha512sum.txt")

# The four cells the closed-world two-axis run needs, plus the checksum lists.
PRIORITY = [
    "pre-conflux/pre-sha512sum.txt",
    "post-conflux/post-sha512sum.txt",
    "post-conflux/post-month0-cfx0-au.npz",   # train, both axes
    "post-conflux/post-month0-cfx0-ca.npz",   # cross-network test
    "post-conflux/post-month6-cfx0-au.npz",   # six-month drift test, same site
    "post-conflux/post-month6-cfx0-ca.npz",
]

def order(files):
    rank = {p: i for i, p in enumerate(PRIORITY)}
    return sorted(files, key=lambda f: (rank.get(f["path"], len(PRIORITY)), f["path"]))

def main():
    files = json.load(open(MANIFEST))
    only = sys.argv[1:] or None
    failed = []
    for f in order(files):
        if only and f["path"] not in LISTINGS \
                and not any(pat in f["path"] for pat in only):
            continue
        dest = os.path.join(DATA, f["path"])
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        have = os.path.getsize(dest) if os.path.exists(dest) else 0
        if have == f["size"]:
            print(f"[have] {f['path']}", flush=True)
            continue
        print(f"[get ] {f['path']}  ({f['size']:,} bytes, have {have:,})", flush=True)
        rc = subprocess.call(["curl", "-sS", "-L", "-C", "-", "--retry", "5",
                              "--retry-delay", "5", "-o", dest, f["download"]])
        got = os.path.getsize(dest) if os.path.exists(dest) else 0
        status = "ok" if got == f["size"] and rc == 0 else f"SIZE MISMATCH got {got:,}"
        print(f"[done] {f['path']}  rc={rc} {status}", flush=True)
        if got != f["size"] or rc != 0:
            failed.append(f["path"])
    if failed:
        print(f"\n{len(failed)} file(s) incomplete: " + ", ".join(failed), flush=True)
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
