// ---------- Cartoon-Baukasten der Shorts-Zentrale ----------
// Baut aus PLAN.scenes (von cartoon.py) die Einstellungen (SHOTS). Jede Szene hat einen Typ
// (figur, zwei, gruppe, objekt, zahl, jahr, liste, vergleich, horror) und einen Ort.
// Figuren, Gesichter und Hilfsfunktionen kommen aus lib.js / chars.js / env.js (MIT, siehe LICENSE-stick-figure.txt).

const G = 1250; // Bodenlinie: Füße stehen hier, Untertitel sitzen darunter (~1345)
const SHOTS = [];
const EMOJI_FONT = 'CEmoji';

const COLS = { rot: 'red', blau: 'blue', gelb: 'yellow', gruen: 'green', lila: 'purple', navy: 'navy' };
const HATCOL = { rot: '#d8312b', blau: '#2f63c9', gelb: '#f2b52a', gruen: '#3fa35b', lila: '#6c43c0', navy: '#2a3f8f' };
const MOOD = {
  freude: { eyes: 'normal', mouth: 'grin' },
  angst: { eyes: 'wide', mouth: 'teeth', browUp: 1, browAng: -.35 },
  staunen: { eyes: 'wide', mouth: 'o', browUp: 1 },
  wut: { eyes: 'squint', mouth: 'teeth', browAng: .4 },
  traurig: { eyes: 'normal', mouth: 'frown', browAng: -.3 },
  denken: { eyes: 'normal', mouth: 'flat', look: [.5, -.6], browOne: 1 },
  cool: { eyes: 'normal', mouth: 'smirk', browAng: .25 },
  neutral: { eyes: 'normal', mouth: 'smile' },
  k_o: { eyes: 'spiral', mouth: 'o' },
};

// ---------- zusätzliche Hüte (werden in drawStick über window.HATS aufgerufen) ----------
window.HATS = {
  keiner() {},
  krone(ctx, hx, hy, hr, lw) {
    const b = hy - hr * .78, w = hr * .8;
    path(ctx, [[hx - w, b], [hx - w, b - .13], [hx - w * .5, b - .06], [hx, b - .17], [hx + w * .5, b - .06], [hx + w, b - .13], [hx + w, b]]);
    fillStroke(ctx, '#f6c93b', lw); circle(ctx, hx, b - .04, .022); fillStroke(ctx, '#e0392f', lw * .6);
  },
  zylinder(ctx, hx, hy, hr, lw) {
    const b = hy - hr * .72;
    rrect(ctx, hx - hr * 1.15, b - .02, hr * 2.3, .045, .02); fillStroke(ctx, '#2b2230', lw);
    rrect(ctx, hx - hr * .7, b - .27, hr * 1.4, .26, .02); fillStroke(ctx, '#2b2230', lw);
    ctx.fillStyle = '#c0392b'; ctx.fillRect(hx - hr * .7, b - .07, hr * 1.4, .035);
  },
  helm(ctx, hx, hy, hr, lw) {
    ctx.beginPath(); ctx.arc(hx, hy - hr * .15, hr * 1.06, Math.PI * 1.02, Math.PI * 1.98); ctx.closePath(); fillStroke(ctx, '#b9c2cc', lw);
    line(ctx, hx, hy - hr * 1.2, hx, hy - hr * .2, lw * .9, INK);
  },
  muetze(ctx, hx, hy, hr, lw, col) {
    ctx.beginPath(); ctx.arc(hx, hy - hr * .35, hr * .95, Math.PI, 0); ctx.closePath(); fillStroke(ctx, col || '#3fa35b', lw);
    circle(ctx, hx, hy - hr * 1.32, .04); fillStroke(ctx, '#fff', lw * .7);
  },
  hexe(ctx, hx, hy, hr, lw) {
    const b = hy - hr * .7;
    ellipse(ctx, hx, b, hr * 1.4, .04); fillStroke(ctx, '#2a2036', lw);
    path(ctx, [[hx - hr * .7, b], [hx + .05, b - .42], [hx + hr * .7, b]]); fillStroke(ctx, '#2a2036', lw);
  },
  ritter(ctx, hx, hy, hr, lw) {
    ctx.beginPath(); ctx.arc(hx, hy, hr * 1.05, Math.PI * .9, Math.PI * 2.1); ctx.closePath(); fillStroke(ctx, '#aab4bf', lw);
    rrect(ctx, hx - hr * .9, hy - .035, hr * 1.8, .05, .02); ctx.fillStyle = '#2b2230'; ctx.fill();
  },
};
const HATMAP = { bandana: 'bandana', matrose: 'sailor', kapitaen: 'captain', keiner: 'keiner', krone: 'krone', zylinder: 'zylinder', helm: 'helm', muetze: 'muetze', hexe: 'hexe', ritter: 'ritter' };

