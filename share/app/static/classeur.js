/* Classeur: interactive CSV preview for the Intranet DécaFlop share.

   Progressive enhancement of the static grid that csv_view() in app.py renders:
   the rows come from <script type="application/json" id="csv-data"> and the
   static table inside #csv-sheet is replaced. No library and no network call:
   everything runs in the player's browser, offline.

   Features: first row as headers (switch), sort per column (numbers, SAP dates
   YYYYMMDD and times HHMMSS sort as such), search, autofilter per column,
   cell / row / column selection with a formula bar and a copy button (raw
   values), keyboard moves, column resize, and an optional readable view of
   SAP dates and times. Cell text is only ever set with textContent. */
(function (root) {
  'use strict';

  var SVG_SEARCH = '<svg width="14" height="14" viewBox="0 0 16 16" aria-hidden="true" focusable="false">' +
    '<circle cx="6.5" cy="6.5" r="4.5" fill="none" stroke="currentColor" stroke-width="1.6"/>' +
    '<path d="M10 10l4.5 4.5" stroke="currentColor" stroke-width="1.7"/></svg>';
  var SVG_FILTER = '<svg width="12" height="12" viewBox="0 0 16 16" aria-hidden="true" focusable="false">' +
    '<path d="M1.5 2.5h13l-5 6v5l-3 1.5V8.5z" fill="currentColor"/></svg>';
  var SVG_SORT = '<svg class="cl-arrow" width="9" height="12" viewBox="0 0 9 12" aria-hidden="true" focusable="false">' +
    '<path class="up" d="M4.5 0.8 8.2 5H0.8z"/><path class="down" d="M4.5 11.2 0.8 7h7.4z"/></svg>';
  var TYPE_LABEL = {text: 'Texte', num: 'Nombre', date: 'Date (AAAAMMJJ)', time: 'Heure (HHMMSS)'};
  var MAX_VALUES = 300;

  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }
  function colName(i) {
    var s = '';
    i += 1;
    while (i) { var r = (i - 1) % 26; s = String.fromCharCode(65 + r) + s; i = Math.floor((i - 1) / 26); }
    return s;
  }
  function fold(s) {
    s = String(s);
    try { s = s.normalize('NFD').replace(/[̀-ͯ]/g, ''); } catch (e) { /* old browser */ }
    return s.toLowerCase();
  }
  function plural(n, one, many) { return n + ' ' + (n > 1 ? many : one); }

  // ------------------------------------------------------------------ types
  var RE_NUM = /^-?\d+(?:[.,]\d+)?$/, RE_D8 = /^\d{8}$/, RE_T6 = /^\d{6}$/;
  function validDate(v) {
    var y = +v.slice(0, 4), m = +v.slice(4, 6), d = +v.slice(6, 8);
    if (y < 1900 || y > 2199 || m < 1 || m > 12 || d < 1) return false;
    return d <= new Date(y, m, 0).getDate();
  }
  function validTime(v) { return +v.slice(0, 2) < 24 && +v.slice(2, 4) < 60 && +v.slice(4, 6) < 60; }
  function detect(values, name) {
    var vals = values.filter(function (v) { return v !== ''; });
    if (!vals.length) return 'text';
    if (vals.every(function (v) { return RE_D8.test(v) && validDate(v); })) return 'date';
    if (vals.every(function (v) { return RE_T6.test(v) && validTime(v); }) &&
        (/(time|zeit|heure|hh)/i.test(name || '') || vals.some(function (v) { return v.charAt(0) === '0'; })))
      return 'time';
    // codes such as 001 or 00 (leading zeros) stay text: they are identifiers, not amounts
    if (vals.every(function (v) { return RE_NUM.test(v) && !/^-?0\d/.test(v); })) return 'num';
    return 'text';
  }
  function pretty(v, type) {
    if (v === '') return v;
    if (type === 'date') return v.slice(6, 8) + '/' + v.slice(4, 6) + '/' + v.slice(0, 4);
    if (type === 'time') return v.slice(0, 2) + ':' + v.slice(2, 4) + ':' + v.slice(4, 6);
    return v;
  }
  var collator = (root.Intl && Intl.Collator) ? new Intl.Collator('fr', {numeric: true, sensitivity: 'base'})
    : {compare: function (a, b) { return a < b ? -1 : a > b ? 1 : 0; }};
  function compare(type, a, b) {
    if (type === 'num') return parseFloat(a.replace(',', '.')) - parseFloat(b.replace(',', '.'));
    if (type === 'date' || type === 'time') return a < b ? -1 : a > b ? 1 : 0;
    return collator.compare(a, b);
  }

  // ------------------------------------------------------------------ prefs
  function pref(key, dflt) {
    try { var v = root.localStorage.getItem('classeur-' + key); return v === null ? dflt : v === '1'; }
    catch (e) { return dflt; }
  }
  function savePref(key, on) { try { root.localStorage.setItem('classeur-' + key, on ? '1' : '0'); } catch (e) {} }

  function copyText(text, done) {
    function legacy() {
      var a = document.createElement('textarea');
      a.value = text; a.setAttribute('readonly', ''); a.style.position = 'fixed'; a.style.opacity = '0';
      document.body.appendChild(a); a.select();
      try { document.execCommand('copy'); done(); } catch (e) {}
      a.remove();
    }
    if (navigator.clipboard && root.isSecureContext) navigator.clipboard.writeText(text).then(done, legacy);
    else legacy();
  }

  // ------------------------------------------------------------------ mount
  function mount(host, data) {
    var all = (data.rows || []).map(function (r) { return r.map(function (c) { return c == null ? '' : String(c); }); });
    var ncol = Math.max(1, all.reduce(function (m, r) { return Math.max(m, r.length); }, 0));
    all.forEach(function (r) { while (r.length < ncol) r.push(''); });

    var st = {head: pref('head', true), dates: pref('dates', false), q: '', sort: null, filters: {},
              sel: {kind: 'cell', line: 0, c: 0}, rows: []};
    var names = [], types = [], items = [];

    function derive() {
      items = all.map(function (cells, i) { return {line: i + 1, cells: cells}; });
      if (st.head && items.length) items = items.slice(1);
      names = []; types = [];
      for (var c = 0; c < ncol; c++) {
        names.push(st.head && all.length && all[0][c] ? all[0][c] : colName(c));
        types.push(detect(items.map(function (it) { return it.cells[c]; }), st.head ? names[c] : ''));
      }
      st.sel = {kind: 'cell', line: items.length ? items[0].line : 0, c: 0};
    }
    function shown(v, c) { return st.dates ? pretty(v, types[c]) : v; }

    function visible() {
      var q = fold(st.q.trim());
      var rows = items.filter(function (it) {
        for (var c in st.filters) {
          var f = st.filters[c], v = it.cells[c];
          if (f.out[v]) return false;
          if (f.contains && fold(shown(v, +c)).indexOf(fold(f.contains)) < 0 && fold(v).indexOf(fold(f.contains)) < 0)
            return false;
        }
        if (!q) return true;
        return it.cells.some(function (v, c) { return fold(shown(v, c)).indexOf(q) >= 0 || fold(v).indexOf(q) >= 0; });
      });
      if (st.sort) {
        var c = st.sort.c, dir = st.sort.dir === 'desc' ? -1 : 1, t = types[c];
        rows = rows.map(function (it, i) { return {it: it, i: i}; }).sort(function (a, b) {
          var x = a.it.cells[c], y = b.it.cells[c];
          if (x === '' || y === '') return x === y ? a.i - b.i : (x === '' ? 1 : -1);   // empty cells last
          return (compare(t, x, y) * dir) || (a.i - b.i);
        }).map(function (o) { return o.it; });
      }
      return rows;
    }
    function filtered() { return st.q.trim() !== '' || Object.keys(st.filters).length > 0; }

    // ---------------------------------------------------------------- DOM
    host.textContent = '';
    var app = el('div', 'cl');
    host.appendChild(app);

    function toggle(id, label, on) {
      var l = el('label', 'cl-sw'), i = el('input');
      i.type = 'checkbox'; i.id = id; i.checked = on; i.setAttribute('role', 'switch');
      l.appendChild(i); l.appendChild(el('span', 'cl-track')); l.appendChild(document.createTextNode(label));
      return {label: l, input: i};
    }
    var bar = el('div', 'cl-bar');
    bar.setAttribute('role', 'toolbar'); bar.setAttribute('aria-label', 'Feuille');
    var headSw = toggle('cl-head', 'Ligne 1 = en-têtes', st.head);
    var search = el('label', 'cl-search');
    search.innerHTML = SVG_SEARCH;
    var q = el('input'); q.type = 'search'; q.id = 'cl-q'; q.placeholder = 'Rechercher dans la feuille';
    q.setAttribute('aria-label', 'Rechercher dans la feuille'); q.autocomplete = 'off'; q.spellcheck = false;
    search.appendChild(q);
    var datesSw = toggle('cl-dates', 'Dates lisibles', st.dates);
    var clear = el('button', 'cl-btn', 'Effacer les filtres'); clear.type = 'button';
    var count = el('span', 'cl-count'); count.setAttribute('aria-live', 'polite');
    [headSw.label, search, datesSw.label, clear, count].forEach(function (n) { bar.appendChild(n); });

    var fx = el('div', 'cl-fx');
    var ref = el('span', 'cl-ref'), val = el('span', 'cl-val'), raw = el('span', 'cl-raw');
    var copy = el('button', 'cl-btn cl-copy', 'Copier'); copy.type = 'button';
    copy.title = 'Copie la valeur brute, telle qu\'elle est dans le fichier';
    val.setAttribute('aria-label', 'Contenu de la sélection');
    fx.appendChild(ref); fx.appendChild(el('span', 'cl-f', 'fx')); fx.appendChild(val); fx.appendChild(raw); fx.appendChild(copy);

    var wrap = el('div', 'cl-wrap');
    wrap.tabIndex = 0;
    wrap.setAttribute('aria-label', 'Feuille, utilisez les flèches pour vous déplacer');
    var table = el('table', 'cl-grid'), colgroup = el('colgroup'), thead = el('thead'), tbody = el('tbody');
    table.appendChild(colgroup); table.appendChild(thead); table.appendChild(tbody); wrap.appendChild(table);
    var empty = el('div', 'cl-empty'); empty.hidden = true;
    empty.appendChild(document.createTextNode('Aucune ligne ne correspond. '));
    var clear2 = el('button', 'cl-link', 'Effacer les filtres'); clear2.type = 'button'; empty.appendChild(clear2);
    wrap.appendChild(empty);

    var pop = el('div', 'cl-pop'); pop.hidden = true; pop.setAttribute('role', 'dialog');
    [bar, fx, wrap, pop].forEach(function (n) { app.appendChild(n); });

    // ---------------------------------------------------------------- header
    var cols = [];
    function width(c) {
      var n = names[c].length + 3;
      for (var i = 0; i < items.length && i < 200; i++) n = Math.max(n, shown(items[i].cells[c], c).length);
      return Math.max(72, Math.min(340, Math.round(n * 7.4 + 30)));
    }
    function buildHead() {
      colgroup.textContent = ''; thead.textContent = ''; cols = [];
      var c0 = el('col'); c0.style.width = '46px'; colgroup.appendChild(c0);
      var letters = el('tr', 'cl-letters'), heads = el('tr', 'cl-names');
      letters.appendChild(el('th', 'cl-corner'));
      var corner = el('th', 'cl-corner', st.head ? '1' : '');
      heads.appendChild(corner);
      for (var c = 0; c < ncol; c++) {
        var col = el('col'); col.style.width = width(c) + 'px'; colgroup.appendChild(col); cols.push(col);
        var lt = el('th', 'cl-lt', colName(c)); lt.dataset.c = c; lt.scope = 'col'; letters.appendChild(lt);
        var th = el('th', 'cl-hd'); th.dataset.c = c; th.scope = 'col';
        var box = el('div', 'cl-h');
        var sb = el('button', 'cl-sort'); sb.type = 'button'; sb.dataset.c = c;
        sb.appendChild(el('span', 'cl-name', names[c]));
        sb.insertAdjacentHTML('beforeend', SVG_SORT);
        var fb = el('button', 'cl-fbtn'); fb.type = 'button'; fb.dataset.c = c;
        fb.setAttribute('aria-label', 'Filtrer la colonne ' + names[c]); fb.setAttribute('aria-haspopup', 'dialog');
        fb.innerHTML = SVG_FILTER;
        box.appendChild(sb); box.appendChild(fb); th.appendChild(box);
        var rz = el('span', 'cl-rz'); rz.dataset.c = c; rz.setAttribute('aria-hidden', 'true');
        rz.title = 'Glisser pour élargir, double-clic pour ajuster';
        th.appendChild(rz);
        heads.appendChild(th);
      }
      thead.appendChild(letters); thead.appendChild(heads);
      table.classList.toggle('cl-nohead', !st.head);
      paintHead();
    }
    function paintHead() {
      thead.querySelectorAll('.cl-hd').forEach(function (th) {
        var c = +th.dataset.c, s = st.sort && st.sort.c === c ? st.sort.dir : '';
        th.setAttribute('aria-sort', s === 'asc' ? 'ascending' : s === 'desc' ? 'descending' : 'none');
        th.querySelector('.cl-sort').dataset.dir = s;
        th.querySelector('.cl-sort').setAttribute('aria-label', 'Trier par ' + names[c] +
          (s === 'asc' ? ', tri croissant' : s === 'desc' ? ', tri décroissant' : ''));
        var on = !!st.filters[c];
        th.classList.toggle('cl-filtered', on);
        th.querySelector('.cl-fbtn').setAttribute('aria-pressed', on ? 'true' : 'false');
      });
    }

    // ---------------------------------------------------------------- body
    function fill(td, text, qq) {
      if (!qq) { td.textContent = text; return; }
      var low = fold(text), at = 0, i = low.indexOf(qq);
      if (i < 0) { td.textContent = text; return; }
      td.textContent = '';
      while (i >= 0) {
        if (i > at) td.appendChild(document.createTextNode(text.slice(at, i)));
        td.appendChild(el('mark', 'cl-hit', text.slice(i, i + qq.length)));
        at = i + qq.length; i = low.indexOf(qq, at);
      }
      if (at < text.length) td.appendChild(document.createTextNode(text.slice(at)));
    }
    function renderBody() {
      var rows = visible(), qq = fold(st.q.trim());
      st.rows = rows;
      tbody.textContent = '';
      var frag = document.createDocumentFragment();
      rows.forEach(function (it) {
        var tr = el('tr'); tr.dataset.line = it.line;
        var th = el('th', 'cl-rn', String(it.line)); th.scope = 'row'; tr.appendChild(th);
        for (var c = 0; c < ncol; c++) {
          var td = el('td', types[c] === 'num' ? 'cl-num' : null); td.dataset.c = c;
          fill(td, shown(it.cells[c], c), qq);
          tr.appendChild(td);
        }
        frag.appendChild(tr);
      });
      tbody.appendChild(frag);
      var total = items.length;
      count.textContent = rows.length === total ? plural(total, 'ligne', 'lignes')
        : rows.length + ' sur ' + plural(total, 'ligne', 'lignes');
      clear.hidden = !filtered();
      empty.hidden = rows.length > 0;
      paint();
    }

    // ---------------------------------------------------------------- selection
    function item(line) { for (var i = 0; i < items.length; i++) if (items[i].line === line) return items[i]; return null; }
    function selectionText() {
      var s = st.sel;
      if (s.kind === 'row') { var it = item(s.line); return it ? it.cells.join('\t') : ''; }
      if (s.kind === 'col') {
        var vals = st.rows.map(function (it) { return it.cells[s.c]; });
        return (st.head ? [names[s.c]] : []).concat(vals).join('\n');
      }
      var cur = item(s.line);
      return cur ? cur.cells[s.c] : '';
    }
    function paint() {
      wrap.querySelectorAll('.cl-sel,.cl-rsel,.cl-csel,.cl-on').forEach(function (n) {
        n.classList.remove('cl-sel', 'cl-rsel', 'cl-csel', 'cl-on');
      });
      var s = st.sel, tr = tbody.querySelector('tr[data-line="' + s.line + '"]');
      var lt = thead.querySelector('.cl-lt[data-c="' + s.c + '"]'), hd = thead.querySelector('.cl-hd[data-c="' + s.c + '"]');
      if (s.kind === 'row') {
        if (tr) tr.classList.add('cl-rsel');
      } else if (s.kind === 'col') {
        tbody.querySelectorAll('td[data-c="' + s.c + '"]').forEach(function (td) { td.classList.add('cl-csel'); });
        if (lt) lt.classList.add('cl-csel');
        if (hd) hd.classList.add('cl-csel');
      } else {
        var td = tr && tr.querySelector('td[data-c="' + s.c + '"]');
        if (td) td.classList.add('cl-sel');
        if (tr) tr.firstChild.classList.add('cl-on');
        if (lt) lt.classList.add('cl-on');
      }
      // formula bar
      raw.textContent = '';
      var it = item(s.line);
      if (s.kind === 'row') {
        ref.textContent = 'Ligne ' + s.line;
        val.textContent = it ? it.cells.map(function (v, c) { return shown(v, c); }).join('  |  ') : '';
        copy.textContent = 'Copier la ligne';
      } else if (s.kind === 'col') {
        ref.textContent = 'Colonne ' + colName(s.c);
        val.textContent = names[s.c] + ', ' + plural(st.rows.length, 'valeur affichée', 'valeurs affichées') +
          ' (' + TYPE_LABEL[types[s.c]] + ')';
        copy.textContent = 'Copier la colonne';
      } else {
        ref.textContent = it ? colName(s.c) + s.line : '';
        var v = it ? it.cells[s.c] : '';
        val.textContent = it ? shown(v, s.c) : '';
        if (it && st.dates && v !== '' && shown(v, s.c) !== v) raw.textContent = 'brut : ' + v;
        copy.textContent = 'Copier la cellule';
      }
      copy.disabled = !it && s.kind !== 'col';
    }
    function select(kind, line, c, scroll) {
      st.sel = {kind: kind, line: line, c: c};
      paint();
      if (scroll) {
        var tr = tbody.querySelector('tr[data-line="' + line + '"]');
        var td = tr && (kind === 'row' ? tr.firstChild : tr.querySelector('td[data-c="' + c + '"]'));
        if (td && td.scrollIntoView) td.scrollIntoView({block: 'nearest', inline: 'nearest'});
      }
    }
    function move(dr, dc) {
      if (!st.rows.length) return;
      var i = -1;
      for (var k = 0; k < st.rows.length; k++) if (st.rows[k].line === st.sel.line) { i = k; break; }
      if (i < 0) i = 0; else i = Math.max(0, Math.min(st.rows.length - 1, i + dr));
      var c = Math.max(0, Math.min(ncol - 1, st.sel.c + dc));
      select('cell', st.rows[i].line, c, true);
    }
    function doCopy() {
      var label = copy.textContent;
      copyText(selectionText(), function () {
        copy.textContent = 'Copié';
        setTimeout(function () { if (copy.textContent === 'Copié') copy.textContent = label; }, 1400);
      });
    }

    // ---------------------------------------------------------------- filter popover
    var popFor = -1, popBtn = null;
    function closePop(focus) {
      if (pop.hidden) return;
      pop.hidden = true; popFor = -1;
      if (focus && popBtn) popBtn.focus();
    }
    function openPop(c, btn) {
      if (popFor === c) { closePop(true); return; }
      popFor = c; popBtn = btn; pop.textContent = '';
      pop.setAttribute('aria-label', 'Filtrer la colonne ' + names[c]);
      var f = st.filters[c] || {contains: '', out: {}};
      var hd = el('div', 'cl-ph');
      hd.appendChild(el('b', null, names[c])); hd.appendChild(el('small', null, TYPE_LABEL[types[c]]));
      var sorts = el('div', 'cl-sorts');
      [['asc', 'Tri croissant'], ['desc', 'Tri décroissant']].forEach(function (d) {
        var b = el('button', 'cl-btn', d[1]); b.type = 'button';
        b.setAttribute('aria-pressed', st.sort && st.sort.c === c && st.sort.dir === d[0] ? 'true' : 'false');
        b.addEventListener('click', function () { setSort(c, d[0]); closePop(true); });
        sorts.appendChild(b);
      });
      var inp = el('input', 'cl-in'); inp.type = 'search'; inp.placeholder = 'Contient…'; inp.value = f.contains;
      inp.setAttribute('aria-label', 'La colonne ' + names[c] + ' contient');
      var counts = {}, order = [];
      items.forEach(function (it) {
        var v = it.cells[c];
        if (!(v in counts)) { counts[v] = 0; order.push(v); }
        counts[v]++;
      });
      order.sort(function (a, b) { return a === '' ? 1 : b === '' ? -1 : compare(types[c], a, b); });
      var list = el('div', 'cl-list'); list.setAttribute('role', 'group');
      list.setAttribute('aria-label', 'Valeurs de ' + names[c]);
      var allBox = el('label', 'cl-all'), allIn = el('input'); allIn.type = 'checkbox';
      allBox.appendChild(allIn); allBox.appendChild(el('span', 'cl-v', 'Tout sélectionner'));
      list.appendChild(allBox);
      var boxes = [];
      order.slice(0, MAX_VALUES).forEach(function (v) {
        var l = el('label'), i = el('input'); i.type = 'checkbox'; i.checked = !f.out[v]; i.value = v;
        l.appendChild(i); l.appendChild(el('span', 'cl-v', v === '' ? '(vide)' : shown(v, c)));
        l.appendChild(el('span', 'cl-n', String(counts[v])));
        list.appendChild(l); boxes.push(i);
      });
      if (order.length > MAX_VALUES)
        list.appendChild(el('p', 'cl-more', (order.length - MAX_VALUES) + ' autres valeurs : utilisez « Contient »'));
      function syncAll() {
        var on = boxes.filter(function (b) { return b.checked; }).length;
        allIn.checked = on === boxes.length; allIn.indeterminate = on > 0 && on < boxes.length;
      }
      function apply() {
        var out = {}, any = false;
        boxes.forEach(function (b) { if (!b.checked) { out[b.value] = true; any = true; } });
        var text = inp.value.trim();
        if (any || text) st.filters[c] = {contains: text, out: out}; else delete st.filters[c];
        paintHead(); renderBody(); syncAll();
      }
      allIn.addEventListener('change', function () { boxes.forEach(function (b) { b.checked = allIn.checked; }); apply(); });
      boxes.forEach(function (b) { b.addEventListener('change', apply); });
      inp.addEventListener('input', apply);
      var foot = el('div', 'cl-foot');
      var reset = el('button', 'cl-link', 'Effacer ce filtre'); reset.type = 'button';
      reset.addEventListener('click', function () { delete st.filters[c]; paintHead(); renderBody(); closePop(true); });
      var done = el('button', 'cl-btn', 'Fermer'); done.type = 'button';
      done.addEventListener('click', function () { closePop(true); });
      foot.appendChild(reset); foot.appendChild(done);
      [hd, sorts, inp, list, foot].forEach(function (n) { pop.appendChild(n); });
      syncAll();
      pop.hidden = false;
      var a = app.getBoundingClientRect(), b = btn.getBoundingClientRect(), w = pop.offsetWidth;
      pop.style.left = Math.max(8, Math.min(a.width - w - 8, b.right - a.left - w)) + 'px';
      pop.style.top = (b.bottom - a.top + 4) + 'px';
      inp.focus();
    }

    // ---------------------------------------------------------------- actions
    function setSort(c, dir) {
      st.sort = dir ? {c: c, dir: dir} : null;
      paintHead(); renderBody();
    }
    function cycleSort(c) {
      var cur = st.sort && st.sort.c === c ? st.sort.dir : '';
      setSort(c, cur === '' ? 'asc' : cur === 'asc' ? 'desc' : '');
    }
    function clearFilters() {
      st.q = ''; q.value = ''; st.filters = {};
      closePop(false); paintHead(); renderBody();
    }
    function setHead(on) {
      st.head = on; headSw.input.checked = on; savePref('head', on);
      st.sort = null; st.filters = {}; closePop(false);
      derive(); buildHead(); renderBody();
    }
    function setDates(on) {
      st.dates = on; datesSw.input.checked = on; savePref('dates', on);
      renderBody();
    }
    function setSearch(text) { st.q = text; q.value = text; renderBody(); }

    headSw.input.addEventListener('change', function () { setHead(headSw.input.checked); });
    datesSw.input.addEventListener('change', function () { setDates(datesSw.input.checked); });
    q.addEventListener('input', function () { st.q = q.value; renderBody(); });
    clear.addEventListener('click', clearFilters);
    clear2.addEventListener('click', clearFilters);
    copy.addEventListener('click', doCopy);

    table.addEventListener('click', function (e) {
      var t = e.target;
      var sb = t.closest('.cl-sort'), fb = t.closest('.cl-fbtn');
      if (sb) { cycleSort(+sb.dataset.c); return; }
      if (fb) { openPop(+fb.dataset.c, fb); return; }
      if (t.closest('.cl-rz')) return;
      var td = t.closest('td'), rn = t.closest('.cl-rn'), lt = t.closest('.cl-lt'), hd = t.closest('.cl-hd');
      if (td) select('cell', +td.parentNode.dataset.line, +td.dataset.c);
      else if (rn) select('row', +rn.parentNode.dataset.line, st.sel.c);
      else if (lt || hd) select('col', st.sel.line, +(lt || hd).dataset.c);
      else return;
      if (!t.closest('button')) wrap.focus({preventScroll: true});
    });
    wrap.addEventListener('keydown', function (e) {
      if (e.target !== wrap) return;
      var k = e.key;
      if (k === 'ArrowDown') move(1, 0);
      else if (k === 'ArrowUp') move(-1, 0);
      else if (k === 'ArrowRight') move(0, 1);
      else if (k === 'ArrowLeft') move(0, -1);
      else if (k === 'Home') move(0, -ncol);
      else if (k === 'End') move(0, ncol);
      else if (k === 'PageDown') move(10, 0);
      else if (k === 'PageUp') move(-10, 0);
      else if ((e.ctrlKey || e.metaKey) && (k === 'c' || k === 'C')) {
        if (String(root.getSelection ? root.getSelection() : '') !== '') return;   // let a text selection copy
        doCopy();
      } else return;
      e.preventDefault();
    });
    document.addEventListener('click', function (e) {
      if (!pop.hidden && !pop.contains(e.target) && !e.target.closest('.cl-fbtn')) closePop(false);
    });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') closePop(true); });

    // column resize: drag the right edge of a header, double-click to fit
    thead.addEventListener('pointerdown', function (e) {
      var rz = e.target.closest('.cl-rz');
      if (!rz) return;
      e.preventDefault();
      var c = +rz.dataset.c, col = cols[c], x0 = e.clientX, w0 = col.getBoundingClientRect().width || parseFloat(col.style.width);
      rz.setPointerCapture && rz.setPointerCapture(e.pointerId);
      function mv(ev) { col.style.width = Math.max(48, Math.round(w0 + ev.clientX - x0)) + 'px'; }
      function up() { rz.removeEventListener('pointermove', mv); rz.removeEventListener('pointerup', up); }
      rz.addEventListener('pointermove', mv); rz.addEventListener('pointerup', up);
    });
    thead.addEventListener('dblclick', function (e) {
      var rz = e.target.closest('.cl-rz');
      if (!rz) return;
      var c = +rz.dataset.c, n = names[c].length + 3;
      items.forEach(function (it) { n = Math.max(n, shown(it.cells[c], c).length); });
      cols[c].style.width = Math.max(48, Math.min(900, Math.round(n * 7.4 + 30))) + 'px';
    });

    derive(); buildHead(); renderBody();
    return {
      sortBy: setSort, search: setSearch, dates: setDates, header: setHead, clear: clearFilters,
      filter: function (c, contains, out) {
        var o = {}; (out || []).forEach(function (v) { o[v] = true; });
        if (contains || (out && out.length)) st.filters[c] = {contains: contains || '', out: o}; else delete st.filters[c];
        paintHead(); renderBody();
      },
      select: function (kind, line, c) { select(kind, line, c, true); },
      state: st
    };
  }

  root.Classeur = {mount: mount, detect: detect, pretty: pretty};

  function init() {
    var src = document.getElementById('csv-data'), host = document.getElementById('csv-sheet');
    if (!src || !host) return;
    var data;
    try { data = JSON.parse(src.textContent); } catch (e) { return; }   // keep the static grid
    root.classeur = mount(host, data);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
})(window);
