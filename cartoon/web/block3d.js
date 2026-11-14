// ---------- Blockwelt: Horror-Shorts im Look eines Bauklotz-Spiels (three.js, MIT, siehe vendor/LICENSE-three.txt) ----------
// Eigene Blockfiguren (Würfelkopf, Kastenkörper) in einer Spielwelt aus Klötzen, Nachtlicht, Taschenlampe, Nebel.
// Keine Marken, Logos oder Figuren anderer Spiele: alles hier ist aus einfachen Kästen selbst gebaut.
// Aktiv, wenn das Skript oben "welt": "block" hat. Szenen figur, zwei, gruppe, horror, monster, objekt, raetsel
// werden dann in 3D gezeichnet, alle anderen Typen bleiben 2D. Zusatzfeld je Szene: "chat" (Spiel-Chat oben links).
// Ohne WebGL bleibt B3 = null und alles läuft wie bisher als Strichmännchen.
const B3 = (() => {
  if (!window.THREE || PLAN.welt !== 'block') return null;
  if (THREE.ColorManagement) THREE.ColorManagement.legacyMode = false;
  const RW = W, RH = H;
  let renderer;
  try { renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true }); } catch (e) { return null; }
  renderer.setPixelRatio(1); renderer.setSize(RW, RH, false);
  renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.outputEncoding = THREE.sRGBEncoding; renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.35;

  const TYPES3 = new Set(['figur', 'zwei', 'gruppe', 'horror', 'monster', 'objekt', 'raetsel']);
  const MATS = {};
  const mat = (c, o = {}) => { const k = c + JSON.stringify(o); return MATS[k] || (MATS[k] = new THREE.MeshStandardMaterial({ color: c, roughness: .75, metalness: 0, ...o })); };
  const box = (w, h, d, c, o) => { const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), typeof c === 'string' ? mat(c, o) : c); m.castShadow = m.receiveShadow = true; return m; };
  const at = (m, x, y, z) => { m.position.set(x, y, z); return m; };
  const R = seed => () => { seed = (seed * 16807) % 2147483647; return (seed - 1) / 2147483646; };
  function canvasTex(w, h, draw) { const c = document.createElement('canvas'); c.width = w; c.height = h; draw(c.getContext('2d'), w, h); const t = new THREE.CanvasTexture(c); t.encoding = THREE.sRGBEncoding; t.magFilter = THREE.NearestFilter; return t; }
  // Klötzchen-Muster für Böden und Wände (leichte Fugen, wie gebaute Platten)
  function tileTex(col, line, n = 8) { const t = canvasTex(256, 256, (g, w, h) => { g.fillStyle = col; g.fillRect(0, 0, w, h); g.strokeStyle = line; g.lineWidth = 6; for (let k = 0; k <= 4; k++) { g.beginPath(); g.moveTo(k * 64, 0); g.lineTo(k * 64, h); g.stroke(); g.beginPath(); g.moveTo(0, k * 64); g.lineTo(w, k * 64); g.stroke(); } }); t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(n, n); t.magFilter = THREE.LinearFilter; return t; }

  // ---------- Gesichter: auf die Vorderseite des Würfelkopfs gemalt ----------
  const FACES = {};
  function faceTex(skin, mood, glow) {
    const k = skin + mood + (glow || ''); if (FACES[k]) return FACES[k];
    return FACES[k] = canvasTex(128, 128, (g, w, h) => {
      g.fillStyle = skin; g.fillRect(0, 0, w, h);
      const ink = glow || '#141018';
      g.fillStyle = ink; g.strokeStyle = ink; g.lineWidth = 7; g.lineCap = 'round';
      const eye = (x, y, rw, rh) => { g.beginPath(); g.ellipse(x, y, rw, rh, 0, 0, Math.PI * 2); g.fill(); };
      const wide = mood === 'angst' || mood === 'staunen';
      if (glow) { eye(42, 56, 11, 9); eye(86, 56, 11, 9); return; }
      if (mood === 'k_o') { [[42, 54], [86, 54]].forEach(([x, y]) => { g.beginPath(); g.moveTo(x - 9, y - 9); g.lineTo(x + 9, y + 9); g.moveTo(x + 9, y - 9); g.lineTo(x - 9, y + 9); g.stroke(); }); }
      else if (wide) { g.fillStyle = '#fff'; eye(42, 54, 14, 17); eye(86, 54, 14, 17); g.fillStyle = ink; eye(42, 56, 6, 7); eye(86, 56, 6, 7); }
      else eye(42, 54, 7, 11), eye(86, 54, 7, 11);
      if (mood === 'wut') { g.beginPath(); g.moveTo(30, 34); g.lineTo(54, 42); g.moveTo(98, 34); g.lineTo(74, 42); g.stroke(); }
      if (mood === 'traurig' || mood === 'angst') { g.beginPath(); g.moveTo(30, 40); g.lineTo(52, 34); g.moveTo(98, 40); g.lineTo(76, 34); g.stroke(); }
      g.beginPath();
      if (mood === 'freude' || mood === 'cool' || mood === 'neutral') { g.arc(64, 80, 22, .15 * Math.PI, .85 * Math.PI); g.stroke(); }
      else if (mood === 'traurig') { g.arc(64, 104, 18, 1.2 * Math.PI, 1.8 * Math.PI); g.stroke(); }
      else if (mood === 'staunen' || mood === 'k_o') { g.ellipse(64, 92, 9, 12, 0, 0, Math.PI * 2); g.fill(); }
      else if (mood === 'angst') { g.ellipse(64, 94, 15, 11, 0, 0, Math.PI * 2); g.fill(); }
      else { g.moveTo(48, 92); g.lineTo(80, 92); g.stroke(); }
    });
  }

  // ---------- Blockfigur ----------
  const SHIRTS = { rot: '#d63a2f', blau: '#2f6fd6', gelb: '#f2b52a', gruen: '#3c9e57', lila: '#7a4bc4', navy: '#2a3f8f' };
  const SKIN = '#f1c7a1';
  // Teile: Beine 0..2, Körper 2..4, Kopf 4..5.2 (Einheiten), Arme hängen an der Schulter (y 3.8)
  function blocky(o = {}) {
    const g = new THREE.Group();
    const shirt = o.shirt || '#d63a2f', pants = o.pants || '#2b3550', skin = o.skin || SKIN;
    const limb = (x, y, h, col) => { const p = new THREE.Group(); at(p, x, y, 0); const m = box(.95, h, .95, col, o.matOpts); at(m, 0, -h / 2, 0); p.add(m); g.add(p); return p; };
    const legL = limb(-.5, 2, 2, pants), legR = limb(.5, 2, 2, pants);
    const torso = box(2, 2, 1, shirt, o.matOpts); at(torso, 0, 3, 0); g.add(torso);
    const armL = limb(-1.5, 3.9, 1.9, o.arms || shirt), armR = limb(1.5, 3.9, 1.9, o.arms || shirt);
    [armL, armR].forEach(a => { const hand = box(.96, .45, .96, skin, o.matOpts); at(hand, 0, -1.75, 0); a.add(hand); });
    const headMats = Array.from({ length: 6 }, (_, k) => k === 4 ? new THREE.MeshStandardMaterial({ map: faceTex(skin, o.mood || 'neutral', o.glow), roughness: .8, ...(o.glow ? { emissive: '#ffffff', emissiveMap: faceTex(skin, o.mood || 'neutral', o.glow), emissiveIntensity: .9 } : {}), ...(o.matOpts || {}) }) : mat(skin, o.matOpts));
    const head = new THREE.Mesh(new THREE.BoxGeometry(1.2, 1.2, 1.2), headMats); head.castShadow = true; at(head, 0, 4.65, 0); g.add(head);
    if (o.hair) { const hair = box(1.3, .35, 1.3, o.hair); at(hair, 0, 5.3, -.03); g.add(hair); const back = box(1.3, .9, .3, o.hair); at(back, 0, 4.85, -.55); g.add(back); }
    if (o.hat === 'muetze') { const cap = box(1.32, .5, 1.32, shirt); at(cap, 0, 5.4, 0); g.add(cap); }
    if (o.lamp) { const fl = box(.3, .3, .8, '#2b2b33'); at(fl, 0, -1.8, .45); armR.add(fl); const lens = box(.26, .26, .05, '#fff6c8', { emissive: '#fff6c8', emissiveIntensity: 2 }); at(lens, 0, -1.8, .87); armR.add(lens); }
    g.userData = { legL, legR, armL, armR, head, torso };
    return g;
  }
  function hero(sc, extra = {}) {
    const f = { ...(PLAN.figur || {}), ...(sc.figur || {}), ...extra };
    const art = f.art || sc.art;
    return blocky({ shirt: SHIRTS[f.farbe] || SHIRTS.rot, mood: extra.mood || sc.gefuehl || 'neutral', hair: f.haare === 'keine' ? null : (['#3b2a20', '#1b1b22', '#c9873b', '#7a3b1f'][(f.farbe || 'rot').length % 4]),
      skin: art === 'zombie' ? '#8fbf6a' : art === 'blass' ? '#e2e8ee' : SKIN, hat: f.hut, lamp: extra.lamp });
  }
  // Pose je Aktion (Winkel in Bogenmaß um die Schulter/Hüfte)
  function animate(fig, act, lt, seed = 0) {
    const u = fig.userData, s = Math.sin(lt * 10 + seed);
    const set = (aL, aR, lL, lR, zL = 0, zR = 0) => { u.armL.rotation.set(aL, 0, zL); u.armR.rotation.set(aR, 0, zR); u.legL.rotation.x = lL; u.legR.rotation.x = lR; };
    fig.rotation.z = 0; u.head.rotation.set(0, 0, 0); u.torso.position.y = 3; let y = 0;
    switch (act) {
      case 'rennt': set(s * 1.1, -s * 1.1, -s * .9, s * .9); y = Math.abs(Math.cos(lt * 10 + seed)) * .25; fig.userData.lean = .12; break;
      case 'schlurft': set(-1.5 + Math.sin(lt * 2) * .1, -1.5 - Math.sin(lt * 2) * .1, Math.sin(lt * 3) * .3, -Math.sin(lt * 3) * .3); u.head.rotation.z = .25; break;
      case 'zittert': set(-2.2, -2.2, 0, 0, -.5, .5); fig.position.x += Math.sin(lt * 70) * .05; break;
      case 'schockiert': set(-2.9, -2.9, 0, 0, -.25, .25); y = lt < .25 ? Math.sin(lt / .25 * Math.PI) * .5 : 0; break;
      case 'jubelt': set(-3, -3, 0, 0, -.3, .3); y = Math.abs(Math.sin(lt * 6)) * .5; break;
      case 'zeigt': set(0, -1.5, 0, 0); break;
      case 'winkt': set(0, -2.8, 0, 0, 0, .4 + Math.sin(lt * 11) * .35); break;
      case 'denkt': set(0, -2.3, 0, 0, 0, -.6); u.head.rotation.z = .12; break;
      case 'haende': set(-2.3, -2.3, 0, 0, .5, -.5); break;
      case 'versteckt': set(-2.4, -2.4, -1.3, -1.3, .4, -.4); y = -1.1; break;
      case 'faellt': set(-2.6, -2.2, .4, -.3); fig.rotation.z = -Math.min(1.45, lt * 2.2); break;
      default: set(Math.sin(lt * 2 + seed) * .05, -Math.sin(lt * 2 + seed) * .05, 0, 0); u.head.rotation.y = Math.sin(lt * .9 + seed) * .25;
    }
    return y;
  }

  // ---------- Monster ----------
  function monster(kind, sc) {
    if (kind === 'zombie') return blocky({ shirt: '#4d6b8a', pants: '#3a3a2e', skin: '#7fae5c', mood: 'wut', arms: '#7fae5c' });
    if (kind === 'geist') { const g = blocky({ shirt: '#eef2ff', pants: '#eef2ff', skin: '#f4f6ff', glow: '#1b1430', matOpts: { transparent: true, opacity: .55, emissive: '#b8c6ff', emissiveIntensity: .5 } }); g.userData.legL.visible = g.userData.legR.visible = false; return g; }
    // Schatten: viel zu groß, ganz schwarz, leuchtende Augen
    const g = blocky({ shirt: '#050407', pants: '#050407', skin: '#050407', arms: '#050407', glow: sc.augen || '#ff2a1f', matOpts: { roughness: 1 } });
    g.userData.armL.scale.y = g.userData.armR.scale.y = 1.6; g.scale.set(1, 1.45, 1);
    const eyeLight = new THREE.PointLight(sc.augen || '#ff2a1f', 1.2, 6); at(eyeLight, 0, 4.7, 1.2); g.add(eyeLight);
    return g;
  }

  // ---------- Orte aus Klötzen ----------
  const NIGHT = new Set(['nacht', 'strasse', 'friedhof', 'spukhaus', 'dunkelwald', 'keller', 'kinderzimmer', 'krankenhaus']);
  const INDOOR = { haus: ['#cdb48f', '#8a5a34'], kinderzimmer: ['#7c93b8', '#9a7350'], keller: ['#4a4450', '#2e2a30'], schule: ['#a9c4a0', '#8f6a48'],
    buero: ['#c7cfd8', '#6c7480'], labor: ['#d4e4ea', '#8a9ca8'], krankenhaus: ['#a8c8bc', '#7f9a90'] };
  function place(scene, ort, dark, world) {
    const rnd = R(ort.length * 97 + 13);
    if (INDOOR[ort]) {
      const [wall, floor] = INDOOR[ort];
      const fl = new THREE.Mesh(new THREE.PlaneGeometry(40, 40), new THREE.MeshStandardMaterial({ map: tileTex(floor, 'rgba(0,0,0,.25)', 10), roughness: .9 })); fl.rotation.x = -Math.PI / 2; fl.receiveShadow = true; scene.add(fl);
      const wm = new THREE.MeshStandardMaterial({ map: tileTex(wall, 'rgba(0,0,0,.12)', 6), roughness: .95 });
      const back = new THREE.Mesh(new THREE.BoxGeometry(24, 12, .6), wm); at(back, 0, 6, -10); back.receiveShadow = true; scene.add(back);
      [-1, 1].forEach(s => { const side = new THREE.Mesh(new THREE.BoxGeometry(.6, 12, 30), wm); at(side, s * 9, 6, 2); side.receiveShadow = true; scene.add(side); });
      const ceil = box(24, .6, 30, '#2a2630'); at(ceil, 0, 11, 2); scene.add(ceil);
      // Tür und Fenster in der Rückwand
      const door = box(3, 6, .3, '#5a3a22'); at(door, -4, 3, -9.6); scene.add(door); world.door = door;
      const knob = box(.3, .3, .3, '#d9b13b', { metalness: .6 }); at(knob, -2.9, 3, -9.4); scene.add(knob);
      const win = box(4, 3, .2, dark ? '#1a2550' : '#a8dcff', { emissive: dark ? '#1a2550' : '#a8dcff', emissiveIntensity: dark ? .6 : .5 }); at(win, 4, 6.5, -9.6); scene.add(win);
      [[4, 6.5, 4.4, .4], [4, 6.5, .4, 3.4]].forEach(([x, y, w, h]) => { const fr = box(w, h, .4, '#e8e2d6'); at(fr, x, y, -9.5); scene.add(fr); });
      if (ort === 'kinderzimmer') { const bed = box(4, 1.2, 6, '#e8e2d6'); at(bed, 5.5, .6, -5); scene.add(bed); const blanket = box(4.1, .5, 4, '#c94f6d'); at(blanket, 5.5, 1.35, -4); scene.add(blanket); const wardrobe = box(3.5, 8, 2, '#6b4428'); at(wardrobe, -6.8, 4, -7.5); scene.add(wardrobe); world.closet = wardrobe; }
      else if (ort === 'keller') { for (let k = 0; k < 6; k++) { const c = box(1.6, 1.6, 1.6, '#8a6a44'); at(c, -7 + rnd() * 3, .8 + (k % 3 === 2 ? 1.6 : 0), -8 + k * 1.3); c.rotation.y = rnd() * .5; scene.add(c); } const pipe = box(24, .4, .4, '#6c6f78', { metalness: .5 }); at(pipe, 0, 10, -9); scene.add(pipe); }
      else if (ort === 'schule' || ort === 'krankenhaus') { for (let k = 0; k < 7; k++) { const l = box(1.4, 5, 1, ort === 'schule' ? '#3a6fb0' : '#e8efe9'); at(l, -8.2, 2.5, -8 + k * 1.6); scene.add(l); } }
      else { const table = box(4, .4, 2.5, '#7a5230'); at(table, 5, 2.4, -6); scene.add(table); [[-1.7, -1], [1.7, -1], [-1.7, 1], [1.7, 1]].forEach(([x, z]) => { const leg = box(.3, 2.2, .3, '#5a3a22'); at(leg, 5 + x, 1.1, -6 + z * .9); scene.add(leg); }); const sofa = box(5, 2, 2, '#4f6a9a'); at(sofa, -5, 1, -7.5); scene.add(sofa); }
      // Deckenlampe (flackert im Dunkeln)
      const bulb = box(.6, .6, .6, '#fff2c0', { emissive: '#fff2c0', emissiveIntensity: 2 }); at(bulb, 0, 9.6, -2); scene.add(bulb);
      const cord = box(.08, 1.2, .08, '#111'); at(cord, 0, 10.3, -2); scene.add(cord);
      const lamp = new THREE.PointLight('#ffd89a', dark ? 1.1 : 1.6, 28, 1.6); at(lamp, 0, 9, -2); lamp.castShadow = true; lamp.shadow.mapSize.set(512, 512); scene.add(lamp);
      world.flicker = { lamp, bulb, base: lamp.intensity };
      return { sky: dark ? '#05040a' : '#2a2630', far: 34 };
    }
    // draußen
    const night = dark || NIGHT.has(ort);
    const grassCol = { friedhof: '#2f3a2c', dunkelwald: '#1d2a1c', strasse: '#3a3a40', stadt: '#555a60', wueste: '#d9b46a', strand: '#e4cc8a' }[ort] || (night ? '#2f4a2c' : '#5fae4f');
    const fl = new THREE.Mesh(new THREE.PlaneGeometry(200, 200), new THREE.MeshStandardMaterial({ map: tileTex(grassCol, 'rgba(0,0,0,.18)', 50), roughness: 1 })); fl.rotation.x = -Math.PI / 2; fl.receiveShadow = true; scene.add(fl);
    const houses = ort === 'strasse' || ort === 'stadt' || ort === 'dorf' || ort === 'nacht' || ort === 'spukhaus';
    if (ort === 'strasse' || ort === 'stadt' || ort === 'nacht') {
      const road = box(7, .1, 200, '#26262c'); at(road, 0, .05, 0); scene.add(road);
      for (let z = -90; z < 90; z += 6) { const stripe = box(.4, .12, 2.5, '#d9d2a6'); at(stripe, 0, .06, z); scene.add(stripe); }
      for (let z = -60; z < 30; z += 14) [-1, 1].forEach(s => { const pole = box(.35, 9, .35, '#3a3c44'); at(pole, s * 5, 4.5, z); scene.add(pole); const arm = box(1.6, .3, .3, '#3a3c44'); at(arm, s * 4.3, 8.9, z); scene.add(arm); const head = box(.8, .3, .8, '#fff2c0', { emissive: '#ffe6a0', emissiveIntensity: night ? 2.2 : .2 }); at(head, s * 3.6, 8.7, z); scene.add(head); if (night && z > -40 && (z / 14 + s) % 2 === 0) { const l = new THREE.PointLight('#ffcf7a', 1.3, 18, 1.5); at(l, s * 3.6, 8, z); scene.add(l); } });
    }
    if (houses) for (let z = -70; z < 20; z += 12) [-1, 1].forEach((s, k) => {
      const w = 7 + rnd() * 3, h = 6 + rnd() * 5, col = night ? ['#3b3446', '#2e3646', '#463a34'][Math.floor(rnd() * 3)] : ['#d9c3a0', '#c7d2e0', '#e0b8a0'][Math.floor(rnd() * 3)];
      const hs = box(w, h, 8, col); at(hs, s * (11 + w / 2), h / 2, z); scene.add(hs);
      const roof = box(w + .8, 1.2, 8.8, night ? '#2a1e22' : '#b3473a'); at(roof, s * (11 + w / 2), h + .6, z); scene.add(roof);
      for (let k2 = 0; k2 < 2; k2++) { const lit = night && rnd() > .7; const wn = box(.2, 1.6, 1.6, lit ? '#ffcf7a' : '#151821', { emissive: lit ? '#ffb347' : '#000000', emissiveIntensity: lit ? 1.4 : 0 }); at(wn, s * 10.95, h * .6, z - 2 + k2 * 4); scene.add(wn); }
    });
    if (ort === 'spukhaus') { const hs = box(14, 12, 10, '#2a2533'); at(hs, 0, 6, -26); scene.add(hs); const roof = box(15, 1.5, 11, '#17121c'); at(roof, 0, 12.75, -26); scene.add(roof); const top = box(6, 4, 6, '#2a2533'); at(top, 3, 15, -26); scene.add(top); [[-4, 8], [4, 8], [-4, 3.5]].forEach(([x, y], k) => { const wn = box(2.2, 2.6, .3, k === 1 ? '#ffcf7a' : '#0c0a10', { emissive: k === 1 ? '#ffb347' : '#000000', emissiveIntensity: k === 1 ? 1.6 : 0 }); at(wn, x, y, -20.9); scene.add(wn); }); const door = box(2.6, 4.4, .3, '#120c10'); at(door, 3.5, 2.2, -20.9); scene.add(door); world.door = door; }
    if (ort === 'wald' || ort === 'dunkelwald' || ort === 'feld' || ort === 'friedhof' || ort === 'dorf') {
      const n = ort === 'feld' ? 10 : 40;
      for (let k = 0; k < n; k++) { const x = (rnd() - .5) * 70, z = -rnd() * 70 + 8; if (Math.abs(x) < 5 && z > -30) continue; const h = 6 + rnd() * 6, trunk = box(1, h, 1, ort === 'dunkelwald' || ort === 'friedhof' ? '#1c1418' : '#6b4428'); at(trunk, x, h / 2, z); scene.add(trunk);
        if (ort !== 'friedhof' && ort !== 'dunkelwald') { const lv = box(4, 3.5, 4, night ? '#1f3d22' : '#3f9a48'); at(lv, x, h + 1, z); scene.add(lv); const lv2 = box(2.6, 2, 2.6, night ? '#1f3d22' : '#4fb558'); at(lv2, x, h + 3.5, z); scene.add(lv2); }
        else { const br = box(3, .5, .5, '#1c1418'); at(br, x + .8, h * .8, z); br.rotation.z = .5; scene.add(br); } }
    }
    if (ort === 'friedhof') for (let k = 0; k < 18; k++) { const x = (rnd() - .5) * 26, z = -rnd() * 40 + 2; if (Math.abs(x) < 2.5) continue; const g = box(1.8, 2.4 + rnd(), .5, '#7d7a88'); at(g, x, 1.2, z); g.rotation.z = (rnd() - .5) * .25; scene.add(g); }
    return { sky: night ? '#0b0d1e' : '#8fcff5', far: night ? 62 : 120, night };
  }

  // ---------- Welt je Einstellung ----------
  const cache = {};
  function build(sc) {
    const scene = new THREE.Scene(), world = { scene, figs: [] };
    const gruselig = PLAN.stimmung === 'gruselig' || PLAN.stimmung === 'mysterioes';
    const ort = sc.ort || (sc.typ === 'horror' ? 'keller' : 'strasse');
    const dark = gruselig || NIGHT.has(ort) || sc.typ === 'horror';
    const env = place(scene, ort, dark, world);
    scene.background = new THREE.Color(env.sky);
    scene.fog = new THREE.Fog(env.sky, dark ? 14 : 24, env.far);
    scene.add(new THREE.HemisphereLight(dark ? '#6a7ab0' : '#cfe8ff', dark ? '#1c1626' : '#5a4a3a', dark ? .75 : .9));
    const moon = new THREE.DirectionalLight(dark ? '#9fb4ff' : '#fff4dc', dark ? .8 : 1.3); at(moon, 12, 25, 14); moon.castShadow = true;
    moon.shadow.mapSize.set(1024, 1024); Object.assign(moon.shadow.camera, { left: -25, right: 25, top: 25, bottom: -25, far: 80 }); scene.add(moon);
    const typ = sc.typ, act = sc.aktion || (typ === 'horror' ? 'zittert' : typ === 'monster' ? 'rennt' : 'steht');
    world.dark = dark; world.act = act;
    if (typ !== 'objekt' && typ !== 'raetsel') {
      const h = hero(sc, { lamp: dark }); scene.add(h); world.figs.push({ obj: h, act, x: 0, z: 0, seed: 0 });
      if (dark) { const spot = new THREE.SpotLight('#fff1cc', 3.2, 34, .42, .55, 1.2); spot.castShadow = true; spot.shadow.mapSize.set(1024, 1024); at(spot, 1.5, 3, .6); scene.add(spot); scene.add(spot.target); world.spot = spot; }
      if (typ === 'zwei') { const z2 = sc.zweite || {}; const b = blocky({ shirt: SHIRTS[z2.farbe] || SHIRTS.blau, mood: z2.gefuehl || 'staunen', hair: '#1b1b22' }); scene.add(b); world.figs.push({ obj: b, act: z2.aktion || 'zeigt', x: 3.4, z: 0, seed: 2, ry: -.5 }); world.figs[0].x = -2.2; world.figs[0].ry = .5; }
      if (typ === 'gruppe') { const n = clamp(sc.anzahl || 4, 3, 7); world.figs[0].x = 0; for (let k = 1; k < n; k++) { const b = blocky({ shirt: Object.values(SHIRTS)[k % 6], mood: sc.gefuehl || 'staunen', hair: ['#3b2a20', '#1b1b22', '#c9873b'][k % 3] }); scene.add(b); const side = k % 2 ? 1 : -1; world.figs.push({ obj: b, act, x: side * (Math.ceil(k / 2) * 2.8), z: -Math.ceil(k / 2) * 1.6, seed: k, ry: -side * .25 }); } }
    }
    const mk = sc.monster || (typ === 'monster' ? 'schatten' : null);
    if (mk && ['zombie', 'geist', 'schatten'].includes(mk)) {
      const n = mk === 'zombie' ? clamp(sc.anzahl || 1, 1, 4) : 1;
      world.monsters = Array.from({ length: n }, (_, k) => { const m = monster(mk, sc); scene.add(m); return { obj: m, kind: mk, k }; });
    } else if (mk) world.emojiMonster = mk;
    if (typ === 'horror' || (dark && !mk && typ !== 'objekt')) { // nur Augen im Dunkeln
      const eyes = new THREE.Group(); [-.5, .5].forEach(x => { const e = box(.45, .3, .1, sc.augen || '#ff2a1f', { emissive: sc.augen || '#ff2a1f', emissiveIntensity: 3 }); e.castShadow = false; at(e, x, 0, 0); eyes.add(e); });
      at(eyes, 4.5, 4.6, -8.5); eyes.visible = typ === 'horror'; scene.add(eyes); world.eyes = eyes;
    }
    const cam = new THREE.PerspectiveCamera(WIDE ? 42 : 50, RW / RH, .3, 300); world.camera = cam;
    // Kamera-Art je Einstellung: vorne (Gesicht), über die Schulter (Blick auf die Gefahr), weit (Ort)
    const kinds = typ === 'monster' ? ['schulter', 'vorne'] : typ === 'horror' ? ['vorne', 'nah'] : typ === 'objekt' || typ === 'raetsel' ? ['weit'] : act === 'rennt' ? ['vorne'] : ['vorne', 'weit', 'nah', 'schulter'];
    world.camKind = sc.kamera || kinds[sc.i % kinds.length];
    return world;
  }

  function draw(ctx, sc, lt, d) {
    const world = cache[sc.i] || (cache[sc.i] = build(sc));
    const { scene, camera } = world;
    const prog = clamp(lt / Math.max(.5, d));
    // Figuren
    let runZ = 0;
    world.figs.forEach((f, k) => {
      const o = f.obj; o.position.set(f.x, 0, f.z);
      if (f.act === 'rennt') { runZ = lt * 7; o.position.z = f.z + runZ; }
      const y = animate(o, f.act, lt, f.seed); o.position.y = y;
      o.rotation.y = (f.ry || 0) + (world.camKind === 'schulter' && k === 0 ? Math.PI : 0);
      if (f.act === 'rennt' && world.camKind === 'schulter') o.rotation.y = 0;
    });
    const hx = world.figs[0] ? world.figs[0].obj.position.x : 0, hz = world.figs[0] ? world.figs[0].obj.position.z : 0;
    if (world.monsters) world.monsters.forEach(m => {
      const o = m.obj, near = ease(prog), off = (m.k - (world.monsters.length - 1) / 2) * 3.2;
      const startZ = hz - 18 - m.k * 2, endZ = hz - (world.act === 'rennt' ? 7 : 5) - m.k * 1.5;
      o.position.set(hx + off + (m.kind === 'schatten' ? 2.5 * (1 - near) : 0), m.kind === 'geist' ? 1.2 + Math.sin(lt * 2 + m.k) * .3 : 0, lerp(startZ, endZ, near));
      if (world.act === 'rennt') o.position.z = hz - 9 + Math.sin(lt * 1.5) * .6 - m.k * 2;
      animate(o, m.kind === 'zombie' ? 'schlurft' : m.kind === 'geist' ? 'haende' : (lt % 3 < .1 ? 'zeigt' : 'steht'), lt, m.k + 3);
      if (m.kind === 'schatten') { o.userData.armL.rotation.x = o.userData.armR.rotation.x = -.15; o.userData.head.rotation.z = Math.sin(lt * .7) * .25; }
      o.rotation.y = 0;
      o.visible = m.kind !== 'schatten' || (lt % 2.2) > .08; // kurzes Flackern
    });
    if (world.eyes) { world.eyes.visible = sc.typ === 'horror' ? lt > d * .3 && (lt % 3.1) > .12 : false; world.eyes.position.x = 4.5 + Math.sin(lt * .5) * .4; }
    // Licht: Lampe flackert, Taschenlampe sucht den Raum ab
    if (world.flicker) { const off = world.dark && (Math.sin(lt * 37) > .9 || (lt % 2.3) < .06); world.flicker.lamp.intensity = off ? .05 : world.flicker.base; world.flicker.bulb.material.emissiveIntensity = off ? .1 : 2; }
    if (world.spot) { const f = world.figs[0].obj; const back = world.camKind === 'schulter' ? -1 : 1; world.spot.position.set(f.position.x + 1.5, 3.1, f.position.z + .6 * back); world.spot.target.position.set(f.position.x + Math.sin(lt * .9) * 5, 1.5, f.position.z + (world.camKind === 'schulter' || world.act === 'rennt' ? -14 : 9)); if (world.act === 'rennt' && world.camKind !== 'schulter') world.spot.target.position.z = f.position.z + 14; world.spot.intensity = world.flicker && world.flicker.lamp.intensity < .1 ? 1.2 : 3.2; }
    if (world.door) world.door.rotation.y = sc.tuer ? -ease(clamp((lt - d * .3) / (d * .5))) * 1.2 : 0;
    // Kamera
    const sh = world.dark ? shake(lt, .06, 1, sc.i) : [0, 0];
    const push = ease(prog);
    const ck = world.camKind;
    if (ck === 'schulter') { camera.position.set(hx + 4.2 + sh[0], 7.6 + sh[1], hz + 15 - push * 3); camera.lookAt(hx - 1.2, 3, hz - 10); }
    else if (ck === 'nah') { camera.position.set(hx + 1 + sh[0], 4.6 + sh[1], hz + 7.5 - push * 1.5); camera.lookAt(hx, 3.6, hz); }
    else if (ck === 'weit') { camera.position.set(hx - 6 + push * 2 + sh[0], 8.5 + sh[1], hz + 15 - push * 3); camera.lookAt(hx, 2.5, hz - 4); }
    else { camera.position.set(hx + 2 + sh[0], 4.4 + sh[1], hz + 12.5 - push * 2.5); camera.lookAt(hx, 2.9, hz - 2); }
    if (world.act === 'rennt' && ck !== 'schulter') { camera.position.set(hx + 1.5 + sh[0], 4.6 + sh[1], hz + 12); camera.lookAt(hx, 3, hz - 3); }
    renderer.render(scene, camera);
    ctx.save(); ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.drawImage(renderer.domElement, 0, 0); ctx.restore();
    overlay(ctx, sc, lt, d, world);
  }

  // ---------- 2D darüber: Schild, Emoji, Spiel-Chat ----------
  function overlay(ctx, sc, lt, d, world) {
    base(ctx);
    if (world.emojiMonster) emoji(ctx, world.emojiMonster, lerp(900, 700, ease(clamp(lt / d))), 820, 360, Math.sin(lt * 3) * .1, .95);
    if (sc.objekt && (sc.typ === 'objekt' || sc.typ === 'raetsel')) {
      const k = popIn(lt, .05, .4), y = 760 + Math.sin(lt * 2) * 14;
      ctx.save(); ctx.globalCompositeOperation = 'lighter'; const g = ctx.createRadialGradient(540, y, 40, 540, y, 420); g.addColorStop(0, world.dark ? 'rgba(255,60,40,.35)' : 'rgba(255,240,170,.45)'); g.addColorStop(1, 'rgba(0,0,0,0)'); ctx.fillStyle = g; ctx.fillRect(0, y - 450, 1080, 900); ctx.restore();
      emoji(ctx, sc.objekt, 540, y, 380 * k, Math.sin(lt * 1.6) * .06);
      if (sc.typ === 'raetsel') text(ctx, '?', 540 + 230, y - 250, 200 * popIn(lt, .4, .3), '#ffe14d', INK, 18);
    } else if (sc.objekt) emoji(ctx, sc.objekt, 820, 1040, 190 * clamp((lt - d * .4) / .3), 0, .95);
    weather(ctx, sc, lt);
    if (sc.chat) chat(ctx, sc.chat, lt);
    if (sc.text) { base(ctx); const k = popIn(lt, .05, .3); ctx.save(); ctx.translate(540, 300); ctx.scale(k, k); fitText(ctx, sc.text.toUpperCase(), 0, 0, 86, 900, world.dark ? '#f2ecff' : '#ffe14d', '#000', 14); ctx.restore(); }
  }
  // Spiel-Chat wie in einem Online-Spiel: Nachricht tippt sich Buchstabe für Buchstabe
  function chat(ctx, msg, lt) {
    base(ctx);
    const i = msg.indexOf(':'), who = i > 0 ? msg.slice(0, i).trim() : '???', said = i > 0 ? msg.slice(i + 1).trim() : msg;
    const n = Math.floor(clamp((lt - .15) / Math.max(.4, said.length * .045)) * said.length);
    const x = 50, y = 430, w = 900, h = 180;
    ctx.save(); ctx.globalAlpha = clamp(lt / .15) * .9; rrect(ctx, x, y, w, h, 18); ctx.fillStyle = 'rgba(8,8,14,.72)'; ctx.fill();
    ctx.globalAlpha = 1; ctx.font = '700 46px Poppins'; ctx.textAlign = 'left'; ctx.textBaseline = 'middle';
    ctx.fillStyle = '#9aa3b5'; ctx.fillText('Chat', x + 30, y + 44);
    ctx.fillStyle = '#ff5a4f'; ctx.fillText(who + ':', x + 30, y + 122); const ww = ctx.measureText(who + ': ').width;
    ctx.fillStyle = '#ffffff'; ctx.font = '700 54px Poppins'; ctx.fillText(said.slice(0, n) + ((lt * 2) % 1 < .5 && n < said.length ? '|' : ''), x + 30 + ww, y + 122, w - 60 - ww);
    ctx.restore();
  }
  return { draw, types: TYPES3 };
})();
window.B3 = B3;
