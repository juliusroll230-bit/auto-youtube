// ---------- Bildmischer: Einstellungen, Wisch-Übergänge, Untertitel, Look ----------
// Nach dem Vorbild von claude-animation-skills (MIT, siehe ../LICENSE-stick-figure.txt), ohne Zeit-Warp.
const canvas = document.getElementById('c'); canvas.width = W; canvas.height = H;
const out = canvas.getContext('2d');
const buf = document.createElement('canvas'); buf.width = W; buf.height = H; const bctx = buf.getContext('2d');
const DUR = PLAN.dur;
const DARK = PLAN.stimmung === 'gruselig' || PLAN.stimmung === 'mysterioes'; // dunklerer Look mit Nebel
// Heller Look (Messwerte aus dem MIT-Paket claude-animated-shorts): Schwarz leicht angehoben und warm, kräftigere Farben, dezenter Rand.
const GRADE = !DARK;
const gbuf = document.createElement('canvas'); gbuf.width = W; gbuf.height = H; const gctx = gbuf.getContext('2d');
function grade(c) {
  c.save(); c.setTransform(1, 0, 0, 1, 0, 0); c.globalAlpha = 1;
  gctx.globalCompositeOperation = 'copy'; gctx.filter = 'none'; gctx.drawImage(canvas, 0, 0);
  c.globalCompositeOperation = 'copy'; c.filter = 'saturate(1.15) brightness(1.06) contrast(1.02)'; c.drawImage(gbuf, 0, 0); c.filter = 'none';
  c.globalCompositeOperation = 'lighten'; c.fillStyle = 'rgb(35,19,20)'; c.fillRect(0, 0, W, H);
  c.restore();
}
const TOTAL_FRAMES = Math.round(DUR * FPS);
const grains = [];
for (let k = 0; k < 4; k++) { const g = document.createElement('canvas'); g.width = g.height = 256; const gc = g.getContext('2d'); const id = gc.createImageData(256, 256); const R = rng(k + 11); for (let i = 0; i < id.data.length; i += 4) { const v = 128 + (R() - .5) * 120; id.data[i] = id.data[i + 1] = id.data[i + 2] = v; id.data[i + 3] = 255; } gc.putImageData(id, 0, 0); grains.push(g); }
const WORDS = PLAN.words;
// Test Tempo "schnell" (seit 21.11.2026, nach Julius' Vorbild-Reels): Schnitt alle ca. 1,3 s (PLAN.cuts, gleiche Zeiten wie die Snaps im Ton),
// jede Einstellung anders gerahmt (nah, halbnah, schräg), Stoß-Zoom auf jedem Schnitt, Wort-für-Wort-Untertitel, Fortschrittsbalken.
const FAST = PLAN.tempo === 'schnell' && !WIDE;
const CUTS = FAST ? [...PLAN.scenes.slice(1).map(s => s.start), ...(PLAN.cuts || [])].sort((a, b) => a - b) : [];
// z: Zoom, x: seitlich, y: Bildpunkt (Höhe), der in die Mitte kommt (Gesichter sitzen oben), r: Neigung
const FRAMINGS = [{ z: 1, x: 0, y: .47, r: 0 }, { z: 1.32, x: 0, y: .39, r: 0 }, { z: 1.16, x: -70, y: .43, r: -.035 }, { z: 1.45, x: 40, y: .36, r: .02 }, { z: 1.1, x: 80, y: .45, r: .03 }];
const TEXTY = new Set(['vergleich', 'liste', 'akte', 'zahl', 'jahr', 'karte', 'titel']);
function fastCam(t) {
  // Nummer der Einstellung innerhalb der Szene: jede Szene startet weit (man sieht, wo man ist), danach wechselt es
  let k = 0, last = 0; const sc = PLAN.scenes.findLast ? PLAN.scenes.findLast(s => t >= s.start) : PLAN.scenes.filter(s => t >= s.start).pop();
  for (const c of PLAN.cuts || []) { if (c <= t && sc && c > sc.start) k++; }
  for (const c of CUTS) if (c <= t) last = c;
  let f = k === 0 ? FRAMINGS[(sc && sc.i % 2) ? 4 : 0] : FRAMINGS[1 + ((k - 1 + (sc ? sc.i : 0)) % 4)];
  if (sc && TEXTY.has(sc.typ)) f = { z: k % 2 ? 1.08 : 1, x: 0, y: .47, r: 0 };   // Schrift-Szenen nur leicht zoomen, sonst wird Text abgeschnitten
  const d = t - last, kick = last > 0 && d < .5 ? .09 * Math.exp(-d * 11) : 0;   // Stoß-Zoom direkt nach dem Schnitt
  return { z: f.z * (1 + kick), x: f.x, y: f.y, r: f.r, flash: last > 0 && d < .07 ? .22 * (1 - d / .07) : 0 };
}
let CAM = { z: 1, x: 0, y: .47, r: 0, flash: 0 };
const CHUNKS = (() => {
  const ch = []; let cur = null;
  WORDS.forEach((w, i) => {
    const prev = WORDS[i - 1];
    const brk = !cur || cur.words.length >= (FAST ? 1 + (w.w.length <= 3 || cur.text.length <= 3 ? 1 : 0) : 2) || (cur.text + ' ' + w.w).length > 13 || /[.,?!:;]$/.test(prev ? prev.w : '') || (prev && prev.line !== w.line);
    if (brk) { cur = { words: [w], text: w.w, s: w.s, e: w.e }; ch.push(cur); } else { cur.words.push(w); cur.text += ' ' + w.w; cur.e = w.e; }
  });
  ch.forEach((c, i) => { const n = ch[i + 1]; c.e = n && n.s - c.e < .5 ? n.s : c.e + .25; });
  return ch;
})();
const capText = s => s.toLowerCase().replace(/[-–—]/g, ' ').replace(/[^\p{L}\p{N}% ]/gu, '').replace(/\s+/g, ' ').trim();
function drawCaption(ctx, t) {
  const c = CHUNKS.find(c => t >= c.s && t < c.e); if (!c) return;
  const k = clamp((t - c.s) / .1); const sc = .82 + .18 * backOut(k);
  ctx.save(); ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.translate(W / 2, WIDE ? H - 130 : FAST ? 1470 : 1345); ctx.scale(sc, sc);
  const key = FAST && c.words.some(w => w.k);   // Schlüsselwort gelb wie in den schnellen Reels
  if (FAST) ctx.rotate(Math.sin(c.s * 13) * .05 * (1 - k));
  const str = capText(c.text); const FS = WIDE ? 66 : FAST ? 112 : 78, MW = WIDE ? 1500 : 900; ctx.font = `700 ${FS}px Poppins`; const wd = ctx.measureText(str).width; const fs = wd > MW ? FS * MW / wd : FS;
  ctx.shadowColor = 'rgba(0,0,0,.55)'; ctx.shadowBlur = 18; ctx.shadowOffsetY = 5;
  const col = key ? '#ffd23a' : '#fff';
  text(ctx, FAST ? str.toUpperCase() : str, 0, 0, fs, col, '#111', FAST ? 18 : 14, 'Poppins', 700);
  ctx.shadowColor = 'transparent'; text(ctx, FAST ? str.toUpperCase() : str, 0, 0, fs, col, '#111', 0, 'Poppins', 700);
  ctx.restore();
}
function renderShot(ctx, i, t) {
  const s = SHOTS[i];
  ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.globalAlpha = 1; ctx.globalCompositeOperation = 'source-over'; ctx.filter = 'none';
  ctx.fillStyle = '#000'; ctx.fillRect(0, 0, W, H);
  ctx.save(); base(ctx); s.draw(ctx, t - s.start, t); ctx.restore();
}
// Test Spannung (seit 20.11.2026): Herzschlag-Puls am Rand und Countdown bis zur Auflösung (PLAN.reveal, Herzschläge PLAN.beats wie im Ton).
const TENSE = PLAN.aufbau === 'spannung' && PLAN.reveal != null && !WIDE;
function tension(t) {
  let pulse = 0;   // roter Rand, der mit jedem Herzschlag aufleuchtet
  for (const b of PLAN.beats || []) { const d = t - b; if (d >= 0 && d < .6) pulse = Math.max(pulse, Math.exp(-d * 7) + .6 * Math.exp(-Math.max(0, d - .16) * 9) * (d > .16)); }
  const R = PLAN.reveal, start = .25;
  out.save(); out.setTransform(1, 0, 0, 1, 0, 0); out.globalCompositeOperation = 'source-over';
  if (pulse > 0 && t < R) {
    const g = out.createRadialGradient(W / 2, H / 2, 420, W / 2, H / 2, 1150); g.addColorStop(0, 'rgba(200,0,20,0)'); g.addColorStop(1, `rgba(200,0,20,${.38 * Math.min(1, pulse)})`);
    out.fillStyle = g; out.fillRect(0, 0, W, H);
  }
  const fade = t < R ? clamp((t - start) / .25) : 1 - clamp((t - R) / .35);
  if (fade > 0) {   // Countdown oben: Sekunden bis zur Auflösung, Ring läuft ab
    const left = Math.max(0, R - t), sec = Math.ceil(left - 1e-6), frac = left - Math.floor(left);
    const cx = 150, cy = 215, r = 68, k = t < R ? 1 + .14 * Math.exp(-(1 - frac) * 10) : 1 + .3 * clamp((t - R) / .35);
    out.globalAlpha = fade; out.translate(cx, cy); out.scale(k, k);
    out.fillStyle = 'rgba(8,6,14,.72)'; circle(out, 0, 0, r + 16); out.fill();
    out.strokeStyle = 'rgba(255,255,255,.18)'; out.lineWidth = 12; circle(out, 0, 0, r); out.stroke();
    const urgent = left < 3.5;
    out.strokeStyle = urgent ? '#ff2d4a' : '#ffd23a'; out.lineCap = 'round'; out.lineWidth = 12;
    out.beginPath(); out.arc(0, 0, r, -Math.PI / 2, -Math.PI / 2 + TAU * clamp(left / Math.max(1, R - start)), false); out.stroke();
    text(out, t < R ? String(sec) : '!', 0, 5, 78, urgent ? '#ff4d63' : '#fff', '#111', 0, 'Poppins', 700);
    text(out, 'AUFLÖSUNG', 0, r + 44, 26, '#fff', '#111', 8, 'Poppins', 700);
  }
  out.restore();
}
let ZOOM = 1;   // Stoß auf der Auflösung (PLAN.punch), sonst 1
function blit(src, dx, blur) {
  const n = blur > 2 ? 7 : 1;
  out.save(); out.setTransform(ZOOM, 0, 0, ZOOM, W / 2 * (1 - ZOOM), H * .47 * (1 - ZOOM));
  if (FAST) { out.translate(W / 2, H * .47); out.rotate(CAM.r); out.scale(CAM.z, CAM.z); out.translate(-(W / 2 + CAM.x), -H * CAM.y); }
  for (let k = 0; k < n; k++) { const off = n > 1 ? (k / (n - 1) - .5) * blur : 0; out.globalAlpha = 1 / (k + 1); const x = dx + off; out.drawImage(src, x, 0); if (x > 0) out.drawImage(src, x - W, 0); if (x < 0) out.drawImage(src, x + W, 0); }
  out.restore();
}
// Test Abo-Aufruf (seit 22.11.2026): Abo-Knopf mit Glocke am Ende (PLAN.abo). Gesprochen: erscheint mit dem Satz,
// eingeblendet: ca. 2,6 s vor Schluss während des letzten Satzes. Beim Loop blendet er kurz vor dem Ende aus, damit der Neustart nicht auffällt.
function aboBadge(t) {
  const A = PLAN.abo; if (!A || WIDE) return;
  const q = t - A.start; if (q < 0) return;
  const k = backOut(clamp(q / .32)), fade = A.loop ? 1 - clamp((t - (DUR - .45)) / .3) : 1;
  if (fade <= 0) return;
  out.save(); out.setTransform(1, 0, 0, 1, 0, 0); out.globalCompositeOperation = 'source-over'; out.globalAlpha = fade * clamp(q / .12);
  const str = A.text, FS = 54; out.font = `700 ${FS}px Poppins`;
  const tw = Math.min(out.measureText(str).width, 760), fs = FS * tw / Math.max(tw, out.measureText(str).width);
  const bw = tw + 200, bh = 128, cy = FAST ? 1250 : 1170;
  const tap = q > .75 && q < 1.1 ? Math.sin((q - .75) / .35 * Math.PI) : 0;   // kurzes "Drücken" des Knopfs
  out.translate(W / 2, cy + (1 - k) * 60); out.scale(.6 + .4 * k - .05 * tap, .6 + .4 * k - .05 * tap);
  out.shadowColor = 'rgba(0,0,0,.45)'; out.shadowBlur = 30; out.shadowOffsetY = 10;
  rrect(out, -bw / 2, -bh / 2, bw, bh, bh / 2); out.fillStyle = 'rgba(14,12,18,.86)'; out.fill();
  out.shadowColor = 'transparent';
  out.lineWidth = 3; out.strokeStyle = 'rgba(255,255,255,.22)'; out.stroke();
  const bx = -bw / 2 + 66;
  out.fillStyle = '#ff2d4a'; circle(out, bx, 0, 46); out.fill();
  emoji(out, '🔔', bx, 2, 50, Math.sin(q * 16) * .35 * Math.exp(-q * 2.2), 1);
  text(out, str, bx + 62 + tw / 2, 3, fs, '#fff', '#111', 0, 'Poppins', 700);
  if (tap > 0) { out.globalAlpha *= tap * .5; out.lineWidth = 6; out.strokeStyle = '#fff'; rrect(out, -bw / 2 - 10 * tap, -bh / 2 - 10 * tap, bw + 20 * tap, bh + 20 * tap, bh / 2 + 10 * tap); out.stroke(); }
  out.restore();
}
// Vorbild-Taktiken (Test seit 25.11.2026): Übergänge zwischen den Szenen (PLAN.uebergang, gelernt) und Dranbleib-Elemente (PLAN.halten).
// Alle Übergänge decken den Schnitt ab: die alte Szene geht in den Übergang hinein, die neue kommt aus ihm heraus (kein Doppel-Rendern).
const TR_OUT = .2, TR_IN = .24;
const WIPE_COLS = DARK ? ['#7a2cff', '#0d0b16'] : ['#ffd23a', '#ff5a4f'];
function trPhase(t, i) {   // -1..0 kurz vor dem Schnitt (raus), 0..1 kurz danach (rein), sonst null; dazu die Art
  const s = SHOTS[i], prev = SHOTS[i - 1];
  if (s.tr && s.tr !== 'cut' && s.tr !== 'whip' && i < SHOTS.length - 1 && t > s.end - TR_OUT) return { k: s.tr, p: (t - s.end) / TR_OUT };
  if (prev && prev.tr && prev.tr !== 'cut' && prev.tr !== 'whip' && t < s.start + TR_IN) return { k: prev.tr, p: (t - s.start) / TR_IN };
  return null;
}
function trZoom(ph) {   // Zoom durchs Bild: raus ins Bild hinein, rein aus der Nähe zurück
  if (!ph) return 1;
  if (ph.k === 'zoom') return ph.p < 0 ? 1 + .7 * easeIn(1 + ph.p) : 1 + .35 * (1 - easeOut(ph.p));
  if (ph.k === 'blitz') return ph.p >= 0 ? 1 + .1 * Math.exp(-ph.p * 4) : 1;
  return 1;
}
function trOverlay(ph) {
  if (!ph) return;
  out.save(); out.setTransform(1, 0, 0, 1, 0, 0); out.globalCompositeOperation = 'source-over';
  if (ph.k === 'zoom') {   // Zoom mit kurzem Aufhellen genau auf dem Schnitt
    const a = ph.p < 0 ? .5 * easeIn(1 + ph.p) : .5 * (1 - easeOut(ph.p));
    out.globalAlpha = a; out.fillStyle = '#fff'; out.fillRect(0, 0, W, H);
  } else if (ph.k === 'blitz') {
    const a = ph.p < 0 ? .25 * easeIn(1 + ph.p) : .85 * Math.exp(-ph.p * 5);
    out.globalAlpha = a; out.fillStyle = '#fff'; out.fillRect(0, 0, W, H);
  } else if (ph.k === 'kreis') {   // Kreis schließt sich um die Mitte, die neue Szene öffnet sich aus einem Kreis
    const R = Math.hypot(W, H) / 2 + 40, r = ph.p < 0 ? R * (1 - easeIn(1 + ph.p)) : R * easeOut(ph.p);
    out.beginPath(); out.rect(0, 0, W, H); out.arc(W / 2, H * .45, Math.max(.5, r), 0, TAU, true);
    out.fillStyle = '#0b0b0c'; out.fill('evenodd');
    out.globalAlpha = .9; out.lineWidth = 16; out.strokeStyle = WIPE_COLS[0]; circle(out, W / 2, H * .45, Math.max(.5, r)); out.stroke();
  } else if (ph.k === 'wisch') {   // flüssiger Farb-Wisch: zwei Farbschichten mit Wellen-Kante laufen von links nach rechts durchs Bild
    const span = W + 520;
    [[WIPE_COLS[0], 0], [WIPE_COLS[1], .16]].forEach(([col, lag]) => {
      // raus: Kante läuft von links bis über den rechten Rand (Akzentfarbe vorneweg), rein: hintere Kante läuft hinterher
      const fr = ph.p < 0 ? clamp(easeIn(1 + ph.p) * (1 + lag) - lag) : 1;
      // rein: die dunkle Schicht gibt das Bild zuerst frei, die Farbe läuft hinterher
      const x1 = -260 + span * fr, x0 = -260 + span * (ph.p < 0 ? 0 : clamp(easeOut(ph.p) * 1.16 - (lag ? 0 : .16)));
      if (x1 - x0 < 2) return;
      const wob = (y, ph2) => 55 * Math.sin(y / 170 + ph2) + 25 * Math.sin(y / 63 + ph2 * 1.7);
      out.beginPath();
      for (let y = 0; y <= H; y += 30) out.lineTo(x1 + wob(y, (ph.p + 1) * 7), y);
      for (let y = H; y >= 0; y -= 30) out.lineTo(ph.p < 0 ? -300 : x0 + wob(y, ph.p * 6 + 2), y);
      out.closePath(); out.fillStyle = col; out.fill();
    });
  }
  out.restore();
}
const HOLD = WIDE ? 'ohne' : (PLAN.halten || 'ohne');
const ASK = (HOLD === 'frage' || HOLD === 'beides') && PLAN.frage;
const BAR = (HOLD === 'balken' || HOLD === 'beides') && !FAST;   // schnell hat schon einen Balken
function lines2(ctx, str, maxW) {   // höchstens zwei Zeilen
  const ws = str.split(' '); let a = '', b = '';
  for (const w of ws) { if (!b && ctx.measureText((a + ' ' + w).trim()).width <= maxW) a = (a + ' ' + w).trim(); else b = (b + ' ' + w).trim(); }
  return b ? [a, b] : [a];
}
function holdUI(t) {
  if (!ASK && !BAR) return;
  out.save(); out.setTransform(1, 0, 0, 1, 0, 0); out.globalCompositeOperation = 'source-over';
  if (BAR) {   // Fortschrittsbalken oben: man sieht, dass es gleich vorbei ist
    out.fillStyle = 'rgba(0,0,0,.35)'; out.fillRect(0, 0, W, 12);
    out.fillStyle = DARK ? '#c9b8ff' : '#ffd23a'; out.fillRect(0, 0, W * clamp(t / DUR), 12);
  }
  const R = PLAN.aufloesung;
  if (ASK && R != null) {   // die Frage bleibt oben stehen, bis sie aufgelöst ist (offene Schleife), dann ein Haken
    const q = t - .35, done = t >= R, dq = t - R;
    const fade = done ? 1 - clamp((dq - 1.3) / .3) : 1;
    if (q > 0 && fade > 0) {
      const k = backOut(clamp(q / .35)), pop = done ? 1 + .12 * Math.exp(-dq * 6) * (1 - Math.exp(-dq * 40)) : 1;
      const cx = TENSE ? W / 2 + 90 : W / 2, cy = 150, maxW = TENSE ? 640 : 820, FS = 46;   // über den Szenen-Schriften (ab ca. y 260)
      out.font = `700 ${FS}px Poppins`;
      const ls = lines2(out, PLAN.frage, maxW), tw = Math.max(...ls.map(l => out.measureText(l).width)), bh = ls.length > 1 ? 150 : 96;
      out.globalAlpha = fade * clamp(q / .15); out.translate(cx, cy + (1 - k) * -40); out.scale(.85 + .15 * k * pop, .85 + .15 * k * pop);
      out.shadowColor = 'rgba(0,0,0,.4)'; out.shadowBlur = 24; out.shadowOffsetY = 8;
      const bw = tw + 150; rrect(out, -bw / 2, -bh / 2, bw, bh, 30); out.fillStyle = done ? 'rgba(20,110,55,.9)' : 'rgba(12,10,18,.78)'; out.fill();
      out.shadowColor = 'transparent'; out.lineWidth = 3; out.strokeStyle = 'rgba(255,255,255,.2)'; out.stroke();
      const ix = -bw / 2 + 52;
      out.fillStyle = done ? '#38d27a' : '#ffd23a'; circle(out, ix, 0, 30); out.fill();
      text(out, done ? '✓' : '?', ix, 3, 44, '#111', '#111', 0, 'Poppins', 700);
      ls.forEach((l, j) => text(out, l, ix + 46 + tw / 2, (ls.length > 1 ? (j ? 30 : -30) : 0) + 2, FS, '#fff', '#111', 0, 'Poppins', 700));
    }
  }
  out.restore();
}
function renderFrame(f) {
  const t = Math.min(f / FPS, DUR - 1e-3);
  let i = SHOTS.findIndex(s => t >= s.start && t < s.end); if (i < 0) i = SHOTS.length - 1;
  const s = SHOTS[i], WT = .2;
  out.setTransform(1, 0, 0, 1, 0, 0); out.fillStyle = '#000'; out.fillRect(0, 0, W, H);
  let dx = 0, blur = 0;
  if (s.tr === 'whip' && i < SHOTS.length - 1 && t > s.end - WT) { const p = easeIn((t - (s.end - WT)) / WT); dx = -p * 420; blur = p * 260; }
  const prev = SHOTS[i - 1];
  if (prev && prev.tr === 'whip' && t < s.start + WT) { const p = 1 - easeOut((t - s.start) / WT); dx = p * 420; blur = p * 260; }
  renderShot(bctx, i, t);
  const pt = PLAN.punch != null ? t - PLAN.punch : -1;
  ZOOM = pt >= 0 && pt < 1.2 ? 1 + .12 * Math.exp(-pt * 4) * (1 - Math.exp(-pt * 40)) : 1;
  if (PLAN.fx === 'voll') {   // langsamer Kamera-Zug in jeder Einstellung + kurzer Zoom auf jedem Schlüsselwort
    ZOOM *= 1 + .05 * clamp((t - s.start) / Math.max(.5, s.end - s.start));
    for (const h of PLAN.hits || []) { const d = t - h; if (d >= 0 && d < .5) ZOOM *= 1 + .05 * Math.exp(-d * 9) * (1 - Math.exp(-d * 60)); }
  }
  if (FAST) CAM = fastCam(t);
  const ph = trPhase(t, i);
  ZOOM *= trZoom(ph);
  blit(buf, dx, blur);
  out.save(); out.setTransform(1, 0, 0, 1, 0, 0);
  const VK = WIDE ? .75 : 1; const g = out.createRadialGradient(W / 2, H * .47, (DARK ? 380 : 500) * VK, W / 2, H / 2, 1250 * VK * (WIDE ? 1.15 : 1)); g.addColorStop(0, 'rgba(0,0,0,0)'); g.addColorStop(1, DARK ? 'rgba(4,2,14,.62)' : 'rgba(10,5,20,.2)'); out.fillStyle = g; out.fillRect(0, 0, W, H);
  if (DARK) { out.globalCompositeOperation = 'multiply'; out.fillStyle = PLAN.stimmung === 'gruselig' ? '#a39fbf' : '#9cadca'; out.fillRect(0, 0, W, H); out.globalCompositeOperation = 'source-over'; fog(out, t, .22, WIDE ? 1250 : 1500); }
  if (GRADE) grade(out);
  out.globalCompositeOperation = 'overlay'; out.globalAlpha = .07; const pat = out.createPattern(grains[f % 4], 'repeat'); out.fillStyle = pat; out.translate((f * 37) % 256, (f * 91) % 256); out.fillRect(-256, -256, W + 512, H + 512);
  if (pt >= 0 && pt < .4) { out.setTransform(1, 0, 0, 1, 0, 0); out.globalCompositeOperation = 'source-over'; out.globalAlpha = .45 * Math.exp(-pt * 12); out.fillStyle = '#fff'; out.fillRect(0, 0, W, H); }
  out.restore();
  if (PLAN.sticker && pt >= .12 && pt < 1.9) {   // Reaktions-Sticker (selbst gezeichnet, Emoji-Schrift): springt rein, wackelt, blendet aus
    const q = pt - .12, k = backOut(clamp(q / .25)), fade = 1 - clamp((q - 1.4) / .35);
    out.save(); out.setTransform(1, 0, 0, 1, 0, 0);
    emoji(out, PLAN.sticker, W * .8, H * .27, 300 * k, Math.sin(q * 9) * .14 * Math.exp(-q * 1.5), fade);
    out.restore();
  }
  trOverlay(ph);
  if (TENSE) tension(t);
  if (FAST) {   // kurzer heller Blitz auf jedem Schnitt und Fortschrittsbalken oben (zeigt: gleich ist es vorbei, also dranbleiben)
    out.save(); out.setTransform(1, 0, 0, 1, 0, 0); out.globalCompositeOperation = 'source-over';
    if (CAM.flash > 0) { out.globalAlpha = CAM.flash; out.fillStyle = '#fff'; out.fillRect(0, 0, W, H); out.globalAlpha = 1; }
    out.fillStyle = 'rgba(0,0,0,.35)'; out.fillRect(0, 0, W, 14);
    out.fillStyle = '#ffd23a'; out.fillRect(0, 0, W * clamp(t / DUR), 14);
    out.restore();
  }
  holdUI(t);
  aboBadge(t);
  drawCaption(out, t);
}
window.renderFrame = renderFrame; window.TOTAL_FRAMES = TOTAL_FRAMES; window.DUR = DUR;
window.grab = (q = .92) => canvas.toDataURL('image/jpeg', q);
window.READY = true;
