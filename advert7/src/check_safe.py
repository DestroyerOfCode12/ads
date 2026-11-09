"""Projects every readable text box (UI mockup and end card) into output pixels per frame
and reports any that leave the safe zone x 96..904, y 154..1536."""
import json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from composite import *

boxes = json.load(open(P('build/ui_boxes.json')))
fs = json.load(open(P('build/frame_states.json')))
MIN_H = 14  # px: text smaller than this on output is not readable, so not "important" at that moment
viol = []; checked = 0; readable = {}
# phone headline box in phone UI pixels (2x): "Your business, online"
PH_HEAD = [80, 330, 720, 500]
for f in range(T_END):
    if T_INS0 <= f < T_INS1: continue
    c = cam(f)
    items = [(k, H_LAP, b) for k, b in boxes[fs[str(f)]].items()]
    if f >= T_PHONE + 4: items.append(('phone_headline', H_PH, PH_HEAD))
    for k, hm, (x0, y0, x1, y1) in items:
        pts = plate_to_out(c, apply_h(hm, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]))
        h = np.hypot(*(pts[3] - pts[0]))
        if h < MIN_H: continue
        checked += 1; readable.setdefault(k, []).append(f)
        ok = (pts[:, 0].min() >= SAFE['x0'] and pts[:, 0].max() <= SAFE['x1'] and
              pts[:, 1].min() >= SAFE['y0'] and pts[:, 1].max() <= SAFE['y1'])
        if not ok: viol.append((f, k, pts.round().astype(int).tolist(), round(h, 1)))
for k, b in end_layout().items():
    checked += 1
    ok = b[0] >= SAFE['x0'] and b[2] <= SAFE['x1'] and b[1] >= SAFE['y0'] and b[3] <= SAFE['y1']
    print('end card %-5s box %s %s' % (k, tuple(round(v) for v in b), 'inside' if ok else 'OUTSIDE'))
    if not ok: viol.append(('end', k, b, 0))
for k, v in readable.items(): print('%-15s readable frames %d..%d (%d frames)' % (k, v[0], v[-1], len(v)))
print('checked', checked, 'box placements;', len(viol), 'outside the safe zone')
from collections import Counter
print('violations per item:', dict(Counter(v[1] for v in viol)))
seen = set()
for v in viol:
    if v[1] in seen: continue
    seen.add(v[1]); print('  first violation', v)
