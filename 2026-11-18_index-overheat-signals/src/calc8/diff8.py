import pandas as pd, numpy as np
a = pd.read_csv("out/windows_stats.csv"); a["combo"] = a["combo"].replace({"SP500 이격도": "S&P500 이격도"}); b = pd.read_csv("calc8/out/recalc.csv")
k = ["combo", "window", "same_start"]
m = a.merge(b, on=k, suffixes=("_o", "_n"))
print(len(a), len(b), len(m))
num = ["t12", "t12_half", "t3", "t3_half", "sh", "c60", "placebo", "cagr", "c60_cagr", "z_now"]
rows = []
for _, r in m.iterrows():
    d = {c: r[c + "_n"] - r[c + "_o"] for c in num}
    rows.append(dict(combo=r.combo, window=r.window, same_start=r.same_start, start_o=r.start_o, start_n=r.start_n, n_o=r.n_o, n_n=r.n_n,
        **{"d_" + c: d[c] for c in num}, ep_hot_o=r.ep_hot_o, ep_hot_n=r.ep_hot_n, ep_cold_o=r.ep_cold_o, ep_cold_n=r.ep_cold_n, verdict_o=r.verdict_o, verdict_n=r.verdict_n))
d = pd.DataFrame(rows); d.to_csv("calc8/out/diff_rows.csv", index=False)
pd.set_option("display.width", 250, "display.max_columns", 40, "display.max_rows", 200)
print(d[["d_" + c for c in num]].abs().max())
print(d[(d.start_o != d.start_n)][["combo", "window", "start_o", "start_n"]])
print(d[(d.ep_hot_o != d.ep_hot_n) | (d.ep_cold_o != d.ep_cold_n)][["combo", "window", "same_start", "ep_hot_o", "ep_hot_n", "ep_cold_o", "ep_cold_n"]])
print(d[(d.verdict_o != d.verdict_n)][["combo", "window", "same_start", "verdict_o", "verdict_n"]])
print(d[(d.d_t12.abs() > 0.01) | (d.d_t3.abs() > 0.01) | (d.d_t12_half.abs() > 0.01)| (d.d_t3_half.abs() > 0.01)][["combo","window","same_start","d_t12","d_t12_half","d_t3","d_t3_half"]])
print(d[(d.d_sh.abs() > 1e-6) | (d.d_placebo.abs() > 0.005)|(d.d_cagr.abs()>1e-6)][["combo","window","same_start","d_sh","d_placebo","d_cagr"]])
print(a[a.combo.str.contains("KOSDAQ PBR")][["combo","window","same_start","start","n","t12","t12_half","t3","ep_hot","ep_cold","verdict"]])
print(d[d.n_o!=d.n_n][["combo","window","n_o","n_n"]].head(5))
