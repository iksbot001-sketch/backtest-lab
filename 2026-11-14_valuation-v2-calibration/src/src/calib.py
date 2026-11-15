import sys, math
sys.path.insert(0, "src")
import engine as E
import pandas as pd, numpy as np
from multiprocessing import Pool

RT = dict(zip(range(2005, 2023), [.085,.089,.084,.086,.082,.085,.079,.075,.080,.080,.084,.081,.075,.086,.071,.056,.058,.098]))
REQ = ["rev0","rev1","rev2","rev3","m1","m2","m3","sc","mktcap","net_cash"]
CORE15 = "AAPL MSFT GOOGL AMZN META NVDA AVGO ORCL ADBE CRM NFLX V MA COST INTU".split()


def mk(row):
    return E.Seg(row["ticker"], [row["rev0"], row["rev1"], row["rev2"], row["rev3"]], [row["m1"], row["m2"], row["m3"]], 0.21, row["sc"])


def V(row, r, h):
    return E.value([mk(row)], r, h, lag=0.75, net_cash=row["net_cash"])


def hstar(row, r):
    mc = row["mktcap"]
    if V(row, r, 100) < mc: return 100.0, "hi"
    if V(row, r, 0.5) > mc: return 0.5, "lo"
    return E.bisect(lambda h: V(row, r, h), mc, 0.5, 100), ""


def work(row):
    row = dict(row); mc = row["mktcap"]; rt = RT[int(row["t"])]
    o = {}
    for h in (4, 8, 12, 20): o[f"VP{h}"] = V(row, 0.09, h) / mc
    o["VP4_rt"] = V(row, rt, 4) / mc
    o["h_star"], o["h_cap"] = hstar(row, 0.09)
    o["h_star_rt"], o["h_cap_rt"] = hstar(row, rt)
    return o


def work_mkt(a):
    row, h = a
    return V(row, 0.09, h) / row["mktcap"]


def md_table(tab, idx):
    t = tab.reset_index() if idx else tab
    f = lambda v: f"{v:.4g}" if isinstance(v, float) else str(v)
    L = ["| " + " | ".join(map(str, t.columns)) + " |", "|" + "---|" * len(t.columns)]
    for r in t.itertuples(index=False): L.append("| " + " | ".join(f(v) for v in r) + " |")
    return "\n".join(L)


def q3(s):
    return pd.qcut(s.rank(method="first"), 3, labels=["low", "mid", "high"])


