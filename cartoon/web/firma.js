// ---------- Firmen-Spiel: "Für jeden Abonnenten stelle ich einen Mitarbeiter in meiner Autofirma ein" ----------
// Szene "firma": Autofabrik mit einem Strichmännchen pro Mitarbeiter (Namen der Abonnenten über den Köpfen),
// Autos entstehen am Fließband, Kontostand oben zählt hoch, neue Leute fallen ins Bild.
// Felder: mitarbeiter (Zahl), neu (wie viele davon neu sind), geld / geld_neu (Kontostand vorher/nachher),
// pro_tag (Einnahmen am Tag), stufe (garage, werkstatt, fabrik, grossfabrik, konzern), name (Firmenname),
// thema (autos, burger, rakete, games), level (0-4), stufe_label (Text oben rechts), icon (Emoji im Kopf),
// namen (Liste, neueste zuerst; gehören den Arbeitern vorne), text (Schild), chef (true: Chef steht vorne).
// scenes.js übernimmt window.EXTRA_TYPES in TYPES; Helfer (stick, emoji, sign, popIn, cam ...) kommen von dort.
const FIRMA_STUFEN = {
  garage: { label: 'HINTERHOF-GARAGE' },
  werkstatt: { label: 'WERKSTATT' },
  fabrik: { label: 'AUTOFABRIK' },
  grossfabrik: { label: 'GROSSFABRIK' },
  konzern: { label: 'WELTKONZERN' },
};
const FIRMA_COLS = ['blau', 'gelb', 'gruen', 'lila', 'navy', 'rot'];
const CAR_COLS = ['#e0392f', '#2f63c9', '#f2b52a', '#3fa35b', '#7a4bc4', '#ff7a1a', '#1fb5b5', '#ececec'];
const euro = v => Math.round(v).toLocaleString('de-DE') + ' €';

// ---------- Auto von der Seite: prog 0 = nur Rahmen, .5 = grau grundiert, 1 = lackiert mit Licht ----------
function carSide(ctx, x, y, w, col, prog, t, spin = 0) {
  const h = w * .42, wr = w * .13, lw = Math.max(4, w * .022);
  const wheel = (wx) => {
    circle(ctx, wx, y - wr, wr); fillStroke(ctx, '#2b2630', lw);
    circle(ctx, wx, y - wr, wr * .5); fillStroke(ctx, '#c9ced6', lw * .7);
    for (let k = 0; k < 3; k++) { const a = spin + k * 2.09; line(ctx, wx, y - wr, wx + Math.cos(a) * wr * .45, y - wr + Math.sin(a) * wr * .45, lw * .6, '#6d6870'); }
  };
  const by = y - wr * 1.05; // Unterkante Karosserie
  if (prog < .34) { // nur Rahmen und Räder
    line(ctx, x - w * .46, by - h * .12, x + w * .46, by - h * .12, lw * 1.6, '#5d6470');
    line(ctx, x - w * .3, by - h * .12, x - w * .3, by - h * .32, lw, '#5d6470'); line(ctx, x + w * .25, by - h * .12, x + w * .25, by - h * .32, lw, '#5d6470');
    rrect(ctx, x - w * .12, by - h * .36, w * .22, h * .22, 6); fillStroke(ctx, '#8a8f99', lw * .8); // Motor
    wheel(x - w * .3); wheel(x + w * .3); return;
  }
  const paint = prog < .67 ? '#b8bcc4' : col;
  ctx.beginPath();
  ctx.moveTo(x - w * .5, by); ctx.lineTo(x - w * .5, by - h * .42); ctx.quadraticCurveTo(x - w * .48, by - h * .52, x - w * .36, by - h * .54);
  ctx.lineTo(x - w * .22, by - h * .56); ctx.lineTo(x - w * .1, by - h * .95); ctx.lineTo(x + w * .2, by - h * .95); ctx.lineTo(x + w * .33, by - h * .58);
  ctx.quadraticCurveTo(x + w * .5, by - h * .54, x + w * .5, by - h * .36); ctx.lineTo(x + w * .5, by); ctx.closePath();
  fillStroke(ctx, paint, lw);
  // Fenster
  path(ctx, [[x - w * .19, by - h * .58], [x - w * .09, by - h * .87], [x + .03 * w, by - h * .87], [x + .03 * w, by - h * .58]]); fillStroke(ctx, prog < .67 ? '#d6dbe2' : '#9fd8f7', lw * .7);
  path(ctx, [[x + w * .07, by - h * .58], [x + w * .07, by - h * .87], [x + w * .18, by - h * .87], [x + w * .28, by - h * .58]]); fillStroke(ctx, prog < .67 ? '#d6dbe2' : '#9fd8f7', lw * .7);
  if (prog >= .67) {
    ctx.fillStyle = 'rgba(255,255,255,.35)'; ctx.fillRect(x - w * .45, by - h * .46, w * .85, h * .05); // Glanz
    circle(ctx, x + w * .45, by - h * .4, w * .035); ctx.fillStyle = '#fff6b0'; ctx.fill();
    ctx.save(); ctx.globalAlpha = .25 + .15 * Math.sin(t * 6); const g = ctx.createRadialGradient(x + w * .5, by - h * .4, 2, x + w * .5, by - h * .4, w * .3); g.addColorStop(0, '#fff6b0'); g.addColorStop(1, 'rgba(255,246,176,0)'); ctx.fillStyle = g; ctx.fillRect(x + w * .4, by - h * .7, w * .4, h * .6); ctx.restore();
    rrect(ctx, x - w * .5, by - h * .32, w * .05, h * .08, 3); ctx.fillStyle = '#e0392f'; ctx.fill();
  }
  line(ctx, x - w * .02, by - h * .5, x - w * .02, by - h * .05, lw * .6, 'rgba(34,28,34,.4)');
  wheel(x - w * .3); wheel(x + w * .3);
}

