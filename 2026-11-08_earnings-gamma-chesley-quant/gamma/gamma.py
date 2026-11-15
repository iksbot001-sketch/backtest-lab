"""AI 전쟁 덱용 이익 감마(성장률의 변화) 계산. 감마 = 이익·매출 성장률(전년 동기 대비)의 분기 변화 a = g(t) − g(t−1).
원자료: EODHD 펀더멘털·전망 추세(~/agent-fund-data/eodhd, 2026-11-08 수집), GOOGL 부문 매출은 10-Q/10-K 원문(googl_work),
MSFT Azure 성장률은 실적 보도자료 원문(msft_work/compact_tables.txt). 출력: gamma.json"""
import gzip, json, re, glob
from pathlib import Path

D = Path.home() / 'agent-fund-data/eodhd'
AW = Path.home() / 'earnings-tracker/fin_sheets/ai_war'
OUT = Path(__file__).with_name('gamma.json')


def load(sub, t):
    return json.load(gzip.open(D / sub / f'{t}.US.json.gz', 'rt'))


def yoy(series):
    """series: [(분기말, 값)] 정렬. 4분기 전 대비 성장률."""
    d = dict(series); ks = sorted(d)
    return [(k, d[k] / d[ks[i - 4]] - 1) for i, k in enumerate(ks) if i >= 4]


def accel(g):
    return [(k, v - g[i - 1][1]) for i, (k, v) in enumerate(g) if i >= 1]


def company(t):
    f = load('fund', t)
    q = f['Financials']['Income_Statement']['quarterly']
    ks = sorted(q)[-13:]
    rev = [(k, float(q[k]['totalRevenue'])) for k in ks]
    oi = [(k, float(q[k]['operatingIncome'])) for k in ks]
    oth = [(k, float(q[k]['totalOtherIncomeExpenseNet'] or 0)) for k in ks]
    eh = f['Earnings']['History']
    eps = [(k, eh[k]['epsActual']) for k in sorted(eh) if eh[k]['epsActual'] is not None][-13:]
    return dict(rev=rev, oi=oi, other=oth, eps=eps)


def consensus(t, rev_hist, eps_hist):
    tr = load('trends', t)
    cur = {}
    for x in tr:  # 기간마다 가장 늦은 날짜 = 지금의 0q·+1q·0y·+1y
        p = x['period']
        if p in ('0q', '+1q', '0y', '+1y') and (p not in cur or x['date'] > cur[p]['date']):
            cur[p] = x
    out = {}
    rv, ep = dict(rev_hist), dict(eps_hist)
    for p in ('0q', '+1q'):
        x = cur[p]; dt = x['date']
        ya = f'{int(dt[:4]) - 1}{dt[4:]}'
        r = float(x['revenueEstimateAvg']); e = float(x['earningsEstimateAvg'])
        out[p] = dict(date=dt, rev_est=r, rev_year_ago=rv.get(ya), rev_g=(r / rv[ya] - 1) if ya in rv else None,
                      eps_est=e, eps_year_ago=ep.get(ya), eps_g=(e / ep[ya] - 1) if ya in ep else None,
                      rev_g_vendor=float(x['revenueEstimateGrowth'] or 'nan'))
    for p in ('0q', '+1q', '0y', '+1y'):
        x = cur[p]
        c, d90 = float(x['epsTrendCurrent']), float(x['epsTrend90daysAgo'])
        out.setdefault(p, {}).update(date=x['date'], eps_now=c, eps_90d=d90, rev90=c / d90 - 1,
                                      up30=float(x['epsRevisionsUpLast30days'] or 0),
                                      down30=float(x['epsRevisionsDownLast30days'] or 0),
                                      fy_rev_g=float(x['revenueEstimateGrowth'] or 'nan') if p in ('0y', '+1y') else None,
                                      fy_eps_g=float(x['earningsEstimateGrowth'] or 'nan') if p in ('0y', '+1y') else None)
    return out


