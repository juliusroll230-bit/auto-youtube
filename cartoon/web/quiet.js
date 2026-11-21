// ---------- Quiet Corner: gemütliche Szenen für den Entspannungskanal (seit 21.11.2026) ----------
// Alles selbst gezeichnet. drawQuiet(ctx, opt, t, w, h) zeichnet eine Szene in (0,0)-(w,h).
// opt = {scene: "regenzimmer" | "kamin" | "cafe" | "bibliothek" | "lagerfeuer", weather: "regen" | "schnee" | "gewitter" | "klar"}
// Gezeichnet wird in Bezugs-Einheiten: Mitte (0,0), Breite -960..960, Höhe -540..540 (16:9). Im Hochformat (Teaser-Shorts)
// wird dieselbe Szene größer gezeigt, man sieht dann nur die Mitte (ca. -300..300). Darum steht alles Wichtige in der Mitte.
// Braucht ambient.js (S, qv, flame, AMB_LOOP): alle Bewegungen wiederholen sich nach LOOP Sekunden genau.
const QC = (() => {
  const R = rng(9137);
  const pick = a => a[Math.floor(R() * a.length)];
  return {
    rain: Array.from({ length: 170 }, () => ({ x: R(), y: R(), v: qv(.9 + R() * .7, 1), l: .05 + R() * .06, a: .12 + R() * .3 })),
    glass: Array.from({ length: 80 }, () => ({ x: R(), y: R(), r: 3 + R() * 7 })),
    runs: Array.from({ length: 9 }, () => ({ x: R(), p: R(), v: qv(.05 + R() * .06, 1.2), r: 5 + R() * 4 })),
    bokeh: Array.from({ length: 30 }, () => ({ x: R(), y: .25 + R() * .75, r: 25 + R() * 60, c: pick(['#ffb35c', '#ffd58a', '#ff8a66', '#8fc7ff', '#c9a8ff', '#ffe3a6']), p: R() * TAU })),
    snow: Array.from({ length: 170 }, () => ({ x: R(), y: R(), v: qv(.05 + R() * .07, 1), s: 1.5 + R() * 3, w: R() * TAU })),
    motes: Array.from({ length: 70 }, () => ({ x: R(), y: R(), v: qv(.015 + R() * .03, 1), w: R() * TAU, s: 1 + R() * 2.4 })),
    stars: Array.from({ length: 120 }, () => ({ x: R(), y: R(), r: .6 + R() * 1.6, p: R() * TAU })),
    books: Array.from({ length: 600 }, () => ({ w: 16 + R() * 22, h: .72 + R() * .26, c: pick(['#6b2f2a', '#2f4a3a', '#2c3b5a', '#7a5a2a', '#4a2f4f', '#5c3a24', '#3d5a55', '#8a6a3a', '#3a2f5a']), g: R() < .25 })),
    candles: Array.from({ length: 11 }, (_, i) => ({ x: -760 + i * 152 + (R() - .5) * 60, y: -430 + R() * 260, p: R() * TAU, s: .75 + R() * .45 })),
    sparks: Array.from({ length: 34 }, () => ({ x: R() - .5, p: R(), v: qv(.3 + R() * .3, 1), s: 1.5 + R() * 3, w: R() * TAU })),
    pines: Array.from({ length: 16 }, (_, i) => ({ x: -1000 + i * 135 + (R() - .5) * 80, h: 260 + R() * 260, s: R() })),
  };
})();
const LEAF = ['#3f7a4a', '#4f8f58', '#2f6340', '#5f9e60', '#36704a'];

