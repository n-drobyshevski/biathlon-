/*
 * War Room, browser side. Everything here is a convenience: the form works
 * without it, and nothing here talks to the server.
 *  - deposit counter: counts the per-IP quota back up as slots free, and holds
 *    the submit button while the window is closed;
 *  - MAC/IP toggle: swaps the device field's example;
 *  - deposit log ("Registre des dépôts"): each scored attempt, kept in this
 *    browser's localStorage only, recorded once per server-issued attempt id;
 *  - flag copy without navigator.clipboard (the Pi serves plain HTTP).
 */
(function () {
  'use strict';
  var KEY = 'warroom-registre-v1';
  var MAX_ENTRIES = 50;

  function pad(n) { return (n < 10 ? '0' : '') + n; }
  function clock() { var d = new Date(); return pad(d.getHours()) + ':' + pad(d.getMinutes()) + ':' + pad(d.getSeconds()); }
  function mmss(s) { return Math.floor(s / 60) + ':' + pad(s % 60); }
  function val(id) { var el = document.getElementById(id); return el ? el.value.trim() : ''; }
  function load() {
    try { var v = JSON.parse(window.localStorage.getItem(KEY) || '[]'); return Array.isArray(v) ? v : []; }
    catch (e) { return []; }
  }
  function save(list) {
    try { window.localStorage.setItem(KEY, JSON.stringify(list.slice(-MAX_ENTRIES))); } catch (e) { /* private mode */ }
  }

  // ---------------------------------------------------------- deposit counter
  var g = document.getElementById('guichet');
  var submit = document.getElementById('submit');
  var lock = document.querySelector('.lock');
  if (g) {
    var max = +g.dataset.max || 0, left = +g.dataset.left || 0;
    var frees = (g.dataset.frees || '').split(',').filter(Boolean).map(Number).sort(function (a, b) { return a - b; });
    var start = Date.now();
    var pips = g.querySelectorAll('.pips i'), text = g.querySelector('.g-text');
    var paint = function () {
      var gone = (Date.now() - start) / 1000;
      var avail = Math.min(max, left + frees.filter(function (f) { return f <= gone; }).length);
      for (var i = 0; i < pips.length; i++) pips[i].classList.toggle('on', i < avail);
      g.classList.toggle('closed', avail === 0);
      if (avail > 0) {
        text.textContent = avail + (avail > 1 ? ' dépôts disponibles' : ' dépôt disponible') + ' sur ' + max + ' cette minute';
        if (submit) submit.disabled = false;
        if (lock) lock.hidden = true;
      } else {
        var next = frees.length ? Math.max(0, Math.ceil(frees[0] - gone)) : 0;
        text.textContent = 'Guichet fermé · prochain dépôt dans ' + mmss(next);
        if (submit) submit.disabled = true;
      }
      return avail < max;
    };
    if (paint()) { var timer = setInterval(function () { if (!paint()) clearInterval(timer); }, 1000); }
  }

  // ---------------------------------------------------------- MAC / IP toggle
  var dev = document.getElementById('f-device'), ex = document.getElementById('x-device');
  var kinds = document.querySelectorAll('input[name="device_kind"]');
  var paintKind = function () {
    var k = 'mac';
    for (var i = 0; i < kinds.length; i++) if (kinds[i].checked) k = kinds[i].value;
    if (dev) dev.placeholder = k === 'ip' ? '192.168.1.20' : '00:11:22:33:44:55';
    if (ex && ex.dataset[k]) ex.textContent = ex.dataset[k];
  };
  for (var k = 0; k < kinds.length; k++) kinds[k].addEventListener('change', function () { paintKind(); if (dev) dev.focus(); });

  // ---------------------------------------------------------- deposit log
  var log = document.getElementById('log');
  var list = load(), fresh = null;
  var result = document.querySelector('[data-attempt]');
  if (result && result.dataset.attempt) {
    var id = result.dataset.attempt;
    if (!list.some(function (e) { return e.id === id; })) {
      var when = (val('f-time-date') + ' ' + val('f-time-clock')).trim();
      list.push({ id: id, at: clock(), c: +result.dataset.correct, n: +result.dataset.total,
                  v: [val('f-saboteur'), val('f-vector'), when, val('f-device')] });
      save(list);
      list = load();
    }
    fresh = id;
  }
  var render = function () {
    if (!log) return;
    var body = log.querySelector('tbody');
    body.textContent = '';
    log.hidden = list.length === 0;
    for (var i = list.length - 1; i >= 0; i--) {
      var e = list[i], tr = document.createElement('tr');
      if (e.id === fresh) tr.className = 'new';
      var cells = ['#' + (i + 1), e.at || ''].concat(Array.isArray(e.v) ? e.v : []);
      for (var j = 0; j < cells.length; j++) {
        var td = document.createElement('td');
        td.textContent = cells[j] || '—';
        if (j > 1) { td.className = 'v'; td.title = cells[j] || ''; }
        tr.appendChild(td);
      }
      var r = document.createElement('td');
      r.className = 'res' + (e.c === 0 ? ' zero' : '');
      r.textContent = e.c + '/' + e.n;
      tr.appendChild(r);
      body.appendChild(tr);
    }
  };
  var clear = document.getElementById('log-clear');
  if (clear) {
    var armed = null;
    clear.addEventListener('click', function () {
      if (!armed) {
        clear.textContent = "Confirmer l'effacement";
        clear.classList.add('confirm');
        armed = setTimeout(function () { armed = null; clear.textContent = 'Effacer le registre'; clear.classList.remove('confirm'); }, 4000);
        return;
      }
      clearTimeout(armed); armed = null;
      list = []; save(list); render();
      clear.textContent = 'Effacer le registre'; clear.classList.remove('confirm');
    });
  }
  render();

  // ---------------------------------------------------------- copy the flag
  var btn = document.querySelector('.copy'), out = document.querySelector('.copied');
  if (btn) {
    btn.addEventListener('click', function () {
      var text = document.getElementById(btn.dataset.target).textContent.trim();
      var done = function () {
        btn.textContent = 'Copié'; out.textContent = 'Flag copié dans le presse-papiers.';
        setTimeout(function () { btn.textContent = 'Copier'; }, 1800);
      };
      var legacy = function () {
        var a = document.createElement('textarea'); a.value = text; a.setAttribute('readonly', '');
        a.style.position = 'fixed'; a.style.opacity = '0'; document.body.appendChild(a); a.select();
        try { if (document.execCommand('copy')) done(); else out.textContent = 'Sélectionnez le flag et copiez-le.'; }
        catch (e) { out.textContent = 'Sélectionnez le flag et copiez-le.'; }
        a.remove();
      };
      if (navigator.clipboard && window.isSecureContext) navigator.clipboard.writeText(text).then(done, legacy);
      else legacy();
    });
  }
})();
