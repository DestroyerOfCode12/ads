// Dumps every piece of visible copy from the UI mockups (all scenes) for the copy and claims scan.
const { chromium } = require('playwright'); const path = require('path');
(async () => {
  const root = path.resolve(__dirname, '..'); const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1600, height: 1000 } });
  await p.goto('file://' + path.join(root, 'src/screen.html'));
  const out = [];
  for (const s of [{ scene: 'home', q: 'web design Midrand' }, { scene: 'results', q: 'web design Midrand', reveal: 1, pin: 1 }, { scene: 'site', load: 1 }]) {
    await p.evaluate(s => setState(s), s); out.push('[' + s.scene + '] ' + (await p.evaluate(() => document.body.innerText)).replace(/\s*\n\s*/g, ' | '));
  }
  await p.goto('file://' + path.join(root, 'src/phone.html'));
  out.push('[phone] ' + (await p.evaluate(() => document.body.innerText)).replace(/\s*\n\s*/g, ' | '));
  console.log(out.join('\n')); await b.close();
})();