// ---------- kleine Bausteine ----------
function qGlow(c, x, y, r, col, a = 1) {
  const g = c.createRadialGradient(x, y, 0, x, y, r); g.addColorStop(0, col); g.addColorStop(1, 'rgba(0,0,0,0)');
  c.globalAlpha = a; c.fillStyle = g; c.fillRect(x - r, y - r, r * 2, r * 2); c.globalAlpha = 1;
}
function qPot(c, x, y, wd, ht, col = '#b5643c') {   // Blumentopf, y = Unterkante
  c.fillStyle = col; c.beginPath(); c.moveTo(x - wd / 2, y - ht); c.lineTo(x + wd / 2, y - ht); c.lineTo(x + wd * .38, y); c.lineTo(x - wd * .38, y); c.closePath(); c.fill();
  c.fillStyle = 'rgba(0,0,0,.18)'; c.fillRect(x - wd / 2 - 4, y - ht, wd + 8, ht * .22);
  c.fillStyle = 'rgba(255,255,255,.08)'; c.fillRect(x - wd * .3, y - ht * .7, wd * .12, ht * .6);
}
function qLeaf(c, x, y, len, wid, ang, col) {   // ein Blatt vom Stiel (x,y) in Richtung ang
  c.save(); c.translate(x, y); c.rotate(ang);
  c.fillStyle = col; c.beginPath(); c.moveTo(0, 0);
  c.bezierCurveTo(len * .3, -wid, len * .8, -wid * .7, len, 0); c.bezierCurveTo(len * .8, wid * .7, len * .3, wid, 0, 0); c.fill();
  c.strokeStyle = 'rgba(255,255,255,.14)'; c.lineWidth = 2; c.beginPath(); c.moveTo(len * .05, 0); c.lineTo(len * .92, 0); c.stroke();
  c.restore();
}
function qBush(c, x, y, s, t, seed, n = 9, potCol) {   // buschige Pflanze im Topf
  qPot(c, x, y, 80 * s, 70 * s, potCol);
  const R = rng(seed);
  for (let i = 0; i < n; i++) {
    const a = -Math.PI / 2 + (i / (n - 1) - .5) * 2.4 + (R() - .5) * .3 + .05 * S(t, .25, seed + i);
    qLeaf(c, x + (R() - .5) * 20 * s, y - 66 * s, (70 + R() * 50) * s, (18 + R() * 10) * s, a, LEAF[i % LEAF.length]);
  }
}
function qMonstera(c, x, y, s, t, seed) {   // große Pflanze mit herzförmigen Blättern im Bodentopf, y = Topfmitte
  const R = rng(seed), tips = [], by = y - 40 * s;
  c.strokeStyle = '#2b5a35'; c.lineWidth = 6 * s; c.lineCap = 'round';
  for (let i = 0; i < 7; i++) {
    const a = -Math.PI / 2 + (i / 6 - .5) * 1.8 + .04 * S(t, .2, seed + i), L = (220 + R() * 160) * s;
    const ex = x + Math.cos(a) * L, ey = by + Math.sin(a) * L;
    c.beginPath(); c.moveTo(x, by); c.quadraticCurveTo(x + Math.cos(a) * L * .35, ey + 70 * s, ex, ey); c.stroke(); tips.push([ex, ey, a, i]);
  }
  for (const [ex, ey, a, i] of tips) {
    const L = 120 * s, Wd = 78 * s;
    c.save(); c.translate(ex, ey); c.rotate(a + .35 * Math.cos(a));
    c.fillStyle = LEAF[i % LEAF.length]; c.beginPath(); c.moveTo(0, 0);
    c.bezierCurveTo(L * .1, -Wd, L * .85, -Wd * .8, L * 1.15, 0); c.bezierCurveTo(L * .85, Wd * .8, L * .1, Wd, 0, 0); c.fill();
    c.strokeStyle = 'rgba(255,255,255,.13)'; c.lineWidth = 3 * s; c.beginPath(); c.moveTo(4 * s, 0); c.lineTo(L * 1.05, 0); c.stroke();
    c.lineWidth = 2 * s; for (let k = 1; k < 5; k++) { const q = k / 5 * L; c.beginPath(); c.moveTo(q, 0); c.lineTo(q + 22 * s, -Wd * .55 * Math.sin(Math.PI * k / 5)); c.moveTo(q, 0); c.lineTo(q + 22 * s, Wd * .55 * Math.sin(Math.PI * k / 5)); c.stroke(); }
    c.restore();
  }
  qPot(c, x, y + 130 * s, 170 * s, 170 * s, '#c9b8a3');
}
function qSnake(c, x, y, s, seed) {   // Bogenhanf: hohe, spitze Blätter
  qPot(c, x, y, 70 * s, 60 * s, '#e6ddd0');
  const R = rng(seed);
  for (let i = 0; i < 6; i++) {
    const bx = x + (i - 2.5) * 9 * s, ht = (110 + R() * 90) * s, lean = (R() - .5) * 30 * s;
    c.fillStyle = i % 2 ? '#3d6b3f' : '#4d7d47';
    c.beginPath(); c.moveTo(bx - 9 * s, y - 56 * s); c.quadraticCurveTo(bx - 10 * s, y - 56 * s - ht * .6, bx + lean, y - 56 * s - ht);
    c.quadraticCurveTo(bx + 10 * s, y - 56 * s - ht * .6, bx + 9 * s, y - 56 * s); c.fill();
    c.strokeStyle = 'rgba(220,230,150,.5)'; c.lineWidth = 2 * s; c.stroke();
  }
}
function qVine(c, x, y, len, s, t, seed) {   // Efeutute: hängt von (x,y) herunter und schwingt leicht
  const R = rng(seed), n = Math.floor(len / 26);
  let px = x, py = y;
  c.strokeStyle = '#3c6a3e'; c.lineWidth = 3 * s; c.beginPath(); c.moveTo(px, py);
  const pts = [];
  for (let i = 1; i <= n; i++) {
    const k = i / n, sw = (14 + 26 * k) * S(t, .18, seed) * k;
    const nx = x + sw + Math.sin(i * .7 + seed) * 10 * s, ny = y + i * 26 * s;
    c.lineTo(nx, ny); pts.push([nx, ny, i]); px = nx; py = ny;
  }
  c.stroke();
  for (const [lx, ly, i] of pts) {
    const side = i % 2 ? 1 : -1, sz = (13 + R() * 7) * s;
    c.save(); c.translate(lx, ly); c.rotate(side * .9 + .1 * S(t, .3, i));
    c.fillStyle = LEAF[(i + seed) % LEAF.length]; c.beginPath(); c.moveTo(0, 0);   // herzförmiges Blatt
    c.bezierCurveTo(-sz, -sz * .2, -sz * .7, sz * 1.2, 0, sz * 1.5); c.bezierCurveTo(sz * .7, sz * 1.2, sz, -sz * .2, 0, 0); c.fill();
    c.restore();
  }
}
function qFern(c, x, y, s, t, seed) {   // Farn: gefiederte Wedel
  const R = rng(seed);
  for (let i = 0; i < 9; i++) {
    const a = -Math.PI / 2 + (i / 8 - .5) * 2.6 + .05 * S(t, .22, seed + i), L = (120 + R() * 60) * s;
    c.save(); c.translate(x, y); c.rotate(a);
    c.strokeStyle = '#3a6b3c'; c.lineWidth = 3 * s; c.beginPath(); c.moveTo(0, 0); c.quadraticCurveTo(L * .5, L * .12, L, L * .3); c.stroke();
    c.fillStyle = LEAF[i % LEAF.length];
    for (let k = 1; k < 10; k++) { const q = k / 10, px = L * q, py = L * .3 * q * q, sz = (1 - q) * 22 * s + 4 * s; qLeaf(c, px, py, sz, sz * .35, -1.1, c.fillStyle); qLeaf(c, px, py, sz, sz * .35, 1.1 + .3, c.fillStyle); }
    c.restore();
  }
}
function qSteam(c, x, y, t, s = 1, n = 3) {   // Dampf über Tasse oder Tee
  c.save(); c.lineCap = 'round';
  for (let i = 0; i < n; i++) {
    const p = (t * qv(.22, 1) + i / n) % 1, yy = y - p * 120 * s;
    c.globalAlpha = Math.sin(p * Math.PI) * .32; c.strokeStyle = '#fff'; c.lineWidth = (7 - p * 4) * s;
    c.beginPath(); c.moveTo(x + (i - 1) * 10 * s, yy + 30 * s);
    c.bezierCurveTo(x + (i - 1) * 10 * s + 14 * s * S(t, .6, i), yy + 10 * s, x - 12 * s * S(t, .45, i + 2), yy - 10 * s, x + 8 * s * S(t, .5, i + 4), yy - 30 * s);
    c.stroke();
  }
  c.restore(); c.globalAlpha = 1;
}
function qMug(c, x, y, s, col = '#d9cbb8') {   // Tasse, y = Unterkante
  c.fillStyle = 'rgba(0,0,0,.35)'; ellipse(c, x, y + 2 * s, 46 * s, 8 * s); c.fill();
  c.strokeStyle = col; c.lineWidth = 9 * s; c.beginPath(); c.arc(x + 36 * s, y - 38 * s, 16 * s, -1.3, 1.3); c.stroke();
  c.fillStyle = col; rrect(c, x - 36 * s, y - 72 * s, 72 * s, 72 * s, 12 * s); c.fill();
  c.fillStyle = 'rgba(0,0,0,.12)'; rrect(c, x + 8 * s, y - 72 * s, 28 * s, 72 * s, 10 * s); c.fill();
  c.fillStyle = '#4a2c1c'; ellipse(c, x, y - 70 * s, 32 * s, 6 * s); c.fill();
}
function qCandle(c, x, y, s, t, seed, glow = true) {   // Kerze, y = Unterkante
  c.fillStyle = '#efe4cf'; rrect(c, x - 11 * s, y - 60 * s, 22 * s, 60 * s, 4 * s); c.fill();
  c.fillStyle = 'rgba(0,0,0,.12)'; c.fillRect(x + 3 * s, y - 60 * s, 8 * s, 60 * s);
  const f = 1 + .12 * S(t, 9, seed) + .06 * S(t, 15, seed * 2), sw = 3 * s * S(t, 3, seed);
  if (glow) qGlow(c, x, y - 80 * s, 150 * s * f, 'rgba(255,180,90,.35)');
  c.fillStyle = '#ffcf6b'; c.beginPath(); c.moveTo(x - 7 * s, y - 64 * s); c.quadraticCurveTo(x - 8 * s, y - 80 * s, x + sw, y - (64 + 30 * f) * s);
  c.quadraticCurveTo(x + 8 * s, y - 80 * s, x + 7 * s, y - 64 * s); c.fill();
  c.fillStyle = '#fff5d6'; ellipse(c, x, y - 70 * s, 3 * s, 7 * s); c.fill();
}
function qLamp(c, x, y, s, t) {   // Tischlampe mit warmem Licht, y = Unterkante
  qGlow(c, x, y - 170 * s, 520 * s * (1 + .01 * S(t, 2)), 'rgba(255,170,90,.32)');
  c.fillStyle = '#3a2a22'; ellipse(c, x, y - 4 * s, 50 * s, 10 * s); c.fill();
  c.fillStyle = '#4a372c'; c.fillRect(x - 5 * s, y - 130 * s, 10 * s, 126 * s);
  const g = c.createLinearGradient(0, y - 230 * s, 0, y - 130 * s); g.addColorStop(0, '#ffe2a8'); g.addColorStop(1, '#f2a65a');
  c.fillStyle = g; c.beginPath(); c.moveTo(x - 50 * s, y - 230 * s); c.lineTo(x + 50 * s, y - 230 * s); c.lineTo(x + 85 * s, y - 130 * s); c.lineTo(x - 85 * s, y - 130 * s); c.closePath(); c.fill();
}
function qBooks(c, x, y, wd, ht, seed, warm = .0) {   // ein Regalbrett voller Bücher, (x,y) = links unten
  let bx = x, i = seed * 37;
  while (bx < x + wd - 10) {
    const b = QC.books[i++ % QC.books.length], bh = ht * b.h;
    c.fillStyle = b.c; c.fillRect(bx, y - bh, b.w - 2, bh);
    c.fillStyle = 'rgba(255,220,160,.18)'; c.fillRect(bx + 3, y - bh + bh * .15, b.w - 8, 3); c.fillRect(bx + 3, y - bh * .2, b.w - 8, 3);
    if (b.g) { c.fillStyle = 'rgba(0,0,0,.25)'; c.fillRect(bx, y - bh, b.w - 2, bh); }
    bx += b.w;
  }
  if (warm) { c.fillStyle = `rgba(255,170,90,${warm})`; c.fillRect(x, y - ht, wd, ht); }
}
function qShelf(c, x, y, wd, rows, rowH, seed) {   // Bücherregal mit Brettern, (x,y) = links oben
  c.fillStyle = '#2a1a12'; c.fillRect(x - 14, y - 14, wd + 28, rows * rowH + 28);
  for (let r = 0; r < rows; r++) {
    const by = y + (r + 1) * rowH;
    c.fillStyle = '#1a100b'; c.fillRect(x, by - rowH, wd, rowH);
    qBooks(c, x + 6, by - 8, wd - 12, rowH - 22, seed + r);
    c.fillStyle = '#4a2f20'; c.fillRect(x - 14, by - 10, wd + 28, 14);
  }
}