// ---------- kleine Helfer ----------
function emoji(ctx, ch, x, y, size, rot = 0, alpha = 1) {
  if (!ch) return;
  ctx.save(); ctx.globalAlpha *= alpha; ctx.translate(x, y); ctx.rotate(rot);
  ctx.font = `${size}px ${EMOJI_FONT}`; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
  ctx.shadowColor = 'rgba(20,10,30,.35)'; ctx.shadowBlur = size * .06; ctx.shadowOffsetY = size * .04;
  ctx.fillText(ch, 0, 0); ctx.restore();
}
function fitText(ctx, str, x, y, size, maxW, fill = '#fff', stroke = INK, sw = 14, font = 'Poppins') {
  ctx.font = `700 ${size}px ${font}`; let s = size; const w = ctx.measureText(str).width;
  if (w > maxW) s = Math.max(28, size * maxW / w);
  text(ctx, str, x, y, s, fill, stroke, sw * s / size, font, 700);
}
function sign(ctx, str, x, y, size = 72, col = '#ffe14d') {
  if (!str) return;
  ctx.font = `700 ${size}px Poppins`; let s = size; const w0 = ctx.measureText(str).width; if (w0 > 860) s = size * 860 / w0;
  ctx.font = `700 ${s}px Poppins`; const w = ctx.measureText(str).width + s * 1.1, h = s * 1.6;
  ctx.save(); ctx.translate(x, y); ctx.rotate(-.03);
  rrect(ctx, -w / 2 + 8, -h / 2 + 10, w, h, s * .35); ctx.fillStyle = 'rgba(20,10,30,.35)'; ctx.fill();
  rrect(ctx, -w / 2, -h / 2, w, h, s * .35); fillStroke(ctx, col, Math.max(6, s * .1));
  text(ctx, str, 0, 2, s, INK, null, 0, 'Poppins', 700); ctx.restore();
}
function popIn(lt, at = 0, dur = .35) { return backOut(clamp((lt - at) / dur)); }
function cam(lt, d, z0 = 1, z1 = 1.08, seed = 0) {
  const [sx, sy] = shake(lt, 6, .35, seed);
  return { x: 540 + sx, y: 960 + sy, z: lerp(z0, z1, ease(clamp(lt / Math.max(d, .5)))), r: Math.sin(lt * .7 + seed) * .006 };
}
function figure(sc, base = {}) {
  const f = sc.figur || {};
  const colName = f.farbe || sc.farbe || 'rot';
  const hat = HATMAP[f.hut || sc.hut || 'keiner'] || 'keiner';
  const art = f.art || sc.art;
  const extra = art === 'zombie' ? { headCol: '#a7c98a', headSh: '#86a96c' } : art === 'blass' ? { headCol: '#e6ecf2', headSh: '#c4ccd6' } : {};
  return { cols: PAL[COLS[colName] || 'red'], hat, hatCol: HATCOL[colName] || '#d8312b', dotCol: '#fff', ...extra, ...base };
}
function face(mood, lt, extra = {}) {
  const m = MOOD[mood] || MOOD.neutral;
  const blink = (Math.floor((lt + .3) / 2.7) % 2 === 0 && ((lt + .3) % 2.7) < .12) ? 1 : 0;
  return { ...m, blink: m.eyes === 'spiral' ? 0 : blink, t: lt, ...extra };
}
// Arm-/Bein-Haltung je Aktion
function pose(act, lt) {
  const sw = Math.sin(lt * 9);
  switch (act) {
    case 'zeigt': return { arms: { L: [.3, -.1], R: [1.85, .05] }, legs: { L: [.14, -.04], R: [.14, -.04] } };
    case 'winkt': return { arms: { L: [.3, -.1], R: [2.55 + Math.sin(lt * 11) * .3, .35] } };
    case 'jubelt': return { arms: { L: [2.55, .3], R: [2.55, .3] }, legs: { L: [.25, -.3], R: [.25, -.3] }, bob: -Math.abs(Math.sin(lt * 6)) * .08 };
    case 'rennt': return { arms: { L: [.9 + sw * .7, -1.2], R: [.9 - sw * .7, -1.2] }, legs: { L: [.5 + sw * .6, -.9], R: [.5 - sw * .6, -.9] }, lean: .12, bob: -Math.abs(Math.cos(lt * 9)) * .03 };
    case 'zittert': return { arms: { L: [.9, -2.3], R: [.9, -2.3] }, legs: { L: [.2, -.25], R: [.2, -.25] }, jitter: 5 };
    case 'denkt': return { arms: { L: [.3, -.1], R: [.95, -2.55] } };
    case 'faellt': return { arms: { L: [2.2, .4], R: [2.0, .2] }, legs: { L: [.6, -.3], R: [.2, -.2] }, lean: -clamp(lt * .9) * .8 };
    case 'schockiert': return { arms: { L: [2.5, .3], R: [2.5, .3] }, legs: { L: [.2, -.1], R: [.2, -.1] }, jitter: 2 };
    case 'schlurft': return { arms: { L: [1.55 + Math.sin(lt * 3) * .08, .05], R: [1.6 - Math.sin(lt * 3) * .08, .05] }, legs: { L: [.25 + Math.sin(lt * 3) * .2, -.3], R: [.25 - Math.sin(lt * 3) * .2, -.3] }, lean: .08 + Math.sin(lt * 1.5) * .04 };
    case 'versteckt': return { arms: { L: [.9, -2.3], R: [.9, -2.3] }, legs: { L: [.9, -1.9], R: [.9, -1.9] }, bob: .16, jitter: 2 };
    case 'haende': return { arms: { L: [.9, -2.2], R: [.9, -2.2] }, legs: { L: [.14, -.04], R: [.14, -.04] } };
    default: return { arms: { L: [.3, -.1], R: [.3, -.1] }, legs: { L: [.1, -.04], R: [.1, -.04] }, bob: Math.sin(lt * 2.2) * .006 };
  }
}
function stick(ctx, sc, x, y, s, mood, act, lt, extra = {}) {
  const p = pose(act, lt);
  let jx = 0, jy = 0; if (p.jitter) { jx = Math.sin(lt * 60) * p.jitter; jy = Math.cos(lt * 53) * p.jitter * .6; }
  drawStick(ctx, figure(sc, { x: x + jx, y: y + jy, s, face: face(mood, lt), arms: p.arms, legs: p.legs, lean: p.lean || 0, bob: p.bob || 0, ...extra }));
  if (act === 'denkt') { const a = clamp((lt - .3) / .3); ctx.save(); ctx.globalAlpha = a; circle(ctx, x + s * .28, y - s * 1.05, s * .03); fillStroke(ctx, '#fff', 5); circle(ctx, x + s * .38, y - s * 1.2, s * .05); fillStroke(ctx, '#fff', 5); ellipse(ctx, x + s * .5, y - s * 1.42, s * .16, s * .12); fillStroke(ctx, '#fff', 6); text(ctx, '?', x + s * .5, y - s * 1.42, s * .16, INK, null, 0, 'Poppins', 700); ctx.restore(); }
  if (act === 'zittert' || mood === 'angst') sweat(ctx, x + s * .17, y - s * .93, s * .05, .9);
  const nm = extra.name !== undefined ? extra.name : (sc.figur || {}).name;
  if (nm && extra.name !== false) nameTag(ctx, nm, x, y - s * 1.18, Math.max(34, s * .07));
}
function nameTag(ctx, str, x, y, size) {
  ctx.font = `700 ${size}px Poppins`; const w = ctx.measureText(str).width + size * .9, h = size * 1.5;
  rrect(ctx, x - w / 2, y - h / 2, w, h, h / 2); fillStroke(ctx, '#fff', 5);
  text(ctx, str, x, y + 1, size, INK, null, 0, 'Poppins', 700);
}

