// ── Theme ──
// 主题由 <head> 同步加载的 assets/theme.js 统一驱动（自动 / 亮色 / 暗色三态），
// 全局 toggleTheme() 也定义在那个脚本里，本文件不再重复实现。

// ── Scroll reveal ──
const io = new IntersectionObserver((entries) => {
  entries.forEach(e => { if (e.isIntersecting) e.target.classList.add('visible'); });
}, { threshold: 0.1 });
document.querySelectorAll('.reveal').forEach(el => io.observe(el));

// ── 文章阅读进度条（仅文章详情页）──
// 正文滚动进度用 transform:scaleX 驱动，避免每帧触发布局。
(function () {
  const bar = document.querySelector('.post-progress');
  const article = document.querySelector('.post-content');
  if (!bar || !article) return;

  let ticking = false;
  function update() {
    const rect = article.getBoundingClientRect();
    const start = window.scrollY + rect.top - window.innerHeight * 0.2;
    const total = rect.height - window.innerHeight * 0.6;
    const ratio = total > 0 ? (window.scrollY - start) / total : (window.scrollY > start ? 1 : 0);
    bar.style.transform = `scaleX(${Math.min(1, Math.max(0, ratio)).toFixed(4)})`;
    ticking = false;
  }
  function onScroll() {
    if (!ticking) { ticking = true; requestAnimationFrame(update); }
  }

  bar.style.transform = 'scaleX(0)';
  window.addEventListener('scroll', onScroll, { passive: true });
  window.addEventListener('resize', onScroll, { passive: true });
  update();
})();

// ── 阅读进度条 + 回顶进度环 ──
(function () {
  const bar = document.getElementById('readingProgress');
  const toTop = document.getElementById('toTop');
  const ring = document.getElementById('toTopBar');
  const R = 19, C = 2 * Math.PI * R;
  if (ring) { ring.style.strokeDasharray = C; ring.style.strokeDashoffset = C; }
  let ticking = false;
  function onScroll() {
    const st = window.scrollY || document.documentElement.scrollTop;
    const docH = document.documentElement.scrollHeight - window.innerHeight;
    const p = docH > 0 ? Math.min(1, Math.max(0, st / docH)) : 0;
    if (bar) bar.style.transform = `scaleX(${p})`;
    if (ring) ring.style.strokeDashoffset = C * (1 - p);
    if (toTop) toTop.classList.toggle('show', st > 400);
    ticking = false;
  }
  window.addEventListener('scroll', () => {
    if (!ticking) { ticking = true; requestAnimationFrame(onScroll); }
  }, { passive: true });
  window.addEventListener('resize', onScroll, { passive: true });
  onScroll();
  if (toTop) toTop.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));
})();

