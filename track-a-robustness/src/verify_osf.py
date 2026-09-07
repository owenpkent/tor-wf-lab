#!/usr/bin/env python3
"""Check downloaded OSF files against the authors' published sha512 lists.

Exit status, because make targets depend on it:

  1  a file is present and its digest does not match  (always fatal)
  1  a checksum listing itself is absent, so nothing in that folder could be
     checked. Silently exiting 0 having verified nothing was the bug that let
     `make fs-figure` publish a figure from an unverified download.
  1  --require-all and a listed file is absent. `make data` fetches all 29, so
     a missing file there means the download failed.
  0  otherwise. A partial download is fine without --require-all: every file
     that is present has been checked.

Usage: python verify_osf.py [--require-all]
"""
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
    require_all = "--require-all" in sys.argv[1:]
    ok = bad = missing = 0
    no_listing = []
    for folder, listing in (("pre-conflux", "pre-sha512sum.txt"),
                            ("post-conflux", "post-sha512sum.txt")):
        lp = os.path.join(DATA, folder, listing)
        if not os.path.exists(lp):
            print(f"[NONE] {folder}: no {listing}, nothing could be verified")
            no_listing.append(folder)
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
    if bad:
        print("FAILED: a downloaded file does not match the authors' digest.")
        return 1
    if no_listing:
        print(f"FAILED: no checksum listing for {', '.join(no_listing)}; "
              "run fetch_osf.py, which always fetches them.")
        return 1
    if require_all and missing:
        print(f"FAILED: {missing} listed file(s) absent and --require-all was given.")
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
