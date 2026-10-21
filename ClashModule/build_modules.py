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
<style>
  :root{
    --bg:#0f1117; --bg2:#161a23; --card:#1b2030; --card2:#20283a;
    --line:#2a3245; --text:#e7ebf3; --muted:#9aa6bd; --accent:#6c8cff;
    --accent2:#48d1a0; --radius:16px; --shadow:0 8px 30px rgba(0,0,0,.35);
    --maxw:1080px;
    --deco1:rgba(108,140,255,.14); --deco2:rgba(72,209,160,.09);
    --glow1:rgba(108,140,255,.16); --glow2:rgba(72,209,160,.10); --glow3:rgba(108,140,255,.18);
    --on-accent:#0b0e16; --on-accent2:#06281f;
    --notice-bg:rgba(255,182,72,.08); --notice-text:#e8b478; --notice-line:rgba(255,182,72,.22);
  }
  :root[data-theme="light"]{
    --bg:#eef1f7; --bg2:#ffffff; --card:#ffffff; --card2:#f3f6fc;
    --line:#dde3ee; --text:#16202e; --muted:#5a6479; --accent:#3b5bff;
    --accent2:#0f9d76; --shadow:0 8px 30px rgba(20,30,60,.12);
    --deco1:rgba(59,91,255,.10); --deco2:rgba(15,157,118,.07);
    --glow1:rgba(59,91,255,.13); --glow2:rgba(15,157,118,.09); --glow3:rgba(59,91,255,.15);
    --on-accent:#ffffff; --on-accent2:#ffffff;
    --notice-bg:#fff7e8; --notice-text:#8a5b12; --notice-line:#f0ddb5;
  }
  *{box-sizing:border-box}
  html,body{margin:0;padding:0}
  body{
    background:radial-gradient(1200px 600px at 80% -10%, var(--deco1) 0%, transparent 60%),
               radial-gradient(900px 500px at -10% 10%, var(--deco2) 0%, transparent 55%),
               var(--bg);
    color:var(--text);
    font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif;
    -webkit-font-smoothing:antialiased;line-height:1.5;min-height:100vh;
  }
  a{color:inherit;text-decoration:none}
  .wrap{max-width:var(--maxw);margin:0 auto;padding:24px 16px calc(40px + env(safe-area-inset-bottom));position:relative;}

  .hero{
    text-align:center;padding:34px 16px 26px;margin-bottom:20px;
    background:linear-gradient(135deg,var(--glow1),var(--glow2));
    border:1px solid var(--line);border-radius:var(--radius);box-shadow:var(--shadow);position:relative;overflow:hidden;
  }
  .hero::after{content:"";position:absolute;inset:0;background:radial-gradient(400px 200px at 30% 0%,var(--glow3),transparent 70%);pointer-events:none;}
  .hero h1{margin:0 0 8px;font-size:clamp(22px,5vw,32px);font-weight:800;letter-spacing:.5px;}
  .hero p{margin:6px auto 0;color:var(--muted);max-width:720px;font-size:14px;}
  .src{display:inline-flex;gap:6px;align-items:center;margin-top:14px;font-size:12.5px;color:var(--muted);
    background:var(--bg2);border:1px solid var(--line);padding:6px 13px;border-radius:999px;}
  .src b{color:var(--accent2);font-weight:600}
  .src a{color:var(--accent)}
  .sync{margin-top:10px;font-size:12px;color:var(--muted);}
  .sync .dot{display:inline-block;width:7px;height:7px;border-radius:50%;margin-right:6px;vertical-align:middle;background:var(--muted)}
  .sync.ok .dot{background:var(--accent2);box-shadow:0 0 8px var(--accent2)}
  .sync.warn .dot{background:#ffb648;box-shadow:0 0 8px #ffb648}
  .sync.load .dot{background:var(--accent);animation:pulse 1s infinite}
  @keyframes pulse{0%,100%{opacity:.4}50%{opacity:1}}

  .notice{margin:0 0 18px;padding:12px 14px;border-radius:12px;border:1px solid var(--notice-line);
    background:var(--notice-bg);color:var(--notice-text);font-size:12.5px;line-height:1.6}
  .notice div{margin:2px 0}

  .controls{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-bottom:10px;}
  .search{flex:1 1 240px;min-width:0;position:relative;}
  .search input{width:100%;padding:12px 14px 12px 40px;border-radius:12px;border:1px solid var(--line);
    background:var(--bg2);color:var(--text);font-size:15px;outline:none;transition:.2s;}
  .search input:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(108,140,255,.18)}
  .search svg{position:absolute;left:13px;top:50%;transform:translateY(-50%);opacity:.6}

  .chips{display:flex;gap:7px;flex-wrap:wrap;margin-bottom:14px;max-height:none}
  .sources{display:flex;gap:7px;flex-wrap:wrap;align-items:center;margin-bottom:12px}
  .sources .src-label{font-size:12.5px;color:var(--muted);margin-right:2px;user-select:none}
  .sources .chip{font-weight:600}
  .chip{padding:7px 12px;border-radius:999px;border:1px solid var(--line);background:var(--bg2);
    color:var(--muted);font-size:12.5px;cursor:pointer;transition:.15s;user-select:none;white-space:nowrap}
  .chip:hover{color:var(--text);border-color:var(--accent)}
  .chip.active{background:linear-gradient(135deg,var(--accent),#8aa0ff);color:var(--on-accent);border-color:transparent;font-weight:600}

  .count{color:var(--muted);font-size:13px;margin:0 2px 14px}

  .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:14px;}
  .card{background:linear-gradient(180deg,var(--card),var(--card2));border:1px solid var(--line);
    border-radius:var(--radius);padding:15px;display:flex;flex-direction:column;gap:10px;transition:.18s;position:relative;overflow:hidden}
  .card:hover{transform:translateY(-3px);border-color:var(--accent);box-shadow:var(--shadow)}
  .grid>.card{height:100%}
  .card .desc{margin-top:auto}
  .card .head{display:flex;gap:12px;align-items:center}
  .icon{flex:0 0 46px;width:46px;height:46px;border-radius:12px;background:var(--bg);border:1px solid var(--line);
    display:flex;align-items:center;justify-content:center;font-size:24px;overflow:hidden}
  .icon img{width:100%;height:100%;object-fit:contain}
  .card h3{margin:0;font-size:15.5px;font-weight:700;line-height:1.3}
  .meta{font-size:11.5px;color:var(--muted);margin-top:2px}
  .desc{font-size:12.8px;color:var(--muted);line-height:1.55;
    display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}
  .tags{display:flex;gap:6px;flex-wrap:wrap}
  .tag{font-size:11px;color:var(--accent2);background:rgba(72,209,160,.10);border:1px solid rgba(72,209,160,.25);
    padding:2px 8px;border-radius:7px;white-space:nowrap}
  .acts{display:flex;flex-direction:column;gap:8px;margin-top:2px}
  .btn{display:inline-flex;align-items:center;justify-content:center;gap:6px;text-align:center;
    padding:10px 10px;border-radius:11px;font-size:13.5px;font-weight:600;
    cursor:pointer;border:1px solid var(--line);background:var(--bg2);color:var(--text);transition:.15s;min-width:0}
  .btn svg{flex:0 0 auto}
  .btn.primary{width:100%;background:linear-gradient(135deg,var(--accent),#7d94ff);color:var(--on-accent);border-color:transparent}
  .btn.primary:hover{filter:brightness(1.07)}
  .btn:hover{border-color:var(--accent)}
  .btn.secondary{flex:1 1 0;font-size:12.8px;color:var(--muted)}
  .btn.secondary.wide{flex:1.7 1 0}
  .btn.secondary:hover{color:var(--text)}
  .sec-row{display:flex;gap:8px}

  .empty{text-align:center;color:var(--muted);padding:50px 10px;font-size:15px}

  .pager{display:flex;justify-content:center;align-items:center;gap:6px;margin-top:26px;flex-wrap:wrap}
  .pager button{min-width:38px;height:38px;padding:0 10px;border-radius:10px;border:1px solid var(--line);
    background:var(--bg2);color:var(--text);font-size:14px;cursor:pointer;transition:.15s}
  .pager button:hover:not(:disabled){border-color:var(--accent)}
  .pager button.active{background:linear-gradient(135deg,var(--accent),#7d94ff);color:var(--on-accent);border-color:transparent;font-weight:700}
  .pager button:disabled{opacity:.35;cursor:not-allowed}
  .pager .ellipsis{color:var(--muted);padding:0 4px}

  footer{margin-top:34px;text-align:center;color:var(--muted);font-size:12px;line-height:1.85;overflow-wrap:anywhere;word-break:break-word}
  footer a{color:var(--accent)}
  footer code{font-size:11.5px;background:var(--bg2);border:1px solid var(--line);padding:1px 6px;border-radius:6px;
    white-space:normal;word-break:break-all;}

  #toast{position:fixed;left:50%;bottom:24px;transform:translateX(-50%) translateY(20px);
    background:var(--accent2);color:var(--on-accent2);padding:11px 18px;border-radius:12px;font-weight:600;font-size:14px;
    opacity:0;pointer-events:none;transition:.25s;z-index:99;box-shadow:var(--shadow)}
  #toast.show{opacity:1;transform:translateX(-50%) translateY(0)}

  .theme-switch{position:fixed;top:14px;right:14px;z-index:50;display:flex;gap:2px;padding:3px;
    background:var(--bg2);border:1px solid var(--line);border-radius:999px;box-shadow:var(--shadow)}
  .theme-switch button{font:inherit;font-size:12px;font-weight:600;color:var(--muted);background:transparent;
    border:none;padding:7px 10px;border-radius:999px;cursor:pointer;transition:.15s;white-space:nowrap;
    display:inline-flex;align-items:center;justify-content:center;line-height:0}
  .theme-switch button svg{display:block}
  .theme-switch button.active{background:var(--accent);color:var(--on-accent)}
  .theme-switch button:hover:not(.active){color:var(--text)}

  @media (max-width:560px){
    .wrap{padding:16px 12px calc(36px + env(safe-area-inset-bottom))}
    .grid{grid-template-columns:1fr;gap:12px}
    .hero{padding:54px 14px 22px}
    .hero h1{font-size:clamp(19px,5.4vw,26px);line-height:1.25}
    .hero p{font-size:13px}
    .src{margin-top:12px;font-size:11.5px;padding:6px 10px}
    .search{flex:1 1 100%}
    .btn.secondary{font-size:12.5px;padding:9px 6px}
    .theme-switch{position:absolute;top:8px;right:8px;transform:none}
    .theme-switch button{padding:5px 8px}
    footer{text-align:left;font-size:11.5px}
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
      <h1>⚡ Clash / Loon / Quantumult X 模块导入</h1>
      <p>可莉插件中心的 Loon 模块，一键拉起 Clash / Loon 导入；另收录 Quantumult X 重写与规则合集（可莉重写库 / 墨鱼手记 / 毒奶特供），支持 Quantumult X 与 hako:// 协议导入。</p>
      <div class="src">数据来源 · <a href="__SRCURL__" target="_blank" rel="noopener"><b>__SRCNAME__</b></a> · Quantumult X 资源合集 · 共 <span id="total">0</span> 个模块</div>
      <div class="sync load" id="sync"><span class="dot"></span><span id="syncText">正在同步源站最新模块…</span></div>
    </header>

    <div class="notice" id="notice"></div>

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
      </div>
    </div>
    <div class="chips" id="chips"></div>

    <div class="count" id="count"></div>
    <div class="grid" id="grid"></div>
    <div class="empty" id="empty" style="display:none">没有匹配的模块，换个关键词试试 🔍</div>
    <div class="pager" id="pager"></div>

    <footer>
      本页为资源索引，模块版权归原作者所有（CC BY-NC-SA 4.0），数据来自 __SRCNAME__。<br/>
      「导入 Clash」使用 <code>hako://install-module</code> 协议；「Loon」使用 <code>loon://import</code> 协议；「导入 Quantumult X」使用 <code>quantumult-x:///add-resource</code> 协议（保留现有资源追加导入）。<br/>
      Quantumult X 资源的导入链接直连 GitHub 仓库，点一下拉取的永远是仓库最新版；其页面数据为构建时快照。<br/>
      可莉插件中心部分：每次打开会自动同步源站最新数据，源站不可达时回退到内置缓存快照。<br/>
      若设备未安装对应客户端，链接将无法拉起，可使用「复制」按钮手动导入。
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
  const primary=`<a class="btn primary" href="${esc(isQx?m.hako:m.install)}">${SVG_DOWN}导入 Clash</a>`;
  const secondary=isQx
    ?`<a class="btn secondary wide" href="${esc(m.install)}" title="用 quantumult-x:///add-resource 协议导入">${SVG_BOLT}导入 Quantumult X</a>`
    :`<a class="btn secondary" href="${esc(m.loon)}">${SVG_BOLT}Loon 导入</a>`;
  return `
  <div class="card">
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
      else b.onclick=()=>{state.page=page;render();window.scrollTo({top:0,behavior:'smooth'});};
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

document.getElementById('q').addEventListener('input',e=>{state.q=e.target.value;state.page=1;render();});

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
