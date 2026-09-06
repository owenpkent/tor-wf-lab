"""Architectures and input transforms for the four CNN classifiers.

Reimplementations. The paper's authors released no code (see logs/deltas.md),
so each architecture comes from its own original paper, and the training
hyperparameters come from thesis Table C.1. Nothing here is retuned.

Input transforms, one per classifier, all from a raw (X, T) pair where
X is (n, 5000) int8 direction (+1 out, -1 in, 0 pad) and T is (n, 5000)
float32 arrival time in seconds:

  DF       direction, length 5000
  Tik-Tok  direction * timestamp, length 5000
  RF       TAM, 2 x 1800 packet counts per time slot

TAM slot duration is TMAX / N. Measured on the actual OSF files, every
collection caps at 45.00 s, so the thesis's "max load time set per experiment"
resolves to TMAX = 45.0 here. See logs/deltas.md.
"""
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

TMAX = 45.0          # measured cap, all five collections
TAM_N = 1800         # thesis Table C.1


# ---------------------------------------------------------------- transforms

def df_input(X, T=None):
    """DF: direction only, +1 / -1 / 0."""
    return X.astype(np.float32)[:, None, :]


def tiktok_input(X, T):
    """Tik-Tok: directional timing, direction * timestamp."""
    return (X.astype(np.float32) * T.astype(np.float32))[:, None, :]


def tam_input(X, T, n_slots=TAM_N, tmax=TMAX, chunk=2048):
    """RF: Traffic Aggregation Matrix, (n, 2, n_slots) of packet counts.

    Row 0 counts outgoing packets per slot, row 1 incoming. Binning follows the
    authors' released code (RF/FeatureExtraction/packets_per_slot.py) exactly:

        idx = int(t * (n_slots - 1) / tmax)          for t < tmax
        idx = n_slots - 1                            for t >= tmax

    Note the (n_slots - 1) divisor, so the slot is tmax / (n_slots - 1), not
    tmax / n_slots. At their default tmax = 80 that is 44.5 ms, which is the
    "roughly 44 ms" the thesis quotes; at the tmax = 45 measured on these files
    it is 25.0 ms. Late packets accumulate in the final slot rather than being
    dropped. Counts are raw, unnormalised, as in their code.
    """
    n = len(X)
    out = np.zeros((n, 2, n_slots), dtype=np.float32)
    for s in range(0, n, chunk):
        e = min(s + chunk, n)
        xb, tb = X[s:e], T[s:e].astype(np.float64)
        b = e - s
        idx = np.where(tb >= tmax, n_slots - 1,
                       (tb * (n_slots - 1) / tmax).astype(np.int32))
        idx = np.clip(idx, 0, n_slots - 1)
        rows = np.arange(b)[:, None] * (2 * n_slots)
        for r, mask in ((0, xb > 0), (1, xb < 0)):
            if not mask.any():
                continue
            flat = (rows + r * n_slots + idx)[mask]
            counts = np.bincount(flat.ravel(), minlength=b * 2 * n_slots)
            out[s:e] += counts[: b * 2 * n_slots].reshape(b, 2, n_slots)
    return out


TRANSFORMS = {"df": df_input, "tiktok": tiktok_input, "rf": tam_input}


# ---------------------------------------------------------------- DF backbone

