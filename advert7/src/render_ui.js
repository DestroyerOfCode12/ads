// Renders each unique laptop UI state to PNG with headless Chromium (Playwright).
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path');
(async () => {
  const root = path.resolve(__dirname, '..');
  const states = JSON.parse(fs.readFileSync(path.join(root, 'build/states.json')));
  const out = path.join(root, 'build/ui'); fs.mkdirSync(out, { recursive: true });
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1600, height: 1000 }, deviceScaleFactor: 1 });
  await page.goto('file://' + path.join(root, 'src/screen.html'));
  await page.evaluate(() => document.fonts.ready);
  const boxes = {};
  for (const { key, state } of states) {
    await page.evaluate(s => window.setState(s), state);
    await page.screenshot({ path: path.join(out, key + '.png') });
    boxes[key] = await page.evaluate(() => {
      const sel = { query: '#q1', place: '.place h4', title: '#r1 h3', snippet: '#r1 p', pinlabel: '#pin div', headline: '#hl' };
      const r = {};
      for (const [k, s] of Object.entries(sel)) {
        const e = document.querySelector(s); if (!e) continue;
        const rg = document.createRange(); rg.selectNodeContents(e); const b = rg.getBoundingClientRect();
        let vis = b.width > 0 && getComputedStyle(e).visibility !== 'hidden';
        for (let n = e; n && n !== document.body; n = n.parentElement) {
          const cs = getComputedStyle(n); if (cs.display === 'none' || parseFloat(cs.opacity) < 0.5) vis = false;
        }
        if (vis) r[k] = [b.left, b.top, b.right, b.bottom];
      }
      return r;
    });
  }
  fs.writeFileSync(path.join(root, 'build/ui_boxes.json'), JSON.stringify(boxes));
  // phone (mobile site)
  const ph = await browser.newPage({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2 });
  await ph.goto('file://' + path.join(root, 'src/phone.html'));
  await ph.evaluate(() => document.fonts.ready);
  await ph.screenshot({ path: path.join(root, 'build/phone_ui.png') });
  await browser.close();
  console.log('rendered', states.length);
})();
