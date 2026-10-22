#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从可莉的插件中心 (https://hub.kelee.one) 的 list.json 生成 ClashModule 页面。

关键设计：免维护 / 自动同步
  - index.html 内联一份「原始快照」(list.json 的 lists/notice/name) 作为离线兜底；
  - 页面在浏览器加载时，先渲染快照（秒开），再实时 fetch https://hub.kelee.one/list.json；
  - 拉取成功则用最新数据重渲染（真正自动同步），失败则保留快照并提示；
  - 因此无需任何定时任务、无需重新生成或推送，数据始终跟随源站更新。

用法:
    1. 抓取数据(可选，仅用于更新内联兜底快照):  curl -L https://hub.kelee.one/list.json > list.json
    2. 生成页面:  python3 build_modules.py

产出:
    - modules.json   纯数据（静态导出，供参考/离线）
    - index.html     自包含、移动端适配、运行时自动同步、带搜索 / 标签筛选 / 分页的导入页面
"""
import json
import os
import datetime
from collections import Counter
from urllib.parse import urlparse, parse_qs, quote

SRC_NAME = "可莉的插件中心"
SRC_URL = "https://hub.kelee.one"
LIST_JSON = "list.json"
LIVE_JSON = "https://hub.kelee.one/list.json"

# 标签筛选最多展示的热门标签数
TOP_TAGS = 16
PAGE_SIZE = 12


def extract_resource(url: str) -> str:
    """从 loon://import?plugin=<url> 之类的链接中提取真实资源地址。"""
    p = urlparse(url)
    if p.scheme in ("http", "https"):
        return url
    q = parse_qs(p.query)
    for key in ("plugin", "config", "module", "url", "file"):
        if key in q:
            return q[key][0]
    return url


def transform(items):
    """把 list.json 的 lists 条目转换为页面模块对象（与前端 JS 保持同一逻辑）。"""
    modules = []
    for it in items:
        url = it.get("url", "")
        lpx = extract_resource(url)
        install = "hako://install-module?url=" + quote(lpx, safe="")
        authors = it.get("author", []) or []
        a0 = authors[0] if authors else {}
        tags = it.get("tag", []) or []
        modules.append({
            "name": it.get("name", ""),
            "desc": (it.get("desc", "") or "").strip(),
            "tags": tags,
            "icon": it.get("icon", ""),
            "date": it.get("date", ""),
            "author": a0.get("name", ""),
            "authorHome": a0.get("homepage", ""),
            "lpx": lpx,
            "install": install,
            "loon": url,
        })
    modules.sort(key=lambda m: m["date"] or "", reverse=True)
    return modules


def top_tags(modules, n=TOP_TAGS):
    c = Counter()
    for m in modules:
        for t in (m.get("tags") or []):
            c[t] += 1
    return [t for t, _ in c.most_common(n)]


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, LIST_JSON), encoding="utf-8") as f:
        data = json.load(f)

    items = data.get("lists", [])
    modules = transform(items)
    tags = top_tags(modules)
    with open(os.path.join(here, "modules.json"), "w", encoding="utf-8") as f:
        json.dump(modules, f, ensure_ascii=False, indent=2)
    print(f"共收集 {len(modules)} 个模块；热门标签 {len(tags)} 个")

    # 内联到页面的是「原始快照」(lists/notice/name)，前端负责转换 + 实时拉取
    snapshot = {
        "lists": items,
        "notice": data.get("notice", []),
        "name": data.get("name", SRC_NAME),
        "srcUrl": SRC_URL,
        "liveUrl": LIVE_JSON,
        "buildDate": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
    }

    # Quantumult X 资源（构建时快照，来自三个 GitHub 仓库，由 fetch_qx.py 采集）
    qx_path = os.path.join(here, "quantumult.json")
    if os.path.exists(qx_path):
        with open(qx_path, encoding="utf-8") as f:
            snapshot["qx"] = json.load(f)
        print(f"已载入 Quantumult X 资源 {len(snapshot['qx'].get('modules', []))} 个")

    build_html(here, snapshot)


