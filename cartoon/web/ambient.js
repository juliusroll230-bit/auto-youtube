// ---------- Ruhige Dauerschleifen für den Split-Screen (Test seit 20.11.2026) ----------
// Unten im Bild läuft etwas Beruhigendes, oben das eigentliche Video. Alles selbst gezeichnet, keine fremden Clips.
// drawAmbient(ctx, art, t, w, h) zeichnet in den Bereich (0,0)-(w,h): "regen", "feuer" oder "pendel".
const AMB = (() => {
  const R = rng(4242);
  const drops = Array.from({ length: 170 }, () => ({ x: R(), y: R(), v: .9 + R() * .9, l: 30 + R() * 50, a: .15 + R() * .35 }));
  const glass = Array.from({ length: 70 }, () => ({ x: R(), y: R(), r: 3 + R() * 9 }));
  const slide = Array.from({ length: 7 }, () => ({ x: R(), p: R(), v: .05 + R() * .07, r: 7 + R() * 6 }));
  const lights = Array.from({ length: 26 }, () => ({ x: R(), y: .35 + R() * .6, r: 30 + R() * 70, c: ['#ffb347', '#ff6f91', '#6fd3ff', '#ffe08a', '#b58cff'][Math.floor(R() * 5)], p: R() * TAU }));
  const sparks = Array.from({ length: 46 }, () => ({ x: R() - .5, p: R(), v: .25 + R() * .35, s: 2 + R() * 4, w: R() * TAU }));
  const stars = Array.from({ length: 60 }, () => ({ x: R(), y: R() * .45, r: .8 + R() * 1.8, p: R() * TAU }));
  return { drops, glass, slide, lights, sparks, stars };
})();

function ambRegen(c, t, w, h) {
  const g = c.createLinearGradient(0, 0, 0, h); g.addColorStop(0, '#0d1630'); g.addColorStop(1, '#23143a');
  c.fillStyle = g; c.fillRect(0, 0, w, h);
  c.save(); c.filter = 'blur(18px)';   // Stadtlichter hinter der nassen Scheibe
  for (const L of AMB.lights) { c.globalAlpha = .35 + .2 * Math.sin(t * .7 + L.p); c.fillStyle = L.c; circle(c, L.x * w, L.y * h, L.r); c.fill(); }
  c.restore(); c.globalAlpha = 1;
  c.strokeStyle = 'rgba(190,210,255,1)'; c.lineCap = 'round';
  for (const d of AMB.drops) {   // Regen draußen: schräge, schnelle Striche
    const y = ((d.y + t * d.v) % 1.15) * h - 60, x = (d.x * w + y * .12) % w;
    c.globalAlpha = d.a; c.lineWidth = 2; c.beginPath(); c.moveTo(x, y); c.lineTo(x + d.l * .12, y + d.l); c.stroke();
  }
  for (const d of AMB.glass) {   // stehende Tropfen auf der Scheibe
    c.globalAlpha = .35; c.fillStyle = 'rgba(200,220,255,.5)'; circle(c, d.x * w, d.y * h, d.r); c.fill();
    c.globalAlpha = .7; c.fillStyle = '#fff'; circle(c, d.x * w - d.r * .3, d.y * h - d.r * .35, d.r * .28); c.fill();
  }
  for (const d of AMB.slide) {   // Tropfen, die langsam herunterlaufen und eine Spur ziehen
    const y = ((d.p + t * d.v) % 1.2) * h - 40, x = d.x * w + Math.sin(y * .02) * 6;
    const tr = c.createLinearGradient(0, y - 160, 0, y); tr.addColorStop(0, 'rgba(200,220,255,0)'); tr.addColorStop(1, 'rgba(200,220,255,.35)');
    c.globalAlpha = 1; c.strokeStyle = tr; c.lineWidth = d.r * .7; c.beginPath(); c.moveTo(x, y - 160); c.lineTo(x, y); c.stroke();
    c.fillStyle = 'rgba(210,228,255,.65)'; ellipse(c, x, y, d.r, d.r * 1.25); c.fill();
    c.fillStyle = '#fff'; circle(c, x - d.r * .3, y - d.r * .4, d.r * .3); c.fill();
  }
  c.globalAlpha = 1;
}