function sparks(ctx, x, y, t, seed, s = 1) {
  const R = rng(seed + Math.floor(t * 12)); if (R() < .45) return;
  ctx.save(); ctx.globalCompositeOperation = 'lighter';
  const g = ctx.createRadialGradient(x, y, 1, x, y, 40 * s); g.addColorStop(0, 'rgba(255,240,170,.9)'); g.addColorStop(1, 'rgba(255,170,40,0)'); ctx.fillStyle = g; ctx.fillRect(x - 40 * s, y - 40 * s, 80 * s, 80 * s);
  for (let k = 0; k < 7; k++) { const a = -Math.PI / 2 + (R() - .5) * 2.6, l = (18 + R() * 40) * s; line(ctx, x, y, x + Math.cos(a) * l, y + Math.sin(a) * l, 3 * s, R() < .5 ? '#ffe14d' : '#ff9a2e'); }
  ctx.restore();
}

function robotArm(ctx, x, top, reach, t, seed) {
  // hängt von der Decke, schwenkt über dem Band
  const a1 = .25 + Math.sin(t * 1.6 + seed) * .35, a2 = .9 + Math.sin(t * 2.3 + seed * 2) * .45;
  const l1 = reach * .55, l2 = reach * .5;
  const ex = x + Math.sin(a1) * l1, ey = top + Math.cos(a1) * l1, hx = ex - Math.sin(a2 - a1) * l2, hy = ey + Math.cos(a2 - a1) * l2;
  rrect(ctx, x - 60, top - 40, 120, 50, 10); fillStroke(ctx, '#3b3442', 7);
  line(ctx, x, top, ex, ey, 34, INK); line(ctx, x, top, ex, ey, 22, '#ff8a1a');
  line(ctx, ex, ey, hx, hy, 28, INK); line(ctx, ex, ey, hx, hy, 17, '#ff8a1a');
  circle(ctx, ex, ey, 20); fillStroke(ctx, '#ffd23a', 6); circle(ctx, x, top, 22); fillStroke(ctx, '#ffd23a', 6);
  path(ctx, [[hx - 18, hy], [hx - 26, hy + 30], [hx - 8, hy + 22]]); fillStroke(ctx, '#6d6870', 5);
  path(ctx, [[hx + 18, hy], [hx + 26, hy + 30], [hx + 8, hy + 22]]); fillStroke(ctx, '#6d6870', 5);
  sparks(ctx, hx, hy + 30, t, seed * 13, 1.1);
}

