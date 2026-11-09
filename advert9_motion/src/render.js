// Renders motion.html frame by frame with sub frame motion blur (4 samples, 180 degree shutter).
// node src/render.js [first last] [--frames 1,2,3] [--samples 4]
const { chromium } = require('playwright'); const fs = require('fs'), path = require('path');
const root = path.resolve(__dirname, '..'); const out = path.join(root, 'build/sub'); fs.mkdirSync(out, { recursive: true });
const args = process.argv.slice(2);
let frames = []; const fi = args.indexOf('--frames');
if (fi >= 0) frames = args[fi + 1].split(',').map(Number); else { const a = +(args[0] || 0), b = +(args[1] || 449); for (let f = a; f <= b; f++) frames.push(f); }
const si = args.indexOf('--samples'); const S = si >= 0 ? +args[si + 1] : 4;
(async () => {
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1080, height: 1920 } });
  await p.goto('file://' + path.join(root, 'src/motion.html')); await p.evaluate(() => document.fonts.ready);
  for (const f of frames) for (let s = 0; s < S; s++) {
    const t = S === 1 ? f : f + (s + 0.5) / S * 0.5 - 0.25;
    await p.evaluate(t => render(t), t);
    await p.screenshot({ path: path.join(out, `f${String(f).padStart(4, '0')}_${s}.png`) });
  }
  await b.close(); console.log('rendered', frames.length, 'frames x', S);
})();
