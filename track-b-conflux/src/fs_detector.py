"""The paper's guard-side first-segment (FS) detector, reimplemented.

Thesis section 4.3.2 states it as three conditions on a guard-observed leg:

  1. the first cell following the Conflux handshake is outgoing;
  2. at least one incoming cell appears within the first 10 cells;
  3. at least one outgoing cell appears within a 10-cell window immediately
     following the first incoming cell.

An FS trace is one where the observed leg was primary at both endpoints during
the initial page load, so the guard sees the feature-rich start of the trace.

On the released traces the handshake appears to be stripped already: non-Conflux
(cfx0) traces begin with the +-++ BEGIN / CONNECTED / request pattern rather
than with conflux link cells. `offset` exists to test that assumption.
"""
import numpy as np

WINDOW = 10


def is_fs(X, offset=0, window=WINDOW):
    """Vectorised detector. X is (n, L) with +1 out, -1 in, 0 pad."""
    D = X[:, offset:]
    n, L = D.shape

    # 1. first cell outgoing
    r1 = D[:, 0] > 0

    # 2. an incoming cell within the first `window` cells
    head_in = D[:, :window] < 0
    r2 = head_in.any(axis=1)

    # 3. an outgoing cell within `window` cells after the first incoming one
    first_in = np.argmax(head_in, axis=1)          # 0 where none, masked by r2
    idx = first_in[:, None] + 1 + np.arange(window)[None, :]
    idx = np.minimum(idx, L - 1)
    r3 = (np.take_along_axis(D, idx, axis=1) > 0).any(axis=1)

    return r1 & r2 & r3
