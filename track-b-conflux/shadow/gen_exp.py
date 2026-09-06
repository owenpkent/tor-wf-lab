#!/usr/bin/env python3
"""Generate a Shadow experiment: one client, two guards at different latencies.

Usage: gen_exp.py <advantage_ms> <outdir> [seed]

Validation harness for Track B: does stock, unpatched tor reproduce the
latency bias measured on the real traces in notes/06? Requires Shadow, tgen
and tor 0.4.8+ on PATH, and SHADOW_TOR_EXAMPLE pointing at Shadow's Tor
example directory.

The advantage is the RTT difference between the two guards, so each guard's
one-way edge latency differs by advantage/2. relay1 is the "advantaged" guard
(the one a WF adversary would run); relay2 is pushed further away.
"""
import os, shutil, sys

# Shadow's own private Tor network example: one authority with pre-generated
# keys, four relays, two exits, a tor client and tgen at both ends. Point
# SHADOW_TOR_EXAMPLE at examples/docs/tor in a Shadow checkout.
EXAMPLE = os.environ.get("SHADOW_TOR_EXAMPLE",
                         os.path.expanduser("~/src/shadow/examples/docs/tor"))
BASE_LATENCY_MS = 25          # one-way, core network
RELAY1_FP = "3FB0BD7827C760FE7F9DD810FCB10322D63AB4CF"
RELAY2_FP = "FF197204099FA0E507FA46D41FED97D3337B4BAA"


def graph(adv_ms):
    l1 = BASE_LATENCY_MS
    l2 = BASE_LATENCY_MS + adv_ms / 2      # one-way, so RTT differs by adv_ms
    nodes = "".join(f"""
        node [
          id {i}
          host_bandwidth_down "1 Gbit"
          host_bandwidth_up "1 Gbit"
        ]""" for i in range(3))
    edges = ""
    for a, b, lat in ((0, 0, l1), (1, 1, l1), (2, 2, l1),
                      (0, 1, l1), (0, 2, l2), (1, 2, l1 + l2)):
        edges += f"""
        edge [
          source {a}
          target {b}
          latency "{int(round(lat))} ms"
          jitter "0 ms"
          packet_loss 0.0
        ]"""
    return f"      graph [\n        directed 0{nodes}{edges}\n      ]"


def main():
    adv = float(sys.argv[1])
    out = sys.argv[2]
    seed = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    if os.path.exists(out):
        shutil.rmtree(out)
    shutil.copytree(EXAMPLE, out)

    # guards on their own network nodes, everything else in the core
    y = open(os.path.join(EXAMPLE, "shadow.yaml")).read()
    # Shadow is deterministic given a seed; vary it to get independent runs.
    y = y.replace("general:\n", f"general:\n  seed: {seed}\n")
    y = y.replace(y[y.index("      graph ["):y.index("hosts:")].rstrip() + "\n",
                  graph(adv) + "\n")
    y = y.replace("""  relay1:
    network_node_id: 0""", """  relay1:
    network_node_id: 1
    host_options:
      pcap_enabled: true""")
    y = y.replace("""  relay2:
    network_node_id: 0""", """  relay2:
    network_node_id: 2
    host_options:
      pcap_enabled: true""")
    open(os.path.join(out, "shadow.yaml"), "w").write(y)

    # client: pin both guards so conflux has exactly two legs to choose from,
    # and rotate circuits often so the run yields many independent conflux sets
    with open(os.path.join(out, "conf", "tor.client.torrc"), "a") as f:
        f.write(f"""
UseEntryGuards 1
NumEntryGuards 2
EntryNodes {RELAY1_FP},{RELAY2_FP}
StrictNodes 1
MaxCircuitDirtiness 20
ConfluxClientUX throughput
Log info file tor.info.log
""")

    # conflux defaults to on in 0.4.9, set it explicitly for the record
    p = os.path.join(out, "conf", "tor.authority.torrc")
    s = open(p).read().replace("ConsensusParams cc_alg=2",
                               "ConsensusParams cc_alg=2 cfx_enabled=1")
    open(p, "w").write(s)
    print(f"wrote {out} (advantage {adv:g} ms RTT, guard edges "
          f"{BASE_LATENCY_MS} / {BASE_LATENCY_MS + adv/2:g} ms one-way)")


if __name__ == "__main__":
    main()
