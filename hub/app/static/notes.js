/* Bloc-notes (notes.py): autosave, teammates' changes picked up every few
   seconds, and a notice when someone saved while you were typing. Without this
   script the page still works: the form saves with "Enregistrer". No library,
   no other host: everything talks to the hub that served the page. */
(function () {
  'use strict';

  function hhmm(t) {
    var d = new Date(t * 1000);
    return ('0' + d.getHours()).slice(-2) + ':' + ('0' + d.getMinutes()).slice(-2);
  }
  document.querySelectorAll('time[data-t]').forEach(function (e) { e.textContent = hhmm(+e.dataset.t); });
  document.querySelectorAll('form[data-confirm]').forEach(function (f) {
    f.addEventListener('submit', function (e) { if (!window.confirm(f.dataset.confirm)) e.preventDefault(); });
  });

  // ---- the list: a notepad someone shares with you shows up without a reload
  var list = document.getElementById('np-list'), incoming = document.getElementById('np-incoming');
  if (list && incoming && window.fetch && window.JSON) {
    var openId = list.dataset.open, known = {}, announced = {}, baseTitle = document.title;
    list.querySelectorAll('a[href*="?n="]').forEach(function (a) { known[a.getAttribute('href').split('n=')[1]] = true; });
    var meta = function (p) {
      var m = p.shared ? p.n + ' membres' : 'Privé';
      if (p.by) m += ', modifié par ' + p.by + ' à ' + hhmm(p.at);
      return m;
    };
    var item = function (p) {
      var a = document.createElement('a'), b = document.createElement('b'), s = document.createElement('small');
      a.href = '/bloc-notes?n=' + p.id;
      if (String(p.id) === openId) a.setAttribute('aria-current', 'true');
      if (p.new && String(p.id) !== openId) {
        var d = document.createElement('span');
        d.className = 'np-dot'; d.setAttribute('aria-label', 'Nouveau');
        b.appendChild(d);
      }
      b.appendChild(document.createTextNode(p.name));
      s.textContent = meta(p);
      a.appendChild(b); a.appendChild(s);
      return a;
    };
    var announce = function (p) {
      var el = document.createElement('p'), w = document.createElement('b'), a = document.createElement('a');
      w.textContent = p.added_by || 'Quelqu\'un';
      el.appendChild(w);
      el.appendChild(document.createTextNode(' vous a ajouté au bloc-notes « ' + p.name + ' ».'));
      a.href = '/bloc-notes?n=' + p.id; a.textContent = 'Ouvrir';
      el.appendChild(a);
      incoming.appendChild(el);
    };
    var refresh = function () {
      if (document.hidden) return;
      fetch('/bloc-notes/liste', {credentials: 'same-origin', cache: 'no-store'}).then(function (r) {
        return r.ok ? r.json() : null;
      }).then(function (d) {
        if (!d) return;
        var frag = document.createDocumentFragment(), waiting = 0;
        d.pads.forEach(function (p) {
          var id = String(p.id);
          frag.appendChild(item(p));
          if (p.new && id !== openId) {
            waiting++;
            if (!known[id] && !announced[id]) { announced[id] = true; announce(p); }
          }
          known[id] = true;
        });
        list.textContent = '';
        list.appendChild(frag);
        document.title = (waiting ? '(' + waiting + ') ' : '') + baseTitle;
        // the header chip's count and the sheet tab's dot follow too
        var chip = document.querySelector('.who:not(.out)'), tab = document.querySelector('.tabs a[href="/bloc-notes"]');
        if (chip) {
          var c = chip.querySelector('.who-new');
          if (waiting && !c) { c = document.createElement('span'); c.className = 'who-new'; chip.appendChild(c); }
          if (c) { if (waiting) c.textContent = String(waiting); else c.remove(); }
        }
        if (tab) {
          var t = tab.querySelector('.tab-new');
          if (waiting && !t) {
            t = document.createElement('span'); t.className = 'tab-new';
            t.setAttribute('aria-label', 'nouveau bloc-notes partagé');
            tab.appendChild(t);
          }
          if (t && !waiting) t.remove();
        }
      }).catch(function () {});
    };
    setInterval(refresh, 6000);
    document.addEventListener('visibilitychange', function () { if (!document.hidden) refresh(); });
  }

  var form = document.getElementById('np-edit');
  if (!form || !window.fetch || !window.JSON) return;
  var box = document.getElementById('np-text'), status = document.getElementById('np-status'),
      count = document.getElementById('np-count'), conf = document.getElementById('np-conf');
  var pad = form.dataset.pad, me = form.dataset.me, csrf = form.dataset.csrf, rev = +form.dataset.rev;
  var dirty = false, saving = false, again = false, timer = null, conflict = null, gone = false;
  form.classList.add('np-js');
  // opened from a no-JavaScript save that hit a newer version: the box holds the player's text
  if (document.querySelector('.np-ed > .np-conf:not(#np-conf)')) dirty = true;

  function who(by) { return by === me ? 'vous' : by; }
  function say(text, cls) {
    status.textContent = '';
    var s = document.createElement('span');
    if (cls) s.className = cls;
    s.textContent = text;
    status.appendChild(s);
  }
  function shown(st) {
    rev = st.rev;
    if (st.by) say('Enregistré. Modifié par ' + who(st.by) + ' à ' + hhmm(st.at) + '.', 'ok');
    else say('Rien d\'écrit pour l\'instant.');
  }
  function counter() { count.textContent = box.value.length + ' caractères'; }
  function schedule() { clearTimeout(timer); timer = setTimeout(save, 700); }
  function send(url, body) {
    var opt = {credentials: 'same-origin', cache: 'no-store', headers: {'X-CSRF': csrf}};
    if (body) {
      opt.method = 'POST';
      opt.headers['Content-Type'] = 'application/json';
      opt.body = JSON.stringify(body);
    }
    return fetch(url, opt);
  }
  function lost(code) {
    gone = true;
    box.readOnly = true;
    say(code === 403
      ? 'Vous êtes déconnecté. Votre texte est encore dans la zone : copiez-le, puis reconnectez-vous.'
      : 'Vous ne faites plus partie de ce bloc-notes. Votre texte est encore dans la zone : copiez-le si besoin.',
      'warn');
  }
  function button(label, onclick) {
    var b = document.createElement('button');
    b.type = 'button'; b.className = 'np-btn'; b.textContent = label;
    b.addEventListener('click', onclick);
    return b;
  }
  function showConflict(st) {
    conflict = st;
    conf.textContent = '';
    var t = document.createElement('span'), name = document.createElement('b');
    name.textContent = st.by || 'Quelqu\'un';
    t.appendChild(name);
    t.appendChild(document.createTextNode(' a enregistré une autre version à ' + hhmm(st.at) + ' pendant que vous écriviez.'));
    conf.appendChild(t);
    conf.appendChild(button('Voir sa version', function () {
      box.value = st.text; dirty = false; conflict = null; conf.hidden = true; shown(st); counter();
    }));
    conf.appendChild(button('Garder la mienne', function () {
      rev = st.rev; conflict = null; conf.hidden = true; save();
    }));
    conf.hidden = false;
    say('Vos modifications ne sont pas encore enregistrées : choisissez une version.', 'warn');
  }

  function save() {
    if (conflict || gone || !dirty) return;
    if (saving) { again = true; return; }
    saving = true; again = false;
    var text = box.value;
    say('Enregistrement en cours');
    send('/bloc-notes/' + pad + '/texte', {text: text, base_rev: rev}).then(function (r) {
      if (r.status === 409) return r.json().then(showConflict);
      if (r.status === 403 || r.status === 404) return lost(r.status);
      if (r.status === 413) return say('Trop long : le bloc-notes est limité à 20 000 caractères.', 'warn');
      if (!r.ok) throw new Error(String(r.status));
      return r.json().then(function (st) {
        if (box.value === text) dirty = false;
        shown(st);
        if (dirty) schedule();
      });
    }).catch(function () {
      say('Pas encore enregistré : le hub ne répond pas. Nouvel essai dans quelques secondes.', 'warn');
      setTimeout(save, 4000);
    }).then(function () {
      saving = false;
      if (again) save();
    });
  }

  function poll() {
    if (document.hidden || saving || conflict || gone) return;
    send('/bloc-notes/' + pad + '/etat').then(function (r) {
      if (r.status === 403 || r.status === 404) { lost(r.status); return null; }
      return r.ok ? r.json() : null;
    }).then(function (st) {
      if (!st || st.rev <= rev || saving || conflict) return;
      if (dirty) return;                       // the next save gets the other version (409)
      var focused = document.activeElement === box, a = box.selectionStart, b = box.selectionEnd;
      box.value = st.text;
      if (focused) box.setSelectionRange(Math.min(a, box.value.length), Math.min(b, box.value.length));
      shown(st); counter();
    }).catch(function () {});
  }

  box.addEventListener('input', function () {
    if (gone) return;
    dirty = true; counter();
    if (!conflict) say('Modifications non enregistrées');
    schedule();
  });
  box.addEventListener('blur', function () { if (dirty) { clearTimeout(timer); save(); } });
  form.addEventListener('submit', function (e) { e.preventDefault(); clearTimeout(timer); dirty = true; save(); });
  document.addEventListener('visibilitychange', function () {
    if (document.hidden && dirty) { clearTimeout(timer); save(); }
    else if (!document.hidden) poll();
  });
  window.addEventListener('beforeunload', function (e) {
    if (dirty || conflict) { e.preventDefault(); e.returnValue = ''; }
  });
  setInterval(poll, 5000);
})();
