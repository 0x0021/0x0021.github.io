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
