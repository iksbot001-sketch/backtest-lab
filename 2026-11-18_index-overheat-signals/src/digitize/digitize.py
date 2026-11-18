"""Digitize forward-P/E line charts photographed from a phone screen.

Pipeline per image (no value is forced to match the printed labels):
 1. Faint gray horizontal gridlines tracked across plot (green dashes masked out) -> (x, y, value).
 2. Bottom-axis line (RANSAC) + year tick marks (ya+1..ya+5) -> (x, y, year-start).
 3. Left y-axis line and right screen/card edge -> two vertical constraints (t = T_L, T_R).
 4. Joint 2D projective homography (pixel -> (t, v)) via Levenberg-Marquardt refinement.
 5. Dark low-saturation neutral-gray pixels = series line (green text/dashes excluded); per column take vertex estimate.
 6. Map to (t, v), sort by t, interpolate to weekly Fridays (W-FRI), write CSV.
Diagnostics: digitize/tmp/<img>_overlay.png, calibration residuals in digitize/out/<img>_calib.json
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw
from scipy.optimize import least_squares
from scipy.signal import find_peaks

ROOT = Path(__file__).resolve().parent.parent
CH = ROOT / "data" / "charts"
OUTD = ROOT / "digitize" / "out"
TMP = ROOT / "digitize" / "tmp"
AGY = ROOT / "data" / "agy"
for d in (OUTD, TMP, AGY):
    d.mkdir(parents=True, exist_ok=True)

CFG = {
    "img1": dict(
        grid_vals=[30.0, 27.5, 25.0, 22.5, 20.0, 17.5, 12.5, 10.0],   # 15.0 skipped: coincides with -1σ dotted line
        grid_y0=[461.3, 534.2, 606.7, 679.9, 752.6, 826.0, 972.9, 1045.8], grid_x0=240,
        grid_x=(225, 1400), slope0=0.018,
        refs={"+1σ": (23.5, 651.0), "mean": (19.2, 775.7), "-1σ": (15.0, 900.3)},
        axis_band=(1065, 1095), axis_x=(210, 1415), years=list(range(2017, 2029)),
        yaxis_band=(195, 225), yaxis_y=(470, 1040),
        rbezel_band=(1410, 1465), rbezel_y=(470, 1040),
        series_x=(205, 1280), vmax=30.3, dark=105,
        exclude=[(845, 470, 1015, 503), (325, 1008, 505, 1040), (1290, 920, 1400, 965)],
        gdot_box=(1250, 900, 1300, 960),
        start="2016-11-17", end="2026-11-17"),
    "img2": dict(
        grid_vals=[32.0, 28.0, 24.0, 20.0], grid_y0=[327.1, 484.2, 643.1, 843.0], grid_x0=200,
        grid_x=(200, 1420), grid_x0_map={20.0: 1100}, slope0=0.044,
        refs={"+1σ": (26.9, 525.2), "mean": (23.7, 657.3), "-1σ": (20.4, 789.2)},
        axis_band=(945, 1025), axis_x=(160, 1430), years=list(range(2017, 2027)),
        yaxis_band=(140, 205), yaxis_y=(340, 945),
        rbezel_band=(1425, 1475), rbezel_y=(380, 960),
        series_x=(152, 1432), vmax=31.8, dark=115,
        exclude=[],
        gdot_box=(1400, 870, 1445, 930),
        start=None, end="2026-11-09"),
    "img3": dict(
        grid_vals=[24.0, 22.0, 20.0, 18.0, 16.0, 14.0], grid_y0=[397.6, 502.1, 606.8, 711.3, 816.3, 921.4], grid_x0=250,
        grid_x=(240, 1415), slope0=0.015,
        refs={"+1σ": (21.3, 536.6), "mean": (19.2, 650.2), "-1σ": (17.0, 763.8)},
        axis_band=(1010, 1040), axis_x=(225, 1415), years=list(range(2017, 2027)),
        yaxis_band=(210, 240), yaxis_y=(400, 1010),
        rbezel_band=(1425, 1470), rbezel_y=(420, 980),
        series_x=(222, 1420), vmax=23.8, dark=115,
        exclude=[],
        gdot_box=(1395, 700, 1435, 745),
        start=None, end="2026-11-09"),
    "img4": dict(
        grid_vals=[32.0, 28.0, 24.0, 16.0, 12.0], grid_y0=[459.7, 552.6, 647.9, 843.9, 944.6], grid_x0=320,
        grid_x=(310, 1380), slope0=0.005,
        refs={"+1σ": (23.5, 659.8), "mean": (19.3, 763.2), "-1σ": (15.0, 868.5)},
        axis_band=(1030, 1060), axis_x=(265, 1320), years=list(range(2017, 2027)),
        yaxis_band=(255, 310), yaxis_y=(470, 1030),
        rbezel_band=(1425, 1480), rbezel_y=(480, 980),
        series_x=(270, 1393), vmax=31.8, dark=115,
        exclude=[(1320, 985, 1420, 1080)],
        gdot_box=(1370, 840, 1405, 890),
        start=None, end="2026-11-09"),
}


def load(name):
    im = Image.open(CH / f"{name}.jpg").convert("RGB")
    a = np.asarray(im).astype(float)
    g = a.mean(axis=2)
    sat = a.max(axis=2) - a.min(axis=2)
    gb = a[:, :, 1] - a[:, :, 2]   # G - B: ~40 on olive green text/dashes, ~0 on neutral black line
    gr = a[:, :, 1] - a[:, :, 0]
    return im, g, sat, gb, gr


def dips(prof, prom=2.0, dist=6):
    base = np.convolve(prof, np.ones(15) / 15, mode="same")
    d = base - prof
    pk, _ = find_peaks(d, prominence=prom, distance=dist)
    res = []
    for p in pk:
        lo, hi = max(p - 2, 0), min(p + 3, len(d))
        w = np.clip(d[lo:hi], 0, None)
        c = (np.arange(lo, hi) * w).sum() / w.sum() if w.sum() > 0 else p
        res.append((c, d[p]))
    return res


def robust_line(x, y, it=3, tol=1.5):
    x, y = np.asarray(x, float), np.asarray(y, float)
    m = np.ones(len(x), bool)
    for _ in range(it):
        c = np.polyfit(x[m], y[m], 1)
        r = y - np.polyval(c, x)
        m = np.abs(r) < max(tol, 2.5 * np.std(r[m]))
    return c, m


def track_hline(g, x0, y0, xr, hw=12, step=30, win=3.5, slope0=0.0, gb=None, max_gb=18.0, max_strength=None):
    """Track a horizontal line from (x0, y0) both directions."""
    pts = []
    for direction in (1, -1):
        y_pred, x = y0, x0
        hist = []
        cc = None
        while xr[0] <= x <= xr[1]:
            lo = int(round(y_pred)) - 20
            strip = g[lo:lo + 41, x - hw:x + hw]
            prof = np.median(strip, axis=1)
            cand = []
            for c, s in dips(prof, prom=1.5):
                yy = lo + c
                if abs(yy - y_pred) > win:
                    continue
                if max_strength is not None and s >= max_strength:
                    continue
                if gb is not None:
                    r0, r1 = int(round(yy)) - 1, int(round(yy)) + 2
                    if np.median(gb[r0:r1, x - hw:x + hw]) >= max_gb:
                        continue
                cand.append((yy, s))
            if cand:
                c, s = min(cand, key=lambda t: abs(t[0] - y_pred))
                hist.append((x, c))
                pts.append((x, c))
                if len(hist) >= 3:
                    cc = np.polyfit([h[0] for h in hist[-6:]], [h[1] for h in hist[-6:]], 1)
                    y_pred = np.polyval(cc, x + direction * step)
                else:
                    y_pred = c + direction * step * slope0
            else:
                y_pred += direction * step * (cc[0] if cc is not None else slope0)
            x += direction * step
    return sorted(set(pts))


def axis_line(g, band, xr):
    """RANSAC straight line through local darkness peaks in axis_band (ignores digit labels below)."""
    pts = []
    for x in range(xr[0], xr[1], 3):
        col = g[band[0]:band[1], x]
        pk, _ = find_peaks(255 - col, height=90, distance=5)
        for p in pk:
            pts.append((x, band[0] + p))
    pts = np.array(pts, float)
    rng = np.random.default_rng(0)
    best_in, best_c = -1, None
    for _ in range(500):
        i, j = rng.choice(len(pts), 2, replace=False)
        if abs(pts[i, 0] - pts[j, 0]) < 100:
            continue
        c = np.polyfit(pts[[i, j], 0], pts[[i, j], 1], 1)
        inl = np.abs(pts[:, 1] - np.polyval(c, pts[:, 0])) < 2.0
        if inl.sum() > best_in:
            best_in = int(inl.sum())
            best_c = c
    inl = np.abs(pts[:, 1] - np.polyval(best_c, pts[:, 0])) < 2.0
    c = np.polyfit(pts[inl, 0], pts[inl, 1], 1)
    return c, pts[inl, 0], pts[inl, 1]


def ticks(g, c_axis, xr, n_expected):
    xs = np.arange(xr[0], xr[1])
    dark = np.array([255 - np.mean([g[int(round(np.polyval(c_axis, x) + k)), x] for k in range(1, 6)]) for x in xs])
    base = pd.Series(dark).rolling(41, center=True, min_periods=1).median().values
    d = dark - base
    pk, pr = find_peaks(d, prominence=12, distance=60)
    if len(pk) > n_expected:
        order = np.argsort(pr["prominences"])[::-1][:n_expected]
        pk = np.sort(pk[order])
    out = []
    for p in pk:
        lo, hi = max(p - 3, 0), min(p + 4, len(d))
        w = np.clip(d[lo:hi], 0, None)
        out.append(xs[lo] + (np.arange(hi - lo) * w).sum() / w.sum())
    return np.array(out), d


def vline(g, band, yr):
    xs, ys = [], []
    for y in range(yr[0], yr[1], 4):
        row = g[y, band[0]:band[1]]
        rs = np.convolve(row, np.ones(3) / 3, mode="same")
        i = int(np.argmin(rs[1:-1])) + 1
        if rs[i] < 150:
            xs.append(band[0] + i); ys.append(y)
    c, m = robust_line(ys, xs)
    return np.array(xs)[m], np.array(ys)[m]


def right_bezel(g, band, yr):
    xs, ys = [], []
    for y in range(yr[0], yr[1], 10):
        row = g[y, band[0]:band[1]]
        k = np.where(row < 100)[0]
        if len(k):
            xs.append(band[0] + k[0]); ys.append(y)
    _, m = robust_line(ys, xs)
    return np.array(xs)[m], np.array(ys)[m]


class Proj:
    def __init__(self, scale):
        self.cx, self.cy, self.s = scale

    def P(self, x, y):
        x = (np.asarray(x, float) - self.cx) / self.s
        y = (np.asarray(y, float) - self.cy) / self.s
        return np.stack([x, y, np.ones_like(x)], axis=-1)

    def fit(self, gx, gy, gv, tx, ty, tt, ax, ay, rx, ry):
        Pg = self.P(gx, gy)
        A = np.hstack([Pg, -gv[:, None] * Pg])
        _, _, vt = np.linalg.svd(A)
        h = vt[-1]
        h2, h3 = h[:3], h[3:]
        s = np.sign(h3[2]); h2, h3 = h2 * s, h3 * s
        nrm = h3[2]; h2, h3 = h2 / nrm, h3 / nrm
        Pt, Pa, Pr = self.P(tx, ty), self.P(ax, ay), self.P(rx, ry)
        w_axis = np.sqrt(len(tx) / max(len(ax), 1))
        A1 = np.hstack([Pt, np.zeros((len(tx), 1))])
        b1 = tt * (Pt @ h3)
        A2 = np.hstack([Pa, -(Pa @ h3)[:, None]]) * w_axis
        b2 = np.zeros(len(ax))
        sol, *_ = np.linalg.lstsq(np.vstack([A1, A2]), np.concatenate([b1, b2]), rcond=None)
        self.h1, self.h2, self.h3, self.T = sol[:3], h2, h3, sol[3]
        # Joint LM refinement including right vertical bezel constraint
        T_r0 = float(np.median((Pr @ self.h1) / (Pr @ self.h3)))
        s_v = abs(1.0 / (self.tv(self.cx, self.cy + 1)[1] - self.tv(self.cx, self.cy)[1]))
        s_t = abs(1.0 / (self.tv(self.cx + 1, self.cy)[0] - self.tv(self.cx, self.cy)[0]))
        p0 = np.concatenate([self.h1, self.h2, self.h3[:2], [self.T, T_r0]])

        def res(p):
            h1_, h2_, h3_ = p[0:3], p[3:6], np.array([p[6], p[7], 1.0])
            TL, TR = p[8], p[9]
            rg = ((Pg @ h2_) / (Pg @ h3_) - gv) * s_v
            rt = ((Pt @ h1_) / (Pt @ h3_) - tt) * s_t
            ra = ((Pa @ h1_) / (Pa @ h3_) - TL) * s_t
            rr = ((Pr @ h1_) / (Pr @ h3_) - TR) * s_t
            return np.concatenate([
                rg / np.sqrt(len(rg)),
                rt / np.sqrt(len(rt)),
                ra / np.sqrt(len(ra)),
                rr / np.sqrt(len(rr)),
            ])

        opt = least_squares(res, p0, method="lm").x
        self.h1, self.h2, self.h3, self.T, self.T_r = opt[0:3], opt[3:6], np.array([opt[6], opt[7], 1.0]), float(opt[8]), float(opt[9])
        return self

    def tv(self, x, y):
        p = self.P(x, y)
        w = p @ self.h3
        return (p @ self.h1) / w, (p @ self.h2) / w

    def inv(self, t, v):
        H = np.vstack([self.h1, self.h2, self.h3])
        q = np.linalg.solve(H, np.array([t, v, 1.0]))
        q = q / q[2]
        return q[0] * self.s + self.cx, q[1] * self.s + self.cy


def year_frac_to_date(t):
    t = np.asarray(t, float)
    yr = np.floor(t).astype(int)
    out = []
    for y, tt in zip(yr, t):
        a = pd.Timestamp(f"{y}-01-01"); b = pd.Timestamp(f"{y + 1}-01-01")
        out.append(a + (b - a) * (tt - y))
    return pd.DatetimeIndex(out)


def date_to_year_frac(d):
    d = pd.DatetimeIndex(d)
    a = pd.to_datetime([f"{y}-01-01" for y in d.year]); b = pd.to_datetime([f"{y + 1}-01-01" for y in d.year])
    return d.year + (d - a) / (b - a)


def vert_conn(mask):
    """True where pixel belongs to a vertical run of >=5 px (series line), False for thin horizontal dots."""
    m = mask.astype(np.int16)
    s = m.copy()
    for k in (1, 2, 3):
        s[k:] += m[:-k]; s[:-k] += m[k:]
    return s >= 5


def run(name):
    c = CFG[name]
    im, g, sat, gb, gr = load(name)
    H, W = g.shape
    # 1 gridlines (gray only: filter out green dashes & thick dark lines)
    gx, gy, gv, glines = [], [], [], {}
    for v, y0 in zip(c["grid_vals"], c["grid_y0"]):
        x0 = c.get("grid_x0_map", {}).get(v, c["grid_x0"])
        pts = track_hline(g, x0, y0, c["grid_x"], slope0=c["slope0"], gb=gb, max_gb=18.0, max_strength=40.0)
        if len(pts) < 5:
            print(name, "gridline lost", v); continue
        xx, yy = np.array(pts).T
        cl, m = robust_line(xx, yy)
        glines[v] = dict(n=int(m.sum()), coef=cl.tolist(), rms=float(np.std(yy[m] - np.polyval(cl, xx[m]))))
        gx += list(xx[m]); gy += list(yy[m]); gv += [v] * int(m.sum())
    gx, gy, gv = map(np.array, (gx, gy, gv))
    # refs (measured only for checking)
    refs = {}
    for k, (val, y0) in c["refs"].items():
        pts = track_hline(g, c["grid_x0"], y0, c["grid_x"], win=3.5, slope0=c["slope0"])
        refs[k] = (val, np.array(pts))
    # 2 axis + ticks
    ca, axs, ays = axis_line(g, c["axis_band"], c["axis_x"])
    tx, _ = ticks(g, ca, c["axis_x"], len(c["years"]))
    if len(tx) != len(c["years"]):
        print(name, "TICK COUNT MISMATCH", len(tx), "expected", len(c["years"]), np.round(tx, 1))
    ty = np.polyval(ca, tx)
    years = np.array(c["years"][:len(tx)], float)
    # 3 left y-axis & right bezel
    vx, vy = vline(g, c["yaxis_band"], c["yaxis_y"])
    rx, ry = right_bezel(g, c["rbezel_band"], c["rbezel_y"])
    pr = Proj((W / 2, H / 2, W / 2)).fit(gx, gy, gv, tx, ty, years, vx, vy, rx, ry)
    # residuals
    _, vg = pr.tv(gx, gy); res_g = vg - gv
    tt, _ = pr.tv(tx, ty); res_t = (tt - years) * 365.25
    _, v_axis = pr.tv(axs, ays)
    ref_meas = {}
    for k, (val, pts) in refs.items():
        if len(pts):
            _, vv = pr.tv(pts[:, 0], pts[:, 1])
            ref_meas[k] = dict(stated=val, measured_median=float(np.median(vv)), n=len(pts))
    # green dot measurement (verification only)
    gx0, gy0, gx1, gy1 = c["gdot_box"]
    gmask = (gr[gy0:gy1, gx0:gx1] > 18) & (gb[gy0:gy1, gx0:gx1] > 18)
    gys, gxs = np.where(gmask)
    gdot = None
    if len(gxs):
        gdx, gdy = float(gx0 + gxs.mean()), float(gy0 + gys.mean())
        gt, gv_d = pr.tv(gdx, gdy)
        gdot = dict(x=gdx, y=gdy, date=str(year_frac_to_date([gt])[0].date()), value=float(gv_d))
    # 5 series pixels (neutral dark gray/black only, exclude olive-green text/dashes)
    x0, x1 = c["series_x"]
    p_top_l = pr.inv(c["years"][0] - 0.3, c["vmax"])
    p_top_r = pr.inv(c["years"][-1] + 0.9, c["vmax"])
    c_top = np.polyfit([p_top_l[0], p_top_r[0]], [p_top_l[1], p_top_r[1]], 1)
    mask = (g < c["dark"]) & (sat < 30) & (gb < 18)
    cy_ax = np.polyfit(vy, vx, 1)
    yy_, xx_ = np.mgrid[0:H, 0:W]
    mask &= (xx_ >= x0) & (xx_ < x1)
    mask &= xx_ > np.polyval(cy_ax, yy_) + 3
    mask &= yy_ < np.polyval(ca, xx_) - 3
    mask &= yy_ > np.polyval(c_top, xx_)
    for (aa, bb, cc_, dd) in c["exclude"]:
        mask[bb:dd, aa:cc_] = False
    for k, (val, pts) in refs.items():
        if len(pts) >= 5:
            cl, _ = robust_line(pts[:, 0], pts[:, 1])
            yl = np.polyval(cl, xx_)
            band = np.abs(yy_ - yl) <= 2.5
            mask &= ~(band & ~vert_conn(mask))
    cols = []
    for x in range(x0, x1):
        ys = np.where(mask[:, x])[0]
        if len(ys) == 0:
            continue
        groups = np.split(ys, np.where(np.diff(ys) > 4)[0] + 1)
        grp = max(groups, key=len)
        if len(grp) < 2:
            continue
        cols.append((x, grp.min(), grp.max()))
    cols = np.array(cols, float)
    xs, top, bot = cols.T
    flat = (bot - top) <= np.percentile(bot - top, 20)
    lw = float(np.median((bot - top)[flat]))
    half = lw / 2
    yv = (top + bot) / 2
    for i in range(1, len(xs) - 1):
        if xs[i + 1] - xs[i - 1] > 3:
            continue
        if top[i] < min(top[i - 1], top[i + 1]) - 0.5:
            yv[i] = top[i] + half
        elif bot[i] > max(bot[i - 1], bot[i + 1]) + 0.5:
            yv[i] = bot[i] - half
    t_col, v_col = pr.tv(xs, yv)
    t_top, v_top = pr.tv(xs, top + half)
    t_bot, v_bot = pr.tv(xs, bot - half)
    ord_ = np.argsort(t_col)
    t_col_s, v_col_s = t_col[ord_], v_col[ord_]
    dcol = year_frac_to_date(t_col_s)
    # 6 weekly Fridays (strictly W-FRI)
    t_start = date_to_year_frac([pd.Timestamp(c["start"])])[0] if c["start"] else t_col_s.min()
    fr_start = year_frac_to_date([max(t_start, t_col_s.min())])[0].normalize()
    fr = pd.date_range(fr_start, c["end"], freq="W-FRI")
    tf = date_to_year_frac(fr)
    tf_ok = (tf >= t_col_s.min()) & (tf <= t_col_s.max())
    vf = np.interp(tf[tf_ok], t_col_s, v_col_s)
    ser = pd.Series(vf, index=fr[tf_ok], name="fwd_pe")

    info = dict(
        name=name, n_grid_pts=int(len(gx)),
        grid_res_rms=float(np.sqrt(np.mean(res_g ** 2))), grid_res_max=float(np.abs(res_g).max()),
        gridlines=glines, ticks_x=np.round(tx, 1).tolist(), tick_res_days=np.round(res_t, 1).tolist(),
        bottom_axis_v_median=float(np.median(v_axis)),
        yaxis_T=float(pr.T), yaxis_date=str(year_frac_to_date([pr.T])[0].date()),
        line_width_px=lw,
        px_per_unit=float(abs(1 / (pr.tv(W / 2, H / 2 + 1)[1] - pr.tv(W / 2, H / 2)[1]))),
        days_per_px=float((pr.tv(W / 2 + 1, H / 2)[0] - pr.tv(W / 2, H / 2)[0]) * 365.25),
        refs=ref_meas, green_dot=gdot,
        first_line_date=str(dcol.min().date()), last_line_date=str(dcol.max().date()),
        last_col_value=float(v_col_s[-1]),
        col_max=float(v_top.max()), col_max_date=str(year_frac_to_date([t_top[np.argmax(v_top)]])[0].date()),
        col_min=float(v_bot.min()), col_min_date=str(year_frac_to_date([t_bot[np.argmin(v_bot)]])[0].date()),
        weekly_n=int(len(ser)),
        weekly_start=str(ser.index[0].date()), weekly_end=str(ser.index[-1].date()),
        weekly_mean=float(ser.mean()), weekly_std=float(ser.std(ddof=1)),
        weekly_plus1s=float(ser.mean() + ser.std(ddof=1)),
        weekly_minus1s=float(ser.mean() - ser.std(ddof=1)),
        weekly_last=float(ser.iloc[-1]),
        weekly_max=float(ser.max()), weekly_max_date=str(ser.idxmax().date()),
        weekly_min=float(ser.min()), weekly_min_date=str(ser.idxmin().date()),
    )
    pd.DataFrame(dict(date=year_frac_to_date(t_col), t=t_col, v=v_col, v_top=v_top, v_bot=v_bot, x=xs, ytop=top, ybot=bot)).to_csv(OUTD / f"{name}_columns.csv", index=False)
    (OUTD / f"{name}_calib.json").write_text(json.dumps(info, indent=1, ensure_ascii=False))
    # overlay
    ov = im.copy(); dr = ImageDraw.Draw(ov)
    for x, y in zip(gx, gy):
        dr.point((x, y), fill=(0, 0, 255))
    for x, y in zip(tx, ty):
        dr.ellipse((x - 4, y - 4, x + 4, y + 4), outline=(255, 0, 0))
    for x, y in zip(vx, vy):
        dr.point((x, y), fill=(255, 0, 255))
    for x, y in zip(rx, ry):
        dr.point((x, y), fill=(255, 0, 255))
    for val in c["grid_vals"]:
        a_ = pr.inv(c["years"][0] - 0.2, val); b_ = pr.inv(c["years"][-1] + 0.6, val)
        dr.line([a_, b_], fill=(0, 160, 255), width=1)
    pts = [pr.inv(t, v) for t, v in zip(date_to_year_frac(ser.index), ser.values)]
    dr.line(pts, fill=(255, 0, 0), width=1)
    ov.save(TMP / f"{name}_overlay.png")
    return ser, info


if __name__ == "__main__":
    names = sys.argv[1:] or ["img1", "img2", "img3", "img4"]
    outname = {"img1": "fwdpe_img1_sox.csv", "img2": "fwdpe_img2.csv", "img3": "fwdpe_img3.csv", "img4": "fwdpe_img4_sox_check.csv"}
    sers = {}
    for n in names:
        s, info = run(n)
        sers[n] = s
        dest = (AGY if n != "img4" else OUTD) / outname[n]
        s.round(3).rename_axis("date").to_frame().to_csv(dest, date_format="%Y-%m-%d")
        print(json.dumps({k: info[k] for k in [
            "name", "n_grid_pts", "grid_res_rms", "tick_res_days", "bottom_axis_v_median",
            "refs", "green_dot", "weekly_n", "weekly_start", "weekly_end",
            "weekly_mean", "weekly_std", "weekly_last", "weekly_max", "weekly_max_date",
            "weekly_min", "weekly_min_date", "col_max", "col_max_date", "col_min", "col_min_date"
        ]}, ensure_ascii=False))
    if "img1" in sers and "img4" in sers:
        common = sers["img1"].index.intersection(sers["img4"].index)
        a1, a4 = sers["img1"].loc[common], sers["img4"].loc[common]
        diff = a4 - a1
        ov_stats = dict(
            n=int(len(common)), start=str(common[0].date()), end=str(common[-1].date()),
            corr=float(a1.corr(a4)), mean_diff=float(diff.mean()),
            mae=float(diff.abs().mean()), rms=float(np.sqrt((diff ** 2).mean())),
            max_abs=float(diff.abs().max()), max_abs_date=str(diff.abs().idxmax().date()),
        )
        (OUTD / "img1_vs_img4.json").write_text(json.dumps(ov_stats, indent=1))
        print("OVERLAP:", json.dumps(ov_stats))
