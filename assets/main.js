// ── Theme ──
(function () {
  const stored = localStorage.getItem('kp-theme');
  if (stored === 'light') document.documentElement.setAttribute('data-theme', 'light');
})();
function toggleTheme() {
  const html = document.documentElement;
  const next = html.getAttribute('data-theme') === 'light' ? 'dark' : 'light';
  html.setAttribute('data-theme', next === 'light' ? 'light' : '');
  localStorage.setItem('kp-theme', next);
}

// ── Scroll reveal ──
const io = new IntersectionObserver((entries) => {
  entries.forEach(e => { if (e.isIntersecting) e.target.classList.add('visible'); });
}, { threshold: 0.1 });
document.querySelectorAll('.reveal').forEach(el => io.observe(el));

// ── Particle canvas (仅当 hero 存在时启用) ──
(function () {
  const canvas = document.getElementById('hero-canvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  let w, h, particles = [], mouse = { x: -1000, y: -1000 };

  function resize() {
    w = canvas.width = window.innerWidth;
    h = canvas.height = window.innerHeight;
  }
  window.addEventListener('resize', resize);
  resize();

  function isDark() {
    return document.documentElement.getAttribute('data-theme') !== 'light';
  }

  class Particle {
    constructor() { this.reset(); }
    reset() {
      this.x = Math.random() * w;
      this.y = Math.random() * h;
      this.vx = (Math.random() - 0.5) * 0.4;
      this.vy = (Math.random() - 0.5) * 0.4;
      this.r = Math.random() * 1.5 + 0.5;
      this.alpha = Math.random() * 0.4 + 0.1;
    }
    update() {
      this.x += this.vx;
      this.y += this.vy;
      const dx = mouse.x - this.x, dy = mouse.y - this.y;
      const dist = Math.sqrt(dx*dx + dy*dy);
      if (dist < 150) { this.x -= dx * 0.008; this.y -= dy * 0.008; }
      if (this.x < 0 || this.x > w) this.vx *= -1;
      if (this.y < 0 || this.y > h) this.vy *= -1;
      this.x = Math.max(0, Math.min(w, this.x));
      this.y = Math.max(0, Math.min(h, this.y));
    }
    draw() {
      ctx.beginPath();
      ctx.arc(this.x, this.y, this.r, 0, Math.PI * 2);
      ctx.fillStyle = isDark()
        ? `rgba(88,166,255,${this.alpha})`
        : `rgba(9,105,218,${this.alpha * 0.6})`;
      ctx.fill();
    }
  }

  const count = Math.min(80, Math.floor(w * h / 15000));
  for (let i = 0; i < count; i++) particles.push(new Particle());

  canvas.addEventListener('mousemove', e => { mouse.x = e.clientX; mouse.y = e.clientY; });
  canvas.addEventListener('mouseleave', () => { mouse.x = -1000; mouse.y = -1000; });

  function loop() {
    ctx.clearRect(0, 0, w, h);
    particles.forEach(p => { p.update(); p.draw(); });
    for (let i = 0; i < particles.length; i++) {
      for (let j = i + 1; j < particles.length; j++) {
        const dx = particles[i].x - particles[j].x;
        const dy = particles[i].y - particles[j].y;
        const dist = dx*dx + dy*dy;
        if (dist < 12000) {
          ctx.strokeStyle = isDark()
            ? `rgba(88,166,255,${0.06 * (1 - dist/12000)})`
            : `rgba(9,105,218,${0.04 * (1 - dist/12000)})`;
          ctx.lineWidth = 0.5;
          ctx.beginPath();
          ctx.moveTo(particles[i].x, particles[i].y);
          ctx.lineTo(particles[j].x, particles[j].y);
          ctx.stroke();
        }
      }
    }
    requestAnimationFrame(loop);
  }
  loop();
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

// ── 右侧章节导航 scrollspy ──
(function () {
  const toc = document.getElementById('pageToc');
  if (!toc) return;
  const items = Array.from(toc.querySelectorAll('.page-toc__item'));
  const map = new Map();
  items.forEach(it => {
    const sec = document.getElementById(it.dataset.target);
    if (sec) map.set(sec, it);
  });
  if (!map.size) return;
  const obs = new IntersectionObserver((entries) => {
    entries.forEach(e => {
      if (e.isIntersecting) {
        items.forEach(i => i.classList.remove('active'));
        const it = map.get(e.target);
        if (it) it.classList.add('active');
      }
    });
  }, { rootMargin: '-45% 0px -50% 0px', threshold: 0 });
  map.forEach((_, sec) => obs.observe(sec));
})();

// ── 文章搜索 + 标签筛选 ──
(function () {
  const grid = document.querySelector('.posts-grid');
  if (!grid) return;
  const search = document.getElementById('postSearch');
  const chipsWrap = document.getElementById('postChips');
  const count = document.getElementById('postCount');
  const empty = document.getElementById('postEmpty');
  const cards = Array.from(grid.querySelectorAll('.post-card'));
  let activeTag = 'all';
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
  function apply() {
    const q = norm(search ? search.value : '');
    let shown = 0;
    cards.forEach(c => {
      const { hay, tags } = cardData(c);
      const matchQ = !q || hay.includes(q);
      const matchTag = activeTag === 'all' || tags.includes(norm(activeTag));
      const ok = matchQ && matchTag;
      c.style.display = ok ? '' : 'none';
      if (ok) shown++;
    });
    if (count) count.textContent = `共 ${shown} 篇`;
    if (empty) empty.hidden = shown !== 0;
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

  // 顶部链接：新标签打开外面，站内的回顶 / 切主题直接关闭
  sheet.querySelectorAll('.more-sheet__item').forEach(el => {
    const action = el.dataset.sheetAction;
    if (!action) return; // GitHub 外链：保留新窗口，由浏览器自己处理
    el.addEventListener('click', () => {
      close();
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

  // 同步主题按钮文案（☾=暗 / ☀=亮）
  function syncThemeHint() {
    const isLight = document.documentElement.getAttribute('data-theme') === 'light';
    const icon = document.getElementById('sheetThemeIcon');
    const label = document.getElementById('sheetThemeLabel');
    const hint = document.getElementById('sheetThemeHint');
    if (icon) icon.textContent = isLight ? '☀' : '☾';
    if (label) label.textContent = isLight ? '切换到深色' : '切换到浅色';
    if (hint) hint.textContent = isLight ? 'LIGHT' : 'DARK';
  }
  syncThemeHint();
  new MutationObserver(syncThemeHint).observe(document.documentElement, {
    attributes: true, attributeFilter: ['data-theme'],
  });
})();