def build_html(here, snapshot):
    html = HTML_TEMPLATE.replace("/*__SNAPSHOT__*/", json.dumps(snapshot, ensure_ascii=False))
    html = html.replace("__SRCURL__", snapshot.get("srcUrl", SRC_URL))
    html = html.replace("__SRCNAME__", snapshot.get("name", SRC_NAME))
    with open(os.path.join(here, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)
    print("已生成 index.html（含内联兜底快照 + 运行时实时同步）")


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover" />
<title>Clash / Loon 模块导入 · 可莉插件中心</title>
<meta name="description" content="从可莉的插件中心收集的 Loon / Clash 模块，浏览器一键拉起 Clash 或 Loon 导入；另收录 Quantumult X 重写与规则合集（可莉重写库 / 墨鱼手记 / 毒奶特供），支持 quantumult-x 与 hako 协议导入。" />
<meta name="theme-color" content="#f5f5f7" />
<style>
  :root{
    --bg:#f5f5f7; --bg2:rgba(255,255,255,.72); --card:rgba(255,255,255,.78); --card2:rgba(255,255,255,.95);
    --line:rgba(0,0,0,.08); --text:#1d1d1f; --muted:#6e6e73; --accent:#0071e3; --accent2:#34c759;
    --radius:18px; --shadow:0 2px 10px rgba(0,0,0,.05); --shadow-lg:0 12px 40px rgba(0,0,0,.10);
    --maxw:1040px; --on-accent:#fff;
    --notice-bg:rgba(255,184,0,.10); --notice-text:#8a5b12; --notice-line:rgba(255,184,0,.28);
    --glass:blur(20px) saturate(180%); --ease:cubic-bezier(.4,0,.2,1);
  }
  :root[data-theme="dark"]{
    --bg:#000; --bg2:rgba(28,28,30,.66); --card:rgba(28,28,30,.66); --card2:rgba(44,44,46,.9);
    --line:rgba(255,255,255,.12); --text:#f5f5f7; --muted:#98989d; --accent:#0a84ff; --accent2:#30d158;
    --shadow:0 2px 10px rgba(0,0,0,.4); --shadow-lg:0 16px 50px rgba(0,0,0,.6);
    --notice-bg:rgba(255,184,0,.12); --notice-text:#e8c07a; --notice-line:rgba(255,184,0,.3);
  }
  *{box-sizing:border-box}
  html,body{margin:0;padding:0}
  body{
    background:var(--bg);
    color:var(--text);
    font-family:-apple-system,BlinkMacSystemFont,"SF Pro Display","SF Pro Text","Segoe UI",Roboto,"PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif;
    -webkit-font-smoothing:antialiased;-moz-osx-font-smoothing:grayscale;line-height:1.5;min-height:100vh;letter-spacing:.2px;
  }
  body::before{content:"";position:fixed;inset:0;pointer-events:none;z-index:-1;
    background:radial-gradient(1200px 620px at 50% -220px, rgba(0,113,227,.08), transparent 62%);}
  :root[data-theme="dark"] body::before{background:radial-gradient(1200px 620px at 50% -220px, rgba(10,132,255,.12), transparent 62%);}
  a{color:inherit;text-decoration:none}
  .wrap{max-width:var(--maxw);margin:0 auto;padding:48px 20px calc(56px + env(safe-area-inset-bottom));position:relative;}

  /* ---------- Hero ---------- */
  .hero{
    position:relative;text-align:center;padding:56px 24px 44px;margin-bottom:28px;overflow:hidden;
    background:linear-gradient(135deg, rgba(0,113,227,.10), rgba(52,199,89,.08));
    border:1px solid var(--line);border-radius:28px;
    -webkit-backdrop-filter:var(--glass);backdrop-filter:var(--glass);box-shadow:var(--shadow-lg);
  }
  .hero .badge{
    width:74px;height:74px;margin:0 auto 18px;border-radius:20px;
    display:flex;align-items:center;justify-content:center;font-size:40px;
    background:linear-gradient(145deg,#0a84ff,#30d158);box-shadow:0 10px 30px rgba(0,113,227,.35);
    transform:rotate(-6deg);
  }
  .hero h1{margin:0 0 12px;font-size:clamp(28px,5.5vw,44px);font-weight:700;letter-spacing:-.5px;line-height:1.1;
    background:linear-gradient(120deg,#0071e3,#5e5ce6,#0a84ff);-webkit-background-clip:text;background-clip:text;color:transparent;}
  .hero p{margin:0 auto;color:var(--muted);max-width:680px;font-size:16px;line-height:1.55;}
  .src{display:inline-flex;gap:6px;align-items:center;margin-top:20px;font-size:13px;color:var(--muted);
    background:var(--bg2);border:1px solid var(--line);padding:7px 16px;border-radius:980px;
    -webkit-backdrop-filter:blur(10px);backdrop-filter:blur(10px);}
  .src b{color:var(--text);font-weight:600}
  .src a{color:var(--accent)}
  .sync{margin-top:14px;font-size:13px;color:var(--muted);}
  .sync .dot{display:inline-block;width:7px;height:7px;border-radius:50%;margin-right:7px;vertical-align:middle;background:var(--muted)}
  .sync.ok .dot{background:var(--accent2);box-shadow:0 0 10px var(--accent2)}
  .sync.warn .dot{background:#ff9f0a;box-shadow:0 0 10px #ff9f0a}
  .sync.load .dot{background:var(--accent);animation:pulse 1.1s infinite}
  @keyframes pulse{0%,100%{opacity:.35;transform:scale(.85)}50%{opacity:1;transform:scale(1)}}

  .notice{margin:0 0 24px;padding:14px 18px;border-radius:14px;border:1px solid var(--notice-line);
    background:var(--notice-bg);color:var(--notice-text);font-size:13.5px;line-height:1.65;
    -webkit-backdrop-filter:blur(10px);backdrop-filter:blur(10px);}
  .notice div{margin:3px 0}

  .toolbar{position:sticky;top:56px;z-index:30;margin:0 0 18px;padding:14px;border-radius:20px;
    background:var(--bg2);border:1px solid var(--line);box-shadow:var(--shadow);
    -webkit-backdrop-filter:var(--glass);backdrop-filter:var(--glass);}
  .controls{display:flex;gap:12px;flex-wrap:wrap;align-items:center;margin-bottom:14px;}
  .search{flex:1 1 260px;min-width:0;position:relative;}
  .search input{width:100%;padding:13px 42px 13px 44px;border-radius:980px;border:1px solid var(--line);
    background:var(--bg2);color:var(--text);font-size:15px;outline:none;transition:.25s var(--ease);
    -webkit-backdrop-filter:blur(12px);backdrop-filter:blur(12px);}
  .search input:focus{border-color:var(--accent);box-shadow:0 0 0 4px rgba(0,113,227,.15)}
  .search input::placeholder{color:var(--muted)}
  .search svg{position:absolute;left:16px;top:50%;transform:translateY(-50%);opacity:.5}
  .search .clear{position:absolute;right:10px;top:50%;transform:translateY(-50%);border:none;background:var(--line);
    color:var(--muted);font-size:18px;line-height:1;cursor:pointer;padding:0;width:24px;height:24px;border-radius:50%;
    display:none;align-items:center;justify-content:center;transition:.15s var(--ease);}
  .search .clear:hover{color:var(--text);background:var(--muted)}
  .search .clear.show{display:flex}

  .chips{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:18px;}
  .sources{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:16px}
  .sources .src-label{font-size:13px;color:var(--muted);margin-right:4px;user-select:none;font-weight:600}
  .sources .chip{font-weight:600}
  .chip{padding:8px 15px;border-radius:980px;border:1px solid var(--line);background:var(--bg2);
    color:var(--muted);font-size:13px;cursor:pointer;transition:.2s var(--ease);user-select:none;white-space:nowrap;
    -webkit-backdrop-filter:blur(10px);backdrop-filter:blur(10px);}
  .chip:hover{color:var(--text);border-color:var(--accent)}
  .chip.active{background:var(--accent);color:#fff;border-color:transparent;font-weight:600;box-shadow:0 4px 14px rgba(0,113,227,.3)}

  .count{display:inline-block;color:var(--muted);font-size:13px;margin:0 2px 18px;font-weight:500;
    background:var(--bg2);border:1px solid var(--line);padding:6px 14px;border-radius:999px;
    -webkit-backdrop-filter:blur(10px);backdrop-filter:blur(10px);}

  .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:18px;}
  .card{background:var(--card);border:1px solid var(--line);border-radius:var(--radius);padding:18px;
    display:flex;flex-direction:column;gap:12px;transition:transform .25s var(--ease),box-shadow .25s var(--ease),border-color .25s var(--ease);
    position:relative;overflow:hidden;-webkit-backdrop-filter:var(--glass);backdrop-filter:var(--glass);}
  .card:hover{transform:translateY(-4px);box-shadow:var(--shadow-lg);border-color:rgba(0,113,227,.4)}
  .grid>.card{height:100%}
  .card .desc{margin-top:0}
  .card .acts{margin-top:auto}
  .card .head{display:flex;gap:13px;align-items:center}
  .icon{flex:0 0 50px;width:50px;height:50px;border-radius:14px;background:var(--bg2);border:1px solid var(--line);
    display:flex;align-items:center;justify-content:center;font-size:26px;overflow:hidden}
  .icon img{width:100%;height:100%;object-fit:contain}
  .card h3{margin:0;font-size:16.5px;font-weight:600;line-height:1.3;letter-spacing:-.2px}
  .meta{font-size:12px;color:var(--muted);margin-top:3px}
  .card .src-badge{position:absolute;top:14px;right:14px;font-size:11px;font-weight:600;padding:3px 9px;border-radius:999px;
    white-space:nowrap;border:1px solid transparent;backdrop-filter:blur(6px);-webkit-backdrop-filter:blur(6px);}
  .card .src-badge[data-r="kelee"],.card .src-badge[data-r="klee"]{color:#0071e3;background:rgba(0,113,227,.10);border-color:rgba(0,113,227,.22)}
  .card .src-badge[data-r="ddg"]{color:#0a9d8e;background:rgba(10,157,142,.12);border-color:rgba(10,157,142,.24)}
  .card .src-badge[data-r="adblock"]{color:#e08600;background:rgba(224,134,0,.12);border-color:rgba(224,134,0,.24)}
  .card .src-badge[data-r="qx"]{color:var(--muted);background:var(--bg2);border-color:var(--line)}
  .card::after{content:"";position:absolute;inset:0;border-radius:inherit;pointer-events:none;
    background:radial-gradient(120% 70% at 50% 0%, rgba(0,113,227,.10), transparent 55%);opacity:0;transition:opacity .25s var(--ease);}
  .card:hover::after{opacity:1}
  .desc{font-size:13.5px;color:var(--muted);line-height:1.55;
    min-height:calc(3 * 1.55em);/* 预留 3 行：不足的卡片以空行占位，保证按钮行对齐 */
    display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}
  .tags{display:flex;gap:7px;flex-wrap:wrap}
  .tag{font-size:11.5px;color:var(--accent);background:rgba(0,113,227,.10);border:1px solid rgba(0,113,227,.18);
    padding:3px 9px;border-radius:980px;white-space:nowrap}
  .acts{display:flex;flex-direction:column;gap:10px;margin-top:2px}
  .btn{display:inline-flex;align-items:center;justify-content:center;gap:7px;text-align:center;
    padding:11px 14px;border-radius:12px;font-size:14px;font-weight:600;
    cursor:pointer;border:1px solid var(--line);background:var(--bg2);color:var(--text);transition:.2s var(--ease);min-width:0;white-space:nowrap;
    -webkit-tap-highlight-color:transparent;}
  .btn svg{flex:0 0 auto}
  .btn.primary{width:100%;background:var(--accent);color:#fff;border-color:transparent;box-shadow:0 4px 16px rgba(0,113,227,.28)}
  .btn.primary:hover{filter:brightness(1.06);transform:translateY(-1px)}
  .btn.primary:active{transform:scale(.985)}
  .btn:hover{border-color:var(--accent)}
  .btn.secondary{flex:1 1 0;font-size:13px;color:var(--text);font-weight:500;background:var(--bg2);}
  .btn.secondary.wide{flex:2 1 0}
  .btn.secondary:hover{color:var(--accent);border-color:var(--accent)}
  .sec-row{display:flex;gap:10px}

  .empty{text-align:center;color:var(--muted);padding:72px 10px;font-size:16px}
  .empty-ico{font-size:46px;margin-bottom:14px;opacity:.85}
  .empty-sub{font-size:13px;margin-top:8px;opacity:.8}

  .pager{display:flex;justify-content:center;align-items:center;gap:8px;margin-top:32px;flex-wrap:wrap}
  .pager button{min-width:40px;height:40px;padding:0 12px;border-radius:980px;border:1px solid var(--line);
    background:var(--bg2);color:var(--text);font-size:14px;font-weight:500;cursor:pointer;transition:.2s var(--ease);
    -webkit-backdrop-filter:blur(10px);backdrop-filter:blur(10px);}
  .pager button:hover:not(:disabled){border-color:var(--accent);color:var(--accent)}
  .pager button.active{background:var(--accent);color:#fff;border-color:transparent;font-weight:600}
  .pager button:disabled{opacity:.3;cursor:not-allowed}
  .pager .ellipsis{color:var(--muted);padding:0 4px}

  footer{margin-top:44px;text-align:center;color:var(--muted);font-size:12.5px;line-height:1.9;overflow-wrap:anywhere;word-break:break-word;
    border-top:1px solid var(--line);padding-top:28px;}
  footer a{color:var(--accent)}
  footer code{font-size:11.5px;background:var(--bg2);border:1px solid var(--line);padding:2px 7px;border-radius:7px;
    white-space:normal;word-break:break-all;}
  footer .recommend{display:inline-block;margin-top:14px;padding-top:14px;border-top:1px dashed var(--line);
    color:var(--text);font-weight:600;font-size:13px;}
  footer .recommend a{color:var(--accent)}

  #toast{position:fixed;left:50%;bottom:28px;transform:translateX(-50%) translateY(20px);
    background:rgba(0,0,0,.82);color:#fff;padding:12px 20px;border-radius:980px;font-weight:600;font-size:14px;
    opacity:0;pointer-events:none;transition:.3s var(--ease);z-index:99;
    -webkit-backdrop-filter:blur(20px);backdrop-filter:blur(20px);box-shadow:0 10px 40px rgba(0,0,0,.4)}
  #toast.show{opacity:1;transform:translateX(-50%) translateY(0)}

  .theme-switch{position:fixed;top:18px;right:18px;z-index:50;display:flex;gap:0;padding:3px;
    background:var(--bg2);border:1px solid var(--line);border-radius:980px;box-shadow:var(--shadow);
    -webkit-backdrop-filter:var(--glass);backdrop-filter:var(--glass);}
  .theme-switch button{font:inherit;font-size:12px;font-weight:600;color:var(--muted);background:transparent;
    border:none;padding:8px 11px;border-radius:980px;cursor:pointer;transition:.2s var(--ease);white-space:nowrap;
    display:inline-flex;align-items:center;justify-content:center;line-height:0}
  .theme-switch button svg{display:block}
  .theme-switch button.active{background:var(--accent);color:#fff;box-shadow:0 2px 8px rgba(0,113,227,.35)}
  .theme-switch button:hover:not(.active){color:var(--text)}

  @media (max-width:560px){
    .wrap{padding:24px 16px calc(44px + env(safe-area-inset-bottom))}
    .grid{grid-template-columns:1fr;gap:14px}
    .hero{padding:60px 18px 32px;border-radius:22px}
    .hero h1{font-size:clamp(24px,7vw,32px)}
    .hero p{font-size:14.5px}
    .src{margin-top:16px;font-size:12px;padding:6px 13px}
    .toolbar{position:static;top:auto;padding:12px;margin-bottom:14px;box-shadow:none}
    .search{flex:1 1 100%}
    .btn.secondary{font-size:12.5px;padding:10px 6px}
    .theme-switch{position:absolute;top:10px;right:10px}
    .theme-switch button{padding:6px 9px}
    footer{text-align:left;font-size:12px}
    footer code{font-size:11px}
  }
</style>
<script>
/* 尽早应用主题，避免浅色用户看到深色闪烁；默认「自动」跟随系统 */
(function(){try{
  var m=localStorage.getItem('clashmod-theme')||'auto';
  var t=m==='auto'?(window.matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light'):m;
  document.documentElement.dataset.theme=t;
}catch(e){}})();
</script>
</head>
<body>
  <div class="wrap">
    <div class="theme-switch" id="themeSwitch" role="group" aria-label="主题切换">
      <button data-theme="light" title="日间模式" aria-label="日间模式">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>
      </button>
      <button data-theme="dark" title="夜间模式" aria-label="夜间模式">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.8A9 9 0 1 1 11.2 3 7 7 0 0 0 21 12.8z"/></svg>
      </button>
      <button data-theme="auto" title="自动（跟随系统）" aria-label="自动（跟随系统）">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><path d="M12 3a9 9 0 0 1 0 18z" fill="currentColor" stroke="none"/></svg>
      </button>
    </div>
    <header class="hero">
      <div class="badge">⚡</div>
      <h1>Clash · Loon · Quantumult X 模块导入</h1>
      <p>可莉插件中心的 Loon 模块，一键拉起 Clash / Loon 导入；另收录 Quantumult X 重写与规则合集（可莉重写库 / 墨鱼手记 / 毒奶特供），支持 Quantumult X 与 hako:// 协议导入。</p>
      <div class="src">数据来源 · <a href="__SRCURL__" target="_blank" rel="noopener"><b>__SRCNAME__</b></a> · Quantumult X 资源合集 · 共 <span id="total">0</span> 个模块</div>
      <div class="sync load" id="sync"><span class="dot"></span><span id="syncText">正在同步源站最新模块…</span></div>
    </header>

    <div class="notice" id="notice"></div>

    <div class="toolbar">
      <div class="sources" id="sources">
        <span class="src-label">来源</span>
        <div class="chip active" data-src="all">全部</div>
        <div class="chip" data-src="kelee">可莉插件中心</div>
        <div class="chip" data-src="qx">Quantumult X</div>
      </div>

      <div class="controls">
        <div class="search">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/></svg>
          <input id="q" type="search" placeholder="搜索模块名称 / 描述 / 标签 / 作者…" autocomplete="off" />
          <button class="clear" id="clearBtn" type="button" aria-label="清空搜索">×</button>
        </div>
      </div>
      <div class="chips" id="chips"></div>
    </div>

    <div class="count" id="count"></div>
    <div class="grid" id="grid"></div>
    <div class="empty" id="empty" style="display:none">
      <div class="empty-ico">🔍</div>
      <div>没有匹配的模块</div>
      <div class="empty-sub">换个关键词，或点上方标签 / 来源重新筛选</div>
    </div>
    <div class="pager" id="pager"></div>

    <footer>
      本页为资源索引，模块版权归原作者所有（CC BY-NC-SA 4.0），数据来自 __SRCNAME__。<br/>
      「导入 Clash」使用 <code>hako://install-module</code> 协议；「Loon」使用 <code>loon://import</code> 协议；「导入 Quantumult X」使用 <code>quantumult-x:///add-resource</code> 协议（保留现有资源追加导入）。<br/>
      Quantumult X 资源的导入链接直连 GitHub 仓库，点一下拉取的永远是仓库最新版；其页面数据为构建时快照。<br/>
      可莉插件中心部分：每次打开会自动同步源站最新数据，源站不可达时回退到内置缓存快照。<br/>
      若设备未安装对应客户端，链接将无法拉起，可使用「复制」按钮手动导入。<br/>
      <span class="recommend">友情推荐 · <a href="https://xn--4gqx1hgtfdmt.com/#/register?code=ayOVtXLb" target="_blank" rel="noopener">一分机场</a>（高速稳定，注册即送流量）</span>
    </footer>
  </div>

  <div id="toast"></div>

<script>
/* 内联兜底快照（构建时从 list.json 写入），实时拉取失败时使用 */
const SNAPSHOT = /*__SNAPSHOT__*/;

const PAGE_SIZE = 12;

/* 与 Python 端 transform 保持一致的转换 + 编码（复刻 urllib.parse.quote(safe="")） */
function pyQuote(s){
  return encodeURIComponent(s).replace(/[!*'()~]/g, c=>({
    '!':'%21','*':'%2A',"'":'%27','(':'%28',')':'%29','~':'%7E'
  }[c]));
}
function extractResource(url){
  try{
    const u=new URL(url);
    if(u.protocol==='http:'||u.protocol==='https:') return url;
    const params=new URLSearchParams(u.search);
    for(const k of ['plugin','config','module','url','file']){
      if(params.has(k)) return params.get(k);
    }
    return url;
  }catch(e){ return url; }
}
function transformLists(lists){
  const mods=[];
  for(const it of (lists||[])){
    const lpx=extractResource(it.url||'');
    const install='hako://install-module?url='+pyQuote(lpx);
    const authors=it.author||[];
    const a0=authors[0]||{};
    const tags=it.tag||[];
    mods.push({
      name:it.name||'', desc:(it.desc||'').trim(), tags, icon:it.icon||'',
      date:it.date||'', author:a0.name||'', authorHome:a0.homepage||'',
      lpx, install, loon:it.url||''
    });
  }
  mods.sort((a,b)=>(b.date||'').localeCompare(a.date||''));
  return mods;
}
function computeTopTags(mods,n){
  const c={};
  for(const m of mods) for(const t of (m.tags||[])) c[t]=(c[t]||0)+1;
  return Object.entries(c).sort((a,b)=>b[1]-a[1]).slice(0,n).map(x=>x[0]);
}

/* ===== Quantumult X 合集：quantumult-x:///add-resource（保留现有资源追加导入）+ hako:// 双协议 ===== */
function qxInstall(url, kind, name){
  const key = kind==='rule' ? 'filter_remote' : 'rewrite_remote';
  const tag = String(name||'').replace(/,/g,'，').slice(0,40);
  const payload = JSON.stringify({[key]:[url+', tag='+tag]});
  return 'quantumult-x:///add-resource?remote-resource='+pyQuote(payload);
}
function transformQx(qx){
  if(!qx || !qx.modules) return [];
  return qx.modules.map(m=>({
    name:m.name||'', desc:(m.desc||'').trim(), tags:m.tags||[], icon:m.icon||'',
    date:'', author:m.author||'', authorHome:'',
    lpx:m.url||'', raw:m.url||'', kind:m.kind||'rewrite', repo:m.repo||'',
    source:'qx',
    install:qxInstall(m.url||'', m.kind, m.name),
    hako:'hako://install-module?url='+pyQuote(m.url||''),
    loon:'loon://import?plugin='+encodeURIComponent(m.url||'')
  }));
}

let KELEE = transformLists(SNAPSHOT.lists);
let QX = transformQx(SNAPSHOT.qx);
let MODULES = KELEE.concat(QX);
let TOP_TAGS = computeTopTags(MODULES, 16);
let state = { q:"", tag:"全部", page:1, source:"all" };

/* 全部视图下两类资源交替排列，保证两边都能被看到 */
function interleave(a,b){
  const out=[]; const n=Math.max(a.length,b.length);
  for(let i=0;i<n;i++){ if(i<a.length) out.push(a[i]); if(i<b.length) out.push(b[i]); }
  return out;
}
function currentSet(){
  if(state.source==='kelee') return KELEE;
  if(state.source==='qx') return QX;
  return interleave(KELEE,QX);
}

const grid=document.getElementById('grid');
const empty=document.getElementById('empty');
const pager=document.getElementById('pager');
const countEl=document.getElementById('count');
const totalEl=document.getElementById('total');
const chipsEl=document.getElementById('chips');
const noticeEl=document.getElementById('notice');
const syncEl=document.getElementById('sync');
const syncText=document.getElementById('syncText');
const SRC_NAME=SNAPSHOT.name||'可莉的插件中心';

/* ===== 主题切换：日间 / 夜间 / 自动（默认自动，跟随系统，localStorage 记忆） ===== */
const THEME_KEY='clashmod-theme';
const themeSwitch=document.getElementById('themeSwitch');
let currentTheme='auto';
try{ currentTheme=localStorage.getItem(THEME_KEY)||'auto'; }catch(e){}
const prefersDark=window.matchMedia('(prefers-color-scheme: dark)');
function applyTheme(mode){
  document.documentElement.dataset.theme=(mode==='auto')?(prefersDark.matches?'dark':'light'):mode;
}
function syncThemeButtons(){
  [...themeSwitch.children].forEach(b=>b.classList.toggle('active',b.dataset.theme===currentTheme));
}
applyTheme(currentTheme); syncThemeButtons();
themeSwitch.addEventListener('click',e=>{
  const btn=e.target.closest('button'); if(!btn) return;
  currentTheme=btn.dataset.theme;
  try{ localStorage.setItem(THEME_KEY,currentTheme); }catch(err){}
  applyTheme(currentTheme); syncThemeButtons();
});
prefersDark.addEventListener?.('change',()=>{ if(currentTheme==='auto') applyTheme('auto'); });

totalEl.textContent=MODULES.length;

if(SNAPSHOT.notice && SNAPSHOT.notice.length){
  noticeEl.innerHTML=SNAPSHOT.notice.map(n=>`<div>• ${esc(n)}</div>`).join('');
}else{ noticeEl.style.display='none'; }

function esc(s){return String(s==null?'':s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));}

function buildChips(){
  chipsEl.innerHTML='';
  ["全部",...TOP_TAGS].forEach(t=>{
    const el=document.createElement('div');
    el.className='chip'+(t===state.tag?" active":"");
    el.textContent=t; el.dataset.tag=t;
    el.onclick=()=>{ state.tag=t; state.page=1;
      [...chipsEl.children].forEach(x=>x.classList.toggle('active',x.dataset.tag===t)); render(); };
    chipsEl.appendChild(el);
  });
}
function refreshTags(){
  TOP_TAGS=computeTopTags(currentSet(),16);
  buildChips();
}
refreshTags();

function filtered(){
  const q=state.q.trim().toLowerCase();
  return currentSet().filter(m=>{
    if(state.tag!=="全部" && !(m.tags||[]).includes(state.tag)) return false;
    if(!q) return true;
    const hay=(m.name+" "+(m.desc||"")+" "+(m.tags||[]).join(" ")+" "+(m.author||"")).toLowerCase();
    return hay.includes(q);
  });
}

const SVG_DOWN='<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3v12"/><path d="m7 10 5 5 5-5"/><path d="M4 19h16"/></svg>';
const SVG_BOLT='<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M13 2 4.5 13.5H11L10 22l8.5-11.5H12z"/></svg>';
const SVG_LINK='<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7.5.5l3-3a5 5 0 0 0-7-7l-1.7 1.7"/><path d="M14 11a5 5 0 0 0-7.5-.5l-3 3a5 5 0 0 0 7 7l1.7-1.7"/></svg>';
const SVG_COPY='<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="12" height="12" rx="2.5"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>';

function card(m){
  const tags=(m.tags||[]).slice(0,4).map(t=>`<span class="tag">${esc(t)}</span>`).join('');
  const author=m.author?`${esc(m.author)}`:'';
  const when=m.date?`${esc((m.date||'').slice(0,10))}`:'';
  const meta=[author,when].filter(Boolean).join(' · ');
  const isQx=m.source==='qx';
  const rk = isQx ? ({'墨鱼手记':'ddg','毒奶特供':'adblock','可莉重写库':'klee'}[m.repo]||'qx') : 'kelee';
  const rlabel = isQx ? (m.repo||'Quantumult X') : '可莉插件中心';
  const primary=`<a class="btn primary" href="${esc(isQx?m.hako:m.install)}">${SVG_DOWN}导入 Clash</a>`;
  const secondary=isQx
    ?`<a class="btn secondary wide" href="${esc(m.install)}" title="用 quantumult-x:///add-resource 协议导入">${SVG_BOLT}导入 Quantumult X</a>`
    :`<a class="btn secondary" href="${esc(m.loon)}">${SVG_BOLT}Loon 导入</a>`;
  return `
  <div class="card">
    <span class="src-badge" data-r="${rk}">${esc(rlabel)}</span>
    <div class="head">
      <div class="icon"><span>🧩</span><img src="${esc(m.icon)}" alt="" loading="lazy" onload="this.previousElementSibling.remove()" onerror="this.remove()"></div>
      <div style="min-width:0">
        <h3>${esc(m.name)}</h3>
        <div class="meta">${meta}</div>
      </div>
    </div>
    <div class="desc">${esc(m.desc)||'—'}</div>
    <div class="tags">${tags}</div>
    <div class="acts">
      ${primary}
      <div class="sec-row">
        ${secondary}
        <button class="btn secondary" data-copy="${esc(m.lpx)}" title="复制资源链接">
          ${SVG_COPY}
          复制链接
        </button>
      </div>
    </div>
  </div>`;
}

function render(){
  const list=filtered();
  const totalPages=Math.max(1,Math.ceil(list.length/PAGE_SIZE));
  if(state.page>totalPages) state.page=totalPages;
  const start=(state.page-1)*PAGE_SIZE;
  const pageItems=list.slice(start,start+PAGE_SIZE);
  grid.innerHTML=pageItems.map(card).join('');
  empty.style.display=list.length?'none':'block';
  countEl.textContent=`显示 ${list.length?start+1:0}–${Math.min(start+PAGE_SIZE,list.length)} / 共 ${list.length} 项`;
  pager.innerHTML='';
  if(totalPages>1){
    const mk=(label,page,opts={})=>{
      const b=document.createElement('button'); b.textContent=label;
      if(opts.active)b.classList.add('active');
      if(opts.disabled)b.disabled=true;
      else b.onclick=()=>{state.page=page;render();const y=(grid.getBoundingClientRect().top+window.scrollY-12);window.scrollTo({top:y,behavior:'smooth'});};
      return b;
    };
    pager.appendChild(mk('‹',state.page-1,{disabled:state.page===1}));
    const nums=[];
    for(let i=1;i<=totalPages;i++){
      if(i===1||i===totalPages||Math.abs(i-state.page)<=1) nums.push(i);
      else if(nums[nums.length-1]!=='…') nums.push('…');
    }
    nums.forEach(i=>{
      if(i==='…'){const s=document.createElement('span');s.className='ellipsis';s.textContent='…';pager.appendChild(s);}
      else pager.appendChild(mk(String(i),i,{active:i===state.page}));
    });
    pager.appendChild(mk('›',state.page+1,{disabled:state.page===totalPages}));
  }
}

grid.addEventListener('click',e=>{
  const t=e.target.closest('[data-copy]');
  if(!t) return;
  const url=t.dataset.copy;
  navigator.clipboard?.writeText(url).then(()=>toast('链接已复制 ✓')).catch(()=>toast('复制失败，请手动复制'));
});

function toast(msg){
  const el=document.getElementById('toast');
  el.textContent=msg;el.classList.add('show');
  clearTimeout(el._t);el._t=setTimeout(()=>el.classList.remove('show'),1600);
}

const qEl=document.getElementById('q');
const clearBtn=document.getElementById('clearBtn');
function syncClear(){ clearBtn.classList.toggle('show', qEl.value.length>0); }
qEl.addEventListener('input',e=>{state.q=e.target.value;state.page=1;render();syncClear();});
clearBtn.addEventListener('click',()=>{ qEl.value=''; state.q=''; state.page=1; render(); syncClear(); qEl.focus(); });

/* 来源筛选：全部 / 可莉插件中心 / Quantumult X */
const sourcesEl=document.getElementById('sources');
sourcesEl.addEventListener('click',e=>{
  const el=e.target.closest('.chip'); if(!el) return;
  const src=el.dataset.src; if(!src||src===state.source) return;
  state.source=src; state.tag='全部'; state.page=1;
  [...sourcesEl.querySelectorAll('.chip')].forEach(x=>x.classList.toggle('active',x.dataset.src===src));
  refreshTags(); updateSyncForSource(); render();
});

/* 先用快照秒开，再根据缓存策略决定是否需要请求源站 */
render();

let keleeSync={cls:'load',text:'正在同步源站最新模块…'};
function setSync(cls,text,remember){
  syncEl.className='sync '+cls; syncText.textContent=text;
  if(remember!==false) keleeSync={cls,text};
}
function updateSyncForSource(){
  if(state.source==='qx'){
    setSync('ok',`Quantumult X 资源共 ${QX.length} 个（构建于 ${SNAPSHOT.buildDate||'—'}），导入链接直连 GitHub 仓库，始终拉取最新版`,false);
  }else{
    setSync(keeleeSync.cls,keeleeSync.text,false);
  }
}
function fmtTime(d){
  const p=n=>String(n).padStart(2,'0');
  return `${d.getFullYear()}-${p(d.getMonth()+1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`;
}
function agoText(ts){
  const sec=Math.round((Date.now()-ts)/1000);
  if(sec<60) return `${sec} 秒前`;
  if(sec<3600) return `${Math.floor(sec/60)} 分钟前`;
  return `${Math.floor(sec/3600)} 小时前`;
}

/* 本地缓存：10 分钟内不重复请求源站，优先用缓存，降低刷新时的请求频次 */
const CACHE_KEY='clashmod-cache';
const CACHE_TTL=10*60*1000; // 10 分钟
function readCache(){
  try{
    const raw=localStorage.getItem(CACHE_KEY);
    if(!raw) return null;
    const obj=JSON.parse(raw);
    if(!obj||!Array.isArray(obj.lists)||!obj.ts) return null;
    return obj;
  }catch(e){ return null; }
}
function writeCache(lists){
  try{ localStorage.setItem(CACHE_KEY,JSON.stringify({lists,ts:Date.now()})); }catch(e){}
}
function applyModules(lists,extra){
  const live=transformLists(lists);
  if(!live.length) return false;
  KELEE=live;                        /* 实时同步只替换可莉插件中心部分，QX 为静态快照 */
  MODULES=KELEE.concat(QX);
  refreshTags(); totalEl.textContent=MODULES.length; render();
  if(extra) setSync(extra.cls,extra.text);
  return true;
}

/* 实时同步源站：源站 CORS 头为重复的 "*, *"（非法），直连必然被浏览器拒绝，
   因此走支持 CORS 的代理：jina（稳定）→ allorigins（备用）→ 内置快照兜底 */
const LIVE_URL=SNAPSHOT.liveUrl||'https://hub.kelee.one/list.json';
const LIVE_SOURCES=[
  {url:'https://r.jina.ai/'+LIVE_URL, parse:async r=>{
    const t=await r.text();
    const i=t.indexOf('Markdown Content:');
    const s=i>=0?t.indexOf('{',i):t.indexOf('{');
    if(s<0) throw new Error('no json');
    return JSON.parse(t.slice(s));
  }},
  {url:'https://api.allorigins.win/raw?url='+encodeURIComponent(LIVE_URL), parse:r=>r.json()}
];

async function syncLive(){
  for(let i=0;i<LIVE_SOURCES.length;i++){
    const src=LIVE_SOURCES[i];
    try{
      const res=await fetch(src.url,{cache:'no-cache'});
      if(!res.ok) throw new Error('HTTP '+res.status);
      const data=await src.parse(res);
      const lists=data.lists||[];
      if(!lists.length) throw new Error('empty');
      writeCache(lists);
      applyModules(lists,{cls:'ok',text:`已实时同步 ${MODULES.length} 个模块（${fmtTime(new Date())}）${i>0?' · 经代理':''}`});
      return true;
    }catch(err){ /* 换下一个源 */ }
  }
  return false;
}

(async function init(){
  const cache=readCache();
  if(cache && (Date.now()-cache.ts) < CACHE_TTL){
    // 10 分钟内的缓存：直接用，不再请求源站
    applyModules(cache.lists,{cls:'ok',text:`已使用本地缓存（${agoText(cache.ts)}同步，10 分钟内不再请求源站）`});
  }else{
    // 缓存过期/缺失：请求源站；失败则回退到本地缓存，再不行才用内置快照
    const ok=await syncLive();
    if(!ok){
      if(cache && cache.lists.length){
        applyModules(cache.lists,{cls:'warn',text:`源站暂不可达，已使用本地缓存（${agoText(cache.ts)}同步）`});
      }else{
        setSync('warn','当前使用内置缓存快照（源站与代理均不可达，仍为最新已知数据）');
      }
    }
  }
})();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main()
