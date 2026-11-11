// ---------- Firmen-Spiel in 3D: Autofabrik als Diorama (three.js, MIT, siehe vendor/LICENSE-three.txt) ----------
// Zeichnet die Szene "firma" als 3D-Bild in eine eigene WebGL-Leinwand; firma.js legt es ins Video und malt
// Namen, Kontostand und Schilder darüber. Ohne WebGL bleibt F3 = null und firma.js zeichnet die 2D-Fabrik.
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

  const SHIRTS = ['#2f63c9', '#e0392f', '#3fa35b', '#7a4bc4', '#f2b52a', '#1fb5b5', '#ff7a1a', '#2a3f8f'];
  const SKINS = ['#f6d7b8', '#e9b98f', '#c98d63', '#8d5a3b', '#f2c9a0'];
  const CARS = ['#e0392f', '#2f63c9', '#f2b52a', '#3fa35b', '#7a4bc4', '#ff7a1a', '#1fb5b5', '#f4f4f4'];
  const LEVELS = {
    garage: { W: 8, D: 6.5, floor: '#8c8f96', wall: '#b7bcc4', bg: ['#ffd6a5', '#ff9e7a'], belts: 0, lifts: 1 },
    werkstatt: { W: 11, D: 8, floor: '#7d8592', wall: '#e3e9f1', bg: ['#a5d8ff', '#6d8dff'], belts: 0, lifts: 3 },
    fabrik: { W: 15, D: 10, floor: '#8a909b', wall: '#d9dee6', bg: ['#b8f0c8', '#3fbfa0'], belts: 1, lifts: 0 },
    grossfabrik: { W: 19, D: 13, floor: '#838a96', wall: '#e6e9ef', bg: ['#c9b8ff', '#6c5bd8'], belts: 2, lifts: 0 },
    konzern: { W: 22, D: 15, floor: '#dfe6ef', wall: '#f7f9fc', bg: ['#ffe9a8', '#ff7aa8'], belts: 2, lifts: 0, fancy: true },
  };

  // ---------- Figuren ----------
  function worker(seed, o = {}) {
    const g = new THREE.Group();
    const shirt = o.shirt || SHIRTS[seed % SHIRTS.length], skin = SKINS[(seed * 7) % SKINS.length];
    const legL = box(.2, .72, .22, '#2b3550'), legR = box(.2, .72, .22, '#2b3550');
    at(legL, -.13, .36, 0); at(legR, .13, .36, 0); g.add(legL, legR);
    const body = new THREE.Mesh(new THREE.CapsuleGeometry(.3, .42, 6, 16), mat(shirt)); body.castShadow = true; at(body, 0, 1.12, 0); g.add(body);
    const strap = box(.62, .08, .05, '#ffd23a', { emissive: '#3a2a00' }); at(strap, 0, 1.2, .29); g.add(strap); // Warnweste-Streifen
    const head = sph(.29, skin); at(head, 0, 1.74, 0); g.add(head);
    [-1, 1].forEach(s => { const e = sph(.045, '#1b1b22', {}, 10); at(e, s * .1, 1.78, .26); g.add(e); });
    const smile = new THREE.Mesh(new THREE.TorusGeometry(.07, .015, 6, 12, Math.PI), mat('#1b1b22')); smile.rotation.z = Math.PI; at(smile, 0, 1.68, .27); g.add(smile);
    if (o.hat === 'zylinder') { const h = cyl(.24, .24, .42, '#1b1b22'); at(h, 0, 2.12, 0); const b = cyl(.38, .38, .04, '#1b1b22'); at(b, 0, 1.92, 0); const band = cyl(.245, .245, .08, '#c0392b'); at(band, 0, 1.98, 0); g.add(h, b, band); }
    else { const helm = new THREE.Mesh(new THREE.SphereGeometry(.31, 20, 12, 0, Math.PI * 2, 0, Math.PI / 2), mat('#ffd23a', { roughness: .35 })); helm.castShadow = true; at(helm, 0, 1.8, 0); const brim = cyl(.36, .36, .03, '#f2b52a'); at(brim, 0, 1.8, .03); g.add(helm, brim); }
    const arm = s => { const p = new THREE.Group(); at(p, s * .38, 1.38, 0); const a = box(.13, .6, .13, shirt); at(a, 0, -.27, 0); const hand = sph(.08, skin, {}, 10); at(hand, 0, -.6, 0); p.add(a, hand); g.add(p); return p; };
    g.userData.armL = arm(-1); g.userData.armR = arm(1);
    const tool = box(.06, .06, .34, '#9aa3ad', { metalness: .6, roughness: .3 }); at(tool, 0, -.62, .14); g.userData.armR.add(tool);
    g.userData.seed = seed;
    return g;
  }
  function animWorker(w, lt, mode) {
    const s = w.userData.seed;
    if (mode === 'wave') { w.userData.armR.rotation.x = Math.PI; w.userData.armR.rotation.z = .4 + Math.sin(lt * 8) * .35; w.userData.armL.rotation.x = 0; return; }
    if (mode === 'cheer') { w.userData.armL.rotation.z = -2.6; w.userData.armR.rotation.z = 2.6; w.position.y = Math.abs(Math.sin(lt * 6 + s)) * .25; return; }
    const k = Math.sin(lt * (7 + s % 3) + s);
    w.userData.armR.rotation.x = -1.1 - k * .5; w.userData.armL.rotation.x = -.6 + Math.sin(lt * 3 + s) * .1;
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
    const j1 = sph(.25, '#ffd23a'); turn.add(j1);
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

  // ---------- Welt bauen ----------
  function build(sc, drawn, newFrom) {
    const L = LEVELS[sc.stufe] || LEVELS.fabrik, W = L.W, D = L.D;
    const scene = new THREE.Scene();
    scene.background = canvasTex(8, 512, (c, w, h) => { const g = c.createLinearGradient(0, 0, 0, h); g.addColorStop(0, L.bg[0]); g.addColorStop(1, L.bg[1]); c.fillStyle = g; c.fillRect(0, 0, w, h); });
    scene.add(new THREE.HemisphereLight('#ffffff', '#6a7080', .55));
    const sun = new THREE.DirectionalLight('#fff1dc', 1.6); sun.position.set(W * .55, W * 1.1, W * .75); sun.castShadow = true;
    sun.shadow.mapSize.set(2048, 2048); const sc2 = sun.shadow.camera; sc2.left = -W; sc2.right = W; sc2.top = W; sc2.bottom = -W; sc2.near = 1; sc2.far = W * 4; sun.shadow.bias = -.0005; sun.shadow.radius = 4;
    scene.add(sun);
    // Diorama: Boden als dicker Block, zwei Wände hinten
    const floorTex = canvasTex(512, 512, (c, w, h) => { c.fillStyle = L.floor; c.fillRect(0, 0, w, h); c.strokeStyle = 'rgba(0,0,0,.12)'; c.lineWidth = 3; for (let i = 0; i <= 8; i++) { c.beginPath(); c.moveTo(i * w / 8, 0); c.lineTo(i * w / 8, h); c.stroke(); c.beginPath(); c.moveTo(0, i * h / 8); c.lineTo(w, i * h / 8); c.stroke(); } });
    floorTex.wrapS = floorTex.wrapT = THREE.RepeatWrapping; floorTex.repeat.set(W / 4, D / 4);
    const floor = box(W, .6, D, new THREE.MeshStandardMaterial({ map: floorTex, roughness: .8 })); at(floor, 0, -.3, 0); floor.castShadow = false; scene.add(floor);
    const rim = box(W + .02, .6, D + .02, '#4a4f5c'); at(rim, 0, -.92, 0); scene.add(rim);
    const wallH = L.fancy ? 6 : 5;
    const back = box(W, wallH, .3, L.wall); at(back, 0, wallH / 2, -D / 2 - .15); scene.add(back);
    const side = box(.3, wallH, D, L.wall); at(side, -W / 2 - .15, wallH / 2, 0); scene.add(side);
    const trim = box(W, .5, .32, sc.stufe === 'garage' ? '#6d7480' : '#c9312b'); at(trim, 0, .25, -D / 2 - .14); scene.add(trim);
    const trim2 = box(.32, .5, D, sc.stufe === 'garage' ? '#6d7480' : '#c9312b'); at(trim2, -W / 2 - .14, .25, 0); scene.add(trim2);
    // Firmenschild an der Rückwand
    const logo = canvasTex(1024, 256, (c, w, h) => { c.fillStyle = '#1f2440'; c.beginPath(); c.roundRect(8, 8, w - 16, h - 16, 60); c.fill(); c.font = '700 130px Poppins'; c.textAlign = 'center'; c.textBaseline = 'middle'; c.fillStyle = '#ffe14d'; c.fillText((sc.name || 'ABO MOTORS').toUpperCase(), w / 2, h / 2 + 6); });
    const sign = new THREE.Mesh(new THREE.PlaneGeometry(Math.min(7, W * .5), Math.min(7, W * .5) / 4), new THREE.MeshStandardMaterial({ map: logo, emissive: '#ffffff', emissiveMap: logo, emissiveIntensity: .35 })); at(sign, W * .08, wallH * .72, -D / 2 + .02); scene.add(sign);
    // Fenster an der Seitenwand
    for (let k = 0; k < Math.floor(D / 3.2); k++) { const win = box(.08, 1.6, 2, '#bfe6ff', { emissive: '#bfe6ff', emissiveIntensity: .25, roughness: .1 }); at(win, -W / 2 + .02, wallH * .6, -D / 2 + 2 + k * 3.2); scene.add(win); }
    if (L.fancy) { const led = box(W, .08, .1, '#4fd6ff', { emissive: '#4fd6ff', emissiveIntensity: 1.5 }); at(led, 0, wallH - .3, -D / 2 + .05); scene.add(led); }

    const world = { scene, workers: [], cars: [], robots: [], belts: [], coins: [], L, W, D };
    // Deko: Reifenstapel, Werkzeugkisten, Fässer
    const props = [[-W / 2 + .9, -D / 2 + .9, 'tires'], [W / 2 - .9, -D / 2 + .9, 'box'], [-W / 2 + .9, D / 2 - 1.4, 'barrel']];
    props.forEach(([x, z, t]) => {
      if (t === 'tires') for (let i = 0; i < 4; i++) { const tr = new THREE.Mesh(new THREE.TorusGeometry(.38, .17, 10, 20), mat('#22202a')); tr.rotation.x = Math.PI / 2; at(tr, x, .17 + i * .32, z); tr.castShadow = true; scene.add(tr); }
      else if (t === 'box') { const b = box(1.1, .8, .6, '#d8312b'); at(b, x, .4, z); scene.add(b); const b2 = box(1.1, .1, .62, '#9aa3ad', { metalness: .5 }); at(b2, x, .5, z); scene.add(b2); }
      else { [[0, 0], [.6, .2], [.2, .65]].forEach(([dx, dz], i) => { const br = cyl(.3, .3, .9, i % 2 ? '#2f63c9' : '#3fa35b'); at(br, x + dx, .45, z + dz); scene.add(br); }); }
    });

    // Arbeitsplätze
    const spots = [];
    if (L.belts) {
      const zs = L.belts === 1 ? [-D * .12] : [-D * .24, D * .08];
      zs.forEach((z, bi) => {
        const len = W * .9;
        const beltTex = canvasTex(256, 64, (c, w, h) => { c.fillStyle = '#2b2630'; c.fillRect(0, 0, w, h); c.fillStyle = '#3d3744'; for (let x = 0; x < w; x += 32) c.fillRect(x, 0, 14, h); });
        beltTex.wrapS = THREE.RepeatWrapping; beltTex.repeat.set(len / 1.2, 1);
        const top = box(len, .12, 1.7, new THREE.MeshStandardMaterial({ map: beltTex, roughness: .7 })); at(top, 0, .9, z); scene.add(top);
        const frame = box(len, .25, 1.85, '#ffd23a', { roughness: .4 }); at(frame, 0, .74, z); scene.add(frame);
        for (let x = -len / 2 + .5; x < len / 2; x += 2.2) { [-1, 1].forEach(s => { const leg = box(.14, .7, .14, '#3b3442'); at(leg, x, .32, z + s * .8); scene.add(leg); }); }
        world.belts.push({ tex: beltTex, z, len });
        const n = Math.ceil(len / 3.3) + 1;
        for (let i = 0; i < n; i++) { const c = car(CARS[(i + bi * 3) % CARS.length]); c.userData.i = i; c.userData.belt = bi; scene.add(c); world.cars.push(c); }
        [-len * .28, len * .22].forEach((x, k) => { const r = robot(k + bi * 2 + 1); at(r, x, 0, z + 1.5); r.rotation.y = Math.PI; scene.add(r); world.robots.push(r); });
        for (let x = -len / 2 + 1; x < len / 2 - .5; x += 1.45) spots.push({ x, z: z - 1.4, ry: 0, kind: 'belt' });
      });
      const frontZ = L.belts === 1 ? D * .18 : D * .3;
      for (let row = 0; row < 2; row++) for (let x = -W / 2 + 1.6; x < W / 2 - 1; x += 1.7) spots.push({ x: x + row * .85, z: frontZ + row * 1.6, ry: 0, kind: 'bench' });
    } else {
      const xs = L.lifts === 1 ? [0] : [-W * .3, 0, W * .3];
      xs.forEach((x, k) => {
        [-1, 1].forEach(s => { const post = box(.22, 2.2, .22, '#c9312b'); at(post, x + s * 1.35, 1.1, -D * .15 - .8); scene.add(post); });
        const plat = box(2.9, .12, 1.4, '#ffd23a'); at(plat, x, 1.3, -D * .15); scene.add(plat);
        const c = car(CARS[k % CARS.length]); at(c, x, 1.36, -D * .15); c.userData.lift = true; c.userData.i = k; scene.add(c); world.cars.push(c);
      });
      xs.forEach(x => { [-1.6, -.5, .5, 1.6].forEach(dx => spots.push({ x: x + dx, z: -D * .15 + 1.6, ry: 0, kind: 'lift' })); });
      for (let x = -W / 2 + 1.2; x < W / 2 - .8; x += 1.5) spots.push({ x, z: D * .28, ry: 0, kind: 'bench' });
    }
    // Spots nach Wichtigkeit: erst am Band/Lift, dann vorne; gleichmäßig auswählen
    const pick = [];
    const prim = spots.filter(s => s.kind !== 'bench'), sec = spots.filter(s => s.kind === 'bench');
    const nPrim = Math.min(prim.length, Math.max(1, Math.round(drawn * .6)));
    for (let i = 0; i < nPrim; i++) pick.push(prim[Math.floor(i * prim.length / nPrim)]);
    for (let i = 0; i < drawn - nPrim && i < sec.length; i++) pick.push(sec[Math.floor(i * sec.length / Math.max(1, Math.min(sec.length, drawn - nPrim)))]);
    while (pick.length < drawn && prim.length > pick.length - sec.length) pick.push(prim[pick.length % prim.length]);
    pick.slice(0, drawn).forEach((s, i) => {
      const w = worker(i + 3); at(w, s.x, 0, s.z); w.rotation.y = s.ry; scene.add(w);
      if (s.kind === 'bench') { const b = box(1.1, .75, .7, '#b07a48'); at(b, s.x, .38, s.z + .7); scene.add(b); const eng = box(.4, .3, .35, '#8a8f99', { metalness: .5 }); at(eng, s.x, .9, s.z + .7); scene.add(eng); }
      world.workers.push({ obj: w, i, born: i >= newFrom ? 1 : 0, x: s.x, z: s.z });
    });
    for (let k = 0; k < 10; k++) { const c = cyl(.2, .2, .06, '#ffcf3f', 20, { metalness: .8, roughness: .25, emissive: '#7a5a00', emissiveIntensity: .4 }); c.rotation.x = Math.PI / 2; c.visible = false; scene.add(c); world.coins.push(c); }
    if (sc.chef) { const ch = worker(1, { hat: 'zylinder', shirt: '#1b1b22' }); ch.scale.setScalar(1.25); at(ch, W * .28, 0, D * .42); ch.rotation.y = -.5; scene.add(ch); world.chef = ch; }
    const camera = new THREE.PerspectiveCamera(30, RW / RH, .5, 400);
    world.camera = camera;
    return world;
  }

  const cache = {};
  const v = new THREE.Vector3();
  function project(world, x, y, z) { v.set(x, y, z).project(world.camera); return [(v.x + 1) / 2 * RW, TOP + (1 - v.y) / 2 * RH, v.z]; }

  function draw(ctx, sc, lt, d, opts) {
    const { drawn, newFrom, step, names } = opts;
    const key = [sc.stufe, drawn, newFrom, sc.chef ? 1 : 0, sc.name].join('|');
    const world = cache[key] || (cache[key] = build(sc, drawn, newFrom));
    const { W, D, camera } = world;
    // Kamera: schräg von oben, fährt langsam heran und schwenkt leicht
    const dist = Math.max(W * 1.62 + 5, 19) - lt * W * .02, ang = .78 + Math.sin(lt * .25 + (sc.i || 0)) * .08;
    camera.position.set(Math.sin(ang) * dist, dist * .78, Math.cos(ang) * dist);
    camera.lookAt(0, -1.2, D * .12);
    // Band, Autos, Roboter
    world.belts.forEach(b => { b.tex.offset.x = -lt * .9; });
    const gap = 3.3;
    world.cars.forEach(c => {
      const u = c.userData;
      if (u.lift) { c.position.y = 1.36 + Math.sin(lt * .8 + u.i) * .05; setCarStage(c, (.45 + ((lt * .1 + u.i * .33) % 1) * .6)); return; }
      const b = world.belts[u.belt]; const span = (Math.ceil(b.len / gap) + 1) * gap;
      const x = ((u.i * gap + lt * 1.1) % span) - span / 2;
      c.position.set(x, .96, b.z); c.visible = Math.abs(x) < b.len / 2 - .2;
      setCarStage(c, (x + b.len / 2) / b.len);
      c.children.forEach(m => { if (m.geometry && m.geometry.type === 'CylinderGeometry' && m.rotation.x) m.rotation.y = lt * 3; });
    });
    world.robots.forEach(r => animRobot(r, lt));
    // Arbeiter: neue fallen nacheinander von oben herein
    world.workers.forEach(wk => {
      const born = wk.born ? .3 + (wk.i - newFrom) * step : null;
      animWorker(wk.obj, lt, null);
      if (born == null) { wk.obj.position.y = 0; wk.obj.visible = true; return; }
      const k = clamp((lt - born) / .45); wk.obj.visible = lt >= born;
      wk.obj.position.y = k < 1 ? (1 - easeOut(k)) * 9 + Math.sin(k * Math.PI) * 0 : Math.max(0, Math.sin(clamp((lt - born - .45) / .2) * Math.PI) * .3);
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
    ctx.save(); base(ctx); ctx.fillStyle = world.L.bg[0]; ctx.fillRect(0, 0, RW, TOP + 2); ctx.drawImage(renderer.domElement, 0, TOP); ctx.restore();
    // Namen und "NEU" über den Köpfen (2D, damit sie scharf bleiben)
    base(ctx);
    const tags = world.workers.map(wk => { const [x, y, z] = project(world, wk.x, wk.obj.position.y + 2.55, wk.z); return { wk, x, y, z }; }).sort((a, b) => b.z - a.z);
    tags.forEach(({ wk, x, y }) => {
      if (!wk.obj.visible) return;
      const nm = names[drawn - 1 - wk.i];
      if (nm) nameTag(ctx, nm.slice(0, 12), x, y, 24);
      const born = wk.born ? .3 + (wk.i - newFrom) * step : null;
      if (born != null && lt > born + .25 && lt < born + 2.4) { const kb = popIn(lt, born + .25, .3); ctx.save(); ctx.translate(x, y - (nm ? 40 : 0)); ctx.scale(kb, kb); sign(ctx, 'NEU', 0, 0, 28, '#7cf08a'); ctx.restore(); }
    });
    if (world.chef) { const [x, y] = project(world, world.chef.position.x, 3.3, world.chef.position.z); nameTag(ctx, 'Chef', x, y, 34); }
  }
  return { draw, ok: true };
})();
window.F3 = F3;
