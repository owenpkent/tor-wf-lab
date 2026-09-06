#!/usr/bin/env python3
"""Check downloaded OSF files against the authors' published sha512 lists."""
import hashlib, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")

def sha512(path, buf=1 << 22):
    h = hashlib.sha512()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(buf), b""):
            h.update(chunk)
    return h.hexdigest()

def main():
    ok = bad = missing = 0
    for folder, listing in (("pre-conflux", "pre-sha512sum.txt"),
                            ("post-conflux", "post-sha512sum.txt")):
        lp = os.path.join(DATA, folder, listing)
        if not os.path.exists(lp):
            print(f"[skip] {folder}: no {listing}")
            continue
        for line in open(lp):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            digest, name = line.split(None, 1)
            name = name.lstrip("*").strip()
            path = os.path.join(DATA, folder, os.path.basename(name))
            if not os.path.exists(path):
                print(f"[miss] {folder}/{os.path.basename(name)}")
                missing += 1
                continue
            got = sha512(path)
            if got == digest:
                print(f"[ok  ] {folder}/{os.path.basename(name)}")
                ok += 1
            else:
                print(f"[BAD ] {folder}/{os.path.basename(name)}\n       want {digest}\n       got  {got}")
                bad += 1
    print(f"\n{ok} ok, {bad} bad, {missing} missing")
    return 1 if bad else 0

if __name__ == "__main__":
    sys.exit(main())