// ---------- Hintergründe je Ausbaustufe ----------
function hazard(ctx, y, hgt = 26) {
  ctx.save(); ctx.beginPath(); ctx.rect(-1500, y, 4080, hgt); ctx.clip(); ctx.fillStyle = '#ffd23a'; ctx.fillRect(-1500, y, 4080, hgt);
  for (let x = -1500; x < 2600; x += 70) { path(ctx, [[x, y + hgt], [x + 35, y], [x + 60, y], [x + 25, y + hgt]]); ctx.fillStyle = '#221c22'; ctx.fill(); }
  ctx.restore();
}
function hangLamp(ctx, x, y, t, col = '#ffe9a8') {
  line(ctx, x, -400, x, y - 30, 4, '#222'); path(ctx, [[x - 60, y], [x - 30, y - 40], [x + 30, y - 40], [x + 60, y]]); fillStroke(ctx, '#3b3442', 6);
  ctx.save(); ctx.globalCompositeOperation = 'lighter'; const g = ctx.createLinearGradient(0, y, 0, y + 520); g.addColorStop(0, 'rgba(255,233,168,.32)'); g.addColorStop(1, 'rgba(255,233,168,0)');
  ctx.fillStyle = g; path(ctx, [[x - 55, y], [x + 55, y], [x + 230, y + 520], [x - 230, y + 520]]); ctx.fill(); ctx.restore();
  circle(ctx, x, y + 4, 16); ctx.fillStyle = col; ctx.fill();
}
function neon(ctx, str, x, y, size, col, t) {
  const on = Math.sin(t * 23) > -.95;
  ctx.save(); ctx.shadowColor = col; ctx.shadowBlur = on ? 40 : 6; ctx.font = `700 ${size}px Poppins`; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
  ctx.lineWidth = size * .12; ctx.strokeStyle = on ? col : 'rgba(120,120,120,.6)'; ctx.strokeText(str, x, y); ctx.fillStyle = on ? '#fff' : '#bbb'; ctx.fillText(str, x, y); ctx.restore();
}
function firmaBackground(ctx, st, t, name) {
  if (st === 'garage') {
    ctx.fillStyle = '#8f949c'; ctx.fillRect(-1500, -1500, 4080, G + 1500);
    for (let y = 440; y < G; y += 70) for (let x = -1500 + ((y / 70) % 2) * 70; x < 2600; x += 140) { rrect(ctx, x, y, 136, 66, 4); ctx.fillStyle = 'rgba(0,0,0,.06)'; ctx.fill(); }
    rrect(ctx, 640, 520, 520, 560, 8); fillStroke(ctx, '#c4c8ce', 8); for (let y = 552; y < 1080; y += 44) line(ctx, 650, y, 1150, y, 5, 'rgba(34,28,34,.25)');
    rrect(ctx, -60, 560, 400, 260, 10); fillStroke(ctx, '#b8865a', 7); ['🔧', '🔨', '🪛'].forEach((e, i) => emoji(ctx, e, 30 + i * 115, 690, 84, Math.sin(t + i) * .06));
    hangLamp(ctx, 540, 470, t);
    ground(ctx, '#7c7e86', '#4c4e56');
    ellipse(ctx, 260, G + 70, 150, 26); ctx.fillStyle = 'rgba(20,20,30,.3)'; ctx.fill();
    return;
  }
  if (st === 'werkstatt') {
    ctx.fillStyle = '#dfe6ee'; ctx.fillRect(-1500, -1500, 4080, G + 1500);
    ctx.fillStyle = '#c9312b'; ctx.fillRect(-1500, 820, 4080, 40); ctx.fillStyle = '#9aa4b2'; ctx.fillRect(-1500, 860, 4080, G);
    rrect(ctx, 120, 450, 840, 150, 24); ctx.fillStyle = '#1f2440'; ctx.fill(); neon(ctx, name || 'WERKSTATT', 540, 525, 92, '#ff4fd8', t);
    emoji(ctx, '🛞', -20, 760, 120); emoji(ctx, '🛞', 1100, 760, 120);
    ground(ctx, '#6f7680', '#40464f'); hazard(ctx, G - 34, 20);
    return;
  }
  const big = st !== 'fabrik';
  if (st === 'konzern') {
    ctx.fillStyle = '#eef3fa'; ctx.fillRect(-1500, -1500, 4080, G + 1500);
    // große Glasfront mit Abendhimmel, Skyline und Teststrecke
    const y0 = 430, h = 330; ctx.save(); rrect(ctx, -740, y0, 2560, h, 0); ctx.clip();
    const g = ctx.createLinearGradient(0, y0, 0, y0 + h); g.addColorStop(0, '#2a2f7a'); g.addColorStop(1, '#ff9a6b'); ctx.fillStyle = g; ctx.fillRect(-740, y0, 2560, h);
    const R = rng(21); let x = -740, i = 0; while (x < 1820) { const w = 70 + R() * 110, bh = 80 + R() * 170; ctx.fillStyle = ['#262a52', '#32366a', '#1d2046'][i++ % 3]; ctx.fillRect(x, y0 + h - bh - 40, w, bh + 40); for (let yy = y0 + h - bh - 20; yy < y0 + h - 40; yy += 28) for (let xx = x + 10; xx < x + w - 14; xx += 22) if (R() < .45) { ctx.fillStyle = '#ffe39a'; ctx.fillRect(xx, yy, 9, 13); } x += w + 6; }
    ctx.fillStyle = '#3a3a48'; ctx.fillRect(-740, y0 + h - 40, 2560, 40); for (let k = 0; k < 30; k++) { ctx.fillStyle = '#fff'; ctx.fillRect(-740 + k * 90 - (t * 120) % 90, y0 + h - 22, 44, 5); }
    carSide(ctx, ((t * 520) % 2200) - 600, y0 + h - 8, 120, '#e0392f', 1, t, -t * 20);
    ctx.restore();
    for (let x2 = -740; x2 <= 1820; x2 += 300) { ctx.fillStyle = '#c8d3e2'; ctx.fillRect(x2 - 7, y0, 14, h); }
    ctx.save(); ctx.shadowColor = '#4fd6ff'; ctx.shadowBlur = 30; ctx.fillStyle = '#4fd6ff'; ctx.fillRect(-1500, y0 + h + 16, 4080, 8); ctx.restore();
    ground(ctx, '#d9e2ee', '#9fb0c6');
    ctx.save(); ctx.globalAlpha = .18; ctx.fillStyle = '#fff'; for (let k = 0; k < 6; k++) ctx.fillRect(-300 + k * 260, G - 20, 90, 1200); ctx.restore(); // Glanzboden
    return;
  }
  // Fabrikhalle
  ctx.fillStyle = big ? '#5e6672' : '#6d7480'; ctx.fillRect(-1500, -1500, 4080, G + 1500);
  for (let x = -1400; x < 2600; x += 260) { ctx.fillStyle = 'rgba(0,0,0,.18)'; ctx.fillRect(x, 400, 26, G); ctx.fillStyle = 'rgba(255,255,255,.06)'; ctx.fillRect(x + 26, 400, 6, G); }
  ctx.fillStyle = '#3b3442'; ctx.fillRect(-1500, 410, 4080, 26); // Träger
  if (big) { // Oberlichter mit Lichtstrahlen
    for (let x = -600; x < 1800; x += 420) { rrect(ctx, x, 440, 200, 90, 6); ctx.fillStyle = '#bfe6ff'; ctx.fill(); ctx.save(); ctx.globalCompositeOperation = 'lighter'; ctx.globalAlpha = .14 + .04 * Math.sin(t + x); ctx.fillStyle = '#fff6d0'; path(ctx, [[x, 530], [x + 200, 530], [x + 420, G], [x + 120, G]]); ctx.fill(); ctx.restore(); }
  }
  rrect(ctx, 150, 560, 780, 120, 18); fillStroke(ctx, '#1f2440', 8); fitText(ctx, name || 'AUTOWERK', 540, 622, 74, 700, '#ffe14d', null, 0);
  [-80, 300, 780, 1160].forEach(x => hangLamp(ctx, x, 720, t));
  ground(ctx, '#7a808a', '#454a54'); hazard(ctx, G - 34, 22);
}

