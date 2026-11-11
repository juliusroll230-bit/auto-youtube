// ---------- Firmen-Spiel in 3D: vier Firmen als Diorama (three.js, MIT, siehe vendor/LICENSE-three.txt) ----------
// Zeichnet die Szene "firma" als 3D-Bild in eine eigene WebGL-Leinwand; firma.js legt es ins Video und malt
// Namen, Kontostand und Schilder darüber. Ohne WebGL bleibt F3 = null und firma.js zeichnet die 2D-Fabrik.
// sc.thema: autos (Autofabrik), burger (Burgerladen), rakete (Raketenbasis), games (Spielestudio)
// sc.level: 0 bis 4 (Ausbaustufe, wächst mit den Abos); alte Folgen geben nur sc.stufe (garage ... konzern)
const F3 = (() => {
  if (!window.THREE) return null;
  if (THREE.ColorManagement) THREE.ColorManagement.legacyMode = false; // Hex-Farben als sRGB, sonst wirkt alles blass
  const RW = 1080, RH = 1540, TOP = 380; // Bildausschnitt: unter dem Kontostand bis zum unteren Rand
  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
  } catch (e) { return null; }
  renderer.setPixelRatio(1); renderer.setSize(RW, RH, false);
  renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.outputEncoding = THREE.sRGBEncoding; renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.0;

  const MATS = {};
  const mat = (c, o = {}) => { const k = c + JSON.stringify(o); return MATS[k] || (MATS[k] = new THREE.MeshStandardMaterial({ color: c, roughness: .55, metalness: .05, ...o })); };
  const box = (w, h, d, c, o) => { const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), typeof c === 'string' ? mat(c, o) : c); m.castShadow = m.receiveShadow = true; return m; };
  const cyl = (r1, r2, h, c, seg = 20, o) => { const m = new THREE.Mesh(new THREE.CylinderGeometry(r1, r2, h, seg), typeof c === 'string' ? mat(c, o) : c); m.castShadow = m.receiveShadow = true; return m; };
  const sph = (r, c, o, seg = 20) => { const m = new THREE.Mesh(new THREE.SphereGeometry(r, seg, seg), typeof c === 'string' ? mat(c, o) : c); m.castShadow = true; return m; };
  const at = (m, x, y, z) => { m.position.set(x, y, z); return m; };
  function canvasTex(w, h, draw) { const c = document.createElement('canvas'); c.width = w; c.height = h; draw(c.getContext('2d'), w, h); const t = new THREE.CanvasTexture(c); t.encoding = THREE.sRGBEncoding; t.anisotropy = 4; return t; }
  const glow = (tex, k = .9) => new THREE.MeshStandardMaterial({ map: tex, emissive: '#ffffff', emissiveMap: tex, emissiveIntensity: k, roughness: .4 });
  const R = seed => () => { seed = (seed * 16807) % 2147483647; return (seed - 1) / 2147483646; };

  const SKINS = ['#f6d7b8', '#e9b98f', '#c98d63', '#8d5a3b', '#f2c9a0'];
  const CARS = ['#e0392f', '#2f63c9', '#f2b52a', '#3fa35b', '#7a4bc4', '#ff7a1a', '#1fb5b5', '#f4f4f4'];
  const AUTO_KEYS = ['garage', 'werkstatt', 'fabrik', 'grossfabrik', 'konzern'];
  const SIZES = [[8, 6.5], [11, 8], [15, 10], [19, 13], [22, 15]]; // Breite, Tiefe je Ausbaustufe

  // ---------- Figuren ----------
  function worker(seed, o = {}) {
    const g = new THREE.Group();
    const shirts = o.shirts || ['#2f63c9', '#e0392f', '#3fa35b', '#7a4bc4', '#f2b52a', '#1fb5b5', '#ff7a1a', '#2a3f8f'];
    const shirt = o.shirt || shirts[seed % shirts.length], skin = SKINS[(seed * 7) % SKINS.length];
    const pants = o.pants || '#2b3550';
    const legL = box(.2, .72, .22, pants), legR = box(.2, .72, .22, pants);
    at(legL, -.13, .36, 0); at(legR, .13, .36, 0); g.add(legL, legR);
    const body = new THREE.Mesh(new THREE.CapsuleGeometry(.3, .42, 6, 16), mat(shirt)); body.castShadow = true; at(body, 0, 1.12, 0); g.add(body);
    if (o.vest) { const strap = box(.62, .08, .05, '#ffd23a', { emissive: '#3a2a00' }); at(strap, 0, 1.2, .29); g.add(strap); }
    if (o.apron) { const ap = box(.46, .62, .05, o.apron); at(ap, 0, .98, .29); g.add(ap); }
    if (o.backpack) { const bp = box(.46, .6, .26, '#d9dde4'); at(bp, 0, 1.2, -.33); g.add(bp); }
    const head = sph(.29, skin); at(head, 0, 1.74, 0); g.add(head);
    [-1, 1].forEach(s => { const e = sph(.045, '#1b1b22', {}, 10); at(e, s * .1, 1.78, .26); g.add(e); });
    const smile = new THREE.Mesh(new THREE.TorusGeometry(.07, .015, 6, 12, Math.PI), mat('#1b1b22')); smile.rotation.z = Math.PI; at(smile, 0, 1.68, .27); g.add(smile);
    const hat = o.hat || 'helm';
    if (hat === 'zylinder') { const h = cyl(.24, .24, .42, '#1b1b22'); at(h, 0, 2.12, 0); const b = cyl(.38, .38, .04, '#1b1b22'); at(b, 0, 1.92, 0); const band = cyl(.245, .245, .08, '#c0392b'); at(band, 0, 1.98, 0); g.add(h, b, band); }
    else if (hat === 'koch') { const h = cyl(.22, .24, .34, '#ffffff'); at(h, 0, 2.08, 0); const puff = sph(.3, '#ffffff'); puff.scale.set(1, .62, 1); at(puff, 0, 2.3, 0); g.add(h, puff); }
    else if (hat === 'astro') { const dome = new THREE.Mesh(new THREE.SphereGeometry(.42, 24, 18), new THREE.MeshStandardMaterial({ color: '#cfeaff', transparent: true, opacity: .32, roughness: .05, metalness: .1 })); at(dome, 0, 1.76, 0); const ring = new THREE.Mesh(new THREE.TorusGeometry(.33, .06, 8, 20), mat('#d9dde4')); ring.rotation.x = Math.PI / 2; at(ring, 0, 1.44, 0); g.add(dome, ring); }
    else if (hat === 'kopfhoerer') { const band = new THREE.Mesh(new THREE.TorusGeometry(.31, .04, 8, 20, Math.PI), mat('#1b1b22')); at(band, 0, 1.76, 0); const col = o.hcol || '#ff3fa4'; [-1, 1].forEach(s => { const cup = cyl(.11, .11, .1, col, 14, { emissive: col, emissiveIntensity: .4 }); cup.rotation.z = Math.PI / 2; at(cup, s * .3, 1.74, 0); g.add(cup); }); const hair = new THREE.Mesh(new THREE.SphereGeometry(.3, 20, 10, 0, Math.PI * 2, 0, Math.PI / 2.2), mat(['#3b2a20', '#1b1b22', '#c9873b', '#7a3b1f'][seed % 4])); at(hair, 0, 1.78, -.02); g.add(band, hair); }
    else if (hat === 'kappe') { const cap = new THREE.Mesh(new THREE.SphereGeometry(.3, 20, 10, 0, Math.PI * 2, 0, Math.PI / 2), mat(o.hcol || '#d8312b')); at(cap, 0, 1.8, 0); const visor = box(.3, .03, .22, o.hcol || '#d8312b'); at(visor, 0, 1.82, .3); g.add(cap, visor); }
    else { const helm = new THREE.Mesh(new THREE.SphereGeometry(.31, 20, 12, 0, Math.PI * 2, 0, Math.PI / 2), mat(o.hcol || '#ffd23a', { roughness: .35 })); helm.castShadow = true; at(helm, 0, 1.8, 0); const brim = cyl(.36, .36, .03, o.hcol || '#f2b52a'); at(brim, 0, 1.8, .03); g.add(helm, brim); }
    const arm = s => { const p = new THREE.Group(); at(p, s * .38, 1.38, 0); const a = box(.13, .6, .13, shirt); at(a, 0, -.27, 0); const hand = sph(.08, skin, {}, 10); at(hand, 0, -.6, 0); p.add(a, hand); g.add(p); return p; };
    g.userData.armL = arm(-1); g.userData.armR = arm(1);
    if (o.tool !== false) { const tool = box(.06, .06, .34, o.tool || '#9aa3ad', { metalness: .6, roughness: .3 }); at(tool, 0, -.62, .14); g.userData.armR.add(tool); }
    if (o.tray) { const tr = cyl(.32, .32, .04, '#c9ced6', 18, { metalness: .6 }); tr.rotation.x = Math.PI / 2 - .05; at(tr, 0, -.66, -.05); g.userData.armR.add(tr); const bg = burger(.5); bg.rotation.x = Math.PI / 2; at(bg, 0, -.68, -.18); g.userData.armR.add(bg); }
    g.userData.seed = seed; g.userData.mode = o.mode || null;
    return g;
  }
  function animWorker(w, lt, mode) {
    const s = w.userData.seed, u = w.userData;
    mode = mode || u.mode;
    if (mode === 'wave') { u.armR.rotation.x = Math.PI; u.armR.rotation.z = .4 + Math.sin(lt * 8) * .35; u.armL.rotation.x = 0; return; }
    if (mode === 'cheer') { u.armL.rotation.z = -2.6; u.armR.rotation.z = 2.6; u.armL.rotation.x = u.armR.rotation.x = 0; w.position.y = Math.abs(Math.sin(lt * 6 + s)) * .25; return; }
    u.armL.rotation.z = u.armR.rotation.z = 0;
    if (mode === 'carry') { u.armR.rotation.x = -1.5 + Math.sin(lt * 4 + s) * .05; u.armL.rotation.x = Math.sin(lt * 4 + s) * .3; w.rotation.z = Math.sin(lt * 4 + s) * .03; return; }
    if (mode === 'type') { u.armR.rotation.x = -1.2 + Math.sin(lt * 16 + s) * .12; u.armL.rotation.x = -1.2 + Math.cos(lt * 15 + s) * .12; return; }
    const k = Math.sin(lt * (7 + s % 3) + s);
    u.armR.rotation.x = -1.1 - k * .5; u.armL.rotation.x = -.6 + Math.sin(lt * 3 + s) * .1;
  }

  // ---------- Dinge ----------
  function burger(sz = 1) { // kleiner Burger aus Scheiben: Brötchen, Salat, Käse, Fleisch, Brötchen
    const g = new THREE.Group(); let y = 0;
    const layer = (r, h, c, o) => { const m = cyl(r * sz, r * sz, h * sz, c, 20, o); at(m, 0, (y + h / 2) * sz, 0); y += h; g.add(m); return m; };
    layer(.3, .1, '#e0a24a'); layer(.32, .1, '#6b3a22', { roughness: .8 }); const ch = box(.6 * sz, .03 * sz, .6 * sz, '#ffcf3f'); at(ch, 0, y * sz, 0); ch.rotation.y = .4; g.add(ch); y += .03;
    layer(.33, .04, '#5fbf4a'); layer(.29, .06, '#e8463b');
    const top = new THREE.Mesh(new THREE.SphereGeometry(.31 * sz, 20, 12, 0, Math.PI * 2, 0, Math.PI / 2), mat('#e9a64d', { roughness: .45 })); top.castShadow = true; at(top, 0, y * sz, 0); top.scale.y = .75; g.add(top);
    return g;
  }
  function car(col) {
    const g = new THREE.Group();
    const chassis = box(2.3, .14, 1.0, '#5d6470', { metalness: .5, roughness: .4 }); at(chassis, 0, .38, 0);
    const engine = box(.6, .35, .6, '#8a8f99', { metalness: .4 }); at(engine, .6, .62, 0);
    const lower = box(2.4, .5, 1.1, col, { roughness: .25, metalness: .3 }); at(lower, 0, .62, 0);
    const cabin = box(1.3, .46, 1.0, col, { roughness: .25, metalness: .3 }); at(cabin, -.15, 1.1, 0);
    const glass = box(1.32, .3, 1.02, '#9fd8f7', { roughness: .1, metalness: .2 }); at(glass, -.15, 1.12, 0);
    const lights = [-1, 1].map(s => { const l = box(.06, .12, .2, '#fff6b0', { emissive: '#fff2a0', emissiveIntensity: .8 }); at(l, 1.21, .68, s * .35); return l; });
    const wheels = [[-.75, -1], [-.75, 1], [.75, -1], [.75, 1]].map(([x, s]) => { const w = cyl(.28, .28, .2, '#22202a', 18); w.rotation.x = Math.PI / 2; at(w, x, .28, s * .5); const hub = cyl(.13, .13, .22, '#c9ced6', 12, { metalness: .7, roughness: .3 }); hub.rotation.x = Math.PI / 2; at(hub, x, .28, s * .5); g.add(hub); return w; });
    g.add(chassis, engine, lower, cabin, glass, ...lights, ...wheels);
    g.userData = { lower, cabin, glass, lights, engine, col };
    return g;
  }
  const PRIMER = mat('#b8bcc4', { roughness: .7 });
  function setCarStage(c, p) { // 0 Rahmen, 1 grundiert, 2 lackiert
    const u = c.userData, st = p < .33 ? 0 : p < .66 ? 1 : 2;
    if (u.st === st) return; u.st = st;
    u.lower.visible = u.cabin.visible = u.glass.visible = st > 0; u.engine.visible = st === 0;
    const m = st === 2 ? mat(u.col, { roughness: .25, metalness: .3 }) : PRIMER;
    u.lower.material = m; u.cabin.material = m; u.lights.forEach(l => { l.visible = st === 2; });
  }
  function robot(seed) {
    const g = new THREE.Group();
    const orange = '#ff8a1a';
    const base = cyl(.45, .55, .35, '#3b3442'); at(base, 0, .18, 0); g.add(base);
    const turn = new THREE.Group(); at(turn, 0, .35, 0); g.add(turn);
    turn.add(sph(.25, '#ffd23a'));
    const up = new THREE.Group(); turn.add(up);
    const a1 = box(.26, 1.6, .26, orange, { roughness: .35 }); at(a1, 0, .8, 0); up.add(a1);
    const elbow = new THREE.Group(); at(elbow, 0, 1.6, 0); up.add(elbow); elbow.add(sph(.2, '#ffd23a'));
    const a2 = box(.22, 1.3, .22, orange, { roughness: .35 }); at(a2, 0, .65, 0); elbow.add(a2);
    const tip = sph(.12, '#9aa3ad', { metalness: .7 }); at(tip, 0, 1.32, 0); elbow.add(tip);
    const spark = new THREE.PointLight('#ffb347', 0, 3); at(spark, 0, 1.45, 0); elbow.add(spark);
    g.userData = { turn, up, elbow, spark, seed, tip };
    return g;
  }
  function animRobot(r, lt) {
    const u = r.userData, s = u.seed;
    u.turn.rotation.y = Math.sin(lt * .9 + s) * .6; u.up.rotation.z = .35 + Math.sin(lt * 1.3 + s) * .2; u.elbow.rotation.z = 1.3 + Math.sin(lt * 1.9 + s * 2) * .35;
    u.spark.intensity = (Math.sin(lt * 31 + s) > .2) ? 2.2 : 0;
  }
  // Dampf/Rauch: Kugeln steigen auf und werden größer
  function puffs(world, n, x, y, z, o = {}) {
    const m = new THREE.MeshStandardMaterial({ color: o.col || '#ffffff', transparent: true, opacity: o.op || .5, roughness: 1, depthWrite: false });
    const arr = [];
    for (let k = 0; k < n; k++) { const s = new THREE.Mesh(new THREE.SphereGeometry(o.size || .22, 10, 8), m); world.scene.add(s); arr.push(s); }
    const sp = o.spread || .4, rise = o.rise || 1.8, speed = o.speed || .5;
    world.anim.push(lt => arr.forEach((s, k) => { const ph = (lt * speed + k / n) % 1; s.position.set(x + Math.sin(k * 2.3) * sp * (.3 + ph), y + ph * rise, z + Math.cos(k * 1.7) * sp * .5 * (.3 + ph)); s.scale.setScalar(.35 + ph * (o.grow || 1.3)); s.visible = ph < .92; }));
  }
  // Bildschirm, der jedes Bild neu gemalt wird (Leitstand, LED-Wand)
  function liveScreen(world, w, h, cw, ch, paint) {
    const c = document.createElement('canvas'); c.width = cw; c.height = ch; const g = c.getContext('2d');
    const tex = new THREE.CanvasTexture(c); tex.encoding = THREE.sRGBEncoding;
    const m = new THREE.Mesh(new THREE.PlaneGeometry(w, h), glow(tex, 1));
    world.anim.push(lt => { paint(g, cw, ch, lt); tex.needsUpdate = true; });
    paint(g, cw, ch, 0);
    return m;
  }
  function plant(x, z, s = 1) { const g = new THREE.Group(); const pot = cyl(.28 * s, .22 * s, .45 * s, '#c9673b'); at(pot, 0, .22 * s, 0); const b = sph(.42 * s, '#3fa35b', { roughness: .8 }); at(b, 0, .75 * s, 0); const b2 = sph(.3 * s, '#4fbf6a', { roughness: .8 }); at(b2, .18 * s, 1.0 * s, .05); g.add(pot, b, b2); return at(g, x, 0, z); }
  function trophy(x, y, z) { const g = new THREE.Group(); const b = box(.3, .12, .3, '#3b3442'); at(b, 0, .06, 0); const s = cyl(.04, .04, .25, '#ffcf3f', 8, { metalness: .8, roughness: .2 }); at(s, 0, .24, 0); const cup = cyl(.18, .07, .26, '#ffcf3f', 16, { metalness: .8, roughness: .2 }); at(cup, 0, .48, 0); g.add(b, s, cup); return at(g, x, y, z); }

  // ---------- Aussehen der vier Firmen ----------
  const grid = (col, line) => (c, w, h) => { c.fillStyle = col; c.fillRect(0, 0, w, h); c.strokeStyle = line; c.lineWidth = 3; for (let i = 0; i <= 8; i++) { c.beginPath(); c.moveTo(i * w / 8, 0); c.lineTo(i * w / 8, h); c.stroke(); c.beginPath(); c.moveTo(0, i * h / 8); c.lineTo(w, i * h / 8); c.stroke(); } };
  const THEMES = {
    autos: {
      floor: lv => grid(['#8c8f96', '#7d8592', '#8a909b', '#838a96', '#dfe6ef'][lv], 'rgba(0,0,0,.12)'),
      wall: lv => ['#b7bcc4', '#e3e9f1', '#d9dee6', '#e6e9ef', '#f7f9fc'][lv],
      trim: lv => lv ? '#c9312b' : '#6d7480',
      bg: lv => [['#ffd6a5', '#ff9e7a'], ['#a5d8ff', '#6d8dff'], ['#b8f0c8', '#3fbfa0'], ['#c9b8ff', '#6c5bd8'], ['#ffe9a8', '#ff7aa8']][lv],
      sign: ['#1f2440', '#ffe14d'], windows: true, logo: 'ABO MOTORS',
    },
    burger: {
      floor: () => (c, w, h) => { const n = 8; for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) { c.fillStyle = (i + j) % 2 ? '#2d2a33' : '#f6f1e7'; c.fillRect(i * w / n, j * h / n, w / n, h / n); } },
      wall: lv => ['#ffd27a', '#ffcf5a', '#ffe08a', '#ffd9e6', '#fff3c4'][lv],
      trim: () => '#d8312b',
      bg: lv => [['#ffe0b0', '#ff8f6b'], ['#fff1a8', '#ffa94d'], ['#ffd1dc', '#ff6f91'], ['#b8f2ff', '#4fb4ff'], ['#ffe9a8', '#ff6fa8']][lv],
      sign: ['#d8312b', '#fff3c4'], windows: false, logo: 'ABO BURGER',
    },
    rakete: {
      floor: () => (c, w, h) => { grid('#5f6675', 'rgba(255,255,255,.08)')(c, w, h); c.fillStyle = 'rgba(0,0,0,.08)'; for (let i = 0; i < 40; i++) c.fillRect((i * 97) % w, (i * 53) % h, 18, 6); },
      wall: lv => ['#c4cad4', '#d2d8e1', '#dfe4ec', '#e9edf3', '#f4f6fa'][lv],
      trim: () => '#2f63c9',
      bg: lv => [['#2a2f6e', '#7a5cff'], ['#20265e', '#6f4bd8'], ['#1b1f4a', '#5b3fc4'], ['#14183d', '#4d2fa8'], ['#100f30', '#b5487a']][lv],
      stars: true, sign: ['#0f1530', '#7fe3ff'], windows: false, logo: 'ABO SPACE',
    },
    games: {
      floor: lv => (c, w, h) => { c.fillStyle = ['#4a3d7a', '#433872', '#3d3168', '#372c60', '#30285a'][lv]; c.fillRect(0, 0, w, h); c.fillStyle = 'rgba(255,255,255,.06)'; for (let y = 0; y < h; y += 32) for (let x = (y / 32 % 2) * 16; x < w; x += 32) c.fillRect(x, y, 8, 8); },
      wall: lv => ['#3b3f73', '#34386b', '#2e3163', '#2a2c5c', '#262855'][lv],
      trim: () => '#ff3fa4',
      bg: lv => [['#ffb0e0', '#8a6bff'], ['#a6f0ff', '#7a5cff'], ['#ff9ad5', '#6c4bd8'], ['#7cf0c8', '#5b3fc4'], ['#ffe08a', '#ff4fa8']][lv],
      neon: ['#ff3fa4', '#3fe0ff'], sign: ['#1b1036', '#ff6fd0'], windows: false, logo: 'ABO GAMES',
    },
  };

  // ---------- Autofabrik ----------
  function buildAutos(world, lv) {
    const { scene, W, D } = world, spots = [];
    const belts = [0, 0, 1, 2, 2][lv], lifts = [1, 3, 0, 0, 0][lv];
    [[-W / 2 + .9, -D / 2 + .9, 'tires'], [W / 2 - .9, -D / 2 + .9, 'box'], [-W / 2 + .9, D / 2 - 1.4, 'barrel']].forEach(([x, z, t]) => {
      if (t === 'tires') for (let i = 0; i < 4; i++) { const tr = new THREE.Mesh(new THREE.TorusGeometry(.38, .17, 10, 20), mat('#22202a')); tr.rotation.x = Math.PI / 2; at(tr, x, .17 + i * .32, z); tr.castShadow = true; scene.add(tr); }
      else if (t === 'box') { const b = box(1.1, .8, .6, '#d8312b'); at(b, x, .4, z); scene.add(b); const b2 = box(1.1, .1, .62, '#9aa3ad', { metalness: .5 }); at(b2, x, .5, z); scene.add(b2); }
      else { [[0, 0], [.6, .2], [.2, .65]].forEach(([dx, dz], i) => { const br = cyl(.3, .3, .9, i % 2 ? '#2f63c9' : '#3fa35b'); at(br, x + dx, .45, z + dz); scene.add(br); }); }
    });
    const bench = (x, z) => { const b = box(1.1, .75, .7, '#b07a48'); at(b, x, .38, z + .7); const eng = box(.4, .3, .35, '#8a8f99', { metalness: .5 }); at(eng, x, .9, z + .7); return [b, eng]; };
    if (belts) {
      const zs = belts === 1 ? [-D * .12] : [-D * .24, D * .08];
      zs.forEach((z, bi) => {
        const len = W * .9;
        const beltTex = canvasTex(256, 64, (c, w, h) => { c.fillStyle = '#2b2630'; c.fillRect(0, 0, w, h); c.fillStyle = '#3d3744'; for (let x = 0; x < w; x += 32) c.fillRect(x, 0, 14, h); });
        beltTex.wrapS = THREE.RepeatWrapping; beltTex.repeat.set(len / 1.2, 1);
        const top = box(len, .12, 1.7, new THREE.MeshStandardMaterial({ map: beltTex, roughness: .7 })); at(top, 0, .9, z); scene.add(top);
        const frame = box(len, .25, 1.85, '#ffd23a', { roughness: .4 }); at(frame, 0, .74, z); scene.add(frame);
        for (let x = -len / 2 + .5; x < len / 2; x += 2.2) { [-1, 1].forEach(s => { const leg = box(.14, .7, .14, '#3b3442'); at(leg, x, .32, z + s * .8); scene.add(leg); }); }
        const belt = { tex: beltTex, z, len, cars: [] };
        const n = Math.ceil(len / 3.3) + 1;
        for (let i = 0; i < n; i++) { const c = car(CARS[(i + bi * 3) % CARS.length]); c.userData.i = i; scene.add(c); belt.cars.push(c); }
        const robots = [-len * .28, len * .22].map((x, k) => { const r = robot(k + bi * 2 + 1); at(r, x, 0, z + 1.5); r.rotation.y = Math.PI; scene.add(r); return r; });
        world.anim.push(lt => {
          beltTex.offset.x = -lt * .9;
          const gap = 3.3, span = (Math.ceil(len / gap) + 1) * gap;
          belt.cars.forEach(c => { const x = ((c.userData.i * gap + lt * 1.1) % span) - span / 2; c.position.set(x, .96, z); c.visible = Math.abs(x) < len / 2 - .2; setCarStage(c, (x + len / 2) / len); });
          robots.forEach(r => animRobot(r, lt));
        });
        for (let x = -len / 2 + 1; x < len / 2 - .5; x += 1.45) spots.push({ x, z: z - 1.4, prim: true });
      });
      const frontZ = belts === 1 ? D * .18 : D * .3;
      for (let row = 0; row < 2; row++) for (let x = -W / 2 + 1.6; x < W / 2 - 1; x += 1.7) spots.push({ x: x + row * .85, z: frontZ + row * 1.6, prop: bench });
    } else {
      const xs = lifts === 1 ? [0] : [-W * .3, 0, W * .3];
      const cars = xs.map((x, k) => {
        [-1, 1].forEach(s => { const post = box(.22, 2.2, .22, '#c9312b'); at(post, x + s * 1.35, 1.1, -D * .15 - .8); scene.add(post); });
        const plat = box(2.9, .12, 1.4, '#ffd23a'); at(plat, x, 1.3, -D * .15); scene.add(plat);
        const c = car(CARS[k % CARS.length]); at(c, x, 1.36, -D * .15); scene.add(c); return c;
      });
      world.anim.push(lt => cars.forEach((c, i) => { c.position.y = 1.36 + Math.sin(lt * .8 + i) * .05; setCarStage(c, .45 + ((lt * .1 + i * .33) % 1) * .6); }));
      xs.forEach(x => { [-1.6, -.5, .5, 1.6].forEach(dx => spots.push({ x: x + dx, z: -D * .15 + 1.6, prim: true })); });
      for (let x = -W / 2 + 1.2; x < W / 2 - .8; x += 1.5) spots.push({ x, z: D * .28, prop: bench });
    }
    world.look = { hat: 'helm', vest: true };
    return spots;
  }

  // ---------- Burgerladen: Küche hinten, Grills mit Burgern, Tische vorne ----------
  function buildBurger(world, lv) {
    const { scene, W, D } = world, spots = [];
    const kz = -D / 2 + 2.2, len = W * .8, kx = W * .06;
    const steel = { metalness: .6, roughness: .3 };
    const counter = box(len, .95, 1.1, '#c9ced6', steel); at(counter, kx, .475, kz); scene.add(counter);
    const front = box(len, .7, .04, '#d8312b'); at(front, kx, .5, kz + .56); scene.add(front);
    const nG = Math.max(1, Math.floor(len / 2.4));
    for (let g = 0; g < nG; g++) {
      const gx = kx - len / 2 + (g + .5) * len / nG;
      const plate = box(1.5, .06, .8, '#26222a', { roughness: .4, metalness: .4 }); at(plate, gx, .98, kz); scene.add(plate);
      const fire = new THREE.PointLight('#ff8a2e', 1.2, 3.5); at(fire, gx, 1.4, kz + .2); scene.add(fire);
      const patties = [-.45, 0, .45].map((dx, k) => { const p = cyl(.2, .2, .08, '#7a4126', 16, { roughness: .8 }); at(p, gx + dx, 1.05, kz); scene.add(p); return p; });
      world.anim.push(lt => { fire.intensity = 1 + Math.sin(lt * 23 + g) * .3 + Math.sin(lt * 37) * .2; patties.forEach((p, k) => { const ph = (lt * .6 + k * .37 + g * .2) % 1; p.position.y = 1.05 + (ph > .85 ? Math.sin((ph - .85) / .15 * Math.PI) * .45 : 0); p.rotation.x = ph > .85 ? (ph - .85) / .15 * Math.PI : 0; }); });
      puffs(world, 5, gx, 1.15, kz + .1, { spread: .45, rise: 1.3, speed: .45, size: .14, op: .35 });
      const hood = box(1.7, .45, .9, '#b8bfc8', steel); at(hood, gx, 3.7, kz - .25); scene.add(hood);
      const pipe = cyl(.18, .18, 1.5, '#b8bfc8', 12, steel); at(pipe, gx, 4.6, kz - .4); scene.add(pipe);
    }
    // Pommes-Station und Ausgabe ab Stufe 2: Insel mit Fritteusen
    let tz = kz + 2.6;
    if (lv >= 2) {
      const iz = kz + 2.6, il = len * .55;
      const isl = box(il, .95, 1.0, '#c9ced6', steel); at(isl, kx, .475, iz); scene.add(isl);
      for (let k = 0; k < Math.floor(il / 1.2); k++) {
        const fx = kx - il / 2 + .6 + k * 1.2;
        const oil = box(.8, .05, .6, '#e8b23a', { emissive: '#7a4a00', emissiveIntensity: .3, roughness: .2 }); at(oil, fx, .97, iz); scene.add(oil);
        const basket = box(.5, .25, .35, '#ffcf3f'); at(basket, fx, 1.1, iz); scene.add(basket);
        world.anim.push(lt => { basket.position.y = 1.1 + Math.max(0, Math.sin(lt * 1.3 + k * 2)) * .35; });
        puffs(world, 3, fx, 1.1, iz, { spread: .3, rise: 1.2, speed: .6, size: .15 });
      }
      for (let x = kx - il / 2 + .5; x < kx + il / 2; x += 1.25) spots.push({ x, z: iz - 1.05, prim: true });
      tz = iz + 2.2;
    }
    for (let x = kx - len / 2 + .6; x < kx + len / 2 - .2; x += 1.2) spots.push({ x, z: kz - 1.05, prim: true });
    // Kasse vorne rechts ab Stufe 1
    if (lv >= 1) {
      const cx = W / 2 - 1.4, cz = D / 2 - 1.3;
      const till = box(1.6, 1.0, .7, '#d8312b'); at(till, cx, .5, cz); scene.add(till);
      const reg = box(.45, .35, .35, '#26222a'); at(reg, cx, 1.18, cz); scene.add(reg);
      spots.push({ x: cx, z: cz - .9, kappe: true });
    }
    // Tische mit Burgern
    const R0 = R(7);
    for (let z = tz; z < D / 2 - .9; z += 2.3) for (let x = -W / 2 + 1.6; x < W / 2 - (lv >= 1 ? 3.2 : 1.2); x += 2.7) {
      const top = cyl(.6, .6, .08, '#ffffff'); at(top, x, .82, z); scene.add(top);
      const rim = cyl(.62, .62, .04, '#d8312b'); at(rim, x, .77, z); scene.add(rim);
      const leg = cyl(.08, .14, .78, '#3b3442'); at(leg, x, .39, z); scene.add(leg);
      [-1, 1].forEach(s => { const st = cyl(.25, .25, .1, '#d8312b'); at(st, x + s * .95, .55, z); scene.add(st); const sl = cyl(.05, .05, .5, '#9aa3ad'); at(sl, x + s * .95, .25, z); scene.add(sl); });
      const b = burger(.55); at(b, x - .15, .86, z); scene.add(b);
      const cup = cyl(.1, .08, .3, ['#2f63c9', '#ff7a1a', '#3fa35b'][Math.floor(R0() * 3)]); at(cup, x + .25, 1.0, z - .1); scene.add(cup);
      spots.push({ x: x + .55, z: z + .75, carry: true });
    }
    // Riesen-Burger auf dem Dach ab Stufe 3
    if (lv >= 3) { const big = burger(4.2); at(big, -W * .25, world.wallH + .1, -D / 2 + .2); scene.add(big); world.anim.push(lt => { big.rotation.y = lt * .6; }); }
    [[-W / 2 + .8, D / 2 - .8]].forEach(([x, z]) => scene.add(plant(x, z)));
    world.look = { hat: 'koch', shirt: '#ffffff', apron: '#d8312b', pants: '#2d2a33', tool: '#c9ced6' };
    return spots.map(s => s.carry ? { ...s, look: { hat: 'kappe', shirts: ['#d8312b', '#2f63c9', '#ff7a1a'], tray: true, tool: false, mode: 'carry', pants: '#2d2a33' } }
      : s.kappe ? { ...s, look: { hat: 'kappe', shirt: '#d8312b', hcol: '#ffcf3f', tool: false, mode: 'type' } } : s);
  }

  // ---------- Raketenbasis: Startrampe mit Rakete, Leitstand mit Bildschirmen ----------
  function rocket(H, r) {
    const g = new THREE.Group();
    const body = cyl(r, r, H * .62, '#f4f6fa', 28, { roughness: .35, metalness: .2 }); at(body, 0, H * .1 + H * .31, 0);
    const band = cyl(r * 1.01, r * 1.01, H * .06, '#d8312b', 28); at(band, 0, H * .62, 0);
    const band2 = cyl(r * 1.01, r * 1.01, H * .04, '#2f63c9', 28); at(band2, 0, H * .2, 0);
    const nose = cyl(0, r, H * .26, '#d8312b', 28, { roughness: .35 }); at(nose, 0, H * .72 + H * .13, 0);
    const bell = cyl(r * .45, r * .75, H * .1, '#3b3442', 20, { metalness: .6, roughness: .3 }); at(bell, 0, H * .05, 0);
    const win = sph(r * .32, '#7fe3ff', { emissive: '#3fa0ff', emissiveIntensity: .5, roughness: .1 }); at(win, 0, H * .52, r * .9);
    const logo = canvasTex(256, 64, (c, w, h) => { c.fillStyle = '#f4f6fa'; c.fillRect(0, 0, w, h); c.font = '800 44px Poppins'; c.textAlign = 'center'; c.textBaseline = 'middle'; c.fillStyle = '#1f2440'; c.fillText('ABO', w / 2, h / 2 + 2); });
    const lp = new THREE.Mesh(new THREE.PlaneGeometry(r * 1.3, r * .33), new THREE.MeshStandardMaterial({ map: logo })); at(lp, 0, H * .36, r * 1.01);
    g.add(body, band, band2, nose, bell, win, lp);
    for (let k = 0; k < 4; k++) { const fin = box(.08, H * .2, r * .9, '#d8312b'); const a = k * Math.PI / 2 + Math.PI / 4; at(fin, Math.sin(a) * r * 1.2, H * .14, Math.cos(a) * r * 1.2); fin.rotation.y = a; g.add(fin); }
    const fm = new THREE.MeshBasicMaterial({ color: '#ffb02e', transparent: true, opacity: .9 }), fm2 = new THREE.MeshBasicMaterial({ color: '#fff3b0' });
    const flame = new THREE.Mesh(new THREE.ConeGeometry(r * .62, H * .3, 18), fm); flame.rotation.x = Math.PI; at(flame, 0, -H * .14, 0);
    const core = new THREE.Mesh(new THREE.ConeGeometry(r * .35, H * .18, 14), fm2); core.rotation.x = Math.PI; at(core, 0, -H * .08, 0);
    g.add(flame, core);
    g.userData = { flame, core, H };
    return g;
  }
  function buildRakete(world, lv) {
    const { scene, W, D } = world, spots = [];
    const H = 4.2 + lv * 1.35, r = .55 + lv * .1, padR = r * 2.6 + .5;
    const px = W * .2, pz = -D * .12;
    const hazard = canvasTex(256, 256, (c, w, h) => { c.fillStyle = '#4b505c'; c.fillRect(0, 0, w, h); c.strokeStyle = '#ffd23a'; c.lineWidth = 22; c.beginPath(); c.arc(w / 2, h / 2, w * .44, 0, Math.PI * 2); c.stroke(); c.fillStyle = '#ffd23a'; c.font = '900 80px Poppins'; c.textAlign = 'center'; c.textBaseline = 'middle'; c.fillText('H', w / 2, h / 2 + 4); });
    const pad = cyl(padR, padR + .2, .3, '#4b505c', 32); at(pad, px, .15, pz); scene.add(pad);
    const padTop = new THREE.Mesh(new THREE.CircleGeometry(padR - .05, 32), new THREE.MeshStandardMaterial({ map: hazard, roughness: .8 })); padTop.rotation.x = -Math.PI / 2; at(padTop, px, .31, pz); padTop.receiveShadow = true; scene.add(padTop);
    const rk = rocket(H, r); at(rk, px, .3 + H * .14 + .1, pz); scene.add(rk);
    const legs = [0, 1, 2].map(k => { const a = k * 2.09 + .5; const l = box(.18, H * .2, .18, '#9aa3ad', { metalness: .5 }); at(l, px + Math.sin(a) * r * 1.3, .3 + H * .1, pz + Math.cos(a) * r * 1.3); scene.add(l); return l; });
    // Turm neben der Rakete
    const tx = px + r + 1.1, th = H * 1.05;
    [[-.4, -.4], [.4, -.4], [-.4, .4], [.4, .4]].forEach(([dx, dz]) => { const p = box(.12, th, .12, '#d8312b'); at(p, tx + dx, th / 2, pz - .2 + dz); scene.add(p); });
    for (let y = .8; y < th; y += .9) { const b = box(.92, .08, .92, '#d8312b'); at(b, tx, y, pz - .2); scene.add(b); }
    const armB = box(r + .9, .14, .3, '#9aa3ad', { metalness: .5 }); at(armB, tx - (r + .9) / 2, th * .72, pz); scene.add(armB);
    puffs(world, 10, px, .5, pz, { col: '#e9edf3', spread: padR * .7, rise: 1.2, speed: .35, size: .45, grow: 2.2, op: .6 });
    world.anim.push(lt => { const u = rk.userData, f = 1 + Math.sin(lt * 41) * .12 + Math.sin(lt * 23) * .08; u.flame.scale.set(1, f, 1); u.core.scale.set(1, 1 + Math.sin(lt * 53) * .15, 1); rk.position.x = px + Math.sin(lt * 60) * .015; });
    // Tanks und Satellitenschüssel
    if (lv >= 1) [0, 1].forEach(k => { const t = cyl(.6, .6, 2.4, '#f4f6fa', 20, { roughness: .35 }); at(t, W / 2 - 1, 1.2, -D / 2 + 1 + k * 1.4); scene.add(t); const b = cyl(.61, .61, .2, '#d8312b'); at(b, W / 2 - 1, 1.9, -D / 2 + 1 + k * 1.4); scene.add(b); });
    if (lv >= 2) { const dish = new THREE.Group(); const post = cyl(.1, .14, 1.6, '#9aa3ad'); at(post, 0, .8, 0); const bowl = new THREE.Mesh(new THREE.SphereGeometry(.9, 20, 10, 0, Math.PI * 2, 0, Math.PI / 3), mat('#f4f6fa', { side: THREE.DoubleSide })); bowl.rotation.x = Math.PI * .75; at(bowl, 0, 1.9, 0); bowl.castShadow = true; dish.add(post, bowl); at(dish, -W / 2 + 1.2, 0, -D / 2 + 1.2); scene.add(dish); world.anim.push(lt => { dish.rotation.y = Math.sin(lt * .4) * .7; }); }
    if (lv >= 3) { const r2 = rocket(H * .6, r * .7); at(r2, -W * .3, .3 + H * .6 * .14 + .1, -D / 2 + 1.6); scene.add(r2); const p2 = cyl(r * 1.6, r * 1.7, .3, '#4b505c', 24); at(p2, -W * .3, .15, -D / 2 + 1.6); scene.add(p2); world.anim.push(lt => { r2.userData.flame.scale.set(1, .9 + Math.sin(lt * 37) * .1, 1); }); }
    if (lv >= 4) { const mars = sph(1.4, '#d0603a', { roughness: .9 }, 32); at(mars, -W * .05, world.wallH + 2.2, -D / 2 - .5); scene.add(mars); world.anim.push(lt => { mars.rotation.y = lt * .3; }); }
    // Große Leinwand: Erde mit Flugbahn
    const sw = Math.min(6, W * .36), sh = sw * .55;
    const screen = liveScreen(world, sw, sh, 512, 280, (c, w, h, lt) => {
      c.fillStyle = '#071330'; c.fillRect(0, 0, w, h);
      c.fillStyle = 'rgba(255,255,255,.6)'; for (let i = 0; i < 40; i++) c.fillRect((i * 131) % w, (i * 71) % h, 2, 2);
      c.fillStyle = '#2f7de0'; c.beginPath(); c.arc(w * .3, h * .62, h * .3, 0, Math.PI * 2); c.fill();
      c.fillStyle = '#3fbf6a'; c.beginPath(); c.ellipse(w * .26, h * .55, h * .1, h * .07, .5, 0, Math.PI * 2); c.fill(); c.beginPath(); c.ellipse(w * .36, h * .72, h * .08, h * .06, -.3, 0, Math.PI * 2); c.fill();
      c.strokeStyle = '#7fe3ff'; c.setLineDash([10, 8]); c.lineWidth = 4; c.beginPath(); c.ellipse(w * .3, h * .62, h * .48, h * .2, -.25, 0, Math.PI * 2); c.stroke(); c.setLineDash([]);
      const a = lt * 1.2; const sx = w * .3 + Math.cos(a) * h * .48 * Math.cos(-.25) - Math.sin(a) * h * .2 * Math.sin(-.25), sy = h * .62 + Math.cos(a) * h * .48 * Math.sin(-.25) + Math.sin(a) * h * .2 * Math.cos(-.25);
      c.fillStyle = '#ffd23a'; c.beginPath(); c.arc(sx, sy, 8, 0, Math.PI * 2); c.fill();
      c.fillStyle = '#c94a2a'; c.beginPath(); c.arc(w * .85, h * .3, h * .1, 0, Math.PI * 2); c.fill();
      c.font = '700 30px Poppins'; c.fillStyle = '#7fe3ff'; c.fillText('T-' + String(Math.max(0, 10 - Math.floor(lt % 11))).padStart(2, '0'), w * .62, h * .78);
    });
    at(screen, -W * .22, world.wallH * .5, -D / 2 + .07); scene.add(screen);
    const frame = box(sw + .2, sh + .2, .1, '#26222a'); at(frame, -W * .22, world.wallH * .5, -D / 2); scene.add(frame);
    // Leitstand: Tische mit Bildschirmen (Blick zur Seite)
    const screens = [0, 1, 2, 3].map(k => glow(canvasTex(128, 80, (c, w, h) => {
      c.fillStyle = '#06142b'; c.fillRect(0, 0, w, h); c.strokeStyle = ['#3fe07a', '#7fe3ff', '#ffd23a', '#ff6fa8'][k]; c.lineWidth = 3; c.beginPath();
      for (let x = 0; x < w; x += 4) c.lineTo(x, h / 2 + Math.sin(x * .08 * (k + 1)) * h * .3); c.stroke();
      if (k % 2) { c.beginPath(); c.arc(w * .75, h * .5, h * .3, 0, Math.PI * 2); c.stroke(); }
    }), .9));
    const deskX0 = -W / 2 + 1.0, deskX1 = px - padR - .6;
    let dk = 0;
    for (let z = -D / 2 + 3 + (lv ? 0 : -.4); z < D / 2 - .7; z += 1.7) for (let x = deskX0; x < deskX1 - 1.2; x += 2.3) {
      const desk = box(.7, .75, 1.3, '#e9edf3'); at(desk, x, .375, z); scene.add(desk);
      const mon = box(.06, .55, .9, '#26222a'); at(mon, x - .1, 1.05, z); scene.add(mon);
      const sc = new THREE.Mesh(new THREE.PlaneGeometry(.82, .48), screens[dk % 4]); sc.rotation.y = Math.PI / 2; at(sc, x - .065, 1.05, z); scene.add(sc);
      const k0 = dk++; world.anim.push(lt => { sc.material = screens[(Math.floor(lt * .7 + k0 * .6)) % 4]; });
      spots.push({ x: x + .78, z, ry: -Math.PI / 2, look: { hat: 'kopfhoerer', hcol: '#3fe0ff', shirts: ['#2f63c9', '#1f2440', '#3b3f73'], tool: false, mode: 'type' } });
    }
    // Astronauten und Technik an der Rampe
    for (let k = 0; k < 9; k++) { const a = -1.4 + k * .42; const x = px + Math.sin(a) * (padR + .5), z = pz + Math.cos(a) * (padR + .5); if (x < W / 2 - .5 && z < D / 2 - .5 && x > deskX1 - .4) spots.push({ x, z, prim: true }); }
    for (let x = px - padR; x < W / 2 - .6; x += 1.3) spots.push({ x, z: D / 2 - .9, prim: true });
    world.look = { hat: 'astro', shirt: '#eef1f6', pants: '#d9dde4', backpack: true, tool: '#ffd23a' };
    return spots;
  }

  // ---------- Spielestudio: Schreibtische mit Bildschirmen, LED-Wand, Spielautomaten ----------
  function pixelGame(c, w, h, lt, hue = 0) { // eigenes kleines Jump-and-run, nur für die LED-Wand
    const g = c.createLinearGradient(0, 0, 0, h); g.addColorStop(0, ['#6fd0ff', '#ff9ad5', '#ffe08a'][hue]); g.addColorStop(1, '#ffffff'); c.fillStyle = g; c.fillRect(0, 0, w, h);
    const t = lt * 120, b = 32;
    c.fillStyle = 'rgba(255,255,255,.9)'; for (let i = 0; i < 4; i++) { const x = ((i * 190 - t * .3) % (w + 200) + w + 200) % (w + 200) - 100; c.fillRect(x, 30 + i % 2 * 30, 70, 20); c.fillRect(x + 15, 18 + i % 2 * 30, 40, 14); }
    for (let x = -((t) % b); x < w; x += b) { c.fillStyle = '#3fbf6a'; c.fillRect(x, h - 2 * b, b - 2, 8); c.fillStyle = '#b06a3a'; c.fillRect(x, h - 2 * b + 8, b - 2, 2 * b); }
    for (let i = 0; i < 6; i++) { const x = ((i * 140 - t) % (w + 140) + w + 140) % (w + 140) - 40; c.fillStyle = i % 3 ? '#ffd23a' : '#e0392f'; if (i % 3) { c.beginPath(); c.arc(x, h - 3.4 * b, 9, 0, Math.PI * 2); c.fill(); } else c.fillRect(x - 14, h - 3 * b, 28, b); }
    const jy = Math.abs(Math.sin(lt * 3.2)) * b * 2.2; const hx = w * .3, hy = h - 2 * b - 28 - jy;
    c.fillStyle = '#7a4bc4'; c.fillRect(hx - 14, hy, 28, 28); c.fillStyle = '#fff'; c.fillRect(hx + 2, hy + 6, 8, 8); c.fillStyle = '#1b1b22'; c.fillRect(hx + 6, hy + 8, 4, 4);
    c.fillStyle = '#1b1b22'; c.font = '700 22px Poppins'; c.fillText('★ ' + (1200 + Math.floor(lt * 50)), 14, 30);
  }
  function buildGames(world, lv) {
    const { scene, W, D } = world, spots = [];
    // LED-Wand mit eigenem Spiel
    const lw = Math.min(8, W * .42), lh = lw * .5;
    const led = liveScreen(world, lw, lh, 512, 256, (c, w, h, lt) => pixelGame(c, w, h, lt, lv % 3));
    at(led, -W * .12, world.wallH * .52, -D / 2 + .07); scene.add(led);
    const lf = box(lw + .25, lh + .25, .1, '#120c24'); at(lf, -W * .12, world.wallH * .52, -D / 2); scene.add(lf);
    const spot = new THREE.PointLight('#ff6fd0', 1.2, 8); at(spot, -W * .12, world.wallH * .5, -D / 2 + 1.5); scene.add(spot);
    // Spielautomaten an der Rückwand
    const nA = 1 + Math.floor(lv / 1.5), cols = ['#ff3fa4', '#3fe0ff', '#ffd23a', '#7cf08a'];
    for (let k = 0; k < nA; k++) {
      const ax = W / 2 - 1 - k * 1.2, az = -D / 2 + .7, col = cols[k % 4];
      const body = box(.95, 1.9, .8, '#1b1036'); at(body, ax, .95, az); scene.add(body);
      const side = box(.97, 1.92, .1, col, { emissive: col, emissiveIntensity: .35 }); at(side, ax, .95, az - .38); scene.add(side);
      const scr = liveScreen(world, .7, .55, 128, 100, (c, w, h, lt) => pixelGame(c, w, h, lt + k * 3, k % 3)); scr.rotation.x = -.25; at(scr, ax, 1.42, az + .42); scene.add(scr);
      const mq = box(.95, .28, .82, col, { emissive: col, emissiveIntensity: .9 }); at(mq, ax, 2.0, az); scene.add(mq);
      const panel = box(.95, .12, .4, '#2d2a50'); panel.rotation.x = .3; at(panel, ax, 1.05, az + .5); scene.add(panel);
      const stick = sph(.07, '#e0392f'); at(stick, ax - .2, 1.2, az + .55); scene.add(stick);
    }
    // Sitzsäcke, Pflanzen, Pokale
    [[-W / 2 + 1, D / 2 - 1, '#ff6fd0'], [-W / 2 + 2.1, D / 2 - .8, '#3fe0ff']].forEach(([x, z, c]) => { const bb = sph(.6, c, { roughness: .9 }); bb.scale.set(1, .6, 1); at(bb, x, .35, z); scene.add(bb); });
    scene.add(plant(W / 2 - .7, D / 2 - .7, .9));
    if (lv >= 3) { const shelf = box(.4, .1, 3.2, '#e9edf3'); at(shelf, -W / 2 + .25, 2.4, -D * .1); scene.add(shelf); for (let k = 0; k < 4; k++) scene.add(trophy(-W / 2 + .25, 2.45, -D * .1 - 1.2 + k * .8)); }
    // Schreibtische: Bildschirm zeigt zur Kamera, Leute sitzen seitlich davor
    const screens = [0, 1, 2, 3, 4, 5].map(k => glow(canvasTex(160, 96, (c, w, h) => {
      if (k === 0) { c.fillStyle = '#1b1d2e'; c.fillRect(0, 0, w, h); ['#ff6fd0', '#7fe3ff', '#ffd23a', '#7cf08a'].forEach((col, i) => { for (let j = 0; j < 4; j++) { c.fillStyle = col; c.fillRect(8 + (i + j) % 3 * 10, 8 + (i * 4 + j) * 5.4, 30 + ((i * 7 + j * 13) % 60), 3); } }); }
      else if (k === 1 || k === 4) pixelGame(c, w, h, k, k % 3);
      else if (k === 2) { c.fillStyle = '#2a2f6e'; c.fillRect(0, 0, w, h); c.fillStyle = '#ffd23a'; c.beginPath(); c.arc(w / 2, h / 2, 26, 0, Math.PI * 2); c.fill(); c.fillStyle = '#1b1b22'; c.fillRect(w / 2 - 12, h / 2 - 8, 6, 8); c.fillRect(w / 2 + 6, h / 2 - 8, 6, 8); }
      else { c.fillStyle = '#0f3a2a'; c.fillRect(0, 0, w, h); for (let i = 0; i < 8; i++) for (let j = 0; j < 5; j++) { c.fillStyle = (i + j) % 3 ? '#3fbf6a' : '#2f7de0'; c.fillRect(i * 20, j * 20, 18, 18); } }
    }), .95));
    let dk = 0;
    for (let z = -D / 2 + 2.6; z < D / 2 - .8; z += 1.7) for (let x = -W / 2 + 1.4; x < W / 2 - 1.6; x += 2.4) {
      if (z > D / 2 - 2 && x < -W / 2 + 3) continue; // Ecke mit Sitzsäcken
      const desk = box(.75, .75, 1.3, '#f4f1ea'); at(desk, x, .375, z); scene.add(desk);
      const mon = box(.06, .6, 1.0, '#1b1b22'); at(mon, x - .12, 1.1, z); scene.add(mon);
      const sc = new THREE.Mesh(new THREE.PlaneGeometry(.92, .52), screens[dk % 6]); sc.rotation.y = Math.PI / 2; at(sc, x - .085, 1.1, z); scene.add(sc);
      const kb = box(.25, .04, .6, '#3b3442', { emissive: '#ff3fa4', emissiveIntensity: .25 }); at(kb, x + .18, .77, z); scene.add(kb);
      const k0 = dk++; world.anim.push(lt => { sc.material = screens[(Math.floor(lt * .6 + k0 * .7)) % 6]; });
      spots.push({ x: x + .78, z, ry: -Math.PI / 2, prim: true, prop: (sx, sz) => { const ch = box(.55, .1, .55, '#e0392f'); at(ch, sx + .55, .55, sz); const bk = box(.1, .8, .55, '#1b1b22'); at(bk, sx + .85, .95, sz); return [ch, bk]; } });
    }
    world.look = { hat: 'kopfhoerer', shirts: ['#7a4bc4', '#1fb5b5', '#ff7a1a', '#3fa35b', '#2f63c9', '#e0392f'], tool: false, mode: 'type', pants: '#2b2f4a' };
    return spots;
  }
  const BUILDERS = { autos: buildAutos, burger: buildBurger, rakete: buildRakete, games: buildGames };

  // ---------- Welt bauen ----------
  function build(sc, drawn, newFrom) {
    const thema = BUILDERS[sc.thema] ? sc.thema : 'autos';
    const T = THEMES[thema];
    let lv = Number.isFinite(+sc.level) && sc.level !== null && sc.level !== undefined ? Math.max(0, Math.min(4, Math.round(+sc.level))) : AUTO_KEYS.indexOf(sc.stufe);
    if (lv < 0) lv = 2;
    const [W, D] = SIZES[lv], bg = T.bg(lv);
    const scene = new THREE.Scene();
    scene.background = canvasTex(256, 512, (c, w, h) => {
      const g = c.createLinearGradient(0, 0, 0, h); g.addColorStop(0, bg[0]); g.addColorStop(1, bg[1]); c.fillStyle = g; c.fillRect(0, 0, w, h);
      if (T.stars) { const r = R(3); for (let i = 0; i < 120; i++) { c.fillStyle = `rgba(255,255,255,${.3 + r() * .7})`; const s = r() < .1 ? 3 : 1.5; c.fillRect(r() * w, r() * h * .8, s, s); } }
    });
    scene.add(new THREE.HemisphereLight('#ffffff', '#6a7080', thema === 'games' ? .7 : .55));
    const sun = new THREE.DirectionalLight('#fff1dc', thema === 'games' ? 1.3 : 1.6); sun.position.set(W * .55, W * 1.1, W * .75); sun.castShadow = true;
    sun.shadow.mapSize.set(2048, 2048); const sc2 = sun.shadow.camera; sc2.left = -W; sc2.right = W; sc2.top = W; sc2.bottom = -W; sc2.near = 1; sc2.far = W * 4; sun.shadow.bias = -.0005; sun.shadow.radius = 4;
    scene.add(sun);
    // Diorama: Boden als dicker Block, zwei Wände hinten
    const floorTex = canvasTex(512, 512, T.floor(lv));
    floorTex.wrapS = floorTex.wrapT = THREE.RepeatWrapping; floorTex.repeat.set(W / 4, D / 4);
    const floor = box(W, .6, D, new THREE.MeshStandardMaterial({ map: floorTex, roughness: .8 })); at(floor, 0, -.3, 0); floor.castShadow = false; scene.add(floor);
    const rim = box(W + .02, .6, D + .02, '#4a4f5c'); at(rim, 0, -.92, 0); scene.add(rim);
    const wallH = lv === 4 ? 6 : 5;
    const back = box(W, wallH, .3, T.wall(lv)); at(back, 0, wallH / 2, -D / 2 - .15); scene.add(back);
    const side = box(.3, wallH, D, T.wall(lv)); at(side, -W / 2 - .15, wallH / 2, 0); scene.add(side);
    const trim = box(W, .5, .32, T.trim(lv)); at(trim, 0, .25, -D / 2 - .14); scene.add(trim);
    const trim2 = box(.32, .5, D, T.trim(lv)); at(trim2, -W / 2 - .14, .25, 0); scene.add(trim2);
    // Firmenschild an der Rückwand
    const logo = canvasTex(1024, 256, (c, w, h) => { c.fillStyle = T.sign[0]; c.beginPath(); c.roundRect(8, 8, w - 16, h - 16, 60); c.fill(); c.font = '700 130px Poppins'; c.textAlign = 'center'; c.textBaseline = 'middle'; c.fillStyle = T.sign[1]; c.fillText((sc.name || T.logo).toUpperCase(), w / 2, h / 2 + 6, w - 80); });
    const sw = Math.min(7, W * .5);
    const signM = new THREE.Mesh(new THREE.PlaneGeometry(sw, sw / 4), new THREE.MeshStandardMaterial({ map: logo, emissive: '#ffffff', emissiveMap: logo, emissiveIntensity: .35 }));
    if (thema === 'autos') at(signM, W * .08, wallH * .72, -D / 2 + .02);
    else { signM.rotation.y = Math.PI / 2; at(signM, -W / 2 + .03, wallH * .72, -D * .06); } // sonst verdeckt die Küche/Rakete das Schild
    scene.add(signM);
    if (T.windows) for (let k = 0; k < Math.floor(D / 3.2); k++) { const win = box(.08, 1.6, 2, '#bfe6ff', { emissive: '#bfe6ff', emissiveIntensity: .25, roughness: .1 }); at(win, -W / 2 + .02, wallH * .6, -D / 2 + 2 + k * 3.2); scene.add(win); }
    if (T.neon) T.neon.forEach((col, k) => { const n1 = box(W, .08, .1, col, { emissive: col, emissiveIntensity: 1.6 }); at(n1, 0, wallH - .3 - k * .25, -D / 2 + .05); const n2 = box(.1, .08, D, col, { emissive: col, emissiveIntensity: 1.6 }); at(n2, -W / 2 + .05, wallH - .3 - k * .25, 0); scene.add(n1, n2); });
    if (lv === 4 && !T.neon) { const led = box(W, .08, .1, '#4fd6ff', { emissive: '#4fd6ff', emissiveIntensity: 1.5 }); at(led, 0, wallH - .3, -D / 2 + .05); scene.add(led); }

    const world = { scene, workers: [], coins: [], anim: [], W, D, wallH, bg, lv };
    const spots = BUILDERS[thema](world, lv);
    // Plätze nach Wichtigkeit: erst die Hauptarbeit (prim), dann der Rest; gleichmäßig verteilt.
    // Reichen die Plätze nicht, stellen sich die übrigen vorne in eine Reihe.
    const prim = spots.filter(s => s.prim), sec = spots.filter(s => !s.prim);
    for (let row = 0; prim.length + sec.length < drawn && row < 2; row++) for (let x = -W / 2 + 1; x < W / 2 - .6; x += 1.15) sec.push({ x: x + row * .55, z: D / 2 - .55 - row * 1.0 });
    const n = Math.min(drawn, prim.length + sec.length);
    const nPrim = Math.min(prim.length, Math.max(n - sec.length, Math.round(n * .6)));
    const pick = [];
    for (let i = 0; i < nPrim; i++) pick.push(prim[Math.floor(i * prim.length / nPrim)]);
    for (let i = 0; i < n - nPrim; i++) pick.push(sec[Math.floor(i * sec.length / (n - nPrim))]);
    world.drawn = pick.length; world.newFrom = Math.max(0, pick.length - (drawn - newFrom));
    pick.forEach((s, i) => {
      const w = worker(i + 3, { ...world.look, ...(s.look || {}) }); at(w, s.x, 0, s.z); w.rotation.y = s.ry || 0; scene.add(w);
      if (s.prop) s.prop(s.x, s.z).forEach(m => scene.add(m));
      world.workers.push({ obj: w, i, born: i >= world.newFrom ? 1 : 0, x: s.x, z: s.z });
    });
    for (let k = 0; k < 10; k++) { const c = cyl(.2, .2, .06, '#ffcf3f', 20, { metalness: .8, roughness: .25, emissive: '#7a5a00', emissiveIntensity: .4 }); c.rotation.x = Math.PI / 2; c.visible = false; scene.add(c); world.coins.push(c); }
    if (sc.chef) { const ch = worker(1, { hat: 'zylinder', shirt: '#1b1b22', tool: false }); ch.scale.setScalar(1.25); at(ch, W * .28, 0, D * .42); ch.rotation.y = -.5; scene.add(ch); world.chef = ch; }
    world.camera = new THREE.PerspectiveCamera(30, RW / RH, .5, 400);
    return world;
  }

  const cache = {};
  const v = new THREE.Vector3();
  function project(world, x, y, z) { v.set(x, y, z).project(world.camera); return [(v.x + 1) / 2 * RW, TOP + (1 - v.y) / 2 * RH, v.z]; }

  // Gibt zurück, wie viele Leute wirklich im Bild stehen (der Rest kommt als "+N weitere")
  function draw(ctx, sc, lt, d, opts) {
    const { drawn, newFrom, step, names } = opts;
    const key = [sc.thema, sc.level, sc.stufe, drawn, newFrom, sc.chef ? 1 : 0, sc.name].join('|');
    const world = cache[key] || (cache[key] = build(sc, drawn, newFrom));
    const { W, D, camera } = world, nf = world.newFrom, dr = world.drawn;
    // Kamera: schräg von oben, fährt langsam heran und schwenkt leicht
    const dist = Math.max(W * 1.62 + 5, 19) - lt * W * .02, ang = .78 + Math.sin(lt * .25 + (sc.i || 0)) * .08;
    camera.position.set(Math.sin(ang) * dist, dist * .78, Math.cos(ang) * dist);
    camera.lookAt(0, -1.2, D * .12);
    world.anim.forEach(f => f(lt));
    // Leute: neue fallen nacheinander von oben herein
    world.workers.forEach(wk => {
      const born = wk.born ? .3 + (wk.i - nf) * step : null;
      animWorker(wk.obj, lt, null);
      if (born == null) { wk.obj.position.y = 0; wk.obj.visible = true; return; }
      const k = clamp((lt - born) / .45); wk.obj.visible = lt >= born;
      wk.obj.position.y = k < 1 ? (1 - easeOut(k)) * 9 : Math.max(0, Math.sin(clamp((lt - born - .45) / .2) * Math.PI) * .3);
      if (lt < born + 1.2 && lt >= born + .4) animWorker(wk.obj, lt, 'cheer');
    });
    if (world.chef) animWorker(world.chef, lt, 'wave');
    // Münzen steigen auf
    world.coins.forEach((c, k) => {
      if (!sc.pro_tag || !world.workers.length) { c.visible = false; return; }
      const wk = world.workers[(k * 7) % world.workers.length]; const ph = (lt * .7 + k * .37) % 1.6;
      c.visible = ph < 1 && wk.obj.visible; c.position.set(wk.x + .3, 2.4 + ph * 2.2, wk.z); c.rotation.z = lt * 6 + k;
    });
    renderer.render(world.scene, camera);
    ctx.save(); base(ctx); ctx.fillStyle = world.bg[0]; ctx.fillRect(0, 0, RW, TOP + 2); ctx.drawImage(renderer.domElement, 0, TOP); ctx.restore();
    // Namen und "NEU" über den Köpfen (2D, damit sie scharf bleiben)
    base(ctx);
    const tags = world.workers.map(wk => { const [x, y, z] = project(world, wk.x, wk.obj.position.y + 2.55, wk.z); return { wk, x, y, z }; }).sort((a, b) => b.z - a.z);
    tags.forEach(({ wk, x, y }) => {
      if (!wk.obj.visible) return;
      const nm = names[dr - 1 - wk.i];
      if (nm) nameTag(ctx, nm.slice(0, 12), x, y, 24);
      const born = wk.born ? .3 + (wk.i - nf) * step : null;
      if (born != null && lt > born + .25 && lt < born + 2.4) { const kb = popIn(lt, born + .25, .3); ctx.save(); ctx.translate(x, y - (nm ? 40 : 0)); ctx.scale(kb, kb); sign(ctx, 'NEU', 0, 0, 28, '#7cf08a'); ctx.restore(); }
    });
    if (world.chef) { const [x, y] = project(world, world.chef.position.x, 3.3, world.chef.position.z); nameTag(ctx, 'Chef', x, y, 34); }
    return dr;
  }
  return { draw, ok: true };
})();
window.F3 = F3;
