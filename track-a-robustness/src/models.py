"""Torch models and input transforms for the four CNN classifiers.

The authors released no code (logs/osf-inventory.md), so these are
reimplementations from the original papers at the hyperparameters in thesis
Table C.1. Every judgement call is listed in logs/deltas.md.

  DF       Sirinam et al. 2018, 1D CNN over the direction sequence
  Tik-Tok  Rahman et al. 2020, the DF architecture over direction x timestamp
  RF       Shen et al. 2023, 2D CNN over a Traffic Aggregation Matrix
  Holmes   Deng et al. 2024, deliberately NOT implemented, see note at bottom

Input transforms take the (X, T) arrays exactly as the .npz files store them:
X is +1 out / -1 in / 0 pad, T is seconds, both (n, 5000).
"""
import numpy as np
import torch
import torch.nn as nn

TRACE_LEN = 5000
TAM_LEN = 1800          # thesis Table C.1
TAM_TMAX = 45.0         # measured: every collection caps at exactly 45.00 s


# --------------------------------------------------------------------------
# input transforms
# --------------------------------------------------------------------------

def direction_input(X, T=None):
    """DF: the direction sequence alone."""
    return torch.from_numpy(X.astype(np.float32)).unsqueeze(1)


def directional_timing_input(X, T):
    """Tik-Tok: direction x timestamp, so sign carries direction and magnitude
    carries arrival time."""
    return torch.from_numpy((X.astype(np.float32) * T.astype(np.float32))).unsqueeze(1)


def tam(X, T, n_slots=TAM_LEN, t_max=TAM_TMAX, chunk=2048):
    """RF: Traffic Aggregation Matrix, (n, 2, n_slots) counts per time slot.

    Row 0 counts outgoing cells, row 1 incoming. Slot width is t_max / n_slots,
    so the published 1800 slots over the 45 s cap give 25 ms slots. Cells beyond
    t_max fall in the last slot, as in the original.

    Built with a single bincount per chunk rather than np.add.at, which is an
    order of magnitude faster here. Returned as uint16: the entries are small
    counts and the cache is otherwise 288 MB per collection.
    """
    n = X.shape[0]
    out = np.zeros((n, 2, n_slots), dtype=np.uint16)
    width = t_max / n_slots
    per_trace = 2 * n_slots
    for lo in range(0, n, chunk):
        hi = min(lo + chunk, n)
        Xc, Tc = X[lo:hi], T[lo:hi]
        rows, cols = np.nonzero(Xc != 0)
        if rows.size == 0:
            continue
        slots = np.minimum((Tc[rows, cols] / width).astype(np.int64), n_slots - 1)
        row_off = (Xc[rows, cols] < 0).astype(np.int64) * n_slots
        flat = rows.astype(np.int64) * per_trace + row_off + slots
        counts = np.bincount(flat, minlength=(hi - lo) * per_trace)
        out[lo:hi] = counts.reshape(hi - lo, 2, n_slots).astype(np.uint16)
    return out


def tam_downsample(tam_arr, n_slots):
    """Aggregate a cached 1800-slot TAM to a coarser one.

    Appendix C.1's slot-size sweep is the reason this exists: 1800 slots is
    25 ms, 300 is 150 ms, 150 is 300 ms. Only exact divisors are allowed, so the
    coarse TAM is identical to one built directly at that resolution.
    """
    fine = tam_arr.shape[-1]
    if n_slots == fine:
        return tam_arr
    if fine % n_slots:
        raise ValueError(f"{n_slots} does not divide the cached {fine} slots")
    k = fine // n_slots
    return tam_arr.reshape(*tam_arr.shape[:-1], n_slots, k).sum(-1)


def tam_input(tam_arr):
    return torch.from_numpy(tam_arr.astype(np.float32))


# --------------------------------------------------------------------------
# architectures
# --------------------------------------------------------------------------