def main():
    raw = pd.read_csv("data/inputs.csv")
    log = [f"raw rows: {len(raw)}"]
    bad = raw[REQ].isna().any(axis=1)
    bad2 = (~bad) & ((raw.rev2 <= 0) | (raw.rev3 <= 0) | (raw.rev1 <= 0) | (raw.mktcap <= 0) | (raw.sc <= 0))
    log.append(f"excluded missing required input: {int(bad.sum())}; excluded nonpositive rev/mktcap/sc: {int(bad2.sum())}")
    df = raw[~bad & ~bad2].reset_index(drop=True)
    rows = df.to_dict("records")
    with Pool() as p:
        res = p.map(work, rows, chunksize=50)
    panel = pd.concat([df, pd.DataFrame(res)], axis=1)
    log.append(f"observations used: {len(panel)}")
    log.append("by year: " + str(panel.groupby("t").size().to_dict()))
    # groups
    panel["roic_top"] = False
    for t, g in panel.groupby("t"):
        v = g["roic"].dropna()
        if len(v): panel.loc[v.index[v >= v.quantile(2 / 3)], "roic_top"] = True
    groups = {
        "all": panel.index == panel.index,
        "tech": panel.sector.isin(["Technology", "Communication Services"]).values,
        "high_roic": panel.roic_top.values,
        "core15": panel.ticker.isin(CORE15).values,
    }
    # T6
    hm = panel.groupby("t").h_star.median()
    with Pool() as p:
        vm = p.map(work_mkt, [(r, hm[int(r["t"])]) for r in panel.to_dict("records")], chunksize=50)
    panel["VP_mkt"] = vm
    panel.to_csv("out/panel.csv", index=False)
    log.append("sector counts: " + str(panel.sector.value_counts().to_dict()))
    log.append("core15 tickers present: " + str(sorted(set(panel.ticker) & set(CORE15))))

    md = []
    def emit(name, title, tab, idx=True):
        tab.to_csv(f"out/{name}.csv", index=idx)
        md.append(f"## {name} {title}\n\n" + md_table(tab, idx) + "\n")

    # T1
    t1 = []
    for col in ["VP4", "VP8", "VP12", "VP20", "VP4_rt"]:
        for gn, m in groups.items():
            g = panel[m]
            for t, gg in list(g.groupby("t")) + [("ALL", g)]:
                t1.append(dict(metric=col, group=gn, t=t, n=len(gg), pass_ge1=(gg[col] >= 1).mean(), pass_ge08=(gg[col] >= .8).mean()))
    t1 = pd.DataFrame(t1)
    emit("T1", "통과율 (VP>=1.0, >=0.8)", t1, False)
    # T2
    c = panel[panel.ticker.isin(CORE15)]
    t2a = c.pivot_table(index="ticker", columns="t", values="VP4").reindex(CORE15)
    t2b = c.pivot_table(index="ticker", columns="t", values="h_star").reindex(CORE15)
    emit("T2a", "대표15 VP4", t2a.round(3)); emit("T2b", "대표15 h_star", t2b.round(2))
    # T3
    t3 = []
    for col, cap in [("h_star", "h_cap"), ("h_star_rt", "h_cap_rt")]:
        for gn, m in groups.items():
            g = panel[m]
            for t, gg in list(g.groupby("t")) + [("ALL", g)]:
                x = gg[col]
                t3.append(dict(metric=col, group=gn, t=t, n=len(gg), p25=x.quantile(.25), median=x.median(), p75=x.quantile(.75),
                               hi_share=(gg[cap] == "hi").mean(), lo_share=(gg[cap] == "lo").mean()))
    emit("T3", "내재 반감기 분포", pd.DataFrame(t3), False)

    def predict(key, gm, ascending_low=True):
        out = []
        for gn in gm:
            g = panel[groups[gn]].dropna(subset=[key]).copy()
            rec = []
            for t, gg in g.groupby("t"):
                if len(gg) < 3: continue
                gg = gg.assign(tr=q3(gg[key]))
                for k in ("ex3", "ex5"):
                    s = gg.dropna(subset=[k])
                    if s.empty: continue
                    gm_ = s.groupby("tr", observed=True)[k].agg(["mean", "median", "count"])
                    if not {"low", "high"} <= set(gm_.index): continue
                    rec.append(dict(t=t, k=k, **{f"{b}_{st}": gm_.loc[b, st] for b in gm_.index for st in ("mean", "median", "count")},
                                    diff=gm_.loc["high", "mean"] - gm_.loc["low", "mean"]))
            r = pd.DataFrame(rec)
            for k in ("ex3", "ex5"):
                rk = r[r.k == k]
                if rk.empty: continue
                row = dict(sort_key=key, group=gn, ex=k, years=len(rk))
                for b in ("low", "mid", "high"):
                    row[f"{b}_mean_avg_over_years"] = rk[f"{b}_mean"].mean()
                    row[f"{b}_median_avg_over_years"] = rk[f"{b}_median"].mean()
                row["high_minus_low_avg"] = rk["diff"].mean()
                row["share_years_high_minus_low_pos"] = (rk["diff"] > 0).mean()
                out.append(row)
            r.to_csv(f"out/T_{key}_{gn}_byyear.csv", index=False)
        return pd.DataFrame(out)
    emit("T4a", "VP4 3분위 → 이후 초과수익 (해별 평균의 전체기간 평균)", predict("VP4", ["all", "tech"]), False)
    emit("T4b", "h_star 3분위 (low = 짧은 해자 가정)", predict("h_star", ["all", "tech"]), False)
    # T5
    t5 = []
    d = panel.dropna(subset=["ret5"])
    top = d[d.ret5 >= d.ret5.quantile(.9)]
    t5.append(dict(item="n_ret5_valid", value=len(d)))
    t5.append(dict(item="n_top10pct_ret5", value=len(top)))
    for th in (1.0, .8):
        t5.append(dict(item=f"top10pct: share VP4>={th}", value=(top.VP4 >= th).mean()))
        t5.append(dict(item=f"all valid: share VP4>={th}", value=(d.VP4 >= th).mean()))
    for lab, m in (("VP4>=1", d.VP4 >= 1), ("VP4<1", d.VP4 < 1)):
        t5.append(dict(item=f"{lab}: n", value=int(m.sum())))
        t5.append(dict(item=f"{lab}: median ret5", value=d[m].ret5.median()))
        t5.append(dict(item=f"{lab}: median ex5", value=d[m].ex5.median()))
    emit("T5", "놓친 종목", pd.DataFrame(t5), False)
    # T6
    tm = pd.DataFrame({"h_mkt": hm}); tm.index.name = "t"
    emit("T6a", "연도별 h_mkt (전체 h_star 중앙값)", tm.round(3))
    emit("T6b", "VP_mkt 3분위 → 이후 초과수익", predict("VP_mkt", ["all", "tech"]), False)

    open("out/REPORT.md", "w").write("# REPORT (계산 결과만, 해석 없음)\n\n" + "\n".join(md))
    open("out/_log.txt", "w").write("\n".join(log))
    print("\n".join(log))


if __name__ == "__main__":
    main()
