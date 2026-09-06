"""Holmes (Deng et al., CCS 2024), architecture and feature extraction.

Transcribed from the authors' released code, WFlib:
  https://github.com/FIND-Lab/Website-Fingerprinting-Library (branch master)
  WFlib/models/Holmes.py, WFlib/tools/data_processor.py,
  exp/data_analysis/spatial_analysis.py, scripts/Holmes.sh

Holmes is NOT the single dual-branch network that thesis Table C.1 describes.
That table's "temporal 1000 / TAF 2000" and "Adam / AdamW" and
"CrossEntropy / SupConLoss" columns are two different models in a four-stage
pipeline, not two branches of one network:

  A. an auxiliary classifier (the RF architecture) on a 1000-bin temporal
     feature, trained with CrossEntropy / Adam / batch 200;
  B. DeepLiftShap attribution over that model to find, per class, the
     "effective range" of the trace where the discriminative signal lives;
  C. offline augmentation, two extra truncated copies of every sample, cut
     inside that per-class effective range;
  D. the Holmes network itself, on TAF only, trained with SupConLoss / AdamW /
     batch 256. It emits a 128-d embedding and has no classifier head, so
     prediction needs a further centroid-and-radius calibration step.

Every deviation forced by this dataset is recorded in logs/deltas.md.
"""
import numpy as np
import torch
import torch.nn as nn

TEMPORAL_LEN = 1000       # stage A input, WFlib extract_temporal_feature
TAF_INTERVAL_MS = 40.0    # stage D, data_processor.extract_TAF
TAF_LEN = 2000


# ------------------------------------------------------------------ features

def _real_mask(X):
    """Direction != 0. Padding in these files is strictly trailing (checked)."""
    return X != 0


def temporal_input(X, T, feat_length=TEMPORAL_LEN, chunk=4096):
    """Stage A feature: (n, 1, 2, feat_length) counts, per WFlib
    extract_temporal_feature.

    Each trace is binned by *its own* load time, interval = load_time /
    feat_length, so this is a per-trace time normalisation rather than a shared
    grid. Row 0 outgoing, row 1 incoming.

    Deviation, forced and documented: their loop is
        for packet in X[idx]:  if packet == 0: break
    over direction*timestamp. Every trace in this dataset has its first packet
    at exactly t = 0.0, so that signed value is 0 and their loop would break on
    the first packet and return an all-zero feature for every trace. Padding is
    detected here by direction == 0, which is what the break is actually for.
    """
    n = len(X)
    out = np.zeros((n, 2, feat_length), dtype=np.float32)
    for s in range(0, n, chunk):
        e = min(s + chunk, n)
        xb, tb = X[s:e], T[s:e].astype(np.float64)
        b = e - s
        real = _real_mask(xb)
        lens = real.sum(1)
        load = np.zeros(b)
        has = lens > 0
        load[has] = tb[np.arange(b)[has], lens[has] - 1]
        ok = real & (load[:, None] > 0)
        if not ok.any():
            continue
        order = np.zeros(tb.shape, dtype=np.int64)
        np.divide(tb * feat_length, np.where(load > 0, load, 1.0)[:, None],
                  out=order, casting="unsafe")
        order = np.clip(order, 0, feat_length - 1)
        rows = np.arange(b)[:, None] * (2 * feat_length)
        for r, m in ((0, ok & (xb > 0)), (1, ok & (xb < 0))):
            if not m.any():
                continue
            flat = (rows + r * feat_length + order)[m]
            cnt = np.bincount(flat.ravel(), minlength=b * 2 * feat_length)
            out[s:e] += cnt[: b * 2 * feat_length].reshape(b, 2, feat_length)
    return out[:, None, :, :]


