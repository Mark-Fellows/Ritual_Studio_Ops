/* cleansweep-widget.js  v1.0.0  (27 Oct 2026)
   Shared CleanSweep designation widget. Identical copies live in:
     Ritual_CleanSweep/app/cleansweep-widget.js   (CleanSweep -> Settings tab)
     Ritual_Studio_Ops/app/cleansweep-widget.js   (Portal user management; Teacher Portal v2 shortcut)
   Keep the two copies identical. It talks only to the Supabase Edge Function "cleansweep-admin",
   which checks that the caller is a portal administrator or a CleanSweep administrator.

   Usage:
     CleanSweepWidget.mount(element, {
       fnUrl:     'https://<project>.supabase.co/functions/v1/cleansweep-admin',
       apikey:    '<anon key>',
       getToken:  function () { return accessTokenOrPromise; },
       selfEmail: 'signed-in user email',          // hides "Remove" on your own row
       defaultVenue: 'Palm Beach',                 // optional
       prefill:   { email, first_name, last_name, teacher_id },   // optional: skip search
       showList:  true,                            // optional, default true (false when prefill)
       onSaved:   function (result) {}             // optional
     });
*/
(function () {
  'use strict';
  if (window.CleanSweepWidget) return;

  var ROLES = [['cleaner', 'Cleaner'], ['administrator', 'Administrator']];
  var VENUES = ['Palm Beach', 'Robina'];
  var uid = 0;

  var CSS = [
    '.csw{--csw-accent:#B8975A;--csw-accent-text:#fff;--csw-line:rgba(128,128,128,.38);color:inherit;font:inherit}',
    '.csw *{box-sizing:border-box}',
    '.csw-hidden{display:none!important}',
    '.csw-label{display:block;font-size:12px;font-weight:600;margin:10px 0 4px;opacity:.85}',
    '.csw-input{display:block;width:100%;font:inherit;font-size:14px;padding:8px 10px;border:1px solid var(--csw-line);border-radius:8px;background:transparent;color:inherit;margin:0}',
    '.csw-input:focus{outline:2px solid var(--csw-accent);outline-offset:1px}',
    'select.csw-input option{color:#2C2118;background:#fff}',
    '.csw-hint{font-size:12px;opacity:.72;margin-top:4px}',
    '.csw-results{margin-top:8px;display:flex;flex-direction:column;gap:6px;max-height:300px;overflow-y:auto}',
    '.csw-result{display:block;width:100%;text-align:left;font:inherit;font-size:14px;padding:8px 10px;border:1px solid var(--csw-line);border-radius:8px;background:transparent;color:inherit;cursor:pointer}',
    '.csw-result:hover,.csw-result:focus{border-color:var(--csw-accent);outline:none}',
    '.csw-sub{font-size:12px;opacity:.75;word-break:break-all}',
    '.csw-badge{display:inline-block;font-size:11px;line-height:1.5;padding:0 7px;border-radius:999px;border:1px solid var(--csw-line);margin:4px 4px 0 0;white-space:nowrap}',
    '.csw-badge.csw-k{border-color:var(--csw-accent)}',
    '.csw-linkbtn{background:none;border:0;padding:0;margin-top:10px;font:inherit;font-size:13px;color:var(--csw-accent);cursor:pointer;text-decoration:underline}',
    '.csw-row2{display:grid;grid-template-columns:1fr 1fr;gap:10px}',
    '@media (max-width:480px){.csw-row2{grid-template-columns:1fr}}',
    '.csw-person{padding:10px;border:1px solid var(--csw-line);border-radius:8px;margin-top:6px;font-size:14px}',
    '.csw-check{display:flex;align-items:center;gap:8px;margin-top:12px;font-size:14px;cursor:pointer}',
    '.csw-check input{width:16px;height:16px;margin:0;accent-color:var(--csw-accent)}',
    '.csw-actions{display:flex;gap:8px;justify-content:flex-end;margin-top:14px;flex-wrap:wrap}',
    '.csw-btn{font:inherit;font-size:14px;padding:8px 14px;border-radius:8px;border:1px solid var(--csw-line);background:transparent;color:inherit;cursor:pointer;margin:0}',
    '.csw-btn:disabled{opacity:.5;cursor:default}',
    '.csw-primary{background:var(--csw-accent);border-color:var(--csw-accent);color:var(--csw-accent-text)}',
    '.csw-small{font-size:12px;padding:3px 9px}',
    '.csw-steps{list-style:none;margin:12px 0 0;padding:0;font-size:13px}',
    '.csw-steps li{padding:3px 0}',
    '.csw-msg{font-size:13px;line-height:1.45}',
    '.csw-msg:not(:empty){padding:8px 10px;margin-bottom:10px;border:1px solid var(--csw-line);border-left-width:4px;border-radius:8px}',
    '.csw-msg.csw-err{border-left-color:#A4483A}',
    '.csw-msg.csw-ok{border-left-color:#7A8C6E}',
    '.csw-section{font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.06em;opacity:.8;margin:18px 0 6px;padding-bottom:4px;border-bottom:1px solid var(--csw-line)}',
    '.csw-tablewrap{overflow-x:auto}',
    '.csw-table{width:100%;border-collapse:collapse;font-size:13px}',
    '.csw-table th,.csw-table td{text-align:left;padding:6px;border-bottom:1px solid var(--csw-line);vertical-align:top}',
    '.csw-table td.csw-acts{white-space:nowrap;text-align:right}',
    '@media (max-width:560px){.csw-table thead{display:none}.csw-table tr{display:block;padding:6px 0;border-bottom:1px solid var(--csw-line)}' +
      '.csw-table td{display:inline-block;border:0;padding:2px 10px 2px 0}.csw-table td:first-child{display:block}' +
      '.csw-table td.csw-acts{display:block;text-align:left;padding-top:4px}.csw-table td[data-l]::before{content:attr(data-l) ": ";opacity:.7}}'
  ].join('\n');

  function injectCss() {
    if (document.getElementById('csw-style')) return;
    var s = document.createElement('style');
    s.id = 'csw-style';
    s.textContent = CSS;
    document.head.appendChild(s);
  }
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function fullName(p) { return [p.first_name, p.last_name].filter(Boolean).join(' '); }
  function opt(list, sel) {
    return list.map(function (o) {
      var v = Array.isArray(o) ? o[0] : o, l = Array.isArray(o) ? o[1] : o;
      return '<option value="' + esc(v) + '"' + (v === sel ? ' selected' : '') + '>' + esc(l) + '</option>';
    }).join('');
  }
  function badges(p) {
    var b = [];
    (p.sources || []).forEach(function (s) {
      if (s === 'portal') b.push('Portal' + (p.portal_role ? ': ' + p.portal_role : ''));
      if (s === 'teacher') b.push('Teacher');
      if (s === 'momence') b.push('Momence customer');
    });
    if (p.cleansweep_role) b.push('CleanSweep: ' + p.cleansweep_role + (p.cleansweep_venue ? ', ' + p.cleansweep_venue : ''));
    var html = b.map(function (t) { return '<span class="csw-badge">' + esc(t) + '</span>'; }).join('');
    if (p.karma_tagged) html += '<span class="csw-badge csw-k">Karma Yogi tag</span>';
    return html;
  }
  var TAG_TEXT = { tagged: 'Tagged', done: 'Tagged', pending: 'Queued', failed: 'Failed', skipped: 'Skipped' };

  function mount(root, opts) {
    injectCss();
    opts = opts || {};
    var id = 'csw' + (++uid);
    var showList = opts.showList !== undefined ? !!opts.showList : !opts.prefill;
    var defaultVenue = VENUES.indexOf(opts.defaultVenue) >= 0 ? opts.defaultVenue : VENUES[0];
    var selfEmail = String(opts.selfEmail || '').toLowerCase();
    var state = { person: null, manual: false, timer: null, seq: 0 };

    root.innerHTML =
      '<div class="csw">' +
      '<div class="csw-msg" role="status" aria-live="polite"></div>' +
      '<div class="csw-find">' +
      '<label class="csw-label" for="' + id + '-q">Find a person</label>' +
      '<input class="csw-input csw-q" id="' + id + '-q" type="search" autocomplete="off" placeholder="Name or email, at least 3 letters">' +
      '<div class="csw-hint">Searches portal users, active teachers and Momence customers.</div>' +
      '<div class="csw-results"></div>' +
      '<button type="button" class="csw-linkbtn csw-manual-toggle">Not listed? Enter details by hand</button>' +
      '<div class="csw-manual csw-hidden">' +
      '<div class="csw-row2"><div><label class="csw-label" for="' + id + '-mf">First name</label><input class="csw-input csw-m-first" id="' + id + '-mf" autocomplete="off"></div>' +
      '<div><label class="csw-label" for="' + id + '-ml">Last name</label><input class="csw-input csw-m-last" id="' + id + '-ml" autocomplete="off"></div></div>' +
      '<label class="csw-label" for="' + id + '-me">Email</label><input class="csw-input csw-m-email" id="' + id + '-me" type="email" autocomplete="off">' +
      '<div class="csw-actions"><button type="button" class="csw-btn csw-m-go">Continue</button></div>' +
      '</div>' +
      '</div>' +
      '<div class="csw-form csw-hidden">' +
      '<div class="csw-person"></div>' +
      '<div class="csw-row2">' +
      '<div><label class="csw-label" for="' + id + '-r">CleanSweep role</label><select class="csw-input csw-role" id="' + id + '-r">' + opt(ROLES, 'cleaner') + '</select></div>' +
      '<div><label class="csw-label" for="' + id + '-v">Venue</label><select class="csw-input csw-venue" id="' + id + '-v">' + opt(VENUES, defaultVenue) + '</select></div>' +
      '</div>' +
      '<label class="csw-check csw-karma-row"><input type="checkbox" class="csw-karma" checked> Tag as Karma Yogi in Momence</label>' +
      '<div class="csw-hint csw-karma-hint"></div>' +
      '<div class="csw-actions"><button type="button" class="csw-btn csw-cancel">Cancel</button>' +
      '<button type="button" class="csw-btn csw-primary csw-save">Save</button></div>' +
      '<ul class="csw-steps"></ul>' +
      '</div>' +
      '<div class="csw-listwrap' + (showList ? '' : ' csw-hidden') + '">' +
      '<div class="csw-section">Current CleanSweep users</div>' +
      '<div class="csw-tablewrap"><table class="csw-table"><thead><tr><th>Name</th><th>Role</th><th>Venue</th><th>Karma Yogi tag</th><th></th></tr></thead>' +
      '<tbody class="csw-list"><tr><td colspan="5" class="csw-sub">Loading…</td></tr></tbody></table></div>' +
      '</div>' +
      '</div>';

    function $(sel) { return root.querySelector(sel); }
    var $msg = $('.csw-msg'), $find = $('.csw-find'), $q = $('.csw-q'), $results = $('.csw-results');
    var $manual = $('.csw-manual'), $form = $('.csw-form'), $person = $('.csw-person');
    var $role = $('.csw-role'), $venue = $('.csw-venue'), $karma = $('.csw-karma');
    var $karmaRow = $('.csw-karma-row'), $karmaHint = $('.csw-karma-hint'), $save = $('.csw-save');
    var $steps = $('.csw-steps'), $list = $('.csw-list');

    function msg(text, ok) {
      $msg.className = 'csw-msg' + (text ? (ok ? ' csw-ok' : ' csw-err') : '');
      $msg.textContent = text || '';
    }

    function call(action, payload) {
      return Promise.resolve(opts.getToken ? opts.getToken() : null).then(function (tok) {
        if (!tok) throw new Error('Your session has expired. Sign in again.');
        return fetch(opts.fnUrl, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', apikey: opts.apikey, Authorization: 'Bearer ' + tok },
          body: JSON.stringify(Object.assign({ action: action }, payload || {}))
        });
      }).then(function (r) {
        return r.json().catch(function () { return {}; }).then(function (d) {
          if (!r.ok || d.error) throw new Error(d.error || ('Request failed (HTTP ' + r.status + ')'));
          return d;
        });
      });
    }

    // ---- search ------------------------------------------------------------------
    function runSearch() {
      var q = $q.value.trim();
      var seq = ++state.seq;
      if (q.length < 3) { $results.innerHTML = ''; return; }
      $results.innerHTML = '<div class="csw-sub">Searching…</div>';
      call('search', { q: q }).then(function (d) {
        if (seq !== state.seq) return;
        var rows = d.results || [];
        if (!rows.length) { $results.innerHTML = '<div class="csw-sub">No one found. Check the spelling, or enter details by hand.</div>'; return; }
        $results.innerHTML = rows.map(function (r, i) {
          return '<button type="button" class="csw-result" data-i="' + i + '"><div>' + esc(fullName(r) || r.email) + '</div>' +
            '<div class="csw-sub">' + esc(r.email) + '</div><div>' + badges(r) + '</div></button>';
        }).join('');
        Array.prototype.forEach.call($results.querySelectorAll('.csw-result'), function (b) {
          b.addEventListener('click', function () { choose(rows[+b.getAttribute('data-i')], false); });
        });
      }).catch(function (e) { if (seq === state.seq) { $results.innerHTML = ''; msg(e.message, false); } });
    }
    $q.addEventListener('input', function () { clearTimeout(state.timer); state.timer = setTimeout(runSearch, 300); });

    $('.csw-manual-toggle').addEventListener('click', function () { $manual.classList.toggle('csw-hidden'); });
    $('.csw-m-go').addEventListener('click', function () {
      var email = $('.csw-m-email').value.trim().toLowerCase();
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) { msg('Enter a valid email address.', false); return; }
      choose({ email: email, first_name: $('.csw-m-first').value.trim(), last_name: $('.csw-m-last').value.trim(), sources: [] }, true);
    });

    // ---- form --------------------------------------------------------------------
    function syncKarma() {
      var p = state.person || {};
      var cleaner = $role.value === 'cleaner';
      $karmaRow.classList.toggle('csw-hidden', !cleaner);
      $karmaHint.classList.toggle('csw-hidden', !cleaner);
      if (p.karma_tagged) {
        $karma.checked = true; $karma.disabled = true;
        $karmaHint.textContent = 'Already tagged in Momence.';
      } else {
        $karma.disabled = false;
        $karmaHint.textContent = state.manual
          ? 'Applied at the next Momence run on Mark’s PC. If no Momence customer has this email, one is created.'
          : ((p.sources || []).indexOf('momence') < 0
            ? 'Applied at the next Momence run on Mark’s PC, if a Momence customer has this email.'
            : 'Applied at the next Momence run on Mark’s PC.');
      }
    }
    $role.addEventListener('change', syncKarma);

    function choose(p, manual) {
      state.person = p; state.manual = !!manual;
      msg('');
      $steps.innerHTML = '';
      $person.innerHTML = '<strong>' + esc(fullName(p) || p.email) + '</strong><div class="csw-sub">' + esc(p.email) + '</div><div>' + badges(p) + '</div>';
      $role.value = p.cleansweep_role || 'cleaner';
      $venue.value = p.cleansweep_venue || defaultVenue;
      $karma.checked = true;
      syncKarma();
      $find.classList.add('csw-hidden');
      $form.classList.remove('csw-hidden');
      $save.disabled = false;
      $role.focus();
    }

    function resetFind() {
      state.person = null; state.manual = false;
      $form.classList.add('csw-hidden');
      if (!opts.prefill) $find.classList.remove('csw-hidden');
      $q.value = ''; $results.innerHTML = '';
      $manual.classList.add('csw-hidden');
      ['.csw-m-first', '.csw-m-last', '.csw-m-email'].forEach(function (s) { $(s).value = ''; });
    }
    $('.csw-cancel').addEventListener('click', function () { msg(''); $steps.innerHTML = ''; resetFind(); if (opts.onCancel) opts.onCancel(); });

    $save.addEventListener('click', function () {
      var p = state.person;
      if (!p) return;
      var role = $role.value;
      $save.disabled = true;
      msg('Saving…', true);
      call('designate', {
        email: p.email, first_name: p.first_name || '', last_name: p.last_name || '',
        cleansweep_role: role, cleansweep_venue: $venue.value,
        teacher_id: p.teacher_id || null, momence_member_id: p.momence_member_id || null,
        karma_tag: role === 'cleaner' && $karma.checked && !$karma.disabled,
        create_if_missing: state.manual
      }).then(function (d) {
        var name = fullName(p) || p.email;
        msg('Saved. ' + name + ' can now sign in at ritual-cleansweep.lesss.com.au.', true);
        $steps.innerHTML = (d.steps || []).map(function (s) {
          var icon = s.status === 'ok' ? '✓' : (s.status === 'queued' ? '⏳' : '–');
          return '<li>' + icon + ' ' + esc(s.step) + ': ' + esc(s.detail) + '</li>';
        }).join('');
        if (!opts.prefill) {
          var keep = $steps.innerHTML;
          resetFind();
          $steps.innerHTML = '';
          $results.innerHTML = '<ul class="csw-steps">' + keep + '</ul>';
        }
        if (showList) loadList();
        if (opts.onSaved) opts.onSaved(d);
      }).catch(function (e) { msg(e.message, false); $save.disabled = false; });
    });

    // ---- list --------------------------------------------------------------------
    function loadList() {
      call('list').then(function (d) {
        var rows = d.members || [];
        if (!rows.length) { $list.innerHTML = '<tr><td colspan="5" class="csw-sub">No CleanSweep users yet.</td></tr>'; return; }
        $list.innerHTML = rows.map(function (m, i) {
          var tag = m.cleansweep_role === 'cleaner' ? (TAG_TEXT[m.karma_tag] || '—') : '—';
          var title = m.karma_note ? ' title="' + esc(m.karma_note) + '"' : '';
          var self = String(m.email || '').toLowerCase() === selfEmail;
          return '<tr><td>' + esc(fullName(m) || m.email) + '<div class="csw-sub">' + esc(m.email) + '</div></td>' +
            '<td data-l="Role">' + esc(m.cleansweep_role) + '</td><td data-l="Venue">' + esc(m.cleansweep_venue || '') + '</td>' +
            '<td data-l="Karma Yogi tag"' + title + '>' + esc(tag) + '</td>' +
            '<td class="csw-acts"><button type="button" class="csw-btn csw-small csw-edit" data-i="' + i + '">Edit</button>' +
            (self ? '' : ' <button type="button" class="csw-btn csw-small csw-remove" data-i="' + i + '">Remove</button>') + '</td></tr>';
        }).join('');
        Array.prototype.forEach.call($list.querySelectorAll('.csw-edit'), function (b) {
          b.addEventListener('click', function () {
            var m = rows[+b.getAttribute('data-i')];
            choose({ email: m.email, first_name: m.first_name, last_name: m.last_name, cleansweep_role: m.cleansweep_role,
              cleansweep_venue: m.cleansweep_venue, sources: ['portal'], portal_role: m.portal_role,
              karma_tagged: m.karma_tag === 'tagged' || m.karma_tag === 'done' }, false);
            $form.scrollIntoView({ block: 'nearest' });
          });
        });
        Array.prototype.forEach.call($list.querySelectorAll('.csw-remove'), function (b) {
          b.addEventListener('click', function () {
            var m = rows[+b.getAttribute('data-i')];
            var name = fullName(m) || m.email;
            if (!window.confirm('Remove CleanSweep access for ' + name + '?\n\nTheir login and any Momence tag are kept.')) return;
            b.disabled = true;
            call('remove', { user_profile_id: m.id }).then(function () {
              msg('CleanSweep access removed for ' + name + '.', true);
              loadList();
            }).catch(function (e) { msg(e.message, false); b.disabled = false; });
          });
        });
      }).catch(function (e) {
        $list.innerHTML = '<tr><td colspan="5" class="csw-sub">Could not load: ' + esc(e.message) + '</td></tr>';
      });
    }

    if (opts.prefill) {
      choose({
        email: String(opts.prefill.email || '').toLowerCase(), first_name: opts.prefill.first_name,
        last_name: opts.prefill.last_name, teacher_id: opts.prefill.teacher_id || null, sources: ['teacher']
      }, false);
      // Look the person up so existing CleanSweep role, Momence ID and tag status are shown.
      if (opts.prefill.email) {
        call('search', { q: opts.prefill.email }).then(function (d) {
          var hit = (d.results || []).filter(function (r) { return r.email === String(opts.prefill.email).toLowerCase(); })[0];
          if (hit && state.person && state.person.email === hit.email) {
            hit.teacher_id = hit.teacher_id || opts.prefill.teacher_id || null;
            choose(hit, false);
          }
        }).catch(function () { /* the form still works without the lookup */ });
      }
    }
    if (showList) loadList();
    return { reload: loadList, reset: resetFind };
  }

  window.CleanSweepWidget = { mount: mount, version: '1.0.0' };
})();