// ---------- Arbeiter ----------
function firmaWorker(ctx, x, y, s, lt, seed, born, nm, job) {
  const drop = born == null ? 0 : (1 - easeOut(clamp((lt - born) / .35))) * -1000;
  const alpha = born == null ? 1 : clamp((lt - born) / .08);
  if (alpha <= 0) return;
  ctx.save(); ctx.globalAlpha *= alpha;
  const col = FIRMA_COLS[seed % FIRMA_COLS.length];
  const hammer = Math.sin(lt * (8 + seed % 3) + seed);
  const mood = (seed % 5 === 0) ? 'cool' : (seed % 3 === 0 ? 'freude' : 'neutral');
  const yy = y + drop;
  drawStick(ctx, figure({ figur: { farbe: col, hut: 'helm' } }, {
    x, y: yy, s, face: face(born != null && lt < born + 1 ? 'staunen' : mood, lt + seed * .37), flip: seed % 2 ? -1 : 1,
    arms: { L: [.5, -.3], R: [1.6 + hammer * .35, -1.2 - hammer * .3] }, legs: { L: [.12, -.04], R: [.12, -.04] },
  }));
  if (job === 'schweisst') sparks(ctx, x + (seed % 2 ? -1 : 1) * s * .3, yy - s * .55, lt, seed, s / 300);
  else emoji(ctx, '🔧', x + (seed % 2 ? -1 : 1) * s * .3, yy - s * .62 - hammer * s * .04, s * .16, hammer * .5);
  if (nm) nameTag(ctx, nm.slice(0, 12), x, yy - s * 1.2, Math.max(22, s * .095));
  if (born != null && lt > born + .25) { const kb = popIn(lt, born + .25, .3); ctx.save(); ctx.translate(x, yy - s * (nm ? 1.42 : 1.18)); ctx.scale(kb, kb); sign(ctx, 'NEU', 0, 0, Math.max(26, s * .13), '#7cf08a'); ctx.restore(); }
  ctx.restore();
}