class DFNet(nn.Module):
    """Deep Fingerprinting, Sirinam et al. CCS 2018, Table 1 of that paper.

    Four conv blocks of two convolutions each, filters 32/64/128/256, kernel 8,
    max pool 8 stride 4, ELU in the first block and ReLU after, then two 512
    fully connected layers. Dropouts 0.1 per conv block and 0.7 / 0.5 in the
    classifier are the published values.
    """

    def __init__(self, n_classes, in_len=TRACE_LEN):
        super().__init__()
        blocks, in_ch = [], 1
        for i, (out_ch, act) in enumerate(zip((32, 64, 128, 256),
                                              (nn.ELU, nn.ReLU, nn.ReLU, nn.ReLU))):
            blocks += [
                nn.Conv1d(in_ch, out_ch, 8, padding="same"), nn.BatchNorm1d(out_ch), act(),
                nn.Conv1d(out_ch, out_ch, 8, padding="same"), nn.BatchNorm1d(out_ch), act(),
                nn.MaxPool1d(8, stride=4, padding=2), nn.Dropout(0.1),
            ]
            in_ch = out_ch
        self.features = nn.Sequential(*blocks)
        with torch.no_grad():
            flat = self.features(torch.zeros(1, 1, in_len)).numel()
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Linear(flat, 512), nn.BatchNorm1d(512), nn.ReLU(), nn.Dropout(0.7),
            nn.Linear(512, 512), nn.BatchNorm1d(512), nn.ReLU(), nn.Dropout(0.5),
            nn.Linear(512, n_classes),
        )

    def forward(self, x):
        return self.classifier(self.features(x))


class RFNet(nn.Module):
    """Robust Fingerprinting, Shen et al. USENIX Security 2023, over a TAM.

    Table C.1 pins the input (TAM length 1800) and the training schedule but
    gives only "2D CNN" for the architecture, and no code was released. This is
    therefore a reimplementation in the spirit of the paper rather than a
    reproduction of it: four 2D conv blocks over the (2, n_slots) matrix,
    pooling along the time axis only, since the channel axis is 2 wide.
    Logged as a delta.
    """

    def __init__(self, n_classes, n_slots=TAM_LEN):
        super().__init__()
        blocks, in_ch = [], 1
        for out_ch in (32, 64, 128, 256):
            blocks += [
                nn.Conv2d(in_ch, out_ch, (2, 8), padding=(0, 4) if in_ch == 1 else "same"),
                nn.BatchNorm2d(out_ch), nn.ReLU(),
                nn.Conv2d(out_ch, out_ch, (1, 8), padding="same"),
                nn.BatchNorm2d(out_ch), nn.ReLU(),
                nn.MaxPool2d((1, 4)), nn.Dropout(0.1),
            ]
            in_ch = out_ch
        self.features = nn.Sequential(*blocks)
        with torch.no_grad():
            flat = self.features(torch.zeros(1, 1, 2, n_slots)).numel()
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Linear(flat, 512), nn.BatchNorm1d(512), nn.ReLU(), nn.Dropout(0.5),
            nn.Linear(512, n_classes),
        )

    def forward(self, x):
        if x.dim() == 3:
            x = x.unsqueeze(1)          # (n, 2, slots) -> (n, 1, 2, slots)
        return self.classifier(self.features(x))


# --------------------------------------------------------------------------
# registry: hyperparameters verbatim from thesis Table C.1
# --------------------------------------------------------------------------

# net takes (n_classes, input_width). The width must come from the data, not a
# default: the RF slot-size sweep feeds 1800, 300 or 150 slots to the same net.
SPECS = {
    "df": {
        "net": lambda k, L: DFNet(k, in_len=L),
        "transform": direction_input,
        "optimizer": "adamax", "lr": 0.002, "betas": (0.9, 0.999), "eps": 1e-8,
        "batch": 128, "epochs": 30, "early_stop": None, "lr_decay": None,
    },
    "tiktok": {
        "net": lambda k, L: DFNet(k, in_len=L),
        "transform": directional_timing_input,
        "optimizer": "adamax", "lr": 0.002, "betas": (0.9, 0.999), "eps": 1e-8,
        "batch": 32, "epochs": 30, "early_stop": 6, "lr_decay": None,
    },
    "rf": {
        "net": lambda k, L: RFNet(k, n_slots=L),
        "transform": None,              # uses the TAM cache, see cache_tam.py
        "optimizer": "adam", "lr": 5e-4, "betas": (0.9, 0.999), "eps": 1e-8,
        "batch": 200, "epochs": 30, "early_stop": None,
        "lr_decay": lambda epoch: 0.2 ** (epoch / 30),
    },
}

# Holmes is absent on purpose. Table C.1 gives it a dual-branch CNN, two
# optimizers, two batch sizes and an unweighted mix of CrossEntropy and
# SupConLoss over a 1000-length temporal branch and a 2000-length TAF branch.
# That is not enough to reimplement faithfully, and an approximation would
# produce a number that looks like a measurement. Report Holmes as not run.


def build_optimizer(model, spec):
    if spec["optimizer"] == "adamax":
        return torch.optim.Adamax(model.parameters(), lr=spec["lr"],
                                  betas=spec["betas"], eps=spec["eps"])
    return torch.optim.Adam(model.parameters(), lr=spec["lr"],
                            betas=spec["betas"], eps=spec["eps"])
