// Captures city.html?render frame by frame (deterministic, time driven) with optional sub frame motion blur.
// node src/render.js first last [--samples N] | --frames a,b,c
const { chromium } = require('playwright'); const http = require('http'); const fs = require('fs'); const path = require('path');
const root = path.resolve(__dirname, '..'); const out = path.join(root, 'build/sub'); fs.mkdirSync(out, { recursive: true });
const args = process.argv.slice(2); let frames = [];
const fi = args.indexOf('--frames'); if (fi >= 0) frames = args[fi + 1].split(',').map(Number); else { for (let f = +args[0]; f <= +args[1]; f++) frames.push(f); }
const si = args.indexOf('--samples'); const S = si >= 0 ? +args[si + 1] : 2;
const types = { '.html': 'text/html', '.js': 'text/javascript', '.json': 'application/json' };
const server = http.createServer((q, r) => { const u = decodeURIComponent(q.url.split('?')[0]); const p = path.join(root, u === '/' ? 'src/office.html' : u.startsWith('/node_modules') ? u : path.join('src', u));
  fs.readFile(p, (e, d) => { if (e) { r.writeHead(404); r.end(); return; } r.writeHead(200, { 'Content-Type': types[path.extname(p)] || 'application/octet-stream' }); r.end(d); }); });
server.listen(0, async () => {
  const port = server.address().port;
  const b = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const p = await b.newPage({ viewport: { width: 1080, height: 1920 } });
  p.on('pageerror', e => console.error('PAGE ERROR', e.message)); p.on('console', m => { if (m.type() === 'error') console.error('CONSOLE', m.text()); });
  await p.goto(`http://127.0.0.1:${port}/?render`); await p.waitForFunction(() => window.ready === true, null, { timeout: 120000 });
  await p.evaluate(() => document.fonts.ready);
  const t0 = Date.now();
  for (const f of frames) for (let s = 0; s < S; s++) {
    const t = S === 1 ? f : f + (s + 0.5) / S * 0.5 - 0.25;
    await p.evaluate(t => window.renderFrame(t), t);
    await p.screenshot({ path: path.join(out, `f${String(f).padStart(4, '0')}_${s}.png`) });
  }
  console.log('rendered', frames.length, 'x', S, 'in', ((Date.now() - t0) / 1000).toFixed(1), 's');
  await b.close(); server.close();
});
