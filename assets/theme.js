/* ==========================================================================
   三态主题：自动（默认，跟随系统） → 亮色 → 暗色 → 自动
   在 <head> 同步执行：首屏渲染前落定 data-theme，避免主题闪烁。
   CSS 契约不变——浅色读 [data-theme="light"]，深色为默认值。
   ========================================================================== */
(function () {
  'use strict';

  var KEY = 'kp-theme';
  var ORDER = ['auto', 'light', 'dark'];
  var NEXT = { auto: '亮色', light: '暗色', dark: '自动' };
  var NAME = { auto: '自动', light: '亮色', dark: '暗色' };
  var ICON = { auto: '◐', light: '☀', dark: '☾' };
  var COLOR = { light: '#eceef2', dark: '#15171c' }; // 与 style.css 的 --bg 同步
  var mq = window.matchMedia ? window.matchMedia('(prefers-color-scheme: light)') : null;

  function read() {
    try {
      var v = localStorage.getItem(KEY);
      return ORDER.indexOf(v) !== -1 ? v : 'auto';
    } catch (e) { return 'auto'; }
  }

  function write(mode) {
    try { localStorage.setItem(KEY, mode); } catch (e) { /* 无痕模式：仅本次生效 */ }
  }

  function resolve(mode) {
    if (mode === 'auto') return mq && mq.matches ? 'light' : 'dark';
    return mode;
  }

  // 让浏览器 chrome 配色跟随实际主题，而不是系统的 media query
  function applyMeta(actual) {
    var metas = document.querySelectorAll('meta[name="theme-color"]');
    if (!metas.length) return;
    for (var i = 1; i < metas.length; i++) metas[i].parentNode.removeChild(metas[i]);
    metas[0].removeAttribute('media');
    metas[0].setAttribute('content', COLOR[actual]);
  }

  function syncUI(mode) {
    mode = mode || read();
    var icon = ICON[mode];
    var tip = '主题：' + NAME[mode] + '（点击切到' + NEXT[mode] + '）';
    var toggles = document.querySelectorAll('.theme-toggle');
    for (var i = 0; i < toggles.length; i++) {
      toggles[i].textContent = icon;
      toggles[i].setAttribute('title', tip);
      toggles[i].setAttribute('aria-label', tip);
    }
    var si = document.getElementById('sheetThemeIcon');
    var sl = document.getElementById('sheetThemeLabel');
    var sh = document.getElementById('sheetThemeHint');
    if (si) si.textContent = icon;
    if (sl) sl.textContent = '主题模式';
    if (sh) sh.textContent = NAME[mode];
  }

  function apply() {
    var mode = read();
    var actual = resolve(mode);
    var root = document.documentElement;
    root.setAttribute('data-theme-mode', mode); // 记录用户选择，CSS 不依赖它
    if (actual === 'light') root.setAttribute('data-theme', 'light');
    else root.removeAttribute('data-theme');
    applyMeta(actual);
    syncUI(mode);
  }

  window.toggleTheme = function () {
    var cur = read();
    write(ORDER[(ORDER.indexOf(cur) + 1) % ORDER.length]);
    apply();
  };

  // 自动模式下实时跟随系统外观变化
  if (mq) {
    var onChange = function () { if (read() === 'auto') apply(); };
    if (mq.addEventListener) mq.addEventListener('change', onChange);
    else if (mq.addListener) mq.addListener(onChange);
  }

  apply(); // head 阶段：先定主题，再渲染首屏

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () { syncUI(); });
  } else {
    syncUI();
  }
})();
