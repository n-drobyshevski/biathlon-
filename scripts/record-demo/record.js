// Records the demo video of the lab: a scripted walkthrough (hub, player sign-up,
// missions 01/04/06, the Intranet, CyberChef + team terminal, the SAP portal of
// mission 14, flag submission and the CTFd scoreboard) shown inside a fake
// multi-tab browser window (harness.html), with French documentary captions.
//
//   node record.js [out.mp4]          (see README.md: prerequisites, reset)
//
// Env (all optional):
//   SHOW_HOST  address shown in the video and used by the terminal (default 192.168.8.2, the Pi)
//   APP_HOST   where the services really answer (default 127.0.0.1; on the Pi's LAN: the Pi's IP)
//   PLAYER, PLAYER_PASS   the account created on camera in CTFd and the terminal
//   STEP_LOG=1 print each caption with a timestamp (to find a scene in the video)
// Logins and the mission 14 flag come from the repo's .env (same values as the lab).
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const fs = require('fs');
const http = require('http');
const net = require('net');
const path = require('path');

// .env of the repo root: the lab's flags and logins (never committed)
const ENV = {};
try {
  for (const l of fs.readFileSync(path.join(__dirname, '..', '..', '.env'), 'utf8').split(/\r?\n/)) {
    const m = l.match(/^([A-Z0-9_]+)=(.*)$/); if (m) ENV[m[1]] = m[2];
  }
} catch { /* no .env: defaults below */ }
const cfg = k => process.env[k] || ENV[k];

const APP_HOST = process.env.APP_HOST || '127.0.0.1';
const SHOW_HOST = process.env.SHOW_HOST || '192.168.8.2';
const OUT = process.argv[2] || path.join(__dirname, 'demo.mp4');
const PLAYER = process.env.PLAYER || 'equipe-it-03';
const PLAYER_PASS = process.env.PLAYER_PASS || 'Demo-2026!';
const SHARE_USER = cfg('SHARE_USER') || 'equipe-it', SHARE_PASS = cfg('SHARE_PASSWORD') || 'transition2026';
const SAP_USER = cfg('SAP_BASIS_USER') || 'basis_dflop', SAP_PASS = cfg('SAP_BASIS_PASS') || 'Trans1tion!2026';
const FLAG_14 = cfg('FLAG_14') || cfg('FLAG_14_SAP_GW');
if (!FLAG_14) { console.error('No mission 14 flag: run ./scripts/gen-flags.sh (or set FLAG_14_SAP_GW).'); process.exit(1); }
const SHARE_B64 = Buffer.from(`${SHARE_USER}:${SHARE_PASS}`).toString('base64');   // what site.config.js leaks
const W = 1920, H = 1080, S = 1.5, FPS = 30;
const U = (port, p = '/') => `http://${SHOW_HOST}:${port}${p}`;
const HARNESS = `http://${SHOW_HOST}:9999/`;

const sleep = ms => new Promise(r => setTimeout(r, ms));
const rnd = (a, b) => a + Math.random() * (b - a);
const ease = t => (t < .5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);