def googl_segments():
    """10-Q 첫 표: [전년 분기, 당분기, (전년 누적, 당해 누적)]. 10-K: [전년, 당해]. 4분기 = 연간 − 3분기 누적."""
    seg = {n: {} for n in ('search', 'youtube', 'cloud', 'total')}
    names = {'Google Search & other': 'search', 'YouTube ads': 'youtube', 'Google Cloud': 'cloud', 'Total revenues': 'total'}
    ann, ytd9 = {n: {} for n in seg}, {n: {} for n in seg}
    for f in sorted(glob.glob(str(AW / 'googl_work/0001652044*.txt'))):
        pe = re.search(r'goog-(\d{8})', f).group(1); y, md = int(pe[:4]), pe[4:]
        lines = open(f).read().splitlines()
        for name, key in names.items():
            for l in lines:
                if l.startswith(name + ' |'):
                    n = [int(x.replace(',', '')) for x in re.findall(r'\d[\d,]*\d', l)]
                    if len(n) < 2: continue
                    if md == '1231':
                        ann[key][y - 1], ann[key][y] = n[0], n[1]
                    else:
                        q = {'0331': '03-31', '0630': '06-30', '0930': '09-30'}[md]
                        seg[key][f'{y - 1}-{q}'], seg[key][f'{y}-{q}'] = n[0], n[1]
                        if md == '0930': ytd9[key][y - 1], ytd9[key][y] = n[2], n[3]
                    break
    for key in seg:
        for y in ann[key]:
            if y in ytd9[key]:
                seg[key][f'{y}-12-31'] = ann[key][y] - ytd9[key][y]
    return {k: sorted(v.items()) for k, v in seg.items()}


def msft_azure():
    """보도자료 문구의 Azure(및 기타 클라우드) 성장률. 파일 안 순서 = 분기 순서. 2025년 3월 분기는 파일에 문구가 없어 비움."""
    txt = (AW / 'msft_work/compact_tables.txt').read_text().splitlines()
    hdr, rows = None, []
    for l in txt:
        m = re.match(r'(Three Months Ended September 30, |Year Ended June 30, )?\| ?(\d{4}) \| (\d{4})', l) or \
            re.match(r'(Three Months Ended September 30, |Year Ended June 30, )?(\d{4}) \| (\d{4})', l)
        if m and hdr is None or (m and l.startswith(('Three', 'Year', '20'))):
            hdr = l
        a = re.search(r'Azure(?: and other cloud services)? revenue (?:growth of|increased) (\d+)%', l)
        if a and (not rows or rows[-1][0] != hdr):
            rows.append((hdr, int(a.group(1))))
    return rows


res = {}
for t in ('MSFT', 'GOOGL'):
    c = company(t)
    g = {k: yoy(c[k]) for k in ('rev', 'oi', 'eps')}
    res[t] = dict(raw=c, g=g, a={k: accel(v) for k, v in g.items()}, cons=consensus(t, c['rev'], c['eps']))
seg = googl_segments()
res['GOOGL']['seg_g'] = {k: yoy(v) for k, v in seg.items()}
res['GOOGL']['seg_a'] = {k: accel(v) for k, v in res['GOOGL']['seg_g'].items()}
res['GOOGL']['seg_raw'] = seg
res['MSFT']['azure_rows'] = msft_azure()
OUT.write_text(json.dumps(res, indent=1, ensure_ascii=False))

pct = lambda v: f'{v * 100:5.1f}' if v is not None else '  -  '
for t in ('MSFT', 'GOOGL'):
    r = res[t]; print('=====', t)
    for k in ('rev', 'oi', 'eps'):
        print(f'{k:4s} g', ' '.join(f'{d[2:7]}:{pct(v)}' for d, v in r['g'][k][-8:]))
        print(f'{k:4s} a', ' '.join(f'{d[2:7]}:{pct(v)}' for d, v in r['a'][k][-7:]))
    for p, x in r['cons'].items():
        print(p, {k: (round(v, 4) if isinstance(v, float) else v) for k, v in x.items()})
for k, v in res['GOOGL']['seg_g'].items():
    print('seg', k, ' '.join(f'{d[2:7]}:{pct(x)}' for d, x in v))
print('azure', res['MSFT']['azure_rows'])
