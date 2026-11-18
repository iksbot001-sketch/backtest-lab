import json
from pathlib import Path
R = Path(__file__).resolve().parents[1]
t = (R / 'src' / 'report_template.html').read_text()
d = (R / 'out' / 'report.json').read_text()
(R / 'report.html').write_text(t.replace('/*DATA*/null', d))
print('ok', len(t) + len(d))