// ---------- Orte (Hintergründe) ----------
function ground(ctx, top, bot, y = G - 30) { const g = ctx.createLinearGradient(0, y, 0, 2400); g.addColorStop(0, top); g.addColorStop(1, bot); ctx.fillStyle = g; ctx.fillRect(-1500, y, 4080, 2500); line(ctx, -1500, y, 2580, y, 8, 'rgba(34,28,34,.55)'); }
function stars(ctx, n, seed, t, yMax = 1100) { const R = rng(seed); for (let i = 0; i < n; i++) { const x = R() * 1600 - 260, y = R() * (yMax + 400) - 400, r = 1.5 + R() * 3.5; ctx.globalAlpha = .45 + .55 * Math.abs(Math.sin(t * (1 + R()) + i)); circle(ctx, x, y, r); ctx.fillStyle = '#fff'; ctx.fill(); } ctx.globalAlpha = 1; }
function moon(ctx, x, y, r) { ctx.save(); ctx.shadowColor = 'rgba(255,250,210,.7)'; ctx.shadowBlur = 80; circle(ctx, x, y, r); ctx.fillStyle = '#fff6d8'; ctx.fill(); ctx.restore(); circle(ctx, x - r * .3, y - r * .2, r * .18); ctx.fillStyle = 'rgba(200,190,150,.5)'; ctx.fill(); circle(ctx, x + r * .25, y + r * .3, r * .12); ctx.fill(); }
function tree(ctx, x, y, s, col = '#3fa35b', dark = false) {
  rrect(ctx, x - s * .08, y - s * .55, s * .16, s * .58, s * .04); fillStroke(ctx, dark ? '#2b1d22' : '#8a5a34', 6);
  ctx.beginPath(); [[0, -.85, .38], [-.25, -.65, .3], [.25, -.65, .3], [0, -1.15, .3]].forEach(([dx, dy, r]) => { ctx.moveTo(x + dx * s + r * s, y + dy * s); ctx.arc(x + dx * s, y + dy * s, r * s, 0, TAU); });
  fillStroke(ctx, dark ? '#1c2a26' : col, 7);
}
function building(ctx, x, w, h, col, seed, lit = .2) {
  const R = rng(seed); rrect(ctx, x, G - 30 - h, w, h + 40, 6); fillStroke(ctx, col, 6);
  for (let yy = G - h; yy < G - 90; yy += 90) for (let xx = x + 26; xx < x + w - 50; xx += 70) { rrect(ctx, xx, yy, 38, 52, 5); ctx.fillStyle = R() < lit ? '#ffe39a' : 'rgba(255,255,255,.35)'; ctx.fill(); }
}
function room(ctx, wall, floor, t, o = {}) {
  ctx.fillStyle = wall; ctx.fillRect(-1500, -1500, 4080, G + 1500);
  for (let x = -600; x < 1700; x += 130) { ctx.fillStyle = 'rgba(0,0,0,.035)'; ctx.fillRect(x, -1500, 60, G + 1500); }
  ground(ctx, floor, mix(floor.startsWith('#') ? floor : '#8a5a34', '#000000', .35));
  for (let x = -600; x < 1700; x += 160) line(ctx, x, G - 30, x - 260, 2400, 4, 'rgba(34,28,34,.18)');
  if (o.window) { const x = 160, y = 420; rrect(ctx, x, y, 300, 360, 10); ctx.save(); ctx.clip(); const g = ctx.createLinearGradient(0, y, 0, y + 360); g.addColorStop(0, o.night ? '#0e1840' : '#4fb2f0'); g.addColorStop(1, o.night ? '#28306a' : '#cdeefc'); ctx.fillStyle = g; ctx.fillRect(x, y, 300, 360); if (o.night) { stars(ctx, 14, 9, t, 700); moon(ctx, x + 210, y + 90, 40); } else drawCloud(ctx, x + 150, y + 140, 60, 3); ctx.restore(); rrect(ctx, x, y, 300, 360, 10); fillStroke(ctx, null, 12, '#5a3a26'); line(ctx, x + 150, y, x + 150, y + 360, 10, '#5a3a26'); line(ctx, x, y + 180, x + 300, y + 180, 10, '#5a3a26'); }
}
const PLACES = {
  strand(ctx, t) { drawSky(ctx, '#3ea6ee', '#c9ecfb', -400, 1000); drawSun(ctx, 860, 260, 90, t, .8); drawCloud(ctx, 260, 330, 95, 2); drawSea(ctx, 980, t); ground(ctx, '#f5d58a', '#d9a85a', G - 110); },
  meer(ctx, t) { drawSky(ctx, '#3ea6ee', '#c9ecfb', -400, 1000); drawCloud(ctx, 780, 300, 110, 5); drawSea(ctx, 1000, t, 2600); drawShip(ctx, 300, 1010, .5, t); },
  stadt(ctx, t) { drawSky(ctx, '#58b7f2', '#d8f1fd', -400, 1100); drawCloud(ctx, 800, 260, 90, 4); const R = rng(7); let x = -300; let i = 0; while (x < 1400) { const w = 180 + R() * 160, h = 380 + R() * 520; building(ctx, x, w, h, ['#7d8fb3', '#9aa7c7', '#6b7ca3', '#b3a6c9'][i++ % 4], i); x += w + 10; } ground(ctx, '#a7a2a8', '#6d6870'); },
  wald(ctx, t) { drawSky(ctx, '#62bdf0', '#dff4fd', -400, 1100); drawCloud(ctx, 300, 300, 90, 6); ctx.beginPath(); ctx.ellipse(300, G + 40, 900, 330, 0, Math.PI, 0); fillStroke(ctx, '#7cc46a', 6); [[-80, .9], [140, 1.2], [900, 1.1], [1120, .8], [420, .7], [700, .75]].forEach(([x, s], i) => tree(ctx, x, G - 20 - (s < .8 ? 120 : 0), s * 420, i % 2 ? '#3fa35b' : '#4fb565')); ground(ctx, '#5fb653', '#3c8a3e'); },
  feld(ctx, t) { drawSky(ctx, '#4fb2f0', '#dff4fd', -400, 1100); drawSun(ctx, 820, 300, 80, t, .7); drawCloud(ctx, 300, 380, 100, 8); ctx.beginPath(); ctx.ellipse(700, G + 60, 1100, 300, 0, Math.PI, 0); fillStroke(ctx, '#8fd16f', 6); ground(ctx, '#74c25c', '#4d9a43'); },
  nacht(ctx, t) { drawSky(ctx, '#070b26', '#2a2f6b', -400, 1200); stars(ctx, 70, 3, t); moon(ctx, 820, 320, 90); [[-60, .9], [1100, 1.0], [180, .6], [900, .65]].forEach(([x, s]) => tree(ctx, x, G - 20, s * 430, '#1c2a26', true)); ground(ctx, '#1b2433', '#0b0f18'); },
  haus(ctx, t) { room(ctx, '#e9d6b4', '#a9733f', t, { window: true }); rrect(ctx, 700, 470, 210, 160, 6); fillStroke(ctx, '#f4efe6', 10, '#7a5230'); emoji(ctx, '🖼️', 805, 550, 90); },
  kinderzimmer(ctx, t) { room(ctx, '#b9d7f2', '#c89a6a', t, { window: true, night: true }); },
  keller(ctx, t) { room(ctx, '#3a3440', '#2a2228', t); const R = rng(4); for (let i = 0; i < 26; i++) { rrect(ctx, R() * 1400 - 200, R() * 1100, 150, 70, 10); ctx.fillStyle = 'rgba(0,0,0,.18)'; ctx.fill(); } line(ctx, 540, -200, 540, 330, 4, '#111'); ctx.save(); ctx.shadowColor = 'rgba(255,220,120,.9)'; ctx.shadowBlur = 60; circle(ctx, 540, 360, 34); ctx.fillStyle = '#ffe9a8'; ctx.fill(); ctx.restore(); },
  schule(ctx, t, sc) { room(ctx, '#cfe3c6', '#b8875a', t); rrect(ctx, 150, 330, 780, 470, 16); fillStroke(ctx, '#244a3a', 16, '#8a5a34'); if (sc && sc.tafel) fitText(ctx, sc.tafel, 540, 565, 86, 680, '#f4f4ee', null, 0); },
  buero(ctx, t) { room(ctx, '#dfe6ee', '#8f98a6', t, { window: true }); rrect(ctx, 560, 980, 480, 40, 8); fillStroke(ctx, '#a0714a', 6); rrect(ctx, 700, 760, 220, 170, 12); fillStroke(ctx, '#2c3442', 8); rrect(ctx, 718, 778, 184, 134, 6); ctx.fillStyle = '#6fc3ff'; ctx.fill(); line(ctx, 810, 930, 810, 980, 12); },
  labor(ctx, t) { room(ctx, '#e4f1f6', '#9fb3c0', t); rrect(ctx, 520, 1000, 560, 36, 8); fillStroke(ctx, '#d7dde3', 6); emoji(ctx, '🧪', 640, 930, 120, -.1); emoji(ctx, '⚗️', 820, 925, 130); emoji(ctx, '🔬', 990, 925, 120); },
  weltall(ctx, t) { ctx.fillStyle = '#0a0620'; ctx.fillRect(-1500, -1500, 4080, 4500); stars(ctx, 110, 11, t, 1300); circle(ctx, 830, 380, 150); fillStroke(ctx, '#e0884a', 8); ctx.save(); ctx.translate(830, 380); ctx.rotate(-.35); ellipse(ctx, 0, 0, 250, 46); ctx.lineWidth = 12; ctx.strokeStyle = '#f4d29a'; ctx.stroke(); ctx.restore(); ground(ctx, '#b9b6c4', '#77748a'); [[200, 1400, 60], [760, 1600, 90], [480, 1330, 40]].forEach(([x, y, r]) => { ellipse(ctx, x, y, r, r * .35); ctx.fillStyle = 'rgba(40,30,60,.25)'; ctx.fill(); }); },
  wueste(ctx, t) { drawSky(ctx, '#f6a64b', '#fde2a6', -400, 1100); drawSun(ctx, 760, 330, 120, t, 1); ctx.beginPath(); ctx.ellipse(200, G + 60, 800, 260, 0, Math.PI, 0); fillStroke(ctx, '#f0c06c', 6); emoji(ctx, '🌵', 950, G - 150, 220); ground(ctx, '#f4cf7e', '#d9a24f'); },
  burg(ctx, t) { drawSky(ctx, '#7cc4ee', '#e2f4fc', -400, 1100); drawCloud(ctx, 260, 280, 90, 9); const c = '#9a96a8'; rrect(ctx, 380, 560, 520, 700, 4); fillStroke(ctx, c, 8); [[300, 420, 170], [820, 420, 170]].forEach(([x, y, w]) => { rrect(ctx, x, y, w, 840, 4); fillStroke(ctx, c, 8); for (let k = 0; k < 3; k++) { rrect(ctx, x + k * 62, y - 50, 44, 60, 3); fillStroke(ctx, c, 8); } }); rrect(ctx, 580, 960, 120, 300, 60); fillStroke(ctx, '#4a3326', 8); ground(ctx, '#6cba5a', '#3f8a3e'); },
  dorf(ctx, t) { drawSky(ctx, '#62bdf0', '#dff4fd', -400, 1100); drawCloud(ctx, 720, 280, 90, 12); [[60, 300, '#e9c69a'], [420, 260, '#f0d9b5'], [760, 320, '#e2b98e']].forEach(([x, w, col], i) => { rrect(ctx, x, G - 360, w, 340, 6); fillStroke(ctx, col, 7); path(ctx, [[x - 30, G - 360], [x + w / 2, G - 560], [x + w + 30, G - 360]]); fillStroke(ctx, '#b3473a', 7); rrect(ctx, x + w / 2 - 40, G - 160, 80, 140, 8); fillStroke(ctx, '#6b4428', 6); }); ground(ctx, '#7cc46a', '#4e9a46'); },
  farbe(ctx, t, sc) { const a = (sc && sc.farbcode) || '#ffcf3f'; ctx.fillStyle = a; ctx.fillRect(-1500, -1500, 4080, 4500); ctx.save(); ctx.translate(540, 760); ctx.rotate(t * .15); for (let i = 0; i < 16; i++) { ctx.rotate(TAU / 16); path(ctx, [[0, 0], [-110, -1700], [110, -1700]]); ctx.fillStyle = 'rgba(255,255,255,.16)'; ctx.fill(); } ctx.restore(); },
};
// ---------- mehr Orte für Gruseliges ----------
function grave(ctx, x, y, s, tilt, label) { ctx.save(); ctx.translate(x, y); ctx.rotate(tilt); ctx.beginPath(); ctx.moveTo(-s * .5, 0); ctx.lineTo(-s * .5, -s * .9); ctx.arc(0, -s * .9, s * .5, Math.PI, 0); ctx.lineTo(s * .5, 0); ctx.closePath(); fillStroke(ctx, '#8d8a99', 7); if (label) text(ctx, label, 0, -s * .75, s * .28, '#4d4a58', null, 0, 'Poppins', 700); else { line(ctx, 0, -s * 1.05, 0, -s * .45, 7, '#5d5a68'); line(ctx, -s * .2, -s * .85, s * .2, -s * .85, 7, '#5d5a68'); } ctx.restore(); }
function deadTree(ctx, x, y, s) { ctx.save(); ctx.translate(x, y); ctx.strokeStyle = '#120d16'; ctx.lineCap = 'round'; const br = (len, w, a, d) => { if (d > 4) return; ctx.lineWidth = w; ctx.beginPath(); ctx.moveTo(0, 0); ctx.lineTo(0, -len); ctx.stroke(); ctx.save(); ctx.translate(0, -len); [-.5, .45].forEach((da, k) => { ctx.save(); ctx.rotate(da + (k ? .1 : -.1) * d); br(len * .68, w * .65, a, d + 1); ctx.restore(); }); ctx.restore(); }; br(s * .45, s * .07, 0, 0); ctx.restore(); }
function fog(ctx, t, a = .5, y = G - 120) { ctx.save(); ctx.setTransform(1, 0, 0, 1, 0, 0); for (let i = 0; i < 7; i++) { const x = ((i * 260 + t * (30 + i * 9)) % 1700) - 300; const g = ctx.createRadialGradient(x, y + (i % 3) * 60, 20, x, y + (i % 3) * 60, 420); g.addColorStop(0, `rgba(210,215,235,${a * .45})`); g.addColorStop(1, 'rgba(210,215,235,0)'); ctx.fillStyle = g; ctx.fillRect(x - 420, y - 400, 840, 900); } ctx.restore(); }
Object.assign(PLACES, {
  friedhof(ctx, t) { drawSky(ctx, '#0b0a24', '#3b2f63', -400, 1200); stars(ctx, 50, 21, t); moon(ctx, 800, 300, 110); deadTree(ctx, 140, G - 20, 900); deadTree(ctx, 980, G - 10, 700); ground(ctx, '#2a2c3a', '#11121a'); [[260, G + 10, 150, -.08, 'RIP'], [560, G - 5, 120, .05], [820, G + 25, 160, .1, 'RIP'], [420, G + 140, 110, -.12], [700, G + 160, 100, .06]].forEach(g => grave(ctx, ...g)); fog(ctx, t, .55); },
  spukhaus(ctx, t) { drawSky(ctx, '#0c0b26', '#40326b', -400, 1200); stars(ctx, 40, 31, t); moon(ctx, 230, 280, 90); const c = '#3a3346'; path(ctx, [[260, 620], [540, 330], [820, 620]]); fillStroke(ctx, '#2a2433', 8); rrect(ctx, 300, 610, 480, 640, 4); fillStroke(ctx, c, 8); rrect(ctx, 720, 380, 60, 160, 4); fillStroke(ctx, c, 7); const flick = Math.sin(t * 9) > .2 ? 1 : .55; [[360, 700], [600, 700], [360, 930], [600, 930]].forEach(([x, y], i) => { rrect(ctx, x, y, 120, 150, 6); ctx.fillStyle = i === 1 ? `rgba(255,214,120,${flick})` : '#141019'; ctx.fill(); ctx.lineWidth = 7; ctx.strokeStyle = INK; ctx.stroke(); line(ctx, x + 60, y, x + 60, y + 150, 6); }); rrect(ctx, 490, 1080, 100, 170, 50); fillStroke(ctx, '#1a1320', 7); deadTree(ctx, 980, G, 820); ground(ctx, '#232030', '#0e0c14'); fog(ctx, t, .4); },
  krankenhaus(ctx, t) { room(ctx, '#bcd8cc', '#7f9a90', t); for (let y = 0; y < G - 30; y += 70) line(ctx, -600, y, 1700, y, 3, 'rgba(40,70,60,.18)'); for (let x = -600; x < 1700; x += 70) line(ctx, x, 0, x, G - 30, 3, 'rgba(40,70,60,.12)'); rrect(ctx, 600, 1010, 470, 60, 12); fillStroke(ctx, '#eef3f6', 7); rrect(ctx, 600, 960, 130, 60, 20); fillStroke(ctx, '#fff', 6); line(ctx, 620, 1070, 620, 1220, 8); line(ctx, 1050, 1070, 1050, 1220, 8); const on = Math.sin(t * 13) > -.6; line(ctx, 540, -100, 540, 240, 4, '#111'); rrect(ctx, 420, 240, 240, 30, 8); ctx.fillStyle = on ? '#f4ffe9' : '#56605a'; ctx.fill(); },
  strasse(ctx, t) { drawSky(ctx, '#0a0d24', '#2e3563', -400, 1200); stars(ctx, 30, 41, t); const R = rng(17); let x = -300, i = 0; while (x < 1400) { const w = 180 + R() * 160, h = 380 + R() * 480; building(ctx, x, w, h, ['#252a44', '#2d3150', '#1f2440'][i++ % 3], i, .12); x += w + 10; } ground(ctx, '#2b2b33', '#121218'); line(ctx, 880, G - 30, 880, 560, 14, '#1a1a22'); line(ctx, 880, 560, 800, 540, 12, '#1a1a22'); const on = Math.sin(t * 7) > -.4 ? 1 : .3; ctx.save(); ctx.globalAlpha = on; const g = ctx.createRadialGradient(800, 560, 10, 800, 900, 520); g.addColorStop(0, 'rgba(255,225,150,.6)'); g.addColorStop(1, 'rgba(255,225,150,0)'); ctx.fillStyle = g; ctx.beginPath(); ctx.moveTo(780, 560); ctx.lineTo(520, G); ctx.lineTo(1080, G); ctx.closePath(); ctx.fill(); circle(ctx, 800, 560, 24); ctx.fillStyle = '#ffe9a8'; ctx.fill(); ctx.restore(); },
  dunkelwald(ctx, t) { drawSky(ctx, '#05060f', '#1b2333', -400, 1200); moon(ctx, 760, 260, 70); [[-80, 1.1], [150, 1.3], [420, .8], [700, 1.2], [950, 1.0], [1150, 1.3]].forEach(([x, s]) => deadTree(ctx, x, G, s * 850)); ground(ctx, '#151a1e', '#07090b'); fog(ctx, t, .45); },
});
// ---------- Wetter und Licht (sc.wetter: regen, nebel, blitz, schnee) ----------
function weather(ctx, sc, lt) {
  const w = sc.wetter; if (!w) return;
  ctx.save(); ctx.setTransform(1, 0, 0, 1, 0, 0);
  if (w === 'regen' || w === 'blitz') { ctx.strokeStyle = 'rgba(190,210,255,.45)'; ctx.lineWidth = 4; const R = rng(5); ctx.beginPath(); for (let i = 0; i < 140; i++) { const x = R() * 1300 - 100, sp = 1800 + R() * 900, y = ((R() * 2200 + lt * sp) % 2200) - 200; ctx.moveTo(x, y); ctx.lineTo(x - 18, y + 60); } ctx.stroke(); }
  if (w === 'schnee') { const R = rng(8); ctx.fillStyle = 'rgba(255,255,255,.85)'; for (let i = 0; i < 90; i++) { const x = (R() * 1200 + Math.sin(lt + i) * 30) % 1200, y = ((R() * 2100 + lt * (90 + R() * 80)) % 2100) - 100; circle(ctx, x, y, 4 + R() * 6); ctx.fill(); } }
  if (w === 'nebel') { ctx.restore(); fog(ctx, lt, .7, 1000); fog(ctx, lt * 1.3, .5, 1300); return; }
  if (w === 'blitz') { const p = lt % 2.6; if (p < .09 || (p > .16 && p < .21)) { ctx.fillStyle = 'rgba(235,240,255,.55)'; ctx.fillRect(0, 0, W, H); ctx.strokeStyle = '#fff'; ctx.lineWidth = 9; ctx.beginPath(); let x = 760, y = -20; ctx.moveTo(x, y); const R = rng(Math.floor(lt / 2.6) + 3); while (y < 700) { x += (R() - .5) * 160; y += 80 + R() * 60; ctx.lineTo(x, y); } ctx.stroke(); } }
  ctx.restore();
}
// ---------- Monster ----------
function ghost(ctx, x, y, s, lt, a = 1) {
  ctx.save(); ctx.globalAlpha = a * (.75 + Math.sin(lt * 3) * .15); ctx.translate(x, y + Math.sin(lt * 2.2) * s * .05);
  ctx.beginPath(); ctx.moveTo(-s * .35, 0); ctx.lineTo(-s * .35, -s * .55); ctx.arc(0, -s * .55, s * .35, Math.PI, 0); ctx.lineTo(s * .35, 0);
  for (let k = 0; k < 4; k++) { const xx = s * .35 - (k + .5) * s * .175; ctx.quadraticCurveTo(xx + s * .05, -s * .08 + Math.sin(lt * 6 + k) * s * .03, xx - s * .09, 0); }
  ctx.closePath(); ctx.shadowColor = 'rgba(200,220,255,.9)'; ctx.shadowBlur = 50; fillStroke(ctx, '#f4f6ff', s * .02);
  ctx.shadowBlur = 0; ellipse(ctx, -s * .12, -s * .6, s * .06, s * .09); ellipse(ctx, s * .12, -s * .6, s * .06, s * .09); ctx.fillStyle = '#1a1424'; ctx.fill(); ellipse(ctx, 0, -s * .38, s * .07, s * .1); ctx.fill(); ctx.restore();
}
function shadowMan(ctx, x, y, s, lt, a = 1) {
  ctx.save(); ctx.globalAlpha = a; drawStick(ctx, { x, y, s, sil: '#06050a', eyesGlow: true, face: { eyes: 'normal', pupil: .2 }, armLen: 1.5, arms: { L: [.5, -.2], R: [.5, -.2] }, legs: { L: [.1, 0], R: [.1, 0] }, shadow: false, cols: PAL.navy, hat: 'keiner' }); ctx.restore();
}
function zombie(ctx, sc, x, y, s, lt, flip = -1, col = 'gruen') {
  const z = { ...sc, figur: { farbe: col, hut: 'keiner', art: 'zombie' } };
  stick(ctx, z, x, y, s, 'k_o', 'schlurft', lt, { flip, name: false, face: { eyes: 'normal', pupil: .25, mouth: 'teeth', browAng: .3, t: lt } });
}
function drawPlace(ctx, ort, t, sc) { (PLACES[ort] || PLACES.feld)(ctx, t, sc); }
const DARK_PLACES = { nacht: 1, keller: 1, weltall: 1, kinderzimmer: 1 };