// ---------- Fenster mit Wetter ----------
function qWindow(c, x, y, ww, wh, t, opt, outside = 'stadt', arch = false) {   // (x,y) = links oben
  const weather = opt.weather || 'regen';
  c.save(); c.beginPath();
  if (arch) { c.moveTo(x, y + wh); c.lineTo(x, y + ww / 2); c.arc(x + ww / 2, y + ww / 2, ww / 2, Math.PI, 0); c.lineTo(x + ww, y + wh); c.closePath(); }
  else c.rect(x, y, ww, wh);
  c.clip();
  const flash = weather === 'gewitter' ? qFlash(t) : 0;
  const sky = c.createLinearGradient(0, y, 0, y + wh);
  if (outside === 'sterne') { sky.addColorStop(0, '#0b1030'); sky.addColorStop(1, '#2a2350'); }
  else if (weather === 'schnee') { sky.addColorStop(0, '#1c2540'); sky.addColorStop(1, '#3a4260'); }
  else { sky.addColorStop(0, '#0e1630'); sky.addColorStop(1, '#2a1b3a'); }
  c.fillStyle = sky; c.fillRect(x, y, ww, wh);
  if (outside === 'sterne') {
    for (const st of QC.stars) { c.globalAlpha = .35 + .4 * S(t, 1.1, st.p); c.fillStyle = '#fff'; circle(c, x + st.x * ww, y + st.y * wh * .8, st.r); c.fill(); }
    c.globalAlpha = 1; qGlow(c, x + ww * .68, y + wh * .22, 160, 'rgba(220,230,255,.35)');
    c.fillStyle = '#f3f0e0'; circle(c, x + ww * .68, y + wh * .22, 38); c.fill();
    c.fillStyle = 'rgba(180,180,170,.35)'; circle(c, x + ww * .68 - 10, y + wh * .22 - 8, 8); c.fill(); circle(c, x + ww * .68 + 12, y + wh * .22 + 10, 6); c.fill();
  } else if (outside === 'wald') {
    c.fillStyle = '#121a26';
    for (const p of QC.pines) { const px = x + (p.x + 1000) / 2000 * ww; c.beginPath(); c.moveTo(px - 40, y + wh); c.lineTo(px, y + wh - p.h * .6); c.lineTo(px + 40, y + wh); c.fill(); }
  } else {   // Stadtlichter, unscharf
    for (const L of QC.bokeh) {
      const lx = x + L.x * ww, ly = y + L.y * wh;
      qGlow(c, lx, ly, L.r * 1.6, L.c, .45 + .15 * S(t, .5, L.p));
      if (outside === 'strasse') { c.globalAlpha = .12; c.fillStyle = L.c; c.fillRect(lx - L.r * .2, ly + L.r, L.r * .4, wh); c.globalAlpha = 1; }   // Spiegelung auf nasser Straße
    }
  }
  if (flash) { c.globalAlpha = flash; c.fillStyle = '#cfd8ff'; c.fillRect(x, y, ww, wh); c.globalAlpha = 1; }
  if (weather === 'regen' || weather === 'gewitter') {
    c.strokeStyle = 'rgba(190,210,255,1)'; c.lineCap = 'round'; c.lineWidth = 2;
    for (const d of QC.rain) {
      const yy = y + ((d.y + t * d.v) % 1) * (wh + 80) - 60, xx = x + ((d.x * ww + (yy - y) * .1) % ww), l = d.l * wh;
      c.globalAlpha = d.a; c.beginPath(); c.moveTo(xx, yy); c.lineTo(xx + l * .1, yy + l); c.stroke();
    }
    for (const d of QC.glass) { c.globalAlpha = .3; c.fillStyle = '#c8dcff'; circle(c, x + d.x * ww, y + d.y * wh, d.r); c.fill(); c.globalAlpha = .6; c.fillStyle = '#fff'; circle(c, x + d.x * ww - d.r * .3, y + d.y * wh - d.r * .35, d.r * .3); c.fill(); }
    for (const d of QC.runs) {
      const yy = y + ((d.p + t * d.v) % 1.2) * wh - 30, xx = x + d.x * ww + Math.sin(yy * .02) * 5;
      const tr = c.createLinearGradient(0, yy - 140, 0, yy); tr.addColorStop(0, 'rgba(200,220,255,0)'); tr.addColorStop(1, 'rgba(200,220,255,.3)');
      c.globalAlpha = 1; c.strokeStyle = tr; c.lineWidth = d.r * .7; c.beginPath(); c.moveTo(xx, yy - 140); c.lineTo(xx, yy); c.stroke();
      c.fillStyle = 'rgba(210,228,255,.6)'; ellipse(c, xx, yy, d.r, d.r * 1.25); c.fill();
    }
  } else if (weather === 'schnee') {
    for (const f of QC.snow) {
      const yy = y + ((f.y + t * f.v) % 1) * wh, xx = x + f.x * ww + 18 * S(t, .3, f.w);
      c.globalAlpha = .75; c.fillStyle = '#fff'; circle(c, xx, yy, f.s); c.fill();
    }
    c.globalAlpha = .9; c.fillStyle = '#e8eef8'; c.beginPath(); c.moveTo(x, y + wh); c.lineTo(x, y + wh - 16); c.quadraticCurveTo(x + ww / 2, y + wh - 34, x + ww, y + wh - 16); c.lineTo(x + ww, y + wh); c.fill();
  }
  c.restore(); c.globalAlpha = 1;
  c.strokeStyle = '#3b271c'; c.lineWidth = 18;   // Rahmen und Sprossen
  if (arch) { c.beginPath(); c.moveTo(x, y + wh); c.lineTo(x, y + ww / 2); c.arc(x + ww / 2, y + ww / 2, ww / 2, Math.PI, 0); c.lineTo(x + ww, y + wh); c.closePath(); c.stroke(); }
  else c.strokeRect(x, y, ww, wh);
  c.lineWidth = 10; c.beginPath(); c.moveTo(x + ww / 2, y + (arch ? 0 : 0)); c.lineTo(x + ww / 2, y + wh); c.moveTo(x, y + wh * .45); c.lineTo(x + ww, y + wh * .45); c.stroke();
}
function qFlash(t) {   // Blitz zweimal pro Schleife (zu festen Zeiten, der Donner in audio.py passt dazu)
  const L = AMB_LOOP || 60, tt = t % L;
  let a = 0;
  for (const [at, k] of [[L * .38, .55], [L * .7, .4]]) { const d = tt - at; if (d >= 0 && d < .5) a = Math.max(a, k * (d < .08 ? 1 : d < .16 ? .3 : d < .24 ? .8 : Math.max(0, 1 - (d - .24) / .26))); }
  return a;
}
function qCurtain(c, x, y, wd, ht, t, side, col = '#5a3b33') {
  const g = c.createLinearGradient(x, 0, x + wd, 0); g.addColorStop(0, col); g.addColorStop(.5, '#6e4a40'); g.addColorStop(1, col);
  c.fillStyle = g; c.beginPath(); c.moveTo(x, y);
  c.lineTo(x + wd, y);
  const sw = 6 * S(t, .15, side);
  c.quadraticCurveTo(x + wd + side * 20 + sw, y + ht * .6, x + wd * (side > 0 ? .7 : 1.1) + sw, y + ht);
  c.lineTo(x + (side > 0 ? 0 : wd * .3), y + ht); c.closePath(); c.fill();
  c.strokeStyle = 'rgba(0,0,0,.2)'; c.lineWidth = 4;
  for (let i = 1; i < 4; i++) { c.beginPath(); c.moveTo(x + wd * i / 4, y); c.lineTo(x + wd * i / 4 + sw, y + ht); c.stroke(); }
}
function qVignette(c, warm = 'rgba(255,150,70,.0)') {
  const g = c.createRadialGradient(0, 0, 300, 0, 0, 1150); g.addColorStop(0, 'rgba(0,0,0,0)'); g.addColorStop(1, 'rgba(0,0,0,.55)');
  c.fillStyle = g; c.fillRect(-1600, -900, 3200, 1800);
}