def taf_input(X, T, interval_ms=TAF_INTERVAL_MS, max_len=TAF_LEN, chunk=1024):
    """Stage D feature: (n, 3, 2, max_len), per WFlib process_TAF/agg_interval.

    Three feature rows per 40 ms bin, each split by direction:
        row 0  packet count
        row 1  burst count        (runs of same-direction packets in that bin)
        row 2  mean burst length
    Bins are measured from the trace's first packet. Their code reaches the
    same bin index via np.searchsorted on the absolute timestamps; timestamps
    here are monotonic within a trace (checked), so the closed form is
    equivalent and vastly faster. Packets past the last bin fall into it, which
    is what their `ed_pos = len` special case for the final bin does.
    """
    n = len(X)
    out = np.zeros((n, 3, 2, max_len), dtype=np.float32)
    for s in range(0, n, chunk):
        e = min(s + chunk, n)
        xb, tb = X[s:e], T[s:e].astype(np.float64) * 1000.0   # their sequences *= 1000
        b = e - s
        real = _real_mask(xb)
        if not real.any():
            continue
        tr, pos = np.nonzero(real)                 # already in (trace, order) order
        t_ms = tb[tr, pos]
        sign = np.where(xb[tr, pos] > 0, 1, -1).astype(np.int8)

        lens = real.sum(1)
        st = np.zeros(b)
        has = lens > 0
        st[has] = tb[np.arange(b)[has], 0]         # first real packet, index 0
        bin_i = np.floor((t_ms - st[tr]) / interval_ms).astype(np.int64)
        bin_i = np.clip(bin_i, 0, max_len - 1)

        flat = tr * max_len + bin_i                # cell id within this chunk
        size = b * max_len

        # row 0: packet counts per direction
        for r, m in ((0, sign > 0), (1, sign < 0)):
            if m.any():
                c = np.bincount(flat[m], minlength=size)
                out[s:e, 0, r] += c[:size].reshape(b, max_len)

        # runs of constant direction, restricted to one cell
        newrun = np.empty(len(flat), dtype=bool)
        newrun[0] = True
        np.not_equal(flat[1:], flat[:-1], out=newrun[1:])
        newrun[1:] |= (sign[1:] != sign[:-1])
        run_id = np.cumsum(newrun) - 1
        run_len = np.bincount(run_id).astype(np.float32)
        starts = np.flatnonzero(newrun)
        run_flat, run_sign = flat[starts], sign[starts]

        for r, m in ((0, run_sign > 0), (1, run_sign < 0)):
            if not m.any():
                continue
            cnt = np.bincount(run_flat[m], minlength=size)[:size]
            tot = np.bincount(run_flat[m], weights=run_len[m], minlength=size)[:size]
            out[s:e, 1, r] += cnt.reshape(b, max_len)
            with np.errstate(invalid="ignore", divide="ignore"):
                mean = np.where(cnt > 0, tot / np.maximum(cnt, 1), 0.0)
            out[s:e, 2, r] += mean.reshape(b, max_len).astype(np.float32)
    return out


# ------------------------------------------------------------------- network

class ConvBlock1d(nn.Module):
    def __init__(self, in_channels, out_channels, kernel_size, dilation=1):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv1d(in_channels, out_channels, kernel_size, dilation=dilation,
                      padding="same"),
            nn.BatchNorm1d(out_channels), nn.ReLU(),
            nn.Conv1d(out_channels, out_channels, kernel_size, dilation=dilation,
                      padding="same"),
            nn.BatchNorm1d(out_channels), nn.ReLU(),
        )
        self.downsample = (nn.Conv1d(in_channels, out_channels, 1)
                           if in_channels != out_channels else None)
        if self.downsample is not None:
            self.downsample.weight.data.normal_(0, 0.01)
        self.last_relu = nn.ReLU()

    def forward(self, x):
        out = self.net(x)
        res = x if self.downsample is None else self.downsample(x)
        return self.last_relu(out + res)


class ConvBlock2d(nn.Module):
    def __init__(self, in_channels, out_channels, kernel_size):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv2d(in_channels, out_channels, kernel_size, 1, padding="same"),
            nn.BatchNorm2d(out_channels), nn.ReLU(),
            nn.Conv2d(out_channels, out_channels, kernel_size, 1, padding="same"),
            nn.BatchNorm2d(out_channels), nn.ReLU(),
        )
        self.downsample = (nn.Conv2d(in_channels, out_channels, 1)
                           if in_channels != out_channels else None)
        if self.downsample is not None:
            self.downsample.weight.data.normal_(0, 0.01)
        self.last_relu = nn.ReLU()

    def forward(self, x):
        out = self.net(x)
        res = x if self.downsample is None else self.downsample(x)
        return self.last_relu(out + res)