function firmaHud(ctx, sc, lt, d) {
  base(ctx);
  const k = popIn(lt, 0, .3);
  ctx.save(); ctx.translate(540, 250); ctx.scale(k, k); ctx.translate(-540, -250);
  rrect(ctx, 46, 116, 1000, 300, 44); ctx.fillStyle = 'rgba(20,10,30,.35)'; ctx.fill();
  const g = ctx.createLinearGradient(0, 104, 0, 404); g.addColorStop(0, '#2a3160'); g.addColorStop(1, '#161a33');
  rrect(ctx, 40, 104, 1000, 300, 44); ctx.fillStyle = g; ctx.fill(); ctx.lineWidth = 10; ctx.strokeStyle = INK; ctx.stroke();
  const S = FIRMA_STUFEN[sc.stufe] || FIRMA_STUFEN.fabrik;
  emoji(ctx, sc.icon || '🚗', 100, 168, 56);
  fitText(ctx, (sc.name || 'MEINE AUTOFIRMA').toUpperCase(), 330, 168, 48, 400, '#fff', INK, 0);
  rrect(ctx, 590, 138, 410, 62, 31); ctx.fillStyle = '#ffe14d'; ctx.fill();
  fitText(ctx, sc.stufe_label || S.label, 795, 170, 36, 380, INK, null, 0);
  const g0 = Number(sc.geld) || 0, g1 = sc.geld_neu != null ? Number(sc.geld_neu) : g0;
  const money = lerp(g0, g1, easeOut(clamp((lt - .2) / Math.max(.6, d * .65))));
  const n = Math.round(Number(sc.mitarbeiter) || 0), nNew = Math.round(Number(sc.neu) || 0);
  const shown = n - nNew + Math.round(nNew * clamp((lt - .3) / Math.max(.4, d * .6)));
  const boxes = [['💰', euro(money), '#3fd67a', 'KONTO'], ['👷', shown.toLocaleString('de-DE'), '#8fd0ff', 'MITARBEITER'], ['📈', '+' + euro(sc.pro_tag || 0), '#ffcf5a', 'PRO TAG']];
  boxes.forEach(([e, v, col, lab], i) => {
    const x = 70 + i * 322;
    rrect(ctx, x, 222, 296, 158, 26); ctx.fillStyle = 'rgba(255,255,255,.08)'; ctx.fill();
    emoji(ctx, e, x + 50, 300, 60);
    const bump = (i === 0 && g1 !== g0 && lt < d * .7) || (i === 1 && nNew && lt < d * .7) ? 1 + Math.sin(lt * 25) * .04 : 1;
    ctx.save(); ctx.translate(x + 186, 282); ctx.scale(bump, bump); fitText(ctx, v, 0, 0, 52, 196, col, null, 0); ctx.restore();
    fitText(ctx, lab, x + 186, 342, 25, 196, 'rgba(255,255,255,.7)', null, 0);
  });
  ctx.restore();
}

