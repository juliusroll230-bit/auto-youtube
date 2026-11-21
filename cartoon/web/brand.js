// ---------- Quiet Corner: Banner und Profilbild (entspannung.branding) ----------
// brandImage(variante, art, w, h) -> PNG/JPEG als data-URL. Varianten: A Regen-Fenster, B Kamin-Ecke, C grüne Ranken.
// Banner 2560x1440: Text nur im sicheren Bereich in der Mitte (1546x423), der auf allen Geräten zu sehen ist.
function brandCanvas(w, h) { const c = document.createElement('canvas'); c.width = w; c.height = h; return c; }

function brandSage(c, w, h, t) {   // Variante C: hell, salbeigrün, geschwungene Ranken und große Blätter
  const g = c.createLinearGradient(0, 0, w, h); g.addColorStop(0, '#e9eee2'); g.addColorStop(.55, '#d3dec8'); g.addColorStop(1, '#b7c9a8');
  c.fillStyle = g; c.fillRect(0, 0, w, h);
  c.save(); c.translate(w / 2, h / 2); const u = h / 1080; c.scale(u, u);
  for (const [x, y, r, a] of [[-700, -300, 420, .18], [760, 260, 520, .16], [80, -520, 300, .12]]) { c.globalAlpha = a; c.fillStyle = '#fffaf0'; circle(c, x, y, r); c.fill(); }
  c.globalAlpha = 1;
  c.strokeStyle = 'rgba(70,110,70,.35)'; c.lineWidth = 5; c.lineCap = 'round';   // geschwungene Linien
  for (let k = 0; k < 3; k++) { c.beginPath(); c.moveTo(-1100, -380 + k * 40); c.bezierCurveTo(-500, -560 + k * 60, 300, -200 + k * 40, 1100, -420 + k * 50); c.stroke(); }
  const vw = (Math.max(w, h * 16 / 9) / u) / 2;
  for (let i = 0; i < 9; i++) qVine(c, -vw + 60 + i * (vw * 2 - 120) / 8, -560, 160 + (i % 3) * 70, 1.2, t, 60 + i);
  qMonstera(c, -vw + 230, 360, 1.0, t, 61); qMonstera(c, vw - 230, 360, .95, t, 63);
  qFern(c, -vw + 560, 540, 1.1, t, 65); qFern(c, vw - 580, 540, 1.1, t, 67);
  c.restore();
}

function brandScene(c, v, w, h, t) {
  if (v === 'C') return brandSage(c, w, h, t);
  drawQuiet(c, { scene: v === 'B' ? 'kamin' : 'regenzimmer', weather: v === 'B' ? 'schnee' : 'regen' }, t, w, h);
}

function brandTitle(c, v, w, h) {   // Kanalname im Glas-Feld in der Mitte
  const light = v === 'C', bw = 1240 * w / 2560, bh = 330 * w / 2560, x = (w - bw) / 2, y = (h - bh) / 2;
  const blur = brandCanvas(w, h), b = blur.getContext('2d'); b.filter = `blur(${Math.round(28 * w / 2560)}px)`; b.drawImage(c.canvas, 0, 0);
  c.save(); c.beginPath(); c.roundRect(x, y, bw, bh, bh / 2); c.clip(); c.drawImage(blur, 0, 0);
  c.fillStyle = light ? 'rgba(255,252,244,.55)' : 'rgba(20,14,12,.45)'; c.fillRect(x, y, bw, bh); c.restore();
  c.save(); c.beginPath(); c.roundRect(x, y, bw, bh, bh / 2); c.lineWidth = 2 * w / 2560; c.strokeStyle = light ? 'rgba(255,255,255,.8)' : 'rgba(255,240,220,.25)'; c.stroke(); c.restore();
  c.textAlign = 'center'; c.textBaseline = 'middle';
  c.fillStyle = light ? '#2f4a33' : '#f6eee2'; c.font = `${Math.round(150 * w / 2560)}px Serif`;
  c.fillText('Quiet Corner', w / 2, h / 2 - 34 * w / 2560);
  c.fillStyle = light ? '#5d7a58' : '#e7c98f'; c.font = `700 ${Math.round(34 * w / 2560)}px Poppins`;
  c.fillText('COZY AMBIENCE  ·  RAIN  ·  FIRE  ·  SLEEP & STUDY', w / 2, h / 2 + 90 * w / 2560);
}

