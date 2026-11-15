"""주가 오류 정제. (a) 하루 +50% 이상 튀었다가 10거래일 안에 원래 수준(±30%)으로 돌아오는 '튐'은 결측 처리 후 직전 값으로 채움.
(b) 하루 5배 이상 오른 날은 자료 단절로 보고 그날부터 결측(그 전에 상장폐지된 것처럼 처리, 진짜 급등이면 수익을 낮추는 보수적 처리). 하루 −80% 같은 급락은 실제 손실이 대부분이라 그대로 둔다."""
import numpy as np, pandas as pd

def clean(s):
    s = s.astype(float).copy(); v = s.values; n = len(v); fixed = 0
    for i in range(1, n):
        if not (np.isfinite(v[i]) and np.isfinite(v[i - 1]) and v[i - 1] > 0): continue
        r = v[i] / v[i - 1]
        if r > 1.5 or r < 1 / 1.5:
            base = v[i - 1]
            for j in range(i + 1, min(i + 11, n)):
                if np.isfinite(v[j]) and abs(v[j] / base - 1) < 0.3:
                    v[i:j] = np.nan; fixed += j - i; break
    s = pd.Series(v, index=s.index).ffill().where(s.notna() | pd.Series(v, index=s.index).notna())
    s[s.index > s.last_valid_index()] = np.nan if s.last_valid_index() is not None else np.nan
    w = s.values; brk = None
    for i in range(1, len(w)):
        if np.isfinite(w[i]) and np.isfinite(w[i - 1]) and w[i - 1] > 0 and w[i] / w[i - 1] >= 5: brk = i; break
    if brk is not None: s.iloc[brk:] = np.nan
    return s, fixed, (s.index[brk] if brk is not None else None)