class Encoder2d(nn.Module):
    def __init__(self, in_channels, out_channels, conv_num_layers):
        super().__init__()
        layers = []
        cur_in, cur_out = in_channels, 32
        for i in range(conv_num_layers):
            layers.append(ConvBlock2d(cur_in, cur_out, (3, 7)))
            layers.append(nn.MaxPool2d((1, 3)) if i < conv_num_layers - 1
                          else nn.MaxPool2d((2, 2)))
            layers.append(nn.Dropout(0.1))
            cur_in, cur_out = cur_out, cur_out * 2
            if i == conv_num_layers - 2:
                cur_out = out_channels
        self.layers = nn.Sequential(*layers)

    def forward(self, x):
        return self.layers(x)


class Encoder1d(nn.Module):
    def __init__(self, in_channels, out_channels, conv_num_layers):
        super().__init__()
        layers = []
        cur_in, cur_out = in_channels, 128
        for i in range(conv_num_layers):
            layers.append(ConvBlock1d(cur_in, cur_out, 3))
            if i < conv_num_layers - 1:
                layers += [nn.MaxPool1d(3), nn.Dropout(0.3)]
            cur_in, cur_out = cur_out, cur_out * 2
            if i == conv_num_layers - 2:
                cur_out = out_channels
        self.layers = nn.Sequential(*layers)

    def forward(self, x):
        return self.layers(x)


class HolmesNet(nn.Module):
    """Emits a 128-d embedding, not logits. Prediction needs the centroid and
    radius calibration in spatial_distribution(), exactly as in WFlib."""

    def __init__(self, num_classes=None):
        super().__init__()
        self.in_channels_1d = 16
        self.encoder2d = Encoder2d(in_channels=3, out_channels=64, conv_num_layers=2)
        self.encoder1d = Encoder1d(in_channels=16, out_channels=128, conv_num_layers=4)
        self.classifier = nn.AdaptiveAvgPool1d(1)
        self._initialize_weights()

    def forward(self, x):
        x = self.encoder2d(x)
        x = x.view(x.shape[0], self.in_channels_1d, -1)
        x = self.encoder1d(x)
        x = self.classifier(x)
        return x.view(x.shape[0], -1)

    def _initialize_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                n = m.kernel_size[0] * m.kernel_size[1] * m.out_channels
                m.weight.data.normal_(0, (2.0 / n) ** 0.5)
                if m.bias is not None:
                    m.bias.data.zero_()
            elif isinstance(m, nn.BatchNorm2d):
                m.weight.data.fill_(1)
                m.bias.data.zero_()
            elif isinstance(m, nn.Linear):
                m.weight.data.normal_(0, 0.01)
                m.bias.data.zero_()


# ------------------------------------------------------- inference calibration

def median_absolute_deviation(a):
    """WFlib evaluator.median_absolute_deviation."""
    med = np.median(a)
    return float(np.median(np.abs(a - med)))


def spatial_distribution(embs, labels, num_classes):
    """Per-class centroid and radius from validation embeddings, then shrink
    radii until no two class balls overlap. Transcribed from WFlib
    exp/data_analysis/spatial_analysis.py."""
    from sklearn.metrics.pairwise import cosine_similarity
    centroids, radii = [], []
    for c in range(num_classes):
        cur = embs[labels == c]
        if len(cur) == 0:
            centroids.append(np.zeros(embs.shape[1], dtype=np.float32))
            radii.append(0.0)
            continue
        cen = cur.mean(axis=0)
        centroids.append(cen)
        d = 1.0 - cosine_similarity(cur, cen.reshape(1, -1))
        radii.append(median_absolute_deviation(d))
    centroids = np.array(centroids, dtype=np.float32)
    radii = np.array(radii, dtype=np.float64)

    sim = cosine_similarity(centroids, centroids)
    for a in range(num_classes):
        for b in range(a + 1, num_classes):
            dist = 1.0 - sim[a, b]
            ra, rb = radii[a], radii[b]
            if ra + rb > 0 and dist <= ra + rb:
                diff = ra + rb - dist
                radii[a] -= diff * ra / (ra + rb)
                radii[b] -= diff * rb / (ra + rb)
    return centroids, radii


def predict_from_distribution(embs, centroids, radii):
    """argmin over classes of (cosine distance to centroid) - radius, which is
    WFlib's closed-world decision rule."""
    from sklearn.metrics.pairwise import cosine_similarity
    d = 1.0 - cosine_similarity(embs, centroids)
    return np.argmin(d - radii[None, :], axis=1)
