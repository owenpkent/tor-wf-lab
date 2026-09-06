#!/usr/bin/env python3
"""Per-guard share of the client's Conflux traffic, from Shadow pcaps.

pcap is LINKTYPE_RAW (101): each record is a bare IPv4 packet.
"""
import struct, sys, os
from collections import defaultdict

CLIENT = "11.0.0.9"


def ip(b):
    return ".".join(str(x) for x in b)


def read(path, peer=CLIENT):
    """Yield (t, src, dst, payload_len) for TCP packets involving `peer`."""
    with open(path, "rb") as f:
        gh = f.read(24)
        if len(gh) < 24:
            return
        _, _, _, _, _, _, link = struct.unpack("<IHHiIII", gh)
        assert link == 101, f"unexpected linktype {link}"
        t0 = None
        while True:
            h = f.read(16)
            if len(h) < 16:
                return
            ts, tus, incl, _ = struct.unpack("<IIII", h)
            d = f.read(incl)
            if len(d) < 20 or (d[0] >> 4) != 4:
                continue
            ihl = (d[0] & 0xF) * 4
            proto = d[9]
            src, dst = ip(d[12:16]), ip(d[16:20])
            if proto != 6 or peer not in (src, dst):
                continue
            total = struct.unpack(">H", d[2:4])[0]
            doff = (d[ihl + 12] >> 4) * 4 if len(d) > ihl + 12 else 20
            payload = max(0, total - ihl - doff)
            t = ts + tus / 1e6
            t0 = t if t0 is None else t0
            yield (t - t0, src, dst, payload)


def summarise(path):
    down = up = 0
    first_down = None
    for t, src, dst, n in read(path):
        if n == 0:
            continue
        if dst == CLIENT:
            down += n
            if first_down is None:
                first_down = t
        else:
            up += n
    return down, up, first_down


def main():
    root = sys.argv[1]
    rows = {}
    for g in ("relay1", "relay2"):
        p = os.path.join(root, "shadow.data", "hosts", g, "eth0.pcap")
        rows[g] = summarise(p)
    d1, u1, f1 = rows["relay1"]
    d2, u2, f2 = rows["relay2"]
    tot = d1 + d2
    print(f"  relay1 (advantaged): down {d1/1e6:8.2f} MB  up {u1/1e6:6.2f} MB  first down at {f1:.2f}s")
    print(f"  relay2             : down {d2/1e6:8.2f} MB  up {u2/1e6:6.2f} MB  first down at {f2:.2f}s")
    print(f"  advantaged guard's share of client downstream: {d1/tot:.4f}")
    return d1 / tot


if __name__ == "__main__":
    main()