// 3D-Fassung (firma3d.js), wenn der Browser WebGL kann
function firma3d(ctx, sc, lt, d) {
  const n = Math.max(0, Math.round(Number(sc.mitarbeiter) || 0)), nNew = Math.min(n, Math.max(0, Math.round(Number(sc.neu) || 0)));
  const lv = sc.level != null ? Number(sc.level) : ['garage', 'werkstatt'].indexOf(sc.stufe);
  const MAX = lv === 0 ? 8 : lv === 1 ? 16 : 32, want = Math.min(n, MAX);
  const newFrom = want - Math.min(nNew, want);
  const step = Math.min(.22, (d * .55) / Math.max(1, want - newFrom));
  const drawn = F3.draw(ctx, { ...sc, stufe: FIRMA_STUFEN[sc.stufe] ? sc.stufe : 'fabrik' }, lt, d, { drawn: want, newFrom, step, names: sc.namen || [] });
  if (n > drawn) { const k = popIn(lt, .5); ctx.save(); ctx.translate(800, 1560); ctx.scale(k, k); sign(ctx, '+' + (n - drawn).toLocaleString('de-DE') + ' weitere', 0, 0, 56, '#7cf08a'); ctx.restore(); }
  if (n === 0) { const k = popIn(lt, .2); ctx.save(); ctx.translate(540, 900); ctx.scale(k, k); sign(ctx, 'NOCH LEER', 0, 0, 90); ctx.restore(); }
  if (sc.objekt) { const k = popIn(lt, .1, .4); ctx.save(); ctx.translate(540, 760 + Math.sin(lt * 2.4) * 16); ctx.scale(k, k); ctx.rotate(lt * .3); burst(ctx, 0, 0, 190, 14, '#fff3b0', 4, .78); ctx.restore(); emoji(ctx, sc.objekt, 540, 760 + Math.sin(lt * 2.4) * 16, 210 * k, Math.sin(lt * 1.6) * .08); }
  if (sc.text) { const k = popIn(lt, .25); ctx.save(); ctx.translate(540, 480); ctx.scale(k, k); sign(ctx, sc.text, 0, 0, 60); ctx.restore(); }
  firmaHud(ctx, sc, lt, d);
}