// ---------- Szenentypen ----------
const TYPES = {
  figur(ctx, sc, lt, d) {
    applyCam(ctx, cam(lt, d, 1, 1.09, sc.i)); drawPlace(ctx, sc.ort, lt, sc);
    const run = sc.aktion === 'rennt'; const x = run ? kf(lt, [[0, -150], [d, 1230]], t => t) : 540;
    if (sc.objekt) { const k = popIn(lt, .25); const fy = 430 + Math.sin(lt * 2.4) * 18; emoji(ctx, sc.objekt, 840, fy, 240 * k, Math.sin(lt * 1.6) * .08); }
    stick(ctx, sc, x, G, 760, sc.gefuehl, sc.aktion, lt);
    if (sc.text) { const k = popIn(lt, .15); ctx.save(); ctx.translate(540, 300); ctx.scale(k, k); sign(ctx, sc.text, 0, 0, 70); ctx.restore(); }
  },
  zwei(ctx, sc, lt, d) {
    applyCam(ctx, cam(lt, d, 1.02, 1.08, sc.i)); drawPlace(ctx, sc.ort, lt, sc);
    const b = sc.zweite || {}; const sc2 = { ...sc, figur: { farbe: b.farbe || 'blau', hut: b.hut || 'keiner' } };
    stick(ctx, sc, 300, G, 620, sc.gefuehl, sc.aktion || 'zeigt', lt);
    const react = lt > d * .45;
    stick(ctx, sc2, 780, G, 620, react ? (b.gefuehl || 'staunen') : 'neutral', react ? (b.aktion || 'schockiert') : 'steht', lt, { flip: -1 });
    if (react && lt < d * .45 + .6) { const k = popIn(lt, d * .45, .2); ctx.save(); ctx.translate(860, 520); ctx.scale(k, k); text(ctx, '!', 0, 0, 160, '#ffe14d', INK, 16, 'Poppins', 700); ctx.restore(); }
    if (sc.text) sign(ctx, sc.text, 540, 300, 64);
  },
  gruppe(ctx, sc, lt, d) {
    applyCam(ctx, cam(lt, d, 1, 1.06, sc.i)); drawPlace(ctx, sc.ort, lt, sc);
    const n = clamp(sc.anzahl || 5, 3, 7), cols = ['blau', 'gelb', 'gruen', 'lila', 'navy', 'rot', 'blau'];
    for (let k = 0; k < n; k++) { const x = 140 + k * (800 / (n - 1)), y = G - (k % 2) * 60; const s2 = { ...sc, figur: { farbe: k === Math.floor(n / 2) ? ((sc.figur || {}).farbe || 'rot') : cols[k], hut: k === Math.floor(n / 2) ? ((sc.figur || {}).hut || 'keiner') : 'keiner' } }; stick(ctx, s2, x, y, 440, sc.gefuehl, (sc.aktion === 'jubelt' || k % 2) ? sc.aktion : 'steht', lt + k * .37, { flip: x > 540 ? -1 : 1 }); }
    if (sc.text) sign(ctx, sc.text, 540, 330, 70);
  },
  objekt(ctx, sc, lt, d) {
    applyCam(ctx, cam(lt, d, 1, 1.05, sc.i)); drawPlace(ctx, sc.ort || 'farbe', lt, sc);
    darkness(ctx, sc.ort && sc.ort !== 'farbe' ? .35 : 0);
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    const k = popIn(lt, .05, .4);
    ctx.save(); ctx.translate(540, 760); ctx.scale(k, k); ctx.rotate(lt * .25); burst(ctx, 0, 0, 430, 14, '#fff3b0', 4, .78); ctx.restore();
    emoji(ctx, sc.objekt || '❓', 540, 770 + Math.sin(lt * 2) * 14, 470 * k, Math.sin(lt * 1.4) * .06);
    if (sc.text) { const k2 = popIn(lt, .3); ctx.save(); ctx.translate(540, 1130); ctx.scale(k2, k2); sign(ctx, sc.text, 0, 0, 84); ctx.restore(); }
  },
  zahl(ctx, sc, lt, d) {
    ctx.setTransform(1, 0, 0, 1, 0, 0); PLACES.farbe(ctx, lt, { farbcode: sc.farbcode || '#ffcf3f' });
    const target = Number(sc.zahl) || 0; const v = target * easeOut(clamp(lt / Math.min(1.4, d * .6)));
    const dec = String(sc.zahl).includes('.') || String(sc.zahl).includes(',') ? 1 : 0;
    const str = (dec ? v.toFixed(1).replace('.', ',') : Math.round(v).toLocaleString('de-DE'));
    const k = popIn(lt, 0, .3); const [sx, sy] = shake(lt, 4, .6, 2);
    if (sc.objekt) emoji(ctx, sc.objekt, 540, 430 + Math.sin(lt * 2.5) * 15, 250 * k);
    ctx.save(); ctx.translate(540 + sx, 800 + sy); ctx.scale(k, k); fitText(ctx, str, 0, 0, 260, 940, '#fff', INK, 26); ctx.restore();
    if (sc.einheit) fitText(ctx, sc.einheit.toUpperCase(), 540, 1010, 110, 900, '#ffe14d', INK, 16);
  },
  jahr(ctx, sc, lt, d) {
    applyCam(ctx, cam(lt, d, 1.02, 1.08, sc.i)); ctx.fillStyle = '#6a3f22'; ctx.fillRect(-1500, -1500, 4080, 4500);
    for (let y = -200; y < 2400; y += 190) line(ctx, -600, y, 1700, y, 4, 'rgba(0,0,0,.18)');
    ctx.save(); ctx.translate(540, 820); ctx.rotate(-.03 + Math.sin(lt) * .01);
    rrect(ctx, -390, -460, 780, 880, 18); ctx.fillStyle = 'rgba(0,0,0,.3)'; ctx.fill(); rrect(ctx, -400, -470, 780, 880, 18); fillStroke(ctx, '#f4e6c6', 9);
    fitText(ctx, String(sc.jahr || ''), -10, -150, 230, 680, '#4a2614', null, 0, 'Poppins');
    line(ctx, -280, 10, 260, 10, 6, '#4a2614');
    if (sc.text) fitText(ctx, sc.text, -10, 140, 76, 660, '#4a2614', null, 0, 'Poppins');
    if (sc.objekt) emoji(ctx, sc.objekt, 250, 310, 140, .1);
    const st = kf(lt, [[.5, 3], [.75, 1, backOut]]); if (lt > .5 && sc.stempel) { ctx.save(); ctx.translate(120, -340); ctx.rotate(-.2); ctx.scale(st, st); ctx.globalAlpha = .85; rrect(ctx, -230, -70, 460, 140, 16); ctx.lineWidth = 14; ctx.strokeStyle = '#d42a2a'; ctx.stroke(); fitText(ctx, sc.stempel.toUpperCase(), 0, 6, 84, 400, '#d42a2a', null, 0); ctx.restore(); }
    ctx.restore();
  },
  liste(ctx, sc, lt, d) {
    applyCam(ctx, cam(lt, d, 1, 1.05, sc.i)); ctx.fillStyle = '#2f6fb3'; ctx.fillRect(-1500, -1500, 4080, 4500);
    ctx.save(); ctx.translate(540, 800); ctx.rotate(.02);
    rrect(ctx, -400, -500, 800, 960, 20); fillStroke(ctx, '#fffaf0', 9);
    if (sc.text) fitText(ctx, sc.text.toUpperCase(), 0, -380, 86, 680, '#4a2614', null, 0);
    line(ctx, -300, -300, 300, -300, 6, '#4a2614');
    const items = (sc.punkte || []).slice(0, 4), step = Math.max(.35, (d - .6) / Math.max(1, items.length));
    items.forEach((s, i) => { const y = -170 + i * 160; const a = clamp((lt - .2 - i * step) / .25); ctx.globalAlpha = .35 + .65 * a; rrect(ctx, -330, y - 38, 76, 76, 10); fillStroke(ctx, '#fffaf0', 6); ctx.font = '600 62px Poppins'; fitText(ctx, s, 60, y, 62, 560, '#4a2614', null, 0); ctx.globalAlpha = 1; const ck = backOut(a); if (a > 0) { ctx.save(); ctx.translate(-292, y); ctx.scale(ck, ck); path(ctx, [[-26, 0], [-6, 22], [32, -30]], false); ctx.lineWidth = 16; ctx.strokeStyle = '#2f9e4f'; ctx.lineCap = 'round'; ctx.stroke(); ctx.restore(); } });
    ctx.restore();
  },
  vergleich(ctx, sc, lt, d) {
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.fillStyle = '#e0392f'; ctx.fillRect(0, 0, 540, H); ctx.fillStyle = '#2f63c9'; ctx.fillRect(540, 0, 540, H);
    const L = sc.links || {}, R = sc.rechts || {}; const k1 = popIn(lt, .05), k2 = popIn(lt, .35);
    emoji(ctx, L.objekt || '❓', 270, 720 + Math.sin(lt * 2) * 12, 300 * k1); emoji(ctx, R.objekt || '❓', 810, 720 + Math.cos(lt * 2) * 12, 300 * k2);
    if (L.text) fitText(ctx, L.text, 270, 1000, 72, 460, '#fff', INK, 12); if (R.text) fitText(ctx, R.text, 810, 1000, 72, 460, '#fff', INK, 12);
    const kv = popIn(lt, .6, .3); ctx.save(); ctx.translate(540, 720); ctx.scale(kv, kv); circle(ctx, 0, 0, 105); fillStroke(ctx, '#ffe14d', 10); text(ctx, 'VS', 0, 4, 92, INK, null, 0, 'Poppins', 700); ctx.restore();
  },
  horror(ctx, sc, lt, d) {
    const ort = sc.ort || 'keller';
    const flick = (Math.sin(lt * 37) > .93 || (lt % 2.3) < .05) ? .25 : 0;
    applyCam(ctx, cam(lt, d, 1.04, 1.14, sc.i)); drawPlace(ctx, ort, lt, sc);
    const who = sc.aktion || 'zittert';
    stick(ctx, sc, who === 'faellt' ? 520 : 400, G, 640, sc.gefuehl || 'angst', who, lt);
    ctx.setTransform(1, 0, 0, 1, 0, 0); darkness(ctx, .8 + flick, '#04030a');
    // Taschenlampen-Kegel wandert durch den Raum
    const ang = -.15 + Math.sin(lt * .9) * .35;
    ctx.save(); ctx.globalCompositeOperation = 'lighter'; ctx.translate(430, 820); ctx.rotate(ang);
    const g = ctx.createLinearGradient(0, 0, 900, 0); g.addColorStop(0, 'rgba(255,230,160,.42)'); g.addColorStop(1, 'rgba(255,230,160,0)');
    ctx.beginPath(); ctx.moveTo(0, -12); ctx.lineTo(950, -260); ctx.lineTo(950, 260); ctx.lineTo(0, 12); ctx.fillStyle = g; ctx.fill(); ctx.restore();
    // die Figur bleibt schwach sichtbar
    ctx.save(); ctx.globalAlpha = .55; applyCam(ctx, cam(lt, d, 1.04, 1.14, sc.i)); stick(ctx, sc, who === 'faellt' ? 520 : 400, G, 640, sc.gefuehl || 'angst', who, lt); ctx.restore();
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    // leuchtende Augen im Dunkeln
    const ea = clamp((lt - d * .35) / .4); const blink = (lt % 3.1) < .12 ? .1 : 1;
    if (ea > 0) { ctx.save(); ctx.globalAlpha = ea; ctx.shadowColor = sc.augen || '#ff3b2f'; ctx.shadowBlur = 40; [[790, 700], [880, 690]].forEach(([x, y]) => { ellipse(ctx, x, y, 30, 18 * blink, .1); ctx.fillStyle = sc.augen || '#ff3b2f'; ctx.fill(); }); ctx.restore(); }
    if (sc.objekt) emoji(ctx, sc.objekt, 820, 1020, 200 * clamp((lt - d * .6) / .3), 0, .9);
    if (sc.text) { ctx.globalAlpha = clamp(lt / .4); fitText(ctx, sc.text.toUpperCase(), 540, 300, 80, 900, '#e8e3f0', '#000', 12); ctx.globalAlpha = 1; }
  },
};