def _keras_same_pool(x, k, stride):
    """Keras 'same' padding for max pooling: out = ceil(in / stride).

    PyTorch's MaxPool1d padding is symmetric and capped at k/2, which cannot
    express Keras's asymmetric right-heavy pad. DF is a Keras model and its
    published tensor shapes only reproduce with this padding.
    """
    n = x.shape[-1]
    out = -(-n // stride)
    total = max((out - 1) * stride + k - n, 0)
    if total:
        x = F.pad(x, (total // 2, total - total // 2), value=float("-inf"))
    return F.max_pool1d(x, k, stride)


class DFNet(nn.Module):
    """Deep Fingerprinting (Sirinam et al., CCS 2018), Table 10.

    Four conv blocks with filters 32/64/128/256, kernel 8, each block two
    convolutions then max pool (size 8, stride 4) and dropout 0.1. Block 1 uses
    ELU, later blocks ReLU, which is the paper's stated activation schedule.
    Two 512-unit fully connected layers with dropout 0.7 and 0.5.

    Tik-Tok (Rahman et al., PoPETs 2020) is this same network on a different
    input, so it shares the class.
    """

    FILTERS = (32, 64, 128, 256)
    KERNEL = 8
    POOL, POOL_STRIDE = 8, 4

    def __init__(self, n_classes, in_len=5000, in_ch=1):
        super().__init__()
        self.blocks = nn.ModuleList()
        self.acts = []
        c_in = in_ch
        for i, c in enumerate(self.FILTERS):
            self.blocks.append(nn.ModuleDict({
                "c1": nn.Conv1d(c_in, c, self.KERNEL, padding="same"),
                "b1": nn.BatchNorm1d(c),
                "c2": nn.Conv1d(c, c, self.KERNEL, padding="same"),
                "b2": nn.BatchNorm1d(c),
                "do": nn.Dropout(0.1),
            }))
            self.acts.append(F.elu if i == 0 else F.relu)
            c_in = c

        n = in_len
        for _ in self.FILTERS:
            n = -(-n // self.POOL_STRIDE)
        self.flat_dim = self.FILTERS[-1] * n

        self.fc = nn.Sequential(
            nn.Linear(self.flat_dim, 512), nn.BatchNorm1d(512), nn.ReLU(),
            nn.Dropout(0.7),
            nn.Linear(512, 512), nn.BatchNorm1d(512), nn.ReLU(),
            nn.Dropout(0.5),
            nn.Linear(512, n_classes),
        )

    def forward(self, x):
        for blk, act in zip(self.blocks, self.acts):
            x = act(blk["b1"](blk["c1"](x)))
            x = act(blk["b2"](blk["c2"](x)))
            x = _keras_same_pool(x, self.POOL, self.POOL_STRIDE)
            x = blk["do"](x)
        return self.fc(x.flatten(1))


# ---------------------------------------------------------------- RF backbone

class RFNet(nn.Module):
    """RF (Shen et al., USENIX Security 2023), transcribed from the authors'
    released RF/models/RF.py.

    Input is the TAM as a single-channel 2D image, (batch, 1, 2, 1800). Two 2D
    conv blocks, then the tensor is reshaped back to 32 channels and run through
    a 1D VGG-style stack whose final convolution emits one channel per class,
    global-average-pooled to logits. There is no fully connected layer.

    Two faithfully reproduced quirks, both in the released code, both recorded
    in logs/deltas.md rather than "fixed":
      * the reshape after the 2D stack is (B, 64, 1, W) -> (B, 32, 2W), which
        mixes channel and width rather than flattening cleanly;
      * the final class-emitting convolution is followed by BatchNorm and ReLU,
        so the pooled logits are non-negative before CrossEntropyLoss.
    """

    CFG = [128, 128, "M", 256, 256, "M", 512]

    def __init__(self, n_classes):
        super().__init__()
        self.first_out = 32
        self.first_layer = self._first_layers()
        self.features = self._make_layers(self.CFG + [n_classes], in_channels=32)
        self.classifier = nn.AdaptiveAvgPool1d(1)
        self._init_weights()

    @staticmethod
    def _first_layers(in_channels=1, out_channel=32):
        return nn.Sequential(
            nn.Conv2d(in_channels, out_channel, (3, 6), 1, (1, 1)),
            nn.BatchNorm2d(out_channel), nn.ReLU(),
            nn.Conv2d(out_channel, out_channel, (3, 6), 1, (1, 1)),
            nn.BatchNorm2d(out_channel), nn.ReLU(),
            nn.MaxPool2d((1, 3)), nn.Dropout(0.1),
            nn.Conv2d(out_channel, 64, (3, 6), 1, (1, 1)),
            nn.BatchNorm2d(64), nn.ReLU(),
            nn.Conv2d(64, 64, (3, 6), 1, (1, 1)),
            nn.BatchNorm2d(64), nn.ReLU(),
            nn.MaxPool2d((2, 2)), nn.Dropout(0.1),
        )

    @staticmethod
    def _make_layers(cfg, in_channels=32):
        layers = []
        for v in cfg:
            if v == "M":
                layers += [nn.MaxPool1d(3), nn.Dropout(0.3)]
            else:
                layers += [nn.Conv1d(in_channels, v, 3, 1, 1),
                           nn.BatchNorm1d(v), nn.ReLU()]
                in_channels = v
        return nn.Sequential(*layers)

    def _init_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                n = m.kernel_size[0] * m.kernel_size[1] * m.out_channels
                m.weight.data.normal_(0, (2.0 / n) ** 0.5)
                if m.bias is not None:
                    m.bias.data.zero_()
            elif isinstance(m, (nn.BatchNorm2d, nn.BatchNorm1d)):
                m.weight.data.fill_(1)
                m.bias.data.zero_()

    def forward(self, x):
        x = self.first_layer(x)
        x = x.view(x.size(0), self.first_out, -1)
        x = self.features(x)
        return self.classifier(x).view(x.size(0), -1)