// ── 文章搜索 + 标签筛选 + 分页 ──
(function () {
  const grid = document.querySelector('.posts-grid');
  if (!grid) return;
  const search = document.getElementById('postSearch');
  const chipsWrap = document.getElementById('postChips');
  const count = document.getElementById('postCount');
  const empty = document.getElementById('postEmpty');
  const pager = document.getElementById('postPager');
  const cards = Array.from(grid.querySelectorAll('.post-card'));
  const PAGE_SIZE = 12;
  let activeTag = 'all';
  let currentPage = 1;
  let filtered = cards.slice();
  const norm = s => (s || '').toLowerCase().trim();

  // 从卡片标签动态生成筛选 chips（排除版本号标签）
  const tagSet = new Set();
  cards.forEach(c => {
    c.querySelectorAll('.post-card__tags .tag').forEach(t => {
      const txt = t.textContent.trim();
      if (txt && !/^v?\d+\.\d+/.test(txt)) tagSet.add(txt);
    });
  });
  const priority = ['AI Agent', '安全', 'Python', 'macOS', '架构', 'IM', '本地化', '质量', '可靠性', '体验', '前端'];
  const ordered = [...tagSet].sort((a, b) => {
    const ia = priority.indexOf(a), ib = priority.indexOf(b);
    if (ia === -1 && ib === -1) return a.localeCompare(b, 'zh');
    if (ia === -1) return 1;
    if (ib === -1) return -1;
    return ia - ib;
  });
  if (chipsWrap) {
    const all = document.createElement('button');
    all.className = 'chip chip--active';
    all.dataset.tag = 'all';
    all.textContent = '全部';
    chipsWrap.appendChild(all);
    ordered.forEach(t => {
      const b = document.createElement('button');
      b.className = 'chip';
      b.dataset.tag = t;
      b.textContent = t;
      chipsWrap.appendChild(b);
    });
  }

  function cardData(c) {
    const t = c.querySelector('.post-card__title')?.textContent || '';
    const e = c.querySelector('.post-card__excerpt')?.textContent || '';
    const tags = Array.from(c.querySelectorAll('.post-card__tags .tag')).map(x => x.textContent).join(' ');
    return { hay: norm(t + ' ' + e), tags: norm(tags) };
  }

  function computeFiltered() {
    const q = norm(search ? search.value : '');
    filtered = cards.filter(c => {
      const { hay, tags } = cardData(c);
      const matchQ = !q || hay.includes(q);
      const matchTag = activeTag === 'all' || tags.includes(norm(activeTag));
      return matchQ && matchTag;
    });
  }

  function mkBtn(label, opts = {}) {
    const b = document.createElement('button');
    b.className = 'post-page-btn'
      + (opts.active ? ' post-page-btn--active' : '')
      + (opts.disabled ? ' post-page-btn--disabled' : '');
    b.textContent = label;
    if (opts.disabled) b.disabled = true;
    return b;
  }

  function renderPager(totalPages) {
    if (!pager) return;
    pager.innerHTML = '';
    if (totalPages <= 1) { pager.hidden = true; return; }
    pager.hidden = false;
    const prev = mkBtn('上一页', { disabled: currentPage === 1 });
    prev.addEventListener('click', () => {
      if (currentPage > 1) { currentPage--; render(); scrollToGridTop(); }
    });
    pager.appendChild(prev);
    for (let p = 1; p <= totalPages; p++) {
      const b = mkBtn(String(p), { active: p === currentPage });
      b.addEventListener('click', () => { currentPage = p; render(); scrollToGridTop(); });
      pager.appendChild(b);
    }
    const next = mkBtn('下一页', { disabled: currentPage === totalPages });
    next.addEventListener('click', () => {
      if (currentPage < totalPages) { currentPage++; render(); scrollToGridTop(); }
    });
    pager.appendChild(next);
  }

  function scrollToGridTop() {
    const top = grid.getBoundingClientRect().top + window.scrollY - 90;
    window.scrollTo({ top, behavior: 'smooth' });
  }

  function render() {
    const total = filtered.length;
    const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
    if (currentPage > totalPages) currentPage = totalPages;
    const start = (currentPage - 1) * PAGE_SIZE;
    const end = start + PAGE_SIZE;
    cards.forEach(c => { c.style.display = 'none'; });
    filtered.forEach((c, i) => { c.style.display = (i >= start && i < end) ? '' : 'none'; });
    if (count) count.textContent = `共 ${total} 篇`;
    if (empty) empty.hidden = total !== 0;
    renderPager(totalPages);
  }

  function apply() {
    computeFiltered();
    currentPage = 1;
    render();
  }

  if (search) search.addEventListener('input', apply);
  if (chipsWrap) chipsWrap.addEventListener('click', (e) => {
    const btn = e.target.closest('.chip');
    if (!btn) return;
    chipsWrap.querySelectorAll('.chip').forEach(c => c.classList.remove('chip--active'));
    btn.classList.add('chip--active');
    activeTag = btn.dataset.tag;
    apply();
  });
  apply();
})();

// ── 近期动态：折叠较早条目，默认只显示最近若干条 ──
(function () {
  const tl = document.querySelector('.timeline');
  if (!tl) return;
  const btn = document.getElementById('timelineToggle');
  const items = Array.from(tl.querySelectorAll('.timeline-item'));
  const VISIBLE = 5;
  if (items.length <= VISIBLE) { if (btn) btn.hidden = true; return; }
  let expanded = false;
  function setExpanded(on) {
    expanded = on;
    items.forEach((it, i) => {
      if (i >= VISIBLE) it.classList.toggle('timeline-item--collapsed', !on);
    });
    if (btn) {
      btn.textContent = on ? '收起较早的动态' : '查看更早的动态';
      btn.setAttribute('aria-expanded', String(on));
    }
  }
  setExpanded(false);
  if (btn) btn.addEventListener('click', () => setExpanded(!expanded));
})();

// ── 移动端底部导航：回顶按钮（保留兼容，实际触发由更多面板处理）──
(function () {
  const b = document.getElementById('mobileTop');
  if (b) b.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));
})();