(async () => {
  // ---- forward proxy maps SHOW_HOST:port -> APP_HOST:port, adds latency ----
  const harnessHtml = fs.readFileSync(path.join(__dirname, 'harness.html'));
  const proxy = http.createServer((req, res) => {
    const u = new URL(req.url);
    if (u.port === '9999') { res.writeHead(200, { 'content-type': 'text/html; charset=utf-8' }); return res.end(harnessHtml); }
    const doc = (req.headers.accept || '').includes('text/html');
    setTimeout(() => {
      const up = http.request({ host: APP_HOST, port: u.port, path: u.pathname + u.search, method: req.method,
        headers: { ...req.headers, connection: 'close' } }, r => { res.writeHead(r.statusCode, r.headers); r.pipe(res); });
      up.on('error', () => { res.writeHead(502); res.end(); });
      req.pipe(up);
    }, doc ? rnd(280, 650) : rnd(10, 70));
  });
  const tunnel = (port, sock, head) => {
    const up = net.connect(+port, APP_HOST, () => { if (head && head.length) up.write(head); sock.pipe(up); up.pipe(sock); });
    up.on('error', () => sock.destroy()); sock.on('error', () => up.destroy());
    return up;
  };
  proxy.on('connect', (req, sock, head) => {          // ws:// through an HTTP proxy arrives as CONNECT
    const port = req.url.split(':').pop();
    const up = tunnel(port, sock);
    up.once('connect', () => { sock.write('HTTP/1.1 200 Connection Established\r\n\r\n'); if (head && head.length) up.write(head); });
  });
  proxy.on('upgrade', (req, sock, head) => {
    const u = new URL(req.url);
    const up = net.connect(+u.port, APP_HOST, () => {
      up.write(`${req.method} ${u.pathname}${u.search} HTTP/1.1\r\n` + Object.entries(req.headers).map(([k, v]) => `${k}: ${v}`).join('\r\n') + '\r\n\r\n');
      if (head && head.length) up.write(head); sock.pipe(up); up.pipe(sock);
    });
    up.on('error', () => sock.destroy()); sock.on('error', () => up.destroy());
  });
  await new Promise(r => proxy.listen(0, '127.0.0.1', r));
  const browser = await chromium.launch({ args: ['--disable-gpu-vsync', '--disable-frame-rate-limit'], proxy: { server: `http://127.0.0.1:${proxy.address().port}` } });
  const ctx = await browser.newContext({ viewport: { width: W, height: H }, deviceScaleFactor: 1, locale: 'fr-FR' });
  const page = await ctx.newPage();
  await page.goto(HARNESS);
  const Hc = (fn, ...a) => page.evaluate(([fn, a]) => window.H[fn](...a), [fn, a]);

  // ---- tab model ----------------------------------------------------------
  let activeTab = null;
  const view = () => page.frames().find(f => f.name() === 'view-' + activeTab);
  const vf = () => page.frameLocator('#view-' + activeTab);

  page.on('request', req => {
    if (req.isNavigationRequest() && req.frame().name() === 'view-' + activeTab) Hc('loading', true).catch(() => {});
  });
  page.on('framenavigated', async f => {
    if (f.name() !== 'view-' + activeTab) return;
    Hc('setUrl', f.url()).catch(() => {});
    try { await f.waitForLoadState('load'); await Hc('loading', false);
      await Hc('setTitle', (await f.title()) || decodeURIComponent(new URL(f.url()).pathname.split('/').pop()) || f.url()); } catch {}
  });

  // ---- capture ------------------------------------------------------------
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-c:v', 'mjpeg', '-framerate', String(FPS),
    '-i', '-', '-c:v', 'libx264', '-preset', 'slow', '-crf', '17', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', OUT],
    { stdio: ['pipe', 'inherit', 'inherit'] });
  let t0 = null, wall0 = 0, last = null, written = 0;
  const emitUntil = idx => { while (last && written < idx) { ff.stdin.write(last); written++; } };
  await page.screencast.start({ size: { width: W, height: H }, quality: 92,
    onFrame: ({ data, timestamp }) => {
      const t = timestamp < 1e11 ? timestamp * 1000 : timestamp;
      if (t0 === null) { t0 = t; wall0 = Date.now(); }
      emitUntil(Math.round((t - t0) / 1000 * FPS)); last = data;
    } });

  // ---- primitives ---------------------------------------------------------
  let cx = W / 2, cy = H / 2 + 80;
  await Hc('cursor', cx / S, cy / S);
  const move = async (x, y) => {
    const d = Math.hypot(x - cx, y - cy); if (d < 2) return;
    const n = Math.max(8, Math.round(Math.min(1100, 320 + d / S * 0.65) / 16));
    const k = rnd(-0.18, 0.18), mx = (cx + x) / 2 - (y - cy) * k, my = (cy + y) / 2 + (x - cx) * k, sx = cx, sy = cy;
    for (let i = 1; i <= n; i++) { const t = ease(i / n), u = 1 - t;
      const px = u * u * sx + 2 * u * t * mx + t * t * x, py = u * u * sy + 2 * u * t * my + t * t * y;
      await page.mouse.move(px, py); await Hc('cursor', px / S, py / S); await sleep(8); }
    cx = x; cy = y;
  };
  const smoothScrollBy = async (dy, dur = 1100) => {
    await view().evaluate(async ([dy, dur]) => {
      let s = document.elementFromPoint(innerWidth / 2, innerHeight / 2);
      while (s && s !== document.body && !(s.scrollHeight > s.clientHeight + 4 && /(auto|scroll)/.test(getComputedStyle(s).overflowY))) s = s.parentElement;
      const el = (!s || s === document.body) ? document.scrollingElement : s;
      const from = el.scrollTop, to = Math.max(0, Math.min(el.scrollHeight - el.clientHeight, from + dy));
      const e = t => (t < .5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
      await new Promise(res => { const st = performance.now();
        const f = now => { const p = Math.min(1, (now - st) / dur); el.scrollTop = from + (to - from) * e(p); p < 1 ? requestAnimationFrame(f) : res(); };
        requestAnimationFrame(f); });
    }, [dy, dur]); await sleep(250);
  };
  const ensureVisible = async loc => {
    const r = await loc.evaluate(el => { const b = el.getBoundingClientRect(); return { top: b.top, bottom: b.bottom, vh: innerHeight }; });
    if (r.top < 70 || r.bottom > r.vh - 110) await smoothScrollBy(r.top - r.vh * 0.4, 900);
  };
  const point = async (loc, { dx, chrome } = {}) => {
    if (!chrome) await ensureVisible(loc);
    const b = await loc.boundingBox();
    await move(b.x + (dx ?? Math.min(b.width / 2, 105)) + rnd(-4, 4), b.y + b.height / 2 + rnd(-2, 2));
    return b;
  };
  const press = async () => { await sleep(rnd(90, 160));
    await page.mouse.down(); await Hc('press', true, cx / S, cy / S); await sleep(85);
    await page.mouse.up(); await Hc('press', false, cx / S, cy / S); };
  const waitNav = async fn => {
    const p = page.waitForEvent('framenavigated', { predicate: f => f.name() === 'view-' + activeTab, timeout: 15000 });
    await fn(); await p; await view().waitForLoadState('load'); await sleep(450);
  };
  const click = async loc => { await point(loc); await press(); await sleep(250); };
  const clickNav = async loc => waitNav(() => click(loc));
  const typeKeys = async text => { for (const c of text) { await page.keyboard.type(c); await sleep(c === ' ' ? rnd(90, 160) : rnd(40, 120)); } };
  const typeInto = async (loc, text) => { await click(loc); await typeKeys(text); await sleep(250); };
  const omni = page.locator('#omni'), newtabBtn = page.locator('.newtab'), tabEl = i => page.locator('#tablist .tab').nth(i);
  const shown = u => u.replace(/^https?:\/\//, '');
  const typeUrl = async url => {
    await point(omni, { dx: 330, chrome: true }); await press();
    await Hc('typeStart');
    for (const c of shown(url)) { await Hc('typeChar', c); await sleep(rnd(35, 95)); }
    await sleep(350);
    await waitNav(async () => { await Hc('setUrl', url); await Hc('nav', url); });
  };
  const editUrl = async (from, to) => {
    await point(omni, { dx: 390, chrome: true }); await press();
    await Hc('typeStart');
    await page.evaluate(t => { document.getElementById('url').textContent = t; }, shown(from));
    await sleep(500);
    let common = 0; while (common < from.length && from[common] === to[common]) common++;
    for (let i = from.length; i > common; i--) { await page.evaluate(t => { document.getElementById('url').textContent = t; }, shown(from.slice(0, i - 1))); await sleep(rnd(70, 120)); }
    await sleep(250);
    for (const c of to.slice(common)) { await Hc('typeChar', c); await sleep(rnd(80, 150)); }
    await sleep(400);
    await waitNav(async () => { await Hc('setUrl', to); await Hc('nav', to); });
  };
  // open a new tab (click +) and make it active
  const openTab = async (id, fav) => {
    await point(newtabBtn, { chrome: true }); await press();
    await Hc('openTab', id, '', fav); activeTab = id; await Hc('switchTab', id); await sleep(450);
  };
  // switch to an existing tab by clicking it in the strip
  const switchTab = async (id, idx) => {
    await point(tabEl(idx), { chrome: true }); await press();
    activeTab = id; await Hc('switchTab', id); await sleep(500);
  };
  // a link opened in a new tab (target=_blank, or Ctrl+click on a plain link)
  const openFromLink = async (loc, id, fav, { ctrl = false } = {}) => {
    const href = await loc.getAttribute('href');
    ctx.once('page', pg => pg.close().catch(() => {}));
    await point(loc);
    if (ctrl) await page.keyboard.down('Control');
    await press();
    if (ctrl) await page.keyboard.up('Control');
    await sleep(300);
    await Hc('openTab', id, '', fav); activeTab = id; await Hc('switchTab', id);
    await waitNav(async () => { await Hc('setUrl', href); await Hc('nav', href); });
  };
  const closeTabAt = async (id, idx) => {
    await point(tabEl(idx).locator('.x'), { chrome: true }); await press();
    await Hc('closeTab', id);
    activeTab = await page.evaluate(() => (document.querySelector('#views iframe.show') || {}).name?.replace('view-', ''));
    await sleep(600);
  };
  const caption = async (h, ms = 2600) => { if (process.env.STEP_LOG) console.log(new Date().toISOString().slice(11, 19), h.replace(/<[^>]+>/g, '').slice(0, 70)); await Hc('caption', h); if (ms) await sleep(ms); };
  const card = async (k, t, s = '', ms = 2800) => { await Hc('caption', ''); await Hc('card', k, t, s); await sleep(ms); await Hc('card', null); await sleep(600); };
  const zoomOn = async (loc, s = 1.8) => { const b = await loc.boundingBox(); await Hc('zoom', s, (b.x + b.width / 2) / S, (b.y + b.height / 2) / S); await sleep(1000); };
  const zoomOnText = async (s = 2.1) => {
    const fb = await page.locator('#view-' + activeTab).boundingBox();
    const r = await view().evaluate(() => { const g = document.createRange(); g.selectNodeContents(document.body); const b = g.getBoundingClientRect(); return { x: b.left, y: b.top, w: b.width, h: b.height }; });
    const x = fb.x + (r.x + Math.min(r.w, 900) / 2) * S, y = fb.y + (r.y + r.h / 2) * S;
    await Hc('zoom', s, x / S, y / S); await sleep(1000);
  };
  const zoomOnTextOf = async (loc, s = 1.8) => {
    const fb = await page.locator('#view-' + activeTab).boundingBox();
    const r = await loc.evaluate(el => { const g = document.createRange(); g.selectNodeContents(el); const b = g.getBoundingClientRect(); return { x: b.left, y: b.top, w: b.width, h: b.height }; });
    const x = fb.x + (r.x + Math.min(r.w, 760) / 2) * S, y = fb.y + (r.y + r.h / 2) * S;
    await Hc('zoom', s, x / S, y / S); await sleep(1000);
  };
  const zoomOut = async () => { await Hc('zoom', 1); await sleep(950); };
  const mark = async loc => loc.evaluate(el => { el.style.outline = '3px solid #ff5a36'; el.style.outlineOffset = '3px'; el.style.borderRadius = '4px'; });
  const flagIn = () => vf().locator('code, .codebox, pre, input').filter({ hasText: 'TRIATHLON' }).first();

  await sleep(600);

  // ---- 0 · title ----------------------------------------------------------
  await card('DÉMO', 'Opération Dernière Transition', 'Un CTF autonome sur Raspberry Pi 5 — 16 missions, aucun accès internet', 3600);

  // ---- 1 · hub (tab 1) ----------------------------------------------------
  await Hc('openTab', 't1', '', 'C'); activeTab = 't1'; await Hc('switchTab', 't1');
  await caption('Les joueurs n’ont qu’une adresse à retenir : celle du Pi, port <code>8080</code>', 0);
  await typeUrl(U(8080));
  await caption('La <b>cellule de crise</b> : briefing, liste des missions et liens vers chaque service', 1800);
  await smoothScrollBy(320, 1400); await sleep(700); await smoothScrollBy(-320, 1100);
  await clickNav(vf().getByRole('link', { name: 'Contexte' }).last());
  await caption('L’onglet <b>Contexte</b> pose l’histoire : la liste de départ de la finale a été truquée', 3200);

  // ---- 1b · the player creates an account on the scoreboard (tab CTFd) -----
  await card('PREMIERS PAS', 'Créer son compte', 'Chaque joueur s’inscrit sur le tableau des scores CTFd, lui aussi sur le Pi');
  await caption('Depuis la cellule de crise, le lien vers le <b>tableau des scores</b>', 0);
  await openFromLink(vf().getByRole('link', { name: /Tableau des scores/ }).first(), 'tc', 'C');
  await caption('Le CTFd de l’événement. On s’inscrit avec un pseudo d’équipe', 0);
  await clickNav(vf().getByRole('link', { name: /inscri/i }).first());
  await typeInto(vf().locator('#name'), PLAYER);
  await typeInto(vf().locator('#email'), PLAYER.replace(/-/g, '') + '@decaflop.lan');
  await typeInto(vf().locator('#password'), PLAYER_PASS);
  await clickNav(vf().locator('#_submit'));
  await caption('Compte créé : les <b>16 missions</b> attendent, classées par catégorie', 2600);
  await smoothScrollBy(500, 1500); await sleep(400); await smoothScrollBy(-500, 1100);
  await caption('On garde cet onglet ouvert pour soumettre les flags', 0);
  await switchTab('t1', 0);

  // ---- 2 · mission 01 — new tab for the site -------------------------------
  await card('MISSION 01 · WEB · FACILE', 'Le secret du sponsor', 'Le site DécaFlop cache une zone interne');
  await caption('On ouvre le site du sponsor dans un <b>nouvel onglet</b>', 0);
  await openTab('t2', 'D');
  await typeUrl(U(8001));
  await caption('Le site public du sponsor : boutique, actualités, espace presse', 1400);
  await smoothScrollBy(450, 1500); await sleep(500); await smoothScrollBy(-450, 1100);
  await caption('Premier réflexe : ce que le site demande aux moteurs de <b>ne pas</b> indexer', 0);
  await typeUrl(U(8001, '/robots.txt'));
  await zoomOnText(2.3);
  await caption('Un chemin « interne » déclaré publiquement…', 2400);
  await zoomOut();
  await typeUrl(U(8001, '/staff-portal-7f3a9'));
  await caption('Le portail staff, accessible sans authentification', 1600);
  let f = flagIn();
  await point(f); await mark(f); await zoomOn(f, 1.9);
  await caption('<b>Flag trouvé.</b> Il se soumet dans l’onglet CTFd', 2800);
  await zoomOut();

  // ---- 3 · the internal share — another new tab ----------------------------
  await card('LES PREUVES', 'Intranet DécaFlop', 'Le partage interne où vivent les fichiers à analyser');
  await caption('L’identifiant du partage fuit dans la configuration front du site', 0);
  await typeUrl(U(8001, '/assets/site.config.js'));
  await zoomOnText(1.9);
  await caption('Un compte de service en <b>base64</b> : on le décodera avec CyberChef, fourni sur le Pi', 3000);
  await zoomOut();
  await caption('On ouvre le partage dans un nouvel onglet', 0);
  await openTab('t3', 'I');
  await typeUrl(U(8020));
  await caption('On se connecte avec le compte récupéré', 0);
  await typeInto(vf().locator('#u'), SHARE_USER);
  await typeInto(vf().locator('#p'), SHARE_PASS);
  await clickNav(vf().locator('button[type=submit]'));
  await caption('Un vrai intranet d’entreprise : documents, annuaire, recherche', 1800);
  await clickNav(vf().getByRole('link', { name: 'Documents' }).first());
  await caption('Chaque mission forensics y trouve son fichier : pcap, image disque, exports SAP…', 2200);
  await clickNav(vf().getByRole('link', { name: /Basis SAP/ }).last());
  await clickNav(vf().getByRole('link', { name: /^Exports/ }).last());
  await clickNav(vf().getByRole('link', { name: /USR02/ }).first());
  await caption('Aperçu intégré : l’export SAP s’affiche comme un tableur, rien à installer', 3200);

  // ---- 4 · mission 04 — back to the site tab -------------------------------
  await card('MISSION 04 · WEB · MOYEN', 'Pas ton profil', 'Portail athlète — faille IDOR');
  await caption('On revient sur l’onglet du site pour la mission suivante', 0);
  await switchTab('t2', 2);
  await typeUrl(U(8004));
  await caption('Le portail des athlètes : on suit son lien de connexion', 1200);
  await clickNav(vf().getByRole('link', { name: /Continuer/ }).first());
  await caption('Mon dossier : n° <b>1042</b>. Et l’identifiant est… dans l’URL', 2400);
  await caption('Essayons un numéro plus bas, réservé à l’organisation', 0);
  await editUrl(U(8004, '/profile/1042'), U(8004, '/profile/1000'));
  await caption('Aucun contrôle d’accès : on lit le <b>journal d’audit</b> de l’admin', 2600);
  f = flagIn();
  await point(f); await mark(f); await zoomOn(f, 1.8);
  await caption('<b>Flag.</b> Et le journal désigne un compte suspect pour la suite de l’enquête', 3000);
  await zoomOut();

  // ---- 5 · mission 06 — same site tab --------------------------------------
  await card('MISSION 06 · WEB · MOYEN', 'Admin des résultats', 'Formulaire de connexion — injection SQL');
  await typeUrl(U(8006));
  await caption('L’outil d’administration des résultats. Pas de mot de passe ? Pas grave.', 0);
  await typeInto(vf().locator('[name=username]'), "' OR 1=1 --");
  await typeInto(vf().locator('[name=password]'), 'x');
  await caption('<code>OR 1=1</code> rend la condition toujours vraie, <code>--</code> neutralise le mot de passe', 2400);
  await clickNav(vf().locator('button[type=submit], input[type=submit]').first());
  await caption('<b>Connecté en administrateur</b>, sans connaître le mot de passe', 2000);
  f = flagIn();
  if (await f.count()) { await point(f); await mark(f); await zoomOn(f, 1.8); await caption('<b>Flag.</b>', 2000); await zoomOut(); }

  // ---- 5a · the players' tools (before SAP) ------------------------------------------------
  await card('LES OUTILS', 'CyberChef et terminal d’équipe', 'Rien à installer : tout tourne sur le Pi, dans le navigateur');
  await caption('On range les onglets terminés : le site et l’intranet', 0);
  await closeTabAt('t2', 2); await closeTabAt('t3', 2);
  await switchTab('t1', 0);
  await clickNav(vf().getByRole('link', { name: 'Outils' }).first());
  await caption('L’onglet <b>Outils</b> de la cellule de crise', 1800);
  await openFromLink(vf().locator('a.open[href*=":8090"]').first(), 't6', 'C');
  await caption('<b>CyberChef</b>, la boîte à outils de décodage. On reprend le compte base64 de la mission 01', 0);
  await vf().locator('#search').waitFor({ timeout: 20000 }); await sleep(800);
  await typeInto(vf().locator('#search'), 'base64');
  const op = vf().locator('#search-results li, li.operation').filter({ hasText: /^From Base64$/ }).first();
  await point(op); await sleep(200); await page.mouse.dblclick(cx, cy); await sleep(800);
  const inRecipe = () => vf().locator('#rec-list li').filter({ hasText: 'From Base64' }).count();
  if (!(await inRecipe())) { await op.dblclick(); await sleep(800); }
  if (!(await inRecipe())) throw new Error('CyberChef: From Base64 not added to the recipe');
  const cin = vf().locator('#input-text .cm-content, #input-text textarea').first();
  await click(cin); await page.keyboard.insertText(SHARE_B64); await sleep(1500);
  const cout = vf().locator('#output-text .cm-content, #output-text').first();
  await cout.filter({ hasText: SHARE_USER }).waitFor({ timeout: 10000 });
  await point(cout, { dx: 120 }); await zoomOnTextOf(cout, 1.8);
  await caption(`<code>${SHARE_USER}:${SHARE_PASS}</code> : l’identifiant de l’intranet, décodé`, 2800);
  await zoomOut();
  await caption('Et le <b>terminal d’équipe</b>, un shell Linux dans le navigateur', 0);
  await switchTab('t1', 0);
  await openFromLink(vf().locator('a.open[href*=":8091"]').first(), 't7', 'T');
  await sleep(1500);
  const term = vf().locator('.xterm-screen, #terminal-container, .xterm').first();
  await click(term);
  await caption('Chaque joueur ouvre son espace personnel avec un pseudo et un mot de passe', 0);
  const tkeys = async (txt, enter = true) => { await typeKeys(txt); if (enter) { await sleep(200); await page.keyboard.press('Enter'); } await sleep(700); };
  await tkeys(PLAYER); await sleep(600);
  await tkeys(PLAYER_PASS); await tkeys(PLAYER_PASS); await sleep(2200);
  await caption('Outils préinstallés : exiftool, binwalk, john, hashcat, tshark… On récupère la photo de la mission 03', 0);
  await tkeys('clear'); await sleep(300);
  await tkeys('grab http://' + SHOW_HOST + ':8001/medias/transition_shot.jpg'); await sleep(1500);
  await tkeys('exiftool -Artist -DateTimeOriginal -Model -GPSPosition transition_shot.jpg'); await sleep(1200);
  const tb = await page.locator('#view-t7').boundingBox();
  await Hc('zoom', 1.5, (tb.x + tb.width * 0.3) / S, (tb.y + tb.height * 0.2) / S); await sleep(1000);
  await caption('Auteur, heure, appareil, GPS : les métadonnées de la photo prise en zone de transition', 3600);
  await zoomOut();

  // ---- 5b · mission 14 — the SAP portal ------------------------------------
  await card('MISSION 14 · SAP · MOYEN', 'Le gateway ouvert', 'Le portail SAP DFlop ERP — système DFL, mandant 001');
  await caption('On ferme CyberChef. Où est le portail SAP ? La cellule de crise le dit', 0);
  await closeTabAt('t6', 2);
  await switchTab('t1', 0);
  await clickNav(vf().getByRole('link', { name: 'Missions' }).last());
  const sapLink = vf().locator('#mission-14 a[href*=":8014"]').first();
  await point(sapLink); await mark(sapLink);
  await caption('La fiche de la mission 14 donne l’accès : <b>Gateway SAP</b>, port <code>8014</code>', 2600);
  await caption('Il figure aussi dans les notes de l’équipe Basis, sur l’intranet. Ctrl + clic : nouvel onglet', 0);
  await sleep(1200);
  await openFromLink(sapLink, 't4', 'S', { ctrl: true });
  await caption('Ouverture de session Basis. Les identifiants ont fuité dans le dépôt <code>.git</code> (mission 11)', 0);
  await typeInto(vf().locator('#sap-user'), SAP_USER);
  await typeInto(vf().locator('#sap-pass'), SAP_PASS);
  await clickNav(vf().locator('form[action$="/sap/logon"] button'));
  await caption('Le menu SAP Easy Access. Comme dans le vrai SAP GUI, on peut taper un <b>code transaction</b>', 2600);
  const tcode = async code => {
    const fld = vf().locator('#sap-cmd');
    await click(fld); await fld.fill(''); await typeKeys(code); await sleep(300);
    await waitNav(() => page.keyboard.press('Enter'));
  };
  await tcode('SM37');
  await caption('<code>SM37</code> : un export lancé <b>à la main</b> à 18 h 42, la veille de la course', 0);
  const hotJob = vf().locator('tr.sap-row-highlight').first();
  await point(hotJob); await mark(hotJob); await sleep(2600);
  await tcode('SE16N');
  await caption('<code>SE16N</code> : la table des utilisateurs <code>USR02</code> confirme la connexion à la même heure', 0);
  const hotUser = vf().locator('tr').filter({ hasText: 'VLINDQVIST' }).first();
  await point(hotUser); await mark(hotUser); await sleep(2800);
  await tcode('SMGW');
  await caption('<code>SMGW</code> : le moniteur de la passerelle et sa liste d’accès <code>reginfo</code>', 2000);
  const acl = vf().locator('pre').first();
  await point(acl); await zoomOnTextOf(acl, 1.7);
  await caption('Une seule règle : <code>TP=* HOST=*</code>. N’importe quel programme peut s’enregistrer', 2800);
  await zoomOut();
  await caption('On enregistre donc un programme externe, avec un nom quelconque', 0);
  await click(vf().locator('#sap-tp')); await page.keyboard.press('Control+A'); await sleep(200);
  await typeKeys('Z_DEMO_RFC'); await sleep(300);
  await clickNav(vf().locator('#sap-tp').locator('xpath=ancestor::form').locator('button'));
  f = vf().locator('pre.sap-flag');
  await point(f, { dx: 120 }); await mark(f); await zoomOnTextOf(f, 1.8);
  await caption('<b>Accepté sans contrôle.</b> La passerelle renvoie le flag', 2800);
  await zoomOut();
  await point(f, { dx: 40 });
  await page.mouse.click(cx, cy, { clickCount: 3 }); await Hc('press', true, cx / S, cy / S); await Hc('press', false, cx / S, cy / S);
  await caption('On copie le flag', 0); await sleep(500);
  await page.keyboard.press('Control+C'); await sleep(900);

  // ---- 6 · hub status, then submit in the CTFd tab ---------------------------
  await card('LA VALIDATION', 'Soumettre le flag', 'La cellule de crise suit l’avancement, CTFd compte les points');
  await caption('Retour à la cellule de crise', 0);
  await switchTab('t1', 0);
  await clickNav(vf().getByRole('link', { name: 'Missions' }).last());
  const row14 = vf().locator('#mission-14');
  await point(row14.locator('b').first());
  await caption('La fiche de la mission 14 : l’équipe la passe en <b>Résolu</b>', 0);
  const st14 = row14.locator('select');
  await point(st14); await press(); await st14.selectOption('Résolu'); await sleep(1600);
  await caption('Puis on soumet le flag dans l’onglet CTFd, resté ouvert', 0);
  await switchTab('tc', 1);
  const tile = vf().getByRole('button', { name: 'The Open Gateway' });
  await click(tile);
  const input = vf().locator('#challenge-input');
  await input.waitFor({ state: 'visible' }); await sleep(600);
  await caption('On colle le flag et on soumet', 0);
  await click(input); await sleep(250);
  await page.keyboard.press('Control+V'); await input.fill(FLAG_14); await sleep(700);
  await click(vf().locator('#challenge-submit'));
  const ok = vf().locator('.notification-row').filter({ hasText: /Correct/i }).first();
  await ok.waitFor({ timeout: 8000 });
  await point(ok); await mark(ok); await zoomOn(ok, 1.7);
  await caption('<b>Correct.</b> +150 points pour l’équipe', 2600);
  await zoomOut();
  const closeBtn = vf().locator('.modal.show .btn-close, .modal.show [data-bs-dismiss=modal]').first();
  if (await closeBtn.count()) await click(closeBtn); else await page.keyboard.press('Escape');
  await sleep(900);
  await caption('La mission passe au vert dans la grille', 0);
  await point(tile); await sleep(2200);

  // ---- 6b · everyone's progress ---------------------------------------------
  await clickNav(vf().getByRole('link', { name: 'Classement' }).first());
  await caption('Le classement : la progression de chaque équipe, minute par minute', 0);
  const chart = vf().locator('#score-graph, .echarts, canvas').first();
  if (await chart.count()) await point(chart, { dx: 380 });
  await sleep(3000);
  const rowMe = vf().locator('tr').filter({ hasText: PLAYER }).first();
  await caption('Notre équipe vient d’entrer au classement, les autres ont une heure d’avance', 0);
  await point(rowMe); await mark(rowMe); await sleep(2600);
  const top = vf().locator('tbody tr').first();
  await caption('En tête, <b>equipe-it-01</b> : 8 missions résolues', 0);
  await point(top); await sleep(2400);

  // ---- 8 · outro --------------------------------------------------------------
  await card('ET ENSUITE', '16 missions · 2175 points',
    'Web, forensics, stégano, SAP — jusqu’au rapport d’incident final en équipe.<br>Tout tourne sur un Pi, hors ligne.', 4200);

  // ---- finish -------------------------------------------------------------
  await page.screencast.stop();
  emitUntil(Math.round((Date.now() - wall0) / 1000 * FPS));
  ff.stdin.end(); await new Promise(r => ff.on('close', r));
  await browser.close(); proxy.close();
  console.log(OUT, `${(written / FPS).toFixed(1)}s`);
  process.exit(0);
})().catch(e => { console.error(e); process.exit(1); });