window.EXTRA_TYPES = {
  firma(ctx, sc, lt, d) {
    if (window.F3) return firma3d(ctx, sc, lt, d);
    const st = FIRMA_STUFEN[sc.stufe] ? sc.stufe : 'fabrik';
    applyCam(ctx, cam(lt, d, 1.0, 1.05, sc.i)); firmaBackground(ctx, st, lt, sc.name);
    const n = Math.max(0, Math.round(Number(sc.mitarbeiter) || 0)), nNew = Math.min(n, Math.max(0, Math.round(Number(sc.neu) || 0)));
    const names = sc.namen || [];
    const MAX = 26, drawn = Math.min(n, MAX);
    const newFrom = drawn - Math.min(nNew, drawn);
    const step = Math.min(.22, (d * .55) / Math.max(1, drawn - newFrom));
    const born = i => i >= newFrom ? .3 + (i - newFrom) * step : null;
    const nameOf = i => names[drawn - 1 - i] || ''; // die neuesten Namen gehören den Arbeitern, die zuletzt kamen
    const spots = []; // {x, y, s, layer}
    let lines = [];
    if (st === 'garage' || st === 'werkstatt') {
      // Autos auf Hebebühnen, Arbeiter drumherum
      const lifts = st === 'garage' ? 1 : Math.min(3, Math.max(2, Math.ceil(drawn / 5)));
      const span = lifts === 1 ? [430] : lifts === 2 ? [290, 790] : [190, 540, 890];
      const cw = lifts === 1 ? 560 : lifts === 2 ? 420 : 320;
      span.forEach((cx, k) => {
        const up = 880 + Math.sin(lt * .8 + k) * 10;
        line(ctx, cx - cw * .38, up, cx - cw * .38, G - 30, 16, '#c9312b'); line(ctx, cx + cw * .38, up, cx + cw * .38, G - 30, 16, '#c9312b');
        rrect(ctx, cx - cw * .45, up - 4, cw * .9, 18, 6); fillStroke(ctx, '#ffd23a', 6);
        const prog = clamp(.35 + ((lt * .12 + k * .3) % 1) * .9);
        carSide(ctx, cx, up - 4, cw, CAR_COLS[(k + (sc.i || 0)) % CAR_COLS.length], prog, lt, 0);
      });
      const per = Math.min(drawn, MAX);
      const s = drawn <= 4 ? 330 : drawn <= 10 ? 260 : 210;
      for (let i = 0; i < per; i++) {
        const row = drawn > 10 && i % 2; const cnt = drawn > 10 ? Math.ceil(per / 2) : per; const j = drawn > 10 ? Math.floor(i / 2) : i;
        const x = cnt === 1 ? 760 : 90 + j * (900 / Math.max(1, cnt - 1));
        spots.push({ x, y: G + (row ? 30 : -10), s: s * (row ? 1.08 : 1) });
      }
    } else {
      // Fließband(er): Autos fahren von links nach rechts und werden dabei fertig
      lines = st === 'fabrik' ? [{ y: 960, s: 1 }] : [{ y: 760, s: .7 }, { y: 990, s: .92 }];
      const back = Math.min(drawn, Math.ceil(drawn * (lines.length > 1 ? .72 : .66)));
      lines.forEach((ln, li) => {
        const cnt = lines.length > 1 ? (li === 0 ? Math.ceil(back / 2) : back - Math.ceil(back / 2)) : back;
        const s = (cnt > 8 ? 210 : cnt > 4 ? 240 : 280) * ln.s;
        for (let j = 0; j < cnt; j++) spots.push({ x: cnt === 1 ? 540 : 80 + j * (920 / Math.max(1, cnt - 1)), y: ln.y + 40 * ln.s, s, line: li, job: j % 3 === 1 ? 'schweisst' : '' });
      });
      for (let i = back; i < drawn; i++) { const k = i - back, cnt = drawn - back; spots.push({ x: cnt === 1 ? 900 : 90 + k * (900 / Math.max(1, cnt - 1)), y: G + 30, s: 230, front: true }); }
    }
    const drawWorkers = filter => spots.forEach((p, i) => { if (filter(p)) firmaWorker(ctx, p.x, p.y, p.s, lt, i + 1, born(i), nameOf(i), p.job); });
    if (lines.length) {
      lines.forEach((ln, li) => {
        drawWorkers(p => p.line === li); // hinter dem Band
        const by = ln.y - 70 * ln.s, bh = 70 * ln.s;
        // Autos auf dem Band
        const cw = 300 * ln.s, gap = cw * 1.45, speed = 150 * ln.s, off = (lt * speed + li * 90) % gap;
        for (let x = -700 - gap + off; x < 1800; x += gap) { const prog = clamp((x + 300) / 1300); carSide(ctx, x, by, cw, CAR_COLS[Math.abs(Math.round((x - off) / gap)) % CAR_COLS.length], prog, lt, 0); }
        rrect(ctx, -1500, by, 4080, bh, 10); fillStroke(ctx, '#3b3442', 7);
        for (let x = -1500 + (lt * speed) % 60; x < 2600; x += 60) line(ctx, x, by + 8, x, by + bh - 8, 4, 'rgba(255,255,255,.12)');
        for (let x = -1500; x < 2600; x += 160) { line(ctx, x + 20, by + bh, x + 20, ln.y + 60 * ln.s, 12 * ln.s, '#2b2630'); }
        if (st !== 'fabrik' || li === 0) [200, 820].forEach((ax, k) => robotArm(ctx, ax + (li ? 0 : 120), by - 330 * ln.s, 330 * ln.s, lt, k + li * 3 + 1));
      });
      drawWorkers(p => p.front);
    } else drawWorkers(() => true);
    // Fertige Autos fahren raus, Geld kommt rein
    if (drawn > 0 && sc.pro_tag) {
      const R = rng((sc.i || 0) + 5);
      for (let k = 0; k < Math.min(8, drawn); k++) { const p = spots[Math.floor(R() * spots.length)], ph = (lt * .8 + R()) % 1.5; if (ph < 1) emoji(ctx, R() < .5 ? '🪙' : '💶', p.x + (R() - .5) * 60, p.y - p.s * 1.0 - ph * 240, p.s * .2, 0, 1 - ph); }
    }
    if (n > drawn) { const k = popIn(lt, .5); ctx.save(); ctx.translate(820, 470); ctx.scale(k, k); sign(ctx, '+' + (n - drawn).toLocaleString('de-DE') + ' weitere', 0, 0, 56, '#7cf08a'); ctx.restore(); }
    if (n === 0) { const k = popIn(lt, .2); ctx.save(); ctx.translate(540, 900); ctx.scale(k, k); sign(ctx, 'NOCH LEER', 0, 0, 90); ctx.restore(); }
    if (sc.chef) stick(ctx, sc, 160, G + 60, 560, sc.gefuehl || 'cool', sc.aktion || 'zeigt', lt);
    if (sc.text) { const k = popIn(lt, .25); ctx.save(); ctx.translate(n > drawn ? 280 : 540, 470); ctx.scale(k, k); sign(ctx, sc.text, 0, 0, 60); ctx.restore(); }
    firmaHud(ctx, sc, lt, d);
  },
};