Object.assign(TYPES, {
  monster(ctx, sc, lt, d) {
    const ort = sc.ort || 'friedhof', dark = DARK_PLACES[ort] || ['friedhof', 'spukhaus', 'strasse', 'dunkelwald'].includes(ort);
    applyCam(ctx, cam(lt, d, 1.02, 1.12, sc.i)); drawPlace(ctx, ort, lt, sc);
    const m = sc.monster || 'zombie', near = ease(clamp(lt / Math.max(1, d * .9)));
    const hero = sc.aktion || (lt > d * .5 ? 'rennt' : 'zittert');
    const hx = hero === 'rennt' ? kf(lt, [[d * .5, 300], [d, -250]], t => t) : 300;
    stick(ctx, sc, hx, G, 600, sc.gefuehl || 'angst', hero, lt, { flip: hero === 'rennt' ? -1 : 1 });
    if (m === 'zombie') { const n = clamp(sc.anzahl || 1, 1, 4); for (let k = n - 1; k >= 0; k--) zombie(ctx, sc, lerp(1020, 760, near) + k * 150, G - k * 30, 600 - k * 60, lt + k * .7, -1, ['gruen', 'blau', 'navy', 'lila'][k]); }
    else if (m === 'geist') ghost(ctx, lerp(1000, 780, near), 980, 520, lt, clamp(lt / .5));
    else if (m === 'schatten') shadowMan(ctx, lerp(1000, 780, near), G, 820, lt, clamp(lt / .8));
    else emoji(ctx, m, lerp(1000, 780, near), 900, 380, Math.sin(lt * 3) * .1);
    if (dark) { ctx.setTransform(1, 0, 0, 1, 0, 0); const g = ctx.createRadialGradient(540, 900, 300, 540, 960, 1300); g.addColorStop(0, 'rgba(0,0,0,0)'); g.addColorStop(1, 'rgba(0,0,0,.6)'); ctx.fillStyle = g; ctx.fillRect(0, 0, W, H); }
    weather(ctx, sc, lt);
    if (sc.text) { ctx.setTransform(1, 0, 0, 1, 0, 0); fitText(ctx, sc.text.toUpperCase(), 540, 290, 84, 900, '#ffe14d', INK, 14); }
  },
  titel(ctx, sc, lt, d) {
    ctx.setTransform(1, 0, 0, 1, 0, 0); drawPlace(ctx, sc.ort || 'spukhaus', lt, sc); darkness(ctx, .45);
    weather(ctx, sc, lt);
    const k = popIn(lt, .1, .5), sh = shake(lt, lt < .6 ? 10 : 2, 1, 4);
    ctx.save(); ctx.translate(540 + sh[0], 380 + sh[1]); ctx.scale(k, k); ctx.rotate(-.04);
    fitText(ctx, (sc.serie || sc.text || '').toUpperCase(), 0, 0, 120, 960, '#f3eefc', '#000', 20);
    if (sc.teil) { const k2 = popIn(lt, .45, .3); ctx.save(); ctx.translate(0, 160); ctx.scale(k2, k2); sign(ctx, 'TEIL ' + sc.teil, 0, 0, 80, '#e0392f'); ctx.restore(); }
    ctx.restore();
    if (sc.figur && sc.figur.name) { applyCam(ctx, cam(lt, d, 1, 1.05, sc.i)); stick(ctx, sc, 540, G, 520, sc.gefuehl || 'cool', sc.aktion || 'steht', lt); }
  },
});
// Wetter auch über allen anderen Szenen, wenn angegeben
['figur', 'zwei', 'gruppe', 'horror', 'objekt'].forEach(k => { const f = TYPES[k]; TYPES[k] = (ctx, sc, lt, d) => { f(ctx, sc, lt, d); if (sc.monster && k !== 'objekt') { applyCam(ctx, cam(lt, d, 1, 1.08, sc.i)); if (sc.monster === 'geist') ghost(ctx, 860, 760, 360, lt); else if (sc.monster === 'schatten') shadowMan(ctx, 900, G, 700, lt, .9); else if (sc.monster === 'zombie') zombie(ctx, sc, 900, G, 520, lt); } weather(ctx, sc, lt); }; });

// ---------- Plan -> Einstellungen ----------
(function build() {
  const list = PLAN.scenes;
  list.forEach((sc, i) => {
    sc.i = i;
    const typ = TYPES[sc.typ] ? sc.typ : 'figur';
    SHOTS.push({ start: sc.start, end: sc.end, tr: i < list.length - 1 ? 'whip' : 'cut', draw(ctx, lt) { TYPES[typ](ctx, sc, lt, sc.end - sc.start); } });
  });
})();
