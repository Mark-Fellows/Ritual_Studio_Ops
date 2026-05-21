(function () {
  const data = JSON.parse(document.getElementById('payload').textContent);
  const main = document.getElementById('main');
  const metaLine = document.getElementById('meta-line');
  const weekdays = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"];
  const studios = ["Robina","Palm Beach"];

  const settingsKey = 'cover_mgmt_timetable_settings_v2';
  const defaultSettings = {
    show_time: true, show_name: true, show_room: false,
    show_capacity: false, show_teacher: false
  };
  const state = {
    week: data.weeks.length ? data.weeks[0].week_start : null,
    disciplines: new Set(data.distinct_disciplines),
    teacher: 'all',
    settings: Object.assign({}, defaultSettings,
      JSON.parse(localStorage.getItem(settingsKey) || '{}'))
  };

  function render() {
    main.innerHTML = '';
    main.appendChild(buildToolbar());
    const week = data.weeks.find(w => w.week_start === state.week);
    if (!week) {
      const empty = document.createElement('div');
      empty.className = 'empty-state';
      empty.textContent = 'No data for this week.';
      main.appendChild(empty);
      return;
    }
    metaLine.textContent = 'Week of ' + fmtDateLong(week.week_start) + ' to '
      + fmtDateLong(addDays(week.week_start, 6))
      + '   |   generated ' + data.generated_at;

    for (const studio of studios) {
      main.appendChild(buildStudioSection(studio, week));
    }
  }

  function buildToolbar() {
    const tb = document.createElement('div');
    tb.className = 'toolbar';

    // Week-ending selector
    const weekGroup = document.createElement('div');
    weekGroup.className = 'group';
    const weekLabel = document.createElement('label');
    weekLabel.className = 'lbl'; weekLabel.textContent = 'Week ending';
    weekGroup.appendChild(weekLabel);
    const weekSel = document.createElement('select');
    for (const w of data.weeks) {
      const opt = document.createElement('option');
      opt.value = w.week_start;
      opt.textContent = 'Sun ' + fmtDateShort(addDays(w.week_start, 6))
        + '   (' + w.total + ' classes)';
      if (w.week_start === state.week) opt.selected = true;
      weekSel.appendChild(opt);
    }
    weekSel.addEventListener('change', e => { state.week = e.target.value; render(); });
    weekGroup.appendChild(weekSel);
    tb.appendChild(weekGroup);

    // Discipline filter pills
    const discGroup = document.createElement('div');
    discGroup.className = 'group';
    const discLabel = document.createElement('label');
    discLabel.className = 'lbl'; discLabel.textContent = 'Disciplines';
    discGroup.appendChild(discLabel);
    const pills = document.createElement('div'); pills.className = 'pills';
    for (const disc of data.distinct_disciplines) {
      const palette = data.colours[disc] || data.colours['Other'];
      const p = document.createElement('button');
      p.type = 'button';
      p.className = 'pill';
      p.style.background = palette[0]; p.style.color = palette[1];
      p.textContent = disc;
      p.setAttribute('aria-pressed', state.disciplines.has(disc));
      p.addEventListener('click', () => {
        if (state.disciplines.has(disc)) state.disciplines.delete(disc);
        else state.disciplines.add(disc);
        render();
      });
      pills.appendChild(p);
    }
    discGroup.appendChild(pills);
    tb.appendChild(discGroup);

    // Teacher dropdown
    const teachGroup = document.createElement('div');
    teachGroup.className = 'group';
    const teachLabel = document.createElement('label');
    teachLabel.className = 'lbl'; teachLabel.textContent = 'Teacher';
    teachGroup.appendChild(teachLabel);
    const teachSel = document.createElement('select');
    const allOpt = document.createElement('option');
    allOpt.value = 'all'; allOpt.textContent = 'All teachers';
    teachSel.appendChild(allOpt);
    for (const t of data.distinct_teachers) {
      const opt = document.createElement('option');
      opt.value = t; opt.textContent = t;
      teachSel.appendChild(opt);
    }
    teachSel.value = state.teacher;
    teachSel.addEventListener('change', e => { state.teacher = e.target.value; render(); });
    teachGroup.appendChild(teachSel);
    tb.appendChild(teachGroup);

    // Settings cog
    const gear = document.createElement('button');
    gear.className = 'gear-btn';
    gear.title = 'Display options';
    gear.textContent = '⚙';
    const panel = document.createElement('div');
    panel.className = 'settings-panel';
    const opts = [
      ['show_time', 'Time'],
      ['show_name', 'Class name'],
      ['show_room', 'Room'],
      ['show_capacity', 'Bookings / capacity'],
      ['show_teacher', 'Teacher']
    ];
    for (const optEntry of opts) {
      const key = optEntry[0], label = optEntry[1];
      const lab = document.createElement('label');
      const cb = document.createElement('input');
      cb.type = 'checkbox'; cb.checked = state.settings[key];
      cb.addEventListener('change', () => {
        state.settings[key] = cb.checked;
        localStorage.setItem(settingsKey, JSON.stringify(state.settings));
        render();
      });
      lab.appendChild(cb);
      lab.appendChild(document.createTextNode(' ' + label));
      panel.appendChild(lab);
    }
    gear.addEventListener('click', () => panel.classList.toggle('open'));
    tb.appendChild(gear);
    tb.appendChild(panel);

    return tb;
  }

  function classMatchesFilters(cls) {
    if (!state.disciplines.has(cls.discipline)) return false;
    if (state.teacher !== 'all' && cls.teacher !== state.teacher) return false;
    return true;
  }

  function buildStudioSection(studio, week) {
    const sec = document.createElement('section');
    sec.className = 'studio';

    const studioClasses = (week.classes || [])
      .filter(c => c.studio === studio && classMatchesFilters(c));

    const h2 = document.createElement('h2');
    h2.innerHTML = studio + ' <span class="stats">' + studioClasses.length
      + ' class' + (studioClasses.length === 1 ? '' : 'es') + ' shown</span>';
    sec.appendChild(h2);

    if (!studioClasses.length) {
      const empty = document.createElement('div');
      empty.className = 'empty-state';
      empty.textContent = 'No classes match the current filters.';
      sec.appendChild(empty);
      return sec;
    }

    // Compute occupied time segments. Two clusters separated by >= 90 min
    // of empty time render as separate stacked grids so dead bands collapse.
    const segments = computeSegments(studioClasses, 90, 30);

    for (let i = 0; i < segments.length; i++) {
      const seg = segments[i];
      const segClasses = studioClasses.filter(c =>
        c.start_minutes >= seg.startMin && c.start_minutes < seg.endMin
      );
      sec.appendChild(buildCalendarGrid(week, seg.startMin, seg.endMin, segClasses));
      if (i < segments.length - 1) {
        const next = segments[i + 1];
        const gapHrs = Math.round((next.startMin - seg.endMin) / 60 * 10) / 10;
        const gap = document.createElement('div');
        gap.className = 'time-gap';
        gap.textContent = '— ' + fmtTime(seg.endMin) + ' to '
          + fmtTime(next.startMin) + ' (' + gapHrs + ' h, no classes) —';
        sec.appendChild(gap);
      }
    }
    return sec;
  }

  function computeSegments(classes, gapThreshold, padMin) {
    if (!classes.length) return [];
    const sorted = [...classes].sort((a, b) => a.start_minutes - b.start_minutes);
    const segs = [];
    let segStart = sorted[0].start_minutes - padMin;
    let segEnd = sorted[0].start_minutes + sorted[0].duration_minutes;
    for (let i = 1; i < sorted.length; i++) {
      const cls = sorted[i];
      if (cls.start_minutes - segEnd >= gapThreshold) {
        segs.push({
          startMin: Math.max(300, segStart),
          endMin:   Math.min(1260, segEnd + padMin)
        });
        segStart = cls.start_minutes - padMin;
        segEnd = cls.start_minutes + cls.duration_minutes;
      } else {
        segEnd = Math.max(segEnd, cls.start_minutes + cls.duration_minutes);
      }
    }
    segs.push({
      startMin: Math.max(300, segStart),
      endMin:   Math.min(1260, segEnd + padMin)
    });
    return segs;
  }

  function buildCalendarGrid(week, startMin, endMin, classes) {
    const pxPerMin = 1.1;
    const totalHeight = (endMin - startMin) * pxPerMin;

    const cal = document.createElement('div');
    cal.className = 'calendar';

    const corner = document.createElement('div');
    corner.className = 'corner'; cal.appendChild(corner);
    for (const wd of weekdays) {
      const dh = document.createElement('div');
      dh.className = 'day-header';
      const dayDate = addDays(week.week_start, weekdays.indexOf(wd));
      dh.innerHTML = wd + '<br><span style="font-weight:400;font-size:11px;color:var(--fg-muted)">'
        + fmtDateShort(dayDate) + '</span>';
      cal.appendChild(dh);
    }

    const ta = document.createElement('div');
    ta.className = 'time-axis';
    ta.style.height = totalHeight + 'px';
    const firstTick = Math.ceil(startMin / 60) * 60;
    for (let m = firstTick; m <= endMin; m += 60) {
      const tick = document.createElement('div');
      tick.className = 'time-axis-tick';
      tick.style.top = ((m - startMin) * pxPerMin) + 'px';
      tick.textContent = fmtTime(m);
      ta.appendChild(tick);
    }
    cal.appendChild(ta);

    const dayBuckets = {};
    for (const wd of weekdays) dayBuckets[wd] = [];
    for (const cls of classes) dayBuckets[cls.weekday].push(cls);

    for (const wd of weekdays) {
      const col = document.createElement('div');
      col.className = 'day-col';
      col.style.height = totalHeight + 'px';
      for (let m = firstTick; m < endMin; m += 60) {
        const ln = document.createElement('div');
        ln.className = 'hour-line';
        ln.style.top = ((m - startMin) * pxPerMin) + 'px';
        col.appendChild(ln);
      }
      dayBuckets[wd].sort((a, b) => a.start_minutes - b.start_minutes);
      for (const cls of dayBuckets[wd]) {
        col.appendChild(buildClassBlock(cls, startMin, pxPerMin));
      }
      cal.appendChild(col);
    }

    return cal;
  }

  function buildClassBlock(cls, startMin, pxPerMin) {
    const palette = data.colours[cls.discipline] || data.colours['Other'];
    const block = document.createElement('div');
    block.className = 'class-block';
    block.style.background = palette[0];
    block.style.color = palette[1];
    block.style.borderLeftColor = palette[1];
    block.style.top = ((cls.start_minutes - startMin) * pxPerMin) + 'px';
    block.style.height = Math.max(28, cls.duration_minutes * pxPerMin - 2) + 'px';

    const lines = [];
    if (state.settings.show_time) {
      lines.push('<span class="cb-time">' + cls.start + '-' + cls.end + '</span>');
    }
    if (state.settings.show_name) {
      lines.push('<span class="cb-name">' + escapeHtml(cls.name) + '</span>');
    }
    if (state.settings.show_room && cls.room) {
      lines.push('<span class="cb-room">' + escapeHtml(cls.room) + '</span>');
    }
    if (state.settings.show_capacity && cls.capacity) {
      lines.push('<span class="cb-cap">' + (cls.signups || '?') + '/' + cls.capacity + '</span>');
    }
    if (state.settings.show_teacher && cls.teacher) {
      lines.push('<span class="cb-teacher">' + escapeHtml(cls.teacher) + '</span>');
    }
    block.innerHTML = lines.join(' ');
    block.title = cls.start + '-' + cls.end + '  ' + cls.name
      + (cls.location ? '  @ ' + cls.location : '')
      + (cls.teacher ? '  (' + cls.teacher + ')' : '');
    return block;
  }

  function addDays(iso, n) {
    const d = new Date(iso + 'T00:00:00');
    d.setDate(d.getDate() + n);
    return d.toISOString().slice(0, 10);
  }
  function fmtDateShort(iso) {
    const d = new Date(iso + 'T00:00:00');
    return d.getDate() + ' ' + d.toLocaleString('en-GB', {month: 'short'});
  }
  function fmtDateLong(iso) {
    const d = new Date(iso + 'T00:00:00');
    return d.toLocaleString('en-GB',
      {weekday: 'short', day: 'numeric', month: 'short', year: 'numeric'});
  }
  function fmtTime(m) {
    const h = Math.floor(m / 60);
    const min = m % 60;
    return (h % 12 || 12) + (min ? ':' + String(min).padStart(2, '0') : '')
      + (h < 12 ? 'am' : 'pm');
  }
  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, function(c) {
      return ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[c];
    });
  }

  render();
})();
