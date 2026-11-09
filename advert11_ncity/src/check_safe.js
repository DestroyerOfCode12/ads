// Safe zone check for the 3D sign text (projected through the camera) and the end card text (DOM).
const { chromium } = require('playwright'); const http = require('http'); const fs = require('fs'); const path = require('path');
const root = path.resolve(__dirname, '..');
const server = http.createServer((q, r) => { const u = decodeURIComponent(q.url.split('?')[0]); const p = path.join(root, u === '/' ? 'src/city.html' : u.startsWith('/node_modules') ? u : path.join('src', u)); fs.readFile(p, (e, d) => { if (e) { r.writeHead(404); r.end(); return; } r.writeHead(200, { 'Content-Type': p.endsWith('.js') ? 'text/javascript' : 'text/html' }); r.end(d); }); });
server.listen(0, async () => {
  const b = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const p = await b.newPage({ viewport: { width: 1080, height: 1920 } });
  await p.goto(`http://127.0.0.1:${server.address().port}/?render`); await p.waitForFunction(() => window.ready === true);
  const SAFE = [96, 154, 904, 1536]; let out = 0, readable = 0, first = null;
  for (let f = 225; f < 315; f++) {
    const v = await p.evaluate(f => window.signBox(f), f);
    const xs = v.map(q => q[0]), ys = v.map(q => q[1]);
    if (Math.max(...ys) - Math.min(...ys) < 40) continue; readable++;
    if (Math.min(...xs) < SAFE[0] || Math.max(...xs) > SAFE[2] || Math.min(...ys) < SAFE[1] || Math.max(...ys) > SAFE[3]) { out++; if (!first) first = [f, xs.map(Math.round), ys.map(Math.round)]; }
  }
  console.log('sign text: readable frames', readable, '| frames outside the safe zone', out, first ? 'first: ' + JSON.stringify(first) : '');
  const end = await p.evaluate(() => { window.renderFrame(470); return ['logo', 'e1', 'e2', 'e3'].map(id => { const r = (id === 'logo' ? document.getElementById(id) : document.getElementById(id)).getBoundingClientRect(); const rg = document.createRange(); rg.selectNodeContents(document.getElementById(id)); const t = rg.getBoundingClientRect(); return [id, Math.round(t.left), Math.round(t.top), Math.round(t.right), Math.round(t.bottom)]; }); });
  for (const [id, l, t, r, bt] of end) console.log('end card', id, [l, t, r, bt], l >= 96 && r <= 904 && t >= 154 && bt <= 1536 ? 'inside' : 'OUTSIDE');
  await b.close(); server.close();
});