function flame(c, x, y, wd, ht, t, seed, cols) {
  const sw = Math.sin(t * 5.3 + seed) * .18 + Math.sin(t * 8.1 + seed * 2) * .1;
  const hh = ht * (1 + .12 * Math.sin(t * 6.7 + seed * 3) + .06 * Math.sin(t * 13 + seed));
  const g = c.createLinearGradient(0, y, 0, y - hh); cols.forEach((col, i) => g.addColorStop(i / (cols.length - 1), col));
  c.fillStyle = g; c.beginPath(); c.moveTo(x - wd / 2, y);
  c.bezierCurveTo(x - wd * .6, y - hh * .45, x + wd * sw - wd * .15, y - hh * .7, x + wd * sw * 1.6, y - hh);
  c.bezierCurveTo(x + wd * sw + wd * .2, y - hh * .65, x + wd * .62, y - hh * .4, x + wd / 2, y);
  c.closePath(); c.fill();
}
function ambFeuer(c, t, w, h) {
  const g = c.createLinearGradient(0, 0, 0, h); g.addColorStop(0, '#07091a'); g.addColorStop(.7, '#1a0e16'); g.addColorStop(1, '#0c0608');
  c.fillStyle = g; c.fillRect(0, 0, w, h);
  for (const s of AMB.stars) { c.globalAlpha = .4 + .4 * Math.sin(t * 1.3 + s.p); c.fillStyle = '#fff'; circle(c, s.x * w, s.y * h, s.r); c.fill(); }
  const cx = w / 2, gy = h * .8, fl = 1 + .06 * Math.sin(t * 7) + .04 * Math.sin(t * 11.3);
  c.globalAlpha = 1; let rg = c.createRadialGradient(cx, gy - 80, 10, cx, gy - 80, 520 * fl);   // warmes Licht
  rg.addColorStop(0, 'rgba(255,150,60,.55)'); rg.addColorStop(1, 'rgba(255,90,20,0)'); c.fillStyle = rg; c.fillRect(0, 0, w, h);
  c.fillStyle = '#120a0a'; ellipse(c, cx, gy + 60, w * .7, 70); c.fill();   // Boden
  for (let i = 0; i < 9; i++) { const a = i / 9 * TAU; c.fillStyle = i % 2 ? '#4a4048' : '#5b5058'; ellipse(c, cx + Math.cos(a) * 190, gy + 18 + Math.sin(a) * 34, 34, 22); c.fill(); }   // Steinkreis
  c.save(); c.lineCap = 'round';   // Holzscheite
  [[-1, '#5a3420'], [1, '#6b3d24']].forEach(([s, col]) => { c.strokeStyle = col; c.lineWidth = 40; c.beginPath(); c.moveTo(cx - 170 * s, gy + 22); c.lineTo(cx + 150 * s, gy - 34); c.stroke(); c.strokeStyle = '#ff7a2a'; c.lineWidth = 6; c.globalAlpha = .5 + .3 * Math.sin(t * 4 + s); c.beginPath(); c.moveTo(cx - 40 * s, gy - 4); c.lineTo(cx + 60 * s, gy - 22); c.stroke(); c.globalAlpha = 1; });
  c.restore();
  c.save(); c.globalCompositeOperation = 'lighter';
  for (let i = 0; i < 5; i++) flame(c, cx + (i - 2) * 48, gy - 10, 150 - Math.abs(i - 2) * 22, 330 - Math.abs(i - 2) * 70, t, i * 1.7, ['rgba(255,80,20,.9)', 'rgba(255,120,30,.6)', 'rgba(255,60,10,0)']);
  for (let i = 0; i < 3; i++) flame(c, cx + (i - 1) * 40, gy - 14, 90, 220 - Math.abs(i - 1) * 50, t * 1.2, 7 + i, ['rgba(255,240,170,.95)', 'rgba(255,200,80,.6)', 'rgba(255,160,40,0)']);
  for (const s of AMB.sparks) {   // Funken steigen auf
    const p = (s.p + t * s.v) % 1, y = gy - 120 - p * 620, x = cx + s.x * 220 + Math.sin(t * 2 + s.w) * 30 * p;
    c.globalAlpha = (1 - p) * .9; c.fillStyle = p < .5 ? '#ffd27a' : '#ff8a3a'; circle(c, x, y, s.s * (1 - p * .5)); c.fill();
  }
  c.restore(); c.globalAlpha = 1;
}

const PEND_COLS = ['#ff4d6d', '#ff7a45', '#ffa940', '#ffd23a', '#c6f04a', '#6ee06e', '#3ed8b0', '#38c6f4', '#4a9bff', '#6b7bff', '#9a6bff', '#c86bff', '#ff6bd6', '#ff6b9a', '#ff8a8a'];
function ambPendel(c, t, w, h) {
  const g = c.createRadialGradient(w / 2, h / 2, 50, w / 2, h / 2, w); g.addColorStop(0, '#16142a'); g.addColorStop(1, '#07060f');
  c.fillStyle = g; c.fillRect(0, 0, w, h);
  c.strokeStyle = 'rgba(255,255,255,.08)'; c.lineWidth = 3; c.beginPath(); c.moveTo(w / 2, 40); c.lineTo(w / 2, h - 40); c.stroke();
  const n = PEND_COLS.length, top = 90, gap = (h - 180) / (n - 1), A = w * .38;
  const pos = (i, tt) => w / 2 + A * Math.sin(TAU * tt * (12 + i) / 30);   // nach 30 s wieder genau am Anfang
  c.save(); c.globalCompositeOperation = 'lighter';
  for (let i = 0; i < n; i++) {
    const y = top + i * gap;
    for (let k = 6; k >= 1; k--) { c.globalAlpha = .07 * (7 - k); c.fillStyle = PEND_COLS[i]; circle(c, pos(i, t - k * .025), y, 20); c.fill(); }   // Schweif
    const x = pos(i, t);
    const rg = c.createRadialGradient(x, y, 0, x, y, 70); rg.addColorStop(0, PEND_COLS[i] + 'aa'); rg.addColorStop(1, PEND_COLS[i] + '00');
    c.globalAlpha = 1; c.fillStyle = rg; circle(c, x, y, 70); c.fill();
    c.fillStyle = PEND_COLS[i]; circle(c, x, y, 22); c.fill();
    c.fillStyle = 'rgba(255,255,255,.8)'; circle(c, x - 7, y - 7, 7); c.fill();
  }
  c.restore(); c.globalAlpha = 1;
}

function drawAmbient(c, art, t, w, h) {
  c.save(); c.beginPath(); c.rect(0, 0, w, h); c.clip();
  (art === 'feuer' ? ambFeuer : art === 'pendel' ? ambPendel : ambRegen)(c, t, w, h);
  c.restore();
}
