// Renders the phone and laptop screen image sequences (textures used inside the 3D scene).
const { chromium } = require('playwright'); const fs = require('fs'), path = require('path');
const root = path.resolve(__dirname, '..'); const T = JSON.parse(fs.readFileSync(path.join(root, 'build/timing.json')));
(async () => {
  const b = await chromium.launch();
  // ---------- laptop: website from advert 1 structure, loading in
  const lp = await b.newPage({ viewport: { width: 1600, height: 1000 } });
  await lp.goto('file://' + path.join(root, 'src/screen.html')); await lp.evaluate(() => document.fonts.ready);
  const ld = path.join(root, 'build/tex/laptop'); fs.mkdirSync(ld, { recursive: true });
  const boxes = {};
  for (let f = 0; f < T.S5[1]; f++) {
    if (f < T.S4[0]) { await lp.evaluate(() => { document.body.style.background='#000'; document.getElementById('win').style.visibility='hidden'; }); await lp.screenshot({ path: path.join(ld, 'l_' + String(f).padStart(4, '0') + '.png') }); continue; }
    await lp.evaluate(() => { document.getElementById('win').style.visibility='visible'; });
    const load = Math.max(0, Math.min(1, (f - T.SITE_LOAD) / 24));
    const prog = f < T.SITE_LOAD ? Math.min(0.85, (f - T.S4[0]) / 10 * 0.85) : (f < T.SITE_LOAD + 5 ? 0.85 + 0.15 * (f - T.SITE_LOAD) / 5 : 0);
    await lp.evaluate(s => setState(s), { scene: 'site', load, progress: prog });
    await lp.screenshot({ path: path.join(ld, 'l_' + String(f).padStart(4, '0') + '.png') });
  }
  boxes.headline = await lp.evaluate(() => { const r = document.createRange(); r.selectNodeContents(document.getElementById('hl')); const b = r.getBoundingClientRect(); return [b.left, b.top, b.right, b.bottom]; });
  // ---------- phone: lock screen, wakes, notification slides in
  const pp = await b.newPage({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 3 });
  await pp.goto('file://' + path.join(root, 'src/phone_lock.html')); await pp.evaluate(() => document.fonts.ready);
  const pd = path.join(root, 'build/tex/phone'); fs.mkdirSync(pd, { recursive: true });
  for (let f = 0; f < T.S5[1]; f++) {
    await pp.evaluate(s => setState(s), { wake: Math.max(0, Math.min(1, (f - T.WAKE) / 6)), note: Math.max(0, Math.min(1, (f - T.NOTE) / 9)) });
    await pp.screenshot({ path: path.join(pd, 'p_' + String(f).padStart(4, '0') + '.png') });
  }
  boxes.note = await pp.evaluate(() => { const out = {}; for (const id of ['nt', 'nb']) { const r = document.createRange(); r.selectNodeContents(document.getElementById(id)); const b = r.getBoundingClientRect(); out[id] = [b.left, b.top, b.right, b.bottom]; } return out; });
  fs.writeFileSync(path.join(root, 'build/screen_boxes.json'), JSON.stringify(boxes));
  await b.close(); console.log('screens ok');
})();
