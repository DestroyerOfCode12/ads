// Safe zone check: for every frame, every visible, readable text run must sit inside x 96..904, y 154..1536
// unless it is wholly off screen. Reports violations per text.
const { chromium } = require('playwright'); const path = require('path');
(async () => {
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1080, height: 1920 } });
  await p.goto('file://' + path.join(__dirname, 'needs.html')); await p.evaluate(() => document.fonts.ready);
  const res = await p.evaluate(() => {
    const SAFE = [96, 154, 904, 1536], out = {}, seen = {}; let prev = {};
    const visible = el => { let o = 1; for (let n = el; n && n !== document.body; n = n.parentElement) { const cs = getComputedStyle(n); if (cs.display === 'none' || cs.visibility === 'hidden') return 0; o *= parseFloat(cs.opacity); } return o; };
    for (let f = 0; f < 480; f++) {
      render(f);
      const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
      const runs = {};
      while (walker.nextNode()) {
        const tn = walker.currentNode; if (!tn.textContent.trim()) continue;
        const el = tn.parentElement; if (el.closest('script,style')) continue;
        if (visible(el) < 0.5) continue;
        const r = document.createRange(); r.selectNodeContents(tn); const b0 = r.getBoundingClientRect();
        const bb = { left: b0.left, top: b0.top, right: b0.right, bottom: b0.bottom };
        for (let n = el.parentElement; n && n !== document.body; n = n.parentElement) {     // clip to masks
          if (getComputedStyle(n).overflow === 'hidden') { const c = n.getBoundingClientRect(); bb.left = Math.max(bb.left, c.left); bb.top = Math.max(bb.top, c.top); bb.right = Math.min(bb.right, c.right); bb.bottom = Math.min(bb.bottom, c.bottom); }
        }
        bb.width = bb.right - bb.left; bb.height = bb.bottom - bb.top;
        if (bb.width < 1 || bb.height < 14) continue;
        if (bb.right < 0 || bb.left > 1080 || bb.bottom < 0 || bb.top > 1920) continue;
        // group characters into their word/line container
        const key = ((el.closest('[id]') || el).id || '') + ':' + (el.closest('#ticker > div, .dw, .v1c') ? el.closest('#ticker > div, .dw, .v1c').textContent.slice(0, 16) : '');
        const k = runs[key] || (runs[key] = [1e9, 1e9, -1e9, -1e9]);
        k[0] = Math.min(k[0], bb.left); k[1] = Math.min(k[1], bb.top); k[2] = Math.max(k[2], bb.right); k[3] = Math.max(k[3], bb.bottom);
      }
      for (const [key, k] of Object.entries(runs)) {
        seen[key] = (seen[key] || 0) + 1;
        const pv = prev[key]; const moving = !pv || Math.max(...k.map((v, i) => Math.abs(v - pv[i]))) > 3;
        if (k[0] < SAFE[0] - 0.5 || k[1] < SAFE[1] || k[2] > SAFE[2] + 0.5 || k[3] > SAFE[3]) (out[(moving ? 'moving ' : 'SETTLED ') + key] = out[(moving ? 'moving ' : 'SETTLED ') + key] || []).push([f, k.map(Math.round)]);
      }
      prev = runs;
    }
    return { out, seen };
  });
  for (const [k, v] of Object.entries(res.out)) console.log('OUTSIDE', k, v.length, 'frames, e.g.', JSON.stringify(v.slice(0, 3)));
  console.log('text runs checked:', Object.keys(res.seen).length, '| runs with frames outside:', Object.keys(res.out).length);
  await b.close();
})();
