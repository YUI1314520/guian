/* =====================================================================
   归岸 · 应用逻辑
   纯前端 / 无依赖 / localStorage 持久化 / 离线优先
   结构：工具函数 → 数据层 → 计算 → 渲染 → 交互 → 启动
   ===================================================================== */
(() => {
  'use strict';

  /* ---------------- 常量 ---------------- */
  const STORAGE_KEY = 'guian.v1';

  const MILESTONES = [
    { days: 1, name: '起岸' },
    { days: 3, name: '破土' },
    { days: 7, name: '一周' },
    { days: 14, name: '扎根' },
    { days: 21, name: '习惯' },
    { days: 30, name: '一个月' },
    { days: 45, name: '稳定' },
    { days: 60, name: '两个月' },
    { days: 90, name: '重写' },
    { days: 120, name: '自由' },
    { days: 180, name: '半年' },
    { days: 365, name: '一年' },
  ];

  const QUOTES = [
    '你不是在戒掉什么，你是在把自己还给自己。',
    '冲动像浪，会来，也会退。',
    '今天只做今天的事。',
    '复发不是回到原点，是带着经验重来。',
    '身体需要时间，你也需要。',
    '把注意力放回呼吸上，十次就够。',
    '你不是你的冲动。',
    '慢一点，稳一点，久一点。',
    '一个人的夜晚，也可以很安静。',
    '你已经在路上了。',
    '不用向谁证明，只要对自己诚实。',
    '休息不是放弃，是继续的一部分。',
    '每一次忍住，都会留下一点力气。',
    '明天还会来，你也会。',
  ];

  const ACTIONS = [
    { id: 'breath', icon: 'i-breath', title: '做 10 次深呼吸', desc: '把节奏放慢，让身体先安静下来' },
    { id: 'leave', icon: 'i-timer', title: '离开屏幕 5 分钟', desc: '去倒杯水，或者站到窗边' },
    { id: 'squat', icon: 'i-fire', title: '做 20 个深蹲', desc: '把冲动变成身体的用力' },
    { id: 'friend', icon: 'i-user', title: '给一个人发条消息', desc: '不用提这件事，聊点别的就好' },
    { id: 'cold', icon: 'i-shield', title: '用冷水洗把脸', desc: '温度变化会打断那个循环' },
  ];

  const TRIGGERS = ['无聊', '压力', '失眠', '孤独', '刷到内容', '说不清'];
  const WEEKDAYS = ['日', '一', '二', '三', '四', '五', '六'];

  /* ---------------- 工具 ---------------- */
  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

  const pad = (n) => String(n).padStart(2, '0');
  const dayKey = (d = new Date()) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
  const parseKey = (k) => {
    const [y, m, d] = k.split('-').map(Number);
    return new Date(y, m - 1, d);
  };
  const addDays = (d, n) => {
    const x = new Date(d.getFullYear(), d.getMonth(), d.getDate());
    x.setDate(x.getDate() + n);
    return x;
  };
  const dayDiff = (a, b) => Math.round((parseKey(a) - parseKey(b)) / 86400000);
  const fmtDate = (k) => {
    const d = parseKey(k);
    return `${d.getMonth() + 1} 月 ${d.getDate()} 日`;
  };
  const fmtFull = (k) => {
    const d = parseKey(k);
    return `${d.getFullYear()} 年 ${d.getMonth() + 1} 月 ${d.getDate()} 日`;
  };
  const fmtStamp = (ts) => {
    const d = new Date(ts);
    return `${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
  };
  const clamp = (n, a, b) => Math.min(b, Math.max(a, n));

  /* ---------------- 数据层 ---------------- */
  const params = new URLSearchParams(location.search);
  const DEMO = params.get('demo') === '1';
  const START_VIEW = params.get('view') || 'today';

  const defaultState = () => ({
    v: 1,
    onboarded: false,
    startDate: dayKey(),
    goalDays: 90,
    checkins: {},
    relapses: [],
    notes: [],
    timer: null,
    actions: null,
    settings: { theme: 'auto' },
    created: Date.now(),
  });

  let state = loadState();

  function demoState() {
    const s = defaultState();
    s.onboarded = true;
    s.goalDays = 90;
    const today = new Date();
    s.startDate = dayKey(addDays(today, -39));
    // 一段 26 天的记录，之后一次重启，再连续 12 天到今天
    for (let i = 39; i >= 14; i--) s.checkins[dayKey(addDays(today, -i))] = true;
    s.relapses.push({ d: dayKey(addDays(today, -13)), reason: '压力', ts: Date.now() - 13 * 86400000 });
    for (let i = 12; i >= 1; i--) s.checkins[dayKey(addDays(today, -i))] = true;
    s.notes = [
      { ts: Date.now() - 3600_000 * 5, text: '晚上一个人，刷到了不该看的东西。关掉手机，去洗了把脸。' },
      { ts: Date.now() - 86400_000 * 4, text: '今天很累，但还是在十一点前睡了。' },
    ];
    return s;
  }

  function loadState() {
    if (DEMO) return demoState();
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return defaultState();
      const parsed = JSON.parse(raw);
      return normalize(parsed);
    } catch (err) {
      console.warn('读取本地数据失败，使用空白档案', err);
      return defaultState();
    }
  }

  function normalize(data) {
    const base = defaultState();
    if (!data || typeof data !== 'object') return base;
    const s = { ...base, ...data };
    s.settings = { ...base.settings, ...(data.settings || {}) };
    s.checkins = data.checkins && typeof data.checkins === 'object' ? data.checkins : {};
    s.relapses = Array.isArray(data.relapses) ? data.relapses.filter((r) => r && r.d) : [];
    s.notes = Array.isArray(data.notes) ? data.notes.filter((n) => n && typeof n.text === 'string') : [];
    s.goalDays = [30, 60, 90, 120, 180, 365, 1000].includes(Number(data.goalDays)) ? Number(data.goalDays) : 90;
    if (!/^\d{4}-\d{2}-\d{2}$/.test(s.startDate)) s.startDate = dayKey();
    return s;
  }

  let saveWarned = false;
  function save() {
    if (DEMO) return; // 演示模式不写入本地
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch (err) {
      console.warn('保存失败', err);
      if (!saveWarned) {
        saveWarned = true;
        snack('存储空间不足，数据没有保存成功', null);
      }
    }
  }

  /* ---------------- 派生数据 ---------------- */
  const todayKey = () => dayKey();

  function isChecked(k) {
    return Boolean(state.checkins[k]);
  }

  const relapseSet = () => new Set(state.relapses.map((r) => r.d));

  function counts() {
    const checked = Object.keys(state.checkins).filter((k) => state.checkins[k]);
    return {
      total: checked.length,
      best: bestStreak(),
      restarts: state.relapses.length,
    };
  }

  /** 当前连续天数：从今天（未打卡则从昨天）往回数，遇到空档或上一次复发日停止 */
  function currentStreak() {
    const relapses = relapseSet();
    const lastRelapse = relapses.size ? [...relapses].sort().pop() : null;
    let d = new Date();
    let streak = 0;
    if (!isChecked(dayKey(d))) d = addDays(d, -1);
    for (let i = 0; i < 5000; i++) {
      const k = dayKey(d);
      if (lastRelapse && k < lastRelapse) break;
      if (lastRelapse && k === lastRelapse) {
        // 复发当天也打了卡：只在它是新链条起点时算作第一天
        if (streak === 0 && isChecked(k)) streak = 1;
        break;
      }
      if (!isChecked(k)) break;
      streak += 1;
      d = addDays(d, -1);
    }
    return streak;
  }

  /** 历史最长连续：遍历全部打卡日，复发日截断链条 */
  function bestStreak() {
    const relapses = relapseSet();
    const days = Object.keys(state.checkins)
      .filter((k) => state.checkins[k])
      .sort();
    let best = 0;
    let run = 0;
    let prev = null;
    for (const k of days) {
      if (relapses.has(k)) {
        run = 1; // 复发当天的打卡视为新链条的第 1 天
      } else if (prev && dayDiff(k, prev) === 1) {
        run += 1;
      } else {
        run = 1;
      }
      best = Math.max(best, run);
      prev = k;
    }
    return best;
  }

  function nextMilestone(streak) {
    return MILESTONES.find((m) => m.days > streak) || MILESTONES[MILESTONES.length - 1];
  }

  function milestoneProgress(streak) {
    const next = nextMilestone(streak);
    const idx = MILESTONES.indexOf(next);
    const prev = idx > 0 ? MILESTONES[idx - 1].days : 0;
    if (streak >= next.days) return 100;
    return clamp(Math.round(((streak - prev) / (next.days - prev)) * 100), 0, 100);
  }

  /* ---------------- 主题 ---------------- */
  const mq = window.matchMedia('(prefers-color-scheme: dark)');

  function applyTheme() {
    const mode = state.settings.theme || 'auto';
    const dark = mode === 'dark' || (mode === 'auto' && mq.matches);
    document.documentElement.dataset.theme = dark ? 'dark' : 'light';
    const meta = $('meta[name="theme-color"]');
    if (meta) meta.content = dark ? '#0D1512' : '#F5FBF6';
    // Android 外壳：把状态栏/导航栏颜色一起切过去（浏览器里没有这个对象，直接跳过）
    if (window.AndroidChrome && window.AndroidChrome.setChrome) {
      try { window.AndroidChrome.setChrome(dark ? '#0D1512' : '#F5FBF6', dark); } catch (e) {}
    }
    const icon = $('#theme-icon use');
    if (icon) icon.setAttribute('href', dark ? '#i-sun' : '#i-moon');
    const btn = $('#theme-btn');
    if (btn) btn.setAttribute('aria-label', dark ? '切换到浅色' : '切换到深色');
    $$('#theme-seg button').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.mode === mode)));
  }

  mq.addEventListener('change', () => {
    if ((state.settings.theme || 'auto') === 'auto') applyTheme();
  });

  /* ---------------- 渲染：今日 ---------------- */
  function greeting() {
    const h = new Date().getHours();
    if (h < 5) return '夜深了';
    if (h < 11) return '早上好';
    if (h < 14) return '中午好';
    if (h < 18) return '下午好';
    return '晚上好';
  }

  function renderToday() {
    const streak = currentStreak();
    const c = counts();
    const checked = isChecked(todayKey());
    const relapses = relapseSet();
    const restartedToday = relapses.has(todayKey());

    $('#today-eyebrow').textContent = `${greeting()} · ${fmtDate(todayKey())} 周${WEEKDAYS[new Date().getDay()]}`;
    $('#streak-num').textContent = String(streak);
    $('#streak-sub').textContent = `连续打卡 · 最长 ${c.best} 天`;

    const btn = $('#check-btn');
    btn.classList.toggle('is-checked', checked);
    btn.setAttribute('aria-pressed', String(checked));
    $('#check-label').textContent = checked ? '已完成' : '打卡';
    $('#check-hint').textContent = checked
      ? restartedToday
        ? '今天重新开始 · 明天继续'
        : `第 ${streak} 天已留下 · 明天见`
      : restartedToday
        ? '今天重新开始，点亮这一格'
        : '点一下，把今天留下';

    btn.style.setProperty('--p', String(milestoneProgress(streak)));

    $('#stat-total').textContent = String(c.total);
    $('#stat-best').textContent = String(c.best);
    $('#stat-restart').textContent = String(c.restarts);

    const next = nextMilestone(streak);
    const reached = MILESTONES[MILESTONES.length - 1].days <= streak;
    $('#next-badge').textContent = reached ? '抵达' : next.name;
    $('#milestone-fill').style.width = `${milestoneProgress(streak)}%`;
    const bar = $('#milestone-bar');
    bar.setAttribute('aria-valuenow', String(milestoneProgress(streak)));
    $('#milestone-text').textContent = reached
      ? '已经走完一整年，接下来是继续'
      : `还差 ${next.days - streak} 天 · 保持现在就好`;

    const strip = $('#badge-strip');
    strip.innerHTML = '';
    const upcoming = MILESTONES.filter((m) => m.days >= next.days).slice(0, 3);
    upcoming.forEach((m) => {
      const el = document.createElement('span');
      el.className = 'mini-badge';
      el.innerHTML = `<svg class="icon" aria-hidden="true"><use href="#i-spark"/></svg>${m.days} 天 · ${m.name}`;
      strip.appendChild(el);
    });

    $('#quote').textContent = QUOTES[dayDiff(todayKey(), '2024-01-01') % QUOTES.length];
    $('#goal-pill').textContent = `目标 ${state.goalDays} 天`;
  }

  /* ---------------- 渲染：日历 ---------------- */
  let calCursor = { y: new Date().getFullYear(), m: new Date().getMonth() };

  function renderCalendar() {
    const { y, m } = calCursor;
    $('#cal-title').textContent = `${y} 年 ${m + 1} 月`;

    const grid = $('#cal-grid');
    grid.innerHTML = '';
    const first = new Date(y, m, 1);
    const lead = (first.getDay() + 6) % 7; // 周一为第一列
    const daysInMonth = new Date(y, m + 1, 0).getDate();
    const relapses = relapseSet();
    const today = todayKey();

    for (let i = 0; i < lead; i++) {
      const blank = document.createElement('span');
      blank.className = 'cal-day is-blank';
      blank.setAttribute('aria-hidden', 'true');
      grid.appendChild(blank);
    }

    for (let d = 1; d <= daysInMonth; d++) {
      const k = `${y}-${pad(m + 1)}-${pad(d)}`;
      const cell = document.createElement('button');
      cell.type = 'button';
      cell.className = 'cal-day';
      cell.dataset.day = k;
      cell.setAttribute('role', 'gridcell');
      cell.textContent = String(d);
      const future = dayDiff(k, today) > 0;
      const beforeStart = dayDiff(k, state.startDate) < 0;
      if (isChecked(k)) cell.classList.add('is-checked');
      if (k === today) cell.classList.add('is-today');
      if (relapses.has(k)) cell.classList.add('is-relapse');
      if (future) cell.classList.add('is-future');
      if (beforeStart) cell.classList.add('is-out');
      cell.disabled = future || beforeStart;
      const labelBits = [`${m + 1} 月 ${d} 日`];
      if (isChecked(k)) labelBits.push('已打卡');
      if (relapses.has(k)) labelBits.push('重新开始');
      if (k === today) labelBits.push('今天');
      if (future) labelBits.push('未来');
      cell.setAttribute('aria-label', labelBits.join('，'));
      if (isChecked(k)) cell.setAttribute('aria-selected', 'true');
      grid.appendChild(cell);
    }

    // 本月统计
    const monthPrefix = `${y}-${pad(m + 1)}-`;
    const checkedThisMonth = Object.keys(state.checkins).filter(
      (k) => state.checkins[k] && k.startsWith(monthPrefix)
    ).length;
    const now = new Date();
    const isThisMonth = now.getFullYear() === y && now.getMonth() === m;
    const elapsed = isThisMonth ? now.getDate() : daysInMonth;
    const rate = elapsed > 0 ? Math.round((checkedThisMonth / elapsed) * 100) : 0;
    const relapseThisMonth = state.relapses.filter((r) => r.d.startsWith(monthPrefix)).length;
    $('#month-checked').textContent = String(checkedThisMonth);
    $('#month-rate').textContent = `${clamp(rate, 0, 100)}%`;
    $('#month-relapse').textContent = String(relapseThisMonth);
  }

  /* ---------------- 渲染：应急 ---------------- */
  const actionState = () => {
    const today = todayKey();
    if (!state.actions || state.actions.date !== today) {
      state.actions = { date: today, done: [] };
    }
    return state.actions;
  };

  function renderActions() {
    const list = $('#action-list');
    const done = new Set(actionState().done);
    list.innerHTML = '';
    ACTIONS.forEach((a) => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = `action-item${done.has(a.id) ? ' is-done' : ''}`;
      btn.dataset.action = a.id;
      btn.setAttribute('aria-pressed', String(done.has(a.id)));
      btn.innerHTML = `
        <span class="action-ico"><svg class="icon" aria-hidden="true"><use href="#${done.has(a.id) ? 'i-check' : a.icon}"/></svg></span>
        <span class="action-text"><b>${a.title}</b><small>${a.desc}</small></span>`;
      list.appendChild(btn);
    });
  }

  function renderNotes() {
    const list = $('#note-list');
    list.innerHTML = '';
    if (!state.notes.length) {
      const li = document.createElement('li');
      li.className = 'note-empty';
      li.textContent = '还没有写下什么。下一次冲动时，试着留一句。';
      list.appendChild(li);
      return;
    }
    state.notes.slice(0, 4).forEach((n) => {
      const li = document.createElement('li');
      const p = document.createElement('p');
      p.textContent = n.text;
      const t = document.createElement('time');
      t.dateTime = new Date(n.ts).toISOString();
      t.textContent = fmtStamp(n.ts);
      li.append(p, t);
      list.appendChild(li);
    });
  }

  /* ---------------- 渲染：我的 ---------------- */
  function renderProfile() {
    const best = bestStreak();
    const days = Math.max(0, dayDiff(todayKey(), state.startDate));
    $('#profile-start').textContent = `从 ${fmtFull(state.startDate)} 开始`;
    $('#profile-days').textContent = `已经走了 ${days + 1} 天 · 目标 ${state.goalDays} 天`;
    $('#goal-chip').textContent = `${state.goalDays} 天目标`;

    const grid = $('#badge-grid');
    grid.innerHTML = '';
    let earned = 0;
    MILESTONES.forEach((m) => {
      const ok = best >= m.days;
      if (ok) earned += 1;
      const el = document.createElement('div');
      el.className = `badge${ok ? ' is-earned' : ''}`;
      el.title = ok ? `已获得：${m.name}` : `达到 ${m.days} 天解锁`;
      el.innerHTML = `
        <span class="badge-ico"><svg class="icon" aria-hidden="true"><use href="#${ok ? 'i-spark' : 'i-target'}"/></svg></span>
        <span class="badge-days">${m.days} 天</span>
        <span class="badge-name">${m.name}</span>`;
      grid.appendChild(el);
    });
    $('#badge-progress').textContent = `${earned} / ${MILESTONES.length}`;
    $$('#theme-seg button').forEach((b) =>
      b.setAttribute('aria-pressed', String(b.dataset.mode === (state.settings.theme || 'auto')))
    );
  }

  function renderAll() {
    renderToday();
    renderCalendar();
    renderActions();
    renderNotes();
    renderProfile();
    applyTheme();
  }

  /* ---------------- 视图切换 ---------------- */
  let currentView = 'today';
  function go(view) {
    if (!view || view === currentView) return;
    $$('.view').forEach((v) => (v.hidden = v.dataset.view !== view));
    $$('.nav-item').forEach((b) => {
      const active = b.dataset.go === view;
      b.classList.toggle('is-active', active);
      if (active) b.setAttribute('aria-current', 'page');
      else b.removeAttribute('aria-current');
    });
    currentView = view;
    const main = $('#main');
    window.scrollTo({ top: 0, behavior: 'instant' in window ? 'instant' : 'auto' });
    if (view === 'calendar') renderCalendar();
    if (view === 'sos') {
      renderActions();
      renderNotes();
      syncTimerUI();
    }
    if (view === 'me') renderProfile();
    // 视图入场动画重放
    const el = $(`.view[data-view="${view}"]`);
    if (el) {
      el.style.animation = 'none';
      void el.offsetWidth;
      el.style.animation = '';
    }
    void main;
  }

  /* ---------------- 打卡 ---------------- */
  let undoTimer = null;

  function toggleCheck(k = todayKey(), opts = {}) {
    if (isChecked(k)) {
      delete state.checkins[k];
      save();
      renderAll();
      snack(`已撤销 ${fmtDate(k)} 的打卡`, () => {
        state.checkins[k] = true;
        save();
        renderAll();
      });
    } else {
      state.checkins[k] = true;
      save();
      renderAll();
      if (k === todayKey()) {
        burst();
        if (navigator.vibrate) navigator.vibrate(14);
      }
      snack(`已留下 ${fmtDate(k)}${opts.quiet ? '' : ''}`, () => {
        delete state.checkins[k];
        save();
        renderAll();
      });
    }
  }

  function burst() {
    const zone = $('.check-zone');
    if (!zone) return;
    for (let i = 0; i < 14; i++) {
      const s = document.createElement('span');
      s.className = 'spark';
      const angle = (-Math.PI / 2) + (Math.random() - 0.5) * Math.PI * 1.9;
      const dist = 70 + Math.random() * 90;
      s.style.setProperty('--dx', `${Math.cos(angle) * dist}px`);
      s.style.setProperty('--dy', `${Math.sin(angle) * dist}px`);
      s.style.animationDelay = `${Math.random() * 90}ms`;
      s.style.background = i % 3 === 0 ? 'var(--tertiary)' : i % 3 === 1 ? 'var(--primary)' : 'var(--primary-container)';
      zone.appendChild(s);
      setTimeout(() => s.remove(), 1100);
    }
  }

  /* ---------------- 弹层 ---------------- */
  let lastFocus = null;
  let dialogOnClose = null;

  function openDialog({ icon = 'i-info', title, body = '', extra = null, actions = [], onClose = null, dismissible = true }) {
    closeDialog(true);
    lastFocus = document.activeElement;
    dialogOnClose = onClose;

    const scrim = $('#scrim');
    const host = $('#dialog-host');
    scrim.hidden = false;
    host.hidden = false;
    void host.offsetWidth;
    scrim.classList.add('is-open');

    const dialog = document.createElement('div');
    dialog.className = 'dialog';
    dialog.setAttribute('role', 'dialog');
    dialog.setAttribute('aria-modal', 'true');
    dialog.setAttribute('aria-labelledby', 'dlg-title');

    const ico = document.createElement('div');
    ico.className = 'dialog-ico';
    ico.innerHTML = `<svg class="icon" aria-hidden="true"><use href="#${icon}"/></svg>`;

    const h = document.createElement('h2');
    h.className = 'dialog-title';
    h.id = 'dlg-title';
    h.textContent = title;

    const b = document.createElement('div');
    b.className = 'dialog-body';
    if (typeof body === 'string') b.innerHTML = body;
    else b.appendChild(body);

    const actionsRow = document.createElement('div');
    actionsRow.className = 'dialog-actions';
    actions.forEach((a, idx) => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = `btn ${a.variant === 'text' ? 'btn-text' : a.variant === 'danger' ? 'btn-filled danger-fill' : 'btn-filled'}`;
      if (a.variant === 'danger') btn.style.background = 'var(--error)';
      btn.textContent = a.label;
      btn.addEventListener('click', () => {
        const close = a.keepOpen ? null : () => closeDialog();
        if (close) close();
        a.onClick?.(dialog);
      });
      actionsRow.appendChild(btn);
      if (idx === 0) setTimeout(() => btn.focus({ preventScroll: true }), 40);
    });

    dialog.append(ico, h, b);
    if (extra) {
      const ex = document.createElement('div');
      ex.className = 'dialog-extra';
      ex.appendChild(extra);
      dialog.appendChild(ex);
    }
    dialog.appendChild(actionsRow);
    host.innerHTML = '';
    host.appendChild(dialog);
    host.setAttribute('data-dismissible', String(dismissible));

    const onKey = (e) => {
      if (e.key === 'Escape' && dismissible) {
        closeDialog();
      }
      if (e.key === 'Tab') {
        const focusables = $$('button, [href], textarea, input', dialog).filter((el) => !el.disabled);
        if (!focusables.length) return;
        const first = focusables[0];
        const last = focusables[focusables.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };
    document.addEventListener('keydown', onKey);
    dialog._onKey = onKey;
  }

  function closeDialog(silent = false) {
    const host = $('#dialog-host');
    const dialog = host.firstElementChild;
    if (!dialog) return;
    if (dialog._onKey) document.removeEventListener('keydown', dialog._onKey);
    host.hidden = true;
    host.innerHTML = '';
    const scrim = $('#scrim');
    scrim.classList.remove('is-open');
    setTimeout(() => (scrim.hidden = true), 220);
    if (!silent && typeof dialogOnClose === 'function') dialogOnClose();
    dialogOnClose = null;
    if (lastFocus && document.contains(lastFocus)) lastFocus.focus({ preventScroll: true });
    lastFocus = null;
  }

  $('#scrim').addEventListener('click', () => {
    const host = $('#dialog-host');
    if (host.getAttribute('data-dismissible') !== 'false') closeDialog();
  });

  /* ---------------- 提示条 ---------------- */
  let snackTimer = null;
  function snack(text, action) {
    const bar = $('#snackbar');
    $('#snack-text').textContent = text;
    const act = $('#snack-action');
    if (action) {
      act.hidden = false;
      act.onclick = () => {
        action();
        hideSnack();
      };
    } else {
      act.hidden = true;
      act.onclick = null;
    }
    bar.hidden = false;
    void bar.offsetWidth;
    bar.classList.add('is-open');
    clearTimeout(snackTimer);
    snackTimer = setTimeout(hideSnack, action ? 5200 : 2600);
  }
  function hideSnack() {
    const bar = $('#snackbar');
    bar.classList.remove('is-open');
    clearTimeout(snackTimer);
    setTimeout(() => (bar.hidden = true), 260);
  }

  /* ---------------- 呼吸练习 ---------------- */
  const PHASES = [
    { cls: 'is-inhale', label: '吸气', secs: 4 },
    { cls: '', label: '停留', secs: 4 },
    { cls: 'is-exhale', label: '呼气', secs: 6 },
  ];
  const breath = { running: false, phase: 0, remain: 0, cycle: 1, total: 6, timer: null };

  function breathUI() {
    const orb = $('#breath-orb');
    const halo = $('#breath-halo');
    const phaseEl = $('#breath-phase');
    const btn = $('#breath-btn');
    const tip = $('#breath-tip');
    if (!breath.running) {
      if (breath.phase === -1) {
        phaseEl.textContent = '完成了 · 感觉如何';
        tip.textContent = '如果还想，再来一轮，或者去「延迟 10 分钟」';
        btn.textContent = '再来一轮';
      } else {
        phaseEl.textContent = '准备好了吗';
        tip.textContent = '吸气 4 秒 · 停 4 秒 · 呼气 6 秒';
        btn.textContent = '开始 90 秒呼吸';
      }
      orb.className = 'breath-orb';
      orb.style.removeProperty('--breath');
      halo.style.transform = '';
      halo.style.opacity = '';
      return;
    }
    const p = PHASES[breath.phase];
    orb.className = `breath-orb ${p.cls}`;
    orb.style.setProperty('--breath', `${p.secs}s`);
    phaseEl.textContent = `${p.label} ${breath.remain}`;
    tip.textContent = `第 ${breath.cycle} / ${breath.total} 轮`;
    btn.textContent = '停下来';
  }

  function startBreath() {
    if (breath.running) {
      stopBreath();
      return;
    }
    breath.running = true;
    breath.phase = 0;
    breath.remain = PHASES[0].secs;
    breath.cycle = 1;
    breathUI();
    clearInterval(breath.timer);
    breath.timer = setInterval(() => {
      breath.remain -= 1;
      if (breath.remain <= 0) {
        breath.phase += 1;
        if (breath.phase >= PHASES.length) {
          breath.phase = 0;
          breath.cycle += 1;
          if (breath.cycle > breath.total) {
            finishBreath();
            return;
          }
        }
        breath.remain = PHASES[breath.phase].secs;
      }
      breathUI();
    }, 1000);
  }

  function finishBreath() {
    clearInterval(breath.timer);
    breath.running = false;
    breath.phase = -1;
    breathUI();
    if (navigator.vibrate) navigator.vibrate([12, 60, 12]);
  }

  function stopBreath() {
    clearInterval(breath.timer);
    breath.running = false;
    breath.phase = -1;
    breathUI();
  }

  /* ---------------- 延迟计时 ---------------- */
  const TIMER_MINUTES = 10;
  let timerTimer = null;

  function timerRemaining() {
    if (!state.timer || !state.timer.end) return 0;
    return Math.max(0, Math.round((state.timer.end - Date.now()) / 1000));
  }

  function startTimer() {
    state.timer = { end: Date.now() + TIMER_MINUTES * 60 * 1000 };
    save();
    if (navigator.vibrate) navigator.vibrate(8);
    syncTimerUI();
  }

  function resetTimer() {
    state.timer = null;
    save();
    syncTimerUI();
  }

  function syncTimerUI() {
    const ring = $('#timer-ring');
    const label = $('#timer-time');
    const btn = $('#timer-btn');
    const note = $('#timer-note');
    if (!ring) return;

    const remain = timerRemaining();
    if (!state.timer) {
      label.textContent = '10:00';
      ring.style.setProperty('--p', '0');
      btn.textContent = '开始计时';
      note.textContent = '十分钟后，冲动通常会弱一半。';
      return;
    }
    if (remain <= 0) {
      label.textContent = '00:00';
      ring.style.setProperty('--p', '100');
      btn.textContent = '再等十分钟';
      note.textContent = '时间到了。现在，你还想吗？';
      clearInterval(timerTimer);
      timerTimer = null;
      if (state.timer && !state.timer.done) {
        state.timer.done = true;
        save();
      }
      return;
    }
    const mm = Math.floor(remain / 60);
    const ss = remain % 60;
    label.textContent = `${pad(mm)}:${pad(ss)}`;
    const pct = 100 - (remain / (TIMER_MINUTES * 60)) * 100;
    ring.style.setProperty('--p', String(clamp(Math.round(pct), 0, 100)));
    btn.textContent = '放弃计时';
    note.textContent = '还剩一点时间，先别做决定。';
    clearInterval(timerTimer);
    timerTimer = setInterval(() => {
      const left = timerRemaining();
      if (left <= 0) {
        syncTimerUI();
      } else {
        const m = Math.floor(left / 60);
        const s = left % 60;
        label.textContent = `${pad(m)}:${pad(s)}`;
        ring.style.setProperty('--p', String(clamp(Math.round(100 - (left / (TIMER_MINUTES * 60)) * 100), 0, 100)));
      }
    }, 1000);
  }

  /* ---------------- 复发 / 重新开始 ---------------- */
  function openRelapseDialog() {
    const chips = document.createElement('div');
    chips.className = 'option-chips';
    let selected = '';
    TRIGGERS.forEach((t) => {
      const b = document.createElement('button');
      b.type = 'button';
      b.className = 'option-chip';
      b.textContent = t;
      b.setAttribute('aria-pressed', 'false');
      b.addEventListener('click', () => {
        const was = selected === t;
        selected = was ? '' : t;
        $$('.option-chip', chips).forEach((x) => x.setAttribute('aria-pressed', String(x.textContent === selected)));
      });
      chips.appendChild(b);
    });

    const wrap = document.createElement('div');
    const label = document.createElement('p');
    label.className = 'muted small';
    label.style.marginBottom = '8px';
    label.textContent = '如果愿意，可以留下原因（可不选）：';
    wrap.append(label, chips);

    openDialog({
      icon: 'i-leaf',
      title: '重新开始',
      body: '<p>这不是失败。复发只是数据，不是判决。</p><p>记录它，然后明天继续。连续天数会归零，但累计的打卡和写下的话都还在。</p>',
      extra: wrap,
      dismissible: true,
      actions: [
        { label: '再想想', variant: 'text' },
        {
          label: '记录并重新开始',
          variant: 'danger',
          onClick: () => {
            state.relapses.push({ d: todayKey(), reason: selected, ts: Date.now() });
            state.startDate = todayKey();
            state.timer = null;
            save();
            renderAll();
            snack('已重新开始 · 明天是新的第 1 天', () => {
              state.relapses.pop();
              save();
              renderAll();
            });
          },
        },
      ],
    });
  }

  /* ---------------- 目标 ---------------- */
  function openGoalDialog() {
    const grid = document.createElement('div');
    grid.className = 'goal-chips';
    let picked = state.goalDays;
    const opts = [30, 60, 90, 120, 180, 365];
    opts.forEach((v) => {
      const b = document.createElement('button');
      b.type = 'button';
      b.className = 'option-chip';
      b.textContent = `${v} 天`;
      b.setAttribute('aria-pressed', String(v === picked));
      b.addEventListener('click', () => {
        picked = v;
        $$('.option-chip', grid).forEach((x) => x.setAttribute('aria-pressed', String(x.textContent === `${picked} 天`)));
      });
      grid.appendChild(b);
    });
    openDialog({
      icon: 'i-target',
      title: '设定一个目标',
      body: '<p>目标只是方向，不是考核。随时可以改。</p>',
      extra: grid,
      actions: [
        { label: '取消', variant: 'text' },
        {
          label: '保存',
          onClick: () => {
            state.goalDays = picked;
            save();
            renderAll();
            snack(`目标已设为 ${picked} 天`);
          },
        },
      ],
    });
  }

  /* ---------------- 备份 ---------------- */
  function exportData() {
    const blob = new Blob([JSON.stringify(state, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `归岸备份-${todayKey()}.json`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 2000);
    snack('备份已下载');
  }

  function importData(file) {
    const reader = new FileReader();
    reader.onload = () => {
      let data;
      try {
        data = JSON.parse(String(reader.result));
      } catch {
        snack('这个文件读不出来，请确认是归岸导出的 JSON');
        return;
      }
      if (!data || typeof data !== 'object' || typeof data.checkins !== 'object') {
        snack('文件格式不对，缺少打卡记录');
        return;
      }
      openDialog({
        icon: 'i-upload',
        title: '导入这份备份？',
        body: `<p>将覆盖当前所有数据：${Object.keys(data.checkins || {}).length} 天打卡、${(data.relapses || []).length} 次重启、${(data.notes || []).length} 条记录。</p>`,
        actions: [
          { label: '取消', variant: 'text' },
          {
            label: '覆盖导入',
            onClick: () => {
              state = normalize(data);
              save();
              renderAll();
              snack('已导入备份');
            },
          },
        ],
      });
    };
    reader.onerror = () => snack('读取文件失败');
    reader.readAsText(file);
  }

  function clearAll() {
    openDialog({
      icon: 'i-trash',
      title: '清空所有数据？',
      body: '<p>打卡、连续天数、写下的话都会消失，且无法恢复。</p><p>如果只是想重新开始，用「我破戒了」更合适，历史会保留。</p>',
      actions: [
        { label: '取消', variant: 'text' },
        {
          label: '确认清空',
          onClick: () => {
            const keepTheme = state.settings.theme;
            state = defaultState();
            state.onboarded = true;
            state.startDate = todayKey();
            state.settings.theme = keepTheme;
            save();
            renderAll();
            snack('已清空，从今天重新开始');
          },
        },
      ],
    });
  }

  /* ---------------- 首次进入 ---------------- */
  function openOnboarding() {
    const grid = document.createElement('div');
    grid.className = 'goal-chips';
    let picked = 90;
    [30, 60, 90, 180, 365, 1000].forEach((v) => {
      const b = document.createElement('button');
      b.type = 'button';
      b.className = 'option-chip';
      b.textContent = v === 1000 ? '不限' : `${v} 天`;
      b.setAttribute('aria-pressed', String(v === picked));
      b.addEventListener('click', () => {
        picked = v;
        $$('.option-chip', grid).forEach((x) => x.setAttribute('aria-pressed', String(x === b)));
      });
      grid.appendChild(b);
    });
    openDialog({
      icon: 'i-leaf',
      title: '欢迎来到归岸',
      body: '<p>每天点一次打卡，把这一天留下。没有排行榜，没有评判，数据只在这台设备上。</p><p>先选一个想走到的天数，之后随时能改。</p>',
      extra: grid,
      dismissible: false,
      actions: [
        {
          label: '开始',
          onClick: () => {
            state.onboarded = true;
            state.goalDays = picked;
            state.startDate = todayKey();
            save();
            renderAll();
          },
        },
      ],
    });
  }

  /* ---------------- 只在键盘操作时显示焦点环 ---------------- */
  // 触摸/鼠标点过之后 html 上没有 .kbd，:focus-visible 不生效，避免点击后出现外框；
  // 一旦用 Tab 键，挂上 .kbd 恢复键盘用户的可访问性焦点环。
  document.addEventListener('pointerdown', () => {
    document.documentElement.classList.remove('kbd');
  }, true);
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Tab') document.documentElement.classList.add('kbd');
  }, true);

  /* ---------------- 涟漪 ---------------- */
  const RIPPLE_SEL = '.btn, .text-btn, .icon-btn, .nav-item, .row-btn, .action-item, .cal-day, .option-chip, .segmented button';
  document.addEventListener('pointerdown', (e) => {
    const host = e.target.closest(RIPPLE_SEL);
    if (!host || host.disabled) return;
    const rect = host.getBoundingClientRect();
    const size = Math.max(rect.width, rect.height) * 2;
    const ink = document.createElement('span');
    ink.className = 'ripple-ink';
    ink.style.width = ink.style.height = `${size}px`;
    ink.style.left = `${e.clientX - rect.left - size / 2}px`;
    ink.style.top = `${e.clientY - rect.top - size / 2}px`;
    host.appendChild(ink);
    setTimeout(() => ink.remove(), 560);
  });

  /* ---------------- 事件绑定 ---------------- */
  $('#check-btn').addEventListener('click', () => toggleCheck());

  $$('.nav-item').forEach((b) => b.addEventListener('click', () => go(b.dataset.go)));

  $('#theme-btn').addEventListener('click', () => {
    const currentDark = document.documentElement.dataset.theme === 'dark';
    state.settings.theme = currentDark ? 'light' : 'dark';
    save();
    applyTheme();
  });

  $('#cal-prev').addEventListener('click', () => {
    calCursor.m -= 1;
    if (calCursor.m < 0) {
      calCursor.m = 11;
      calCursor.y -= 1;
    }
    renderCalendar();
  });
  $('#cal-next').addEventListener('click', () => {
    calCursor.m += 1;
    if (calCursor.m > 11) {
      calCursor.m = 0;
      calCursor.y += 1;
    }
    renderCalendar();
  });
  $('#cal-reset').addEventListener('click', () => {
    const now = new Date();
    calCursor = { y: now.getFullYear(), m: now.getMonth() };
    renderCalendar();
  });

  $('#cal-grid').addEventListener('click', (e) => {
    const cell = e.target.closest('.cal-day');
    if (!cell || cell.disabled || cell.classList.contains('is-blank')) return;
    const k = cell.dataset.day;
    if (!k) return;
    const checked = isChecked(k);
    const relapse = relapseSet().has(k);
    openDialog({
      icon: checked ? 'i-undo' : 'i-calendar',
      title: `${fmtDate(k)}${relapse ? ' · 重新开始' : ''}`,
      body: checked
        ? '<p>这一天已经打卡。要撤销吗？撤销会改变连续天数。</p>'
        : '<p>给这一天补一个记录。补记的日期越近，连续天数越容易接上。</p>',
      actions: [
        { label: '取消', variant: 'text' },
        {
          label: checked ? '撤销这一天' : '补记这一天',
          onClick: () => toggleCheck(k),
        },
      ],
    });
  });

  $('#breath-btn').addEventListener('click', startBreath);

  $('#timer-btn').addEventListener('click', () => {
    if (!state.timer || timerRemaining() <= 0) startTimer();
    else resetTimer();
  });

  $('#action-list').addEventListener('click', (e) => {
    const item = e.target.closest('.action-item');
    if (!item) return;
    const a = actionState();
    const id = item.dataset.action;
    if (a.done.includes(id)) a.done = a.done.filter((x) => x !== id);
    else a.done.push(id);
    save();
    renderActions();
    if (a.done.includes(id)) snack('做一件小事，浪就会退一点');
  });

  $('#note-save').addEventListener('click', () => {
    const input = $('#note-input');
    const text = input.value.trim();
    if (!text) {
      input.focus();
      return;
    }
    state.notes.unshift({ ts: Date.now(), text });
    if (state.notes.length > 200) state.notes.length = 200;
    save();
    input.value = '';
    renderNotes();
    $('#note-status').textContent = '已收好';
    setTimeout(() => ($('#note-status').textContent = ''), 2400);
    if (navigator.vibrate) navigator.vibrate(8);
  });

  $('#relapse-btn').addEventListener('click', openRelapseDialog);
  $('#goal-edit').addEventListener('click', openGoalDialog);

  $('#theme-seg').addEventListener('click', (e) => {
    const b = e.target.closest('button[data-mode]');
    if (!b) return;
    state.settings.theme = b.dataset.mode;
    save();
    applyTheme();
    renderProfile();
  });

  $('#export-btn').addEventListener('click', exportData);
  $('#import-btn').addEventListener('click', () => $('#import-file').click());
  $('#import-file').addEventListener('change', (e) => {
    const file = e.target.files?.[0];
    if (file) importData(file);
    e.target.value = '';
  });
  $('#clear-btn').addEventListener('click', clearAll);

  /* ---------------- 跨天检测 ---------------- */
  let lastDay = todayKey();
  setInterval(() => {
    const now = todayKey();
    if (now !== lastDay) {
      lastDay = now;
      actionState();
      renderAll();
    }
  }, 30000);

  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') {
      if (todayKey() !== lastDay) {
        lastDay = todayKey();
        renderAll();
      }
      syncTimerUI();
    }
  });

  /* ---------------- 启动 ---------------- */
  function boot() {
    applyTheme();
    renderAll();
    syncTimerUI();
    if (START_VIEW !== 'today') go(START_VIEW);
    if (!state.onboarded) {
      openOnboarding();
    }
    // 注册 Service Worker：仅在 http(s) 下生效，file:// 打开时会静默失败
    if ('serviceWorker' in navigator && location.protocol.startsWith('http')) {
      navigator.serviceWorker.register('sw.js').catch(() => {});
    }
  }

  boot();
})();