function brandProfile(c, v, s) {   // 800x800, YouTube schneidet rund zu: alles Wichtige in der Mitte
  c.save(); c.scale(s / 800, s / 800);
  if (v === 'C') {
    const g = c.createRadialGradient(400, 330, 40, 400, 400, 560); g.addColorStop(0, '#f2f4ea'); g.addColorStop(1, '#b9cbaa');
    c.fillStyle = g; c.fillRect(0, 0, 800, 800);
    c.save(); c.translate(400, 560); c.scale(.82, .82); qMonstera(c, 0, 0, 1, 3, 71); c.restore();
    qVine(c, 250, 20, 260, 1.2, 2, 72); qVine(c, 560, 20, 220, 1.2, 2, 73);
  } else if (v === 'B') {
    const g = c.createLinearGradient(0, 0, 0, 800); g.addColorStop(0, '#3a2219'); g.addColorStop(1, '#1a0f0b');
    c.fillStyle = g; c.fillRect(0, 0, 800, 800);
    qGlow(c, 400, 560, 520, 'rgba(255,130,50,.45)');
    c.save(); c.translate(400, 640); c.globalCompositeOperation = 'lighter';
    for (let i = 0; i < 5; i++) flame(c, (i - 2) * 42, 0, 130 - Math.abs(i - 2) * 20, 300 - Math.abs(i - 2) * 60, 2, i * 1.7, 1, ['rgba(255,80,20,.9)', 'rgba(255,120,30,.6)', 'rgba(255,60,10,0)']);
    for (let i = 0; i < 3; i++) flame(c, (i - 1) * 36, -2, 80, 200 - Math.abs(i - 1) * 46, 2, 7 + i, 1.2, ['rgba(255,240,170,.95)', 'rgba(255,200,80,.6)', 'rgba(255,160,40,0)']);
    c.restore();
    c.strokeStyle = '#5a3420'; c.lineWidth = 36; c.lineCap = 'round'; c.beginPath(); c.moveTo(250, 680); c.lineTo(550, 630); c.moveTo(550, 680); c.lineTo(250, 630); c.stroke();
    qBush(c, 215, 640, 1.1, 1, 74); qVine(c, 560, 40, 300, 1.3, 1, 75); qVine(c, 250, 40, 220, 1.3, 1, 76);
  } else {
    const g = c.createLinearGradient(0, 0, 0, 800); g.addColorStop(0, '#2b1f1b'); g.addColorStop(1, '#17100e');
    c.fillStyle = g; c.fillRect(0, 0, 800, 800);
    qWindow(c, 210, 110, 380, 470, 4, { weather: 'regen' }, 'stadt', true);
    c.fillStyle = '#5b3c2a'; c.fillRect(150, 578, 500, 30);
    qBush(c, 290, 580, 1.15, 4, 77); qMug(c, 480, 580, 1.25); qSteam(c, 480, 490, 4, 1.25);
    qVine(c, 190, 80, 300, 1.2, 4, 78); qVine(c, 610, 80, 240, 1.2, 4, 79);
    qGlow(c, 400, 600, 420, 'rgba(255,170,90,.18)');
  }
  c.restore();
}

function brandImage(v, kind, w, h) {
  const cv = brandCanvas(w, h), c = cv.getContext('2d');
  if (kind === 'profil') { brandProfile(c, v, w); return cv.toDataURL('image/png'); }
  brandScene(c, v, w, h, 6);
  brandTitle(c, v, w, h);
  return cv.toDataURL('image/jpeg', .92);
}