// ---------- Szenen ----------
function qcRegenzimmer(c, t, opt) {
  const g = c.createLinearGradient(0, -540, 0, 540); g.addColorStop(0, '#2b1f1b'); g.addColorStop(1, '#17100e');
  c.fillStyle = g; c.fillRect(-1600, -900, 3200, 1800);
  qWindow(c, -320, -400, 640, 560, t, opt, opt.weather === 'schnee' ? 'wald' : 'stadt');
  qCurtain(c, -470, -470, 150, 660, t, 1); qCurtain(c, 320, -470, 150, 660, t, -1);
  c.fillStyle = '#4a3123'; c.fillRect(-1600, -480, 3200, 16);   // Gardinenstange
  c.fillStyle = '#5b3c2a'; c.fillRect(-380, 160, 760, 34); c.fillStyle = '#3a271b'; c.fillRect(-1600, 194, 3200, 400);   // Fensterbank, Tisch
  c.fillStyle = 'rgba(255,190,120,.06)'; c.fillRect(-1600, 194, 3200, 12);
  qShelf(c, -900, -330, 300, 3, 150, 3);
  qLamp(c, -470, 300, 1, t);
  qBush(c, -230, 162, .8, t, 11);
  qCandle(c, -110, 162, 1, t, 2);
  qMug(c, 60, 162, 1); qSteam(c, 60, 82, t);
  qSnake(c, 230, 162, 1, 5);
  qVine(c, -300, -470, 360, 1, t, 3); qVine(c, 280, -470, 280, 1, t, 7);
  qMonstera(c, 700, 340, 1, t, 9);
  qVignette(c);
}
function qcKamin(c, t, opt) {
  const fl = 1 + .05 * S(t, 7) + .04 * S(t, 11.3);
  const g = c.createLinearGradient(0, -540, 0, 540); g.addColorStop(0, '#2a1b16'); g.addColorStop(1, '#140c09');
  c.fillStyle = g; c.fillRect(-1600, -900, 3200, 1800);
  qWindow(c, 560, -380, 300, 420, t, { weather: opt.weather === 'regen' ? 'regen' : 'schnee' }, 'wald');
  qGlow(c, 0, 250, 1100 * fl, 'rgba(255,120,50,.32)');
  c.fillStyle = '#1f1410'; c.fillRect(-1600, 420, 3200, 300);   // Boden
  c.fillStyle = '#5a2e26'; ellipse(c, 0, 470, 560, 60); c.fill(); c.strokeStyle = '#7a4434'; c.lineWidth = 6; ellipse(c, 0, 470, 520, 50); c.stroke();   // Teppich
  c.fillStyle = '#6b4a3c'; c.fillRect(-330, -170, 660, 600);   // Kamin aus Stein
  for (let r = 0; r < 12; r++) for (let k = 0; k < 7; k++) { c.fillStyle = (r + k) % 3 ? '#7a5646' : '#6a4a3c'; c.fillRect(-330 + k * 96 + (r % 2) * 48 - 48, -170 + r * 50, 92, 46); }
  c.fillStyle = '#4a3024'; c.fillRect(-380, -200, 760, 40);   // Sims
  c.fillStyle = '#0c0706'; rrect(c, -210, 40, 420, 390, [200, 200, 0, 0]); c.fill();
  c.save(); c.beginPath(); c.roundRect(-210, 40, 420, 390, [200, 200, 0, 0]); c.clip();
  c.lineCap = 'round'; [[-1, '#5a3420'], [1, '#6b3d24']].forEach(([s, col]) => { c.strokeStyle = col; c.lineWidth = 34; c.beginPath(); c.moveTo(-140 * s, 410); c.lineTo(120 * s, 360); c.stroke(); });
  c.globalCompositeOperation = 'lighter';
  for (let i = 0; i < 5; i++) flame(c, (i - 2) * 38, 395, 120 - Math.abs(i - 2) * 18, 240 - Math.abs(i - 2) * 50, t, i * 1.7, 1, ['rgba(255,80,20,.9)', 'rgba(255,120,30,.6)', 'rgba(255,60,10,0)']);
  for (let i = 0; i < 3; i++) flame(c, (i - 1) * 32, 392, 70, 160 - Math.abs(i - 1) * 40, t, 7 + i, 1.2, ['rgba(255,240,170,.95)', 'rgba(255,200,80,.6)', 'rgba(255,160,40,0)']);
  for (const s of QC.sparks.slice(0, 18)) { const p = (s.p + t * s.v) % 1; c.globalAlpha = (1 - p) * .8; c.fillStyle = '#ffc870'; circle(c, s.x * 200 + S(t, 2, s.w) * 20 * p, 330 - p * 280, s.s); c.fill(); }
  c.restore(); c.globalAlpha = 1;
  qVine(c, -360, -165, 300, 1, t, 4); qVine(c, 340, -165, 220, 1, t, 8);
  qBush(c, -260, -200, .75, t, 13); qCandle(c, -130, -200, 1, t, 5); qCandle(c, -90, -200, .8, t, 6);
  c.fillStyle = '#d9c9b0'; circle(c, 150, -270, 52); c.fill(); c.strokeStyle = '#3a2a20'; c.lineWidth = 6; c.stroke();   // Uhr
  const ang = (t % 60) / 60 * TAU - Math.PI / 2; c.lineWidth = 3; c.beginPath(); c.moveTo(150, -270); c.lineTo(150 + Math.cos(ang) * 42, -270 + Math.sin(ang) * 42); c.stroke();
  c.lineWidth = 5; c.beginPath(); c.moveTo(150, -270); c.lineTo(150, -300); c.moveTo(150, -270); c.lineTo(172, -262); c.stroke();
  qSnake(c, 260, -200, .9, 2);
  c.fillStyle = '#4a2a24'; rrect(c, -800, 80, 330, 360, 60); c.fill(); c.fillStyle = '#5a332c'; rrect(c, -830, 200, 390, 240, 40); c.fill();   // Sessel
  c.fillStyle = '#b8a07a'; rrect(c, -760, 210, 200, 140, 20); c.fill(); c.strokeStyle = 'rgba(0,0,0,.15)'; c.lineWidth = 4; for (let i = 0; i < 5; i++) { c.beginPath(); c.moveTo(-760, 230 + i * 26); c.lineTo(-560, 230 + i * 26); c.stroke(); }   // Decke
  qMonstera(c, 620, 330, .95, t, 21); qFern(c, -420, 420, .9, t, 17); qPot(c, -420, 480, 110, 70, '#b5643c');
  qVignette(c);
}
function qcCafe(c, t, opt) {
  const g = c.createLinearGradient(0, -540, 0, 540); g.addColorStop(0, '#22171a'); g.addColorStop(1, '#120c0c');
  c.fillStyle = g; c.fillRect(-1600, -900, 3200, 1800);
  qWindow(c, -760, -430, 1520, 590, t, opt, 'strasse');
  c.strokeStyle = '#3b271c'; c.lineWidth = 14; for (const xx of [-380, 380]) { c.beginPath(); c.moveTo(xx, -430); c.lineTo(xx, 160); c.stroke(); }
  for (const [px, ph] of [[-260, 0], [260, 1.7]]) {   // Hängelampen
    const sw = 10 * S(t, .2, ph), ly = -310;
    c.strokeStyle = '#1a1210'; c.lineWidth = 4; c.beginPath(); c.moveTo(px, -560); c.lineTo(px + sw, ly); c.stroke();
    qGlow(c, px + sw, ly + 60, 380, 'rgba(255,175,95,.33)');
    c.fillStyle = '#2f2420'; c.beginPath(); c.moveTo(px + sw - 20, ly); c.lineTo(px + sw + 20, ly); c.lineTo(px + sw + 70, ly + 60); c.lineTo(px + sw - 70, ly + 60); c.closePath(); c.fill();
    c.fillStyle = '#ffdca0'; ellipse(c, px + sw, ly + 62, 40, 10); c.fill();
  }
  c.fillStyle = '#6a4630'; c.fillRect(-1600, 160, 3200, 40); c.fillStyle = '#3d281c'; c.fillRect(-1600, 200, 3200, 400);   // Tresen am Fenster
  c.fillStyle = 'rgba(255,200,140,.08)'; c.fillRect(-1600, 160, 3200, 8);
  c.fillStyle = '#e9e0d2'; ellipse(c, 0, 200, 90, 14); c.fill();   // Untertasse
  qMug(c, 0, 196, 1.1, '#f1ebe2'); qSteam(c, 0, 108, t, 1.1);
  c.fillStyle = '#d8c39a'; c.save(); c.translate(210, 190); c.rotate(-.12); c.fillRect(-80, -8, 160, 16); c.fillStyle = '#efe6d4'; c.fillRect(-74, -14, 148, 8); c.restore();   // Notizbuch
  qBush(c, -220, 196, .7, t, 23, 8, '#d8d0c4'); qCandle(c, -110, 196, .8, t, 9);
  qVine(c, -760, -440, 420, 1, t, 12); qVine(c, 740, -440, 380, 1, t, 14); qVine(c, -560, -440, 220, 1, t, 16);
  qMonstera(c, 820, 360, .9, t, 27);
  qVignette(c);
}
function qcBibliothek(c, t, opt) {
  const g = c.createLinearGradient(0, -540, 0, 540); g.addColorStop(0, '#15142a'); g.addColorStop(1, '#0c0a14');
  c.fillStyle = g; c.fillRect(-1600, -900, 3200, 1800);
  qWindow(c, -200, -480, 400, 660, t, { weather: opt.weather === 'klar' ? 'klar' : opt.weather }, 'sterne', true);
  c.save(); c.globalCompositeOperation = 'lighter';   // Mondlicht fällt schräg in den Raum
  const beam = c.createLinearGradient(0, 180, 0, 540); beam.addColorStop(0, 'rgba(150,170,255,.16)'); beam.addColorStop(1, 'rgba(150,170,255,0)');
  c.fillStyle = beam; c.beginPath(); c.moveTo(-190, 180); c.lineTo(190, 180); c.lineTo(420, 540); c.lineTo(-40, 540); c.closePath(); c.fill(); c.restore();
  qShelf(c, -960, -500, 700, 6, 150, 1); qShelf(c, 260, -500, 700, 6, 150, 9);
  c.fillStyle = 'rgba(255,170,90,.06)'; c.fillRect(-960, -500, 1920, 1000);
  c.fillStyle = '#3a2618'; c.save(); c.translate(-420, 0); c.rotate(.12); c.fillRect(-60, -480, 14, 980); c.fillRect(40, -480, 14, 980); for (let i = 0; i < 12; i++) c.fillRect(-56, -440 + i * 80, 106, 10); c.restore();   // Leiter
  qVine(c, -320, -520, 380, 1, t, 31); qVine(c, 300, -520, 300, 1, t, 33); qVine(c, -700, -520, 240, 1, t, 35); qVine(c, 720, -520, 320, 1, t, 37);
  for (const m of QC.motes) {   // glitzernder Staub im Mondlicht
    const p = (m.y + t * m.v) % 1, x = -100 + m.x * 360 + 30 * S(t, .2, m.w) + p * 120, y = 520 - p * 640;
    c.globalAlpha = Math.sin(p * Math.PI) * (.4 + .3 * S(t, 1.5, m.w)); c.fillStyle = '#dfe4ff'; circle(c, x, y, m.s); c.fill();
  }
  c.globalAlpha = 1;
  for (const k of QC.candles) qCandle(c, k.x, k.y + 14 * S(t, .25, k.p), k.s, t, k.p * 10);   // schwebende Kerzen
  c.fillStyle = '#3c2618'; rrect(c, -330, 360, 660, 40, 6); c.fill(); c.fillRect(-300, 400, 30, 200); c.fillRect(270, 400, 30, 200);   // Lesetisch
  c.fillStyle = '#efe3c8'; c.beginPath(); c.moveTo(-120, 360); c.quadraticCurveTo(-60, 330, 0, 352); c.quadraticCurveTo(60, 330, 120, 360); c.lineTo(120, 368); c.lineTo(-120, 368); c.fill();   // offenes Buch
  c.strokeStyle = 'rgba(120,90,60,.35)'; c.lineWidth = 2; for (let i = 0; i < 4; i++) { c.beginPath(); c.moveTo(-100, 352 - i * 4 + 8); c.lineTo(-20, 352 - i * 4 + 4); c.moveTo(20, 352 - i * 4 + 4); c.lineTo(100, 352 - i * 4 + 8); c.stroke(); }
  qMug(c, 200, 362, .7, '#c9d4cf'); qSteam(c, 200, 310, t, .7);
  qFern(c, -230, 300, .65, t, 41); qPot(c, -230, 362, 80, 64, '#8a6a4a');
  qVignette(c);
}
let QTREES = false;   // ambient.js ruft qTrees nur für Quiet Corner auf (die alten Lagerfeuer-Videos bleiben gleich)
function qTrees(c, w, h) {   // Waldrand hinter dem Lagerfeuer
  c.save(); c.translate(w / 2, h / 2); c.scale(h / 1080, h / 1080); c.fillStyle = '#0d1220';
  for (const p of QC.pines) { c.beginPath(); c.moveTo(p.x - 80, 330); for (let k = 0; k < 4; k++) { const y = 330 - p.h * (k + 1) / 4, wd = 80 * (1 - k / 4); c.lineTo(p.x - wd - 10, y + 40); c.lineTo(p.x - wd * .4, y + 40); } c.lineTo(p.x, 330 - p.h - 40); for (let k = 3; k >= 0; k--) { const y = 330 - p.h * (k + 1) / 4, wd = 80 * (1 - k / 4); c.lineTo(p.x + wd * .4, y + 40); c.lineTo(p.x + wd + 10, y + 40); } c.lineTo(p.x + 80, 330); c.fill(); }
  c.fillStyle = '#0a0d16'; c.fillRect(-1600, 320, 3200, 400);
  c.restore();
}
function qcLagerfeuer(c, t) {   // das Feuer selbst zeichnet drawQuiet über ambFeuer, hier nur die Farne davor
  qFern(c, -620, 470, 1.1, t, 51); qFern(c, 640, 480, 1.2, t, 53); qFern(c, -880, 520, .9, t, 55); qFern(c, 900, 520, .9, t, 57);
  qVignette(c);
}

const QUIET = { regenzimmer: qcRegenzimmer, kamin: qcKamin, cafe: qcCafe, bibliothek: qcBibliothek, lagerfeuer: qcLagerfeuer };
function drawQuiet(c, opt, t, w, h) {
  const vw = Math.max(w, h * 16 / 9), u = h / 1080;
  c.save(); c.beginPath(); c.rect(0, 0, w, h); c.clip();
  c.translate((w - vw) / 2, 0); c.scale(u, u);   // Hochformat: Mitte der 16:9-Szene, alles in 1920x1080 gedacht
  if (opt.scene === 'lagerfeuer') { QTREES = true; ambFeuer(c, t, 1920, 1080); QTREES = false; }
  c.translate(960, 540);
  (QUIET[opt.scene] || qcRegenzimmer)(c, t, opt);
  c.restore();
}