// ── 移动端"更多"面板（底部弹层）──
(function () {
  const btn = document.getElementById('mobileMore');
  const sheet = document.getElementById('moreSheet');
  if (!btn || !sheet) return;

  const CLOSE_MS = 220;

  function open() {
    sheet.classList.remove('hide');
    sheet.classList.add('show');
    btn.setAttribute('aria-expanded', 'true');
  }
  function close() {
    if (!sheet.classList.contains('show')) return;
    sheet.classList.add('hide');
    btn.setAttribute('aria-expanded', 'false');
    setTimeout(() => {
      sheet.classList.remove('show');
      sheet.classList.remove('hide');
    }, CLOSE_MS);
  }
  function toggle() {
    sheet.classList.contains('show') ? close() : open();
  }

  btn.addEventListener('click', (e) => { e.stopPropagation(); toggle(); });

  // 点击 backdrop 关闭
  sheet.addEventListener('click', (e) => {
    if (e.target.closest('[data-close-sheet]')) close();
  });

  // 顶部链接：新标签打开外面；站内锚点直接跳转并关闭；回顶 / 切主题执行动作
  sheet.querySelectorAll('.more-sheet__item').forEach(el => {
    const isAnchor = (el.getAttribute('href') || '').startsWith('#');
    const action = el.dataset.sheetAction;
    if (!action && !isAnchor) return; // GitHub 外链：保留新窗口，由浏览器自己处理
    el.addEventListener('click', () => {
      close();
      if (isAnchor) return; // 交给浏览器处理锚点滚动
      if (action === 'top') {
        window.scrollTo({ top: 0, behavior: 'smooth' });
      } else if (action === 'theme') {
        if (typeof toggleTheme === 'function') toggleTheme();
      }
    });
  });

  // ESC 关闭
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && sheet.classList.contains('show')) close();
  });
  // 主题项文案由 theme.js 的 syncUI 统一维护（三态），此处不再重复。
})();

// ── 文章侧边浮动目录（自动从 h2 生成，类 Markdown [TOC]，高亮当前章节）──
(function () {
  const article = document.querySelector('.post-content');
  const box = document.querySelector('.toc');
  if (!article || !box) return;
  const heads = [...article.querySelectorAll('h2')];
  if (!heads.length) { box.remove(); return; }

  const list = document.createElement('ul');
  list.className = 'toc-list';
  const links = heads.map((h, i) => {
    if (!h.id) h.id = 'sec-' + (i + 1);
    const li = document.createElement('li');
    const a = document.createElement('a');
    a.href = '#' + h.id;
    a.textContent = h.textContent;
    a.dataset.target = h.id;
    li.appendChild(a);
    list.appendChild(li);
    return a;
  });
  // 滑动 accent 指示条
  const ind = document.createElement('div');
  ind.className = 'toc-ind';
  list.appendChild(ind);
  box.appendChild(list);

  // 目录顶部与正文第一段顶端对齐：用 transform 平移（不占布局，避免撑大 grid 行高）
  const inner = document.createElement('div');
  inner.className = 'toc-inner';
  while (box.firstChild) inner.appendChild(box.firstChild);
  box.appendChild(inner);
  const alignToc = () => {
    if (getComputedStyle(box).display === 'none') return;
    const delta = article.offsetTop - box.offsetTop;
    inner.style.transform = delta > 0 ? `translateY(${delta}px)` : '';
  };
  alignToc();
  window.addEventListener('resize', alignToc);
  window.addEventListener('load', alignToc);

  const setActive = (id) => links.forEach(l => {
    const on = l.dataset.target === id;
    l.classList.toggle('active', on);
    if (on) {
      ind.style.top = l.offsetTop + 'px';
      ind.style.height = l.offsetHeight + 'px';
    }
  });
  setActive(heads[0].id);
  // 字体加载完成后指示条位置可能漂移，再校准一次
  requestAnimationFrame(() => {
    const cur = links.find(l => l.classList.contains('active'));
    if (cur) { ind.style.top = cur.offsetTop + 'px'; ind.style.height = cur.offsetHeight + 'px'; }
  });

  // 点击平滑滚动到对应章节
  links.forEach(a => a.addEventListener('click', (e) => {
    e.preventDefault();
    const t = document.getElementById(a.dataset.target);
    if (t) t.scrollIntoView({ behavior: 'smooth', block: 'start' });
    history.replaceState(null, '', '#' + a.dataset.target);
  }));

  const obs = new IntersectionObserver((entries) => {
    entries.forEach(e => { if (e.isIntersecting) setActive(e.target.id); });
  }, { rootMargin: '-80px 0px -65% 0px', threshold: 0 });
  heads.forEach(h => obs.observe(h));
})();

