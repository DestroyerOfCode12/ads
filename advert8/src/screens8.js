// Screen textures for advert 8: laptop shows the website all night; phone gets an email notification.
const { chromium } = require('playwright'); const fs = require('fs'), path = require('path');
const root = path.resolve(__dirname, '..'); const T = JSON.parse(fs.readFileSync(path.join(root, 'build/timing.json')));
(async () => {
  const b = await chromium.launch();
  const lp = await b.newPage({ viewport: { width: 1600, height: 1000 } });
  await lp.goto('file://' + path.join(root, 'src/screen.html')); await lp.evaluate(() => document.fonts.ready);
  await lp.evaluate(s => setState(s), { scene: 'site', load: 1 });
  const ld = path.join(root, 'build/tex/laptop'); fs.mkdirSync(ld, { recursive: true });
  const one = path.join(ld, 'l_0000.png'); await lp.screenshot({ path: one });
  for (let f = 1; f < T.N3D; f++) fs.copyFileSync(one, path.join(ld, 'l_' + String(f).padStart(4, '0') + '.png'));
  const boxes = {};
  boxes.headline = await lp.evaluate(() => { const r = document.createRange(); r.selectNodeContents(document.getElementById('hl')); const b = r.getBoundingClientRect(); return [b.left, b.top, b.right, b.bottom]; });
  const pp = await b.newPage({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 3 });
  await pp.goto('file://' + path.join(root, 'src/phone_lock8.html')); await pp.evaluate(() => document.fonts.ready);
  const pd = path.join(root, 'build/tex/phone'); fs.mkdirSync(pd, { recursive: true });
  let last = null;
  for (let f = 0; f < T.N3D; f++) {
    const s = { wake: Math.max(0, Math.min(1, (f - T.WAKE) / 6)) * (f < T.S3[0] ? 1 : 0), note: Math.max(0, Math.min(1, (f - T.NOTE) / 9)) };
    const k = JSON.stringify(s), out = path.join(pd, 'p_' + String(f).padStart(4, '0') + '.png');
    if (k === last) { fs.copyFileSync(path.join(pd, 'p_' + String(f - 1).padStart(4, '0') + '.png'), out); continue; }
    await pp.evaluate(s => setState(s), s); await pp.screenshot({ path: out }); last = k;
  }
  boxes.note = await pp.evaluate(() => { const o = {}; for (const id of ['nt', 'nb']) { const r = document.createRange(); r.selectNodeContents(document.getElementById(id)); const b = r.getBoundingClientRect(); o[id] = [b.left, b.top, b.right, b.bottom]; } return o; });
  fs.writeFileSync(path.join(root, 'build/screen_boxes.json'), JSON.stringify(boxes));
  await b.close(); console.log('screens ok');
})();
