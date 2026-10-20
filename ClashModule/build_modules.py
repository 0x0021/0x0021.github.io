#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 luestr/ProxyResource 仓库的 git tree 生成 ClashModule 页面数据。

用法:
    1. gh api 'repos/luestr/ProxyResource/git/trees/main?recursive=1' > tree.json
    2. python3 build_modules.py

会产出:
    - modules.json   纯数据，便于其它工具复用
    - index.html     自包含、移动端适配、带搜索与分页的导入页面
"""
import json
import os
import re
from urllib.parse import quote

REPO = "luestr/ProxyResource"
BRANCH = "main"
RAW_BASE = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/"

# 仅收集这些扩展名的“可导入资源”，全部位于 Tool/ 目录下
ALLOWED_EXT = {"yaml", "yml", "lcf", "conf", "snippet", "star", "lpx", "js"}

CLIENT_MAP = [
    ("Tool/Clash", "Clash"),
    ("Tool/Loon", "Loon"),
    ("Tool/QuantumultX/Config", "Quantumult X"),
    ("Tool/QuantumultX/Rewrite", "Quantumult X"),
    ("Tool/QuantumultX", "Quantumult X"),
]

PREFIXES = ["Loon_", "Clash_", "Quantumult_X_", "QuantumultX_", "QX_"]


def detect_client(path: str) -> str:
    for key, name in CLIENT_MAP:
        if path.startswith(key):
            return name
    return "其它"


def clean_title(filename: str) -> str:
    name = re.sub(r"\.[^.]+$", "", filename)  # 去扩展名
    for p in PREFIXES:
        if name.startswith(p):
            name = name[len(p):]
    name = re.sub(r"_By_.*$", "", name)       # 去作者后缀
    name = name.replace("_", " ").strip()
    name = re.sub(r"\s+", " ", name)
    return name or filename


def human_size(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    if n < 1024 * 1024:
        return f"{n / 1024:.1f} KB"
    return f"{n / 1024 / 1024:.2f} MB"


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "tree.json"), encoding="utf-8") as f:
        tree = json.load(f)

    modules = []
    for item in tree.get("tree", []):
        path = item["path"]
        if item["type"] != "blob":
            continue
        if not path.startswith("Tool/"):
            continue
        ext = path.rsplit(".", 1)[-1].lower() if "." in path else ""
        if ext not in ALLOWED_EXT:
            continue
        filename = path.rsplit("/", 1)[-1]
        raw_clean = RAW_BASE + path          # 字面量 URL，浏览器/客户端均可直接识别
        install = "hako://install-module?url=" + quote(raw_clean, safe="")  # 仅编码一次（含括号/斜杠）
        raw = raw_clean
        client = detect_client(path)
        modules.append({
            "name": clean_title(filename),
            "file": filename,
            "client": client,
            "path": path,
            "raw": raw,
            "install": install,
            "size": item.get("size", 0),
            "sizeText": human_size(item.get("size", 0)),
        })

    # 排序：按客户端分组，再按名称
    order = {"Clash": 0, "Loon": 1, "Quantumult X": 2, "其它": 9}
    modules.sort(key=lambda m: (order.get(m["client"], 9), m["name"].lower()))

    with open(os.path.join(here, "modules.json"), "w", encoding="utf-8") as f:
        json.dump(modules, f, ensure_ascii=False, indent=2)

    print(f"共收集 {len(modules)} 个模块：")
    from collections import Counter
    for c, n in Counter(m["client"] for m in modules).most_common():
        print(f"  {c}: {n}")

    build_html(here, modules)


def build_html(here, modules):
    data_js = json.dumps(modules, ensure_ascii=False)
    html = HTML_TEMPLATE.replace("/*__MODULES_DATA__*/", data_js)
    with open(os.path.join(here, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)
    print("已生成 index.html")


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover" />
<title>Clash 模块导入 · ProxyResource</title>
<meta name="description" content="从 luestr/ProxyResource 收集的 Clash / Loon / Quantumult X 模块，浏览器一键拉起 Stash(Hako) 导入。" />
<style>
  :root{
    --bg:#0f1117; --bg2:#161a23; --card:#1b2030; --card2:#20283a;
    --line:#2a3245; --text:#e7ebf3; --muted:#9aa6bd; --accent:#6c8cff;
    --accent2:#48d1a0; --clash:#ff6b6b; --loon:#ffb648; --qx:#7c9cff;
    --radius:16px; --shadow:0 8px 30px rgba(0,0,0,.35);
    --maxw:1080px;
  }
  *{box-sizing:border-box}
  html,body{margin:0;padding:0}
  body{
    background:radial-gradient(1200px 600px at 80% -10%, #1d2740 0%, transparent 60%),
               radial-gradient(900px 500px at -10% 10%, #1a2236 0%, transparent 55%),
               var(--bg);
    color:var(--text);
    font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif;
    -webkit-font-smoothing:antialiased;
    line-height:1.5;
    min-height:100vh;
  }
  a{color:inherit;text-decoration:none}
  .wrap{max-width:var(--maxw);margin:0 auto;padding:24px 16px calc(40px + env(safe-area-inset-bottom));}

  /* Hero */
  .hero{
    text-align:center;padding:34px 16px 26px;margin-bottom:22px;
    background:linear-gradient(135deg,rgba(108,140,255,.16),rgba(72,209,160,.10));
    border:1px solid var(--line);border-radius:var(--radius);box-shadow:var(--shadow);
    position:relative;overflow:hidden;
  }
  .hero::after{content:"";position:absolute;inset:0;background:
    radial-gradient(400px 200px at 30% 0%,rgba(108,140,255,.18),transparent 70%);pointer-events:none;}
  .hero h1{margin:0 0 8px;font-size:clamp(22px,5vw,32px);font-weight:800;letter-spacing:.5px;}
  .hero p{margin:6px auto 0;color:var(--muted);max-width:680px;font-size:14px;}
  .hero .src{display:inline-flex;gap:6px;align-items:center;margin-top:12px;font-size:12.5px;
    color:var(--muted);background:var(--bg2);border:1px solid var(--line);padding:6px 12px;border-radius:999px;}
  .hero .src b{color:var(--accent2);font-weight:600}

  /* Controls */
  .controls{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-bottom:16px;}
  .search{flex:1 1 240px;min-width:0;position:relative;}
  .search input{
    width:100%;padding:12px 14px 12px 40px;border-radius:12px;border:1px solid var(--line);
    background:var(--bg2);color:var(--text);font-size:15px;outline:none;transition:.2s;
  }
  .search input:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(108,140,255,.18)}
  .search svg{position:absolute;left:13px;top:50%;transform:translateY(-50%);opacity:.6}
  .chips{display:flex;gap:8px;flex-wrap:wrap;}
  .chip{
    padding:9px 14px;border-radius:999px;border:1px solid var(--line);background:var(--bg2);
    color:var(--muted);font-size:13.5px;cursor:pointer;transition:.15s;user-select:none;white-space:nowrap;
  }
  .chip:hover{color:var(--text);border-color:var(--accent)}
  .chip.active{background:linear-gradient(135deg,var(--accent),#8aa0ff);color:#0b0e16;border-color:transparent;font-weight:600}

  .count{color:var(--muted);font-size:13px;margin:2px 2px 14px;}

  /* Grid */
  .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:14px;}
  .card{
    background:linear-gradient(180deg,var(--card),var(--card2));
    border:1px solid var(--line);border-radius:var(--radius);padding:16px 16px 14px;
    display:flex;flex-direction:column;gap:10px;transition:.18s;position:relative;overflow:hidden;
  }
  .card:hover{transform:translateY(-3px);border-color:var(--accent);box-shadow:var(--shadow)}
  .card .top{display:flex;align-items:center;justify-content:space-between;gap:10px}
  .badge{font-size:11.5px;font-weight:700;padding:4px 9px;border-radius:8px;letter-spacing:.3px}
  .badge.Clash{background:rgba(255,107,107,.16);color:var(--clash)}
  .badge.Loon{background:rgba(255,182,72,.16);color:var(--loon)}
  .badge.QuantumultX,.badge.Quantumult\.X{background:rgba(124,156,255,.16);color:var(--qx)}
  .size{font-size:12px;color:var(--muted)}
  .card h3{margin:0;font-size:16px;font-weight:700;line-height:1.35}
  .card .fname{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:11.5px;color:var(--muted);
    background:var(--bg);border:1px solid var(--line);border-radius:8px;padding:5px 8px;word-break:break-all}
  .acts{display:flex;gap:8px;margin-top:4px}
  .btn{flex:1;text-align:center;padding:11px 10px;border-radius:11px;font-size:14px;font-weight:600;
    cursor:pointer;border:1px solid var(--line);background:var(--bg2);color:var(--text);transition:.15s}
  .btn.primary{background:linear-gradient(135deg,var(--accent),#7d94ff);color:#0b0e16;border-color:transparent}
  .btn.primary:hover{filter:brightness(1.07)}
  .btn:hover{border-color:var(--accent)}
  .btn.ghost{flex:0 0 auto;padding:11px 12px}

  .empty{text-align:center;color:var(--muted);padding:50px 10px;font-size:15px}

  /* Pagination */
  .pager{display:flex;justify-content:center;align-items:center;gap:6px;margin-top:26px;flex-wrap:wrap}
  .pager button{min-width:38px;height:38px;padding:0 10px;border-radius:10px;border:1px solid var(--line);
    background:var(--bg2);color:var(--text);font-size:14px;cursor:pointer;transition:.15s}
  .pager button:hover:not(:disabled){border-color:var(--accent)}
  .pager button.active{background:linear-gradient(135deg,var(--accent),#7d94ff);color:#0b0e16;border-color:transparent;font-weight:700}
  .pager button:disabled{opacity:.35;cursor:not-allowed}
  .pager .ellipsis{color:var(--muted);padding:0 4px}

  footer{margin-top:34px;text-align:center;color:var(--muted);font-size:12px;line-height:1.7}
  footer a{color:var(--accent)}

  /* Toast */
  #toast{position:fixed;left:50%;bottom:24px;transform:translateX(-50%) translateY(20px);
    background:var(--accent2);color:#06281f;padding:11px 18px;border-radius:12px;font-weight:600;font-size:14px;
    opacity:0;pointer-events:none;transition:.25s;z-index:99;box-shadow:var(--shadow)}
  #toast.show{opacity:1;transform:translateX(-50%) translateY(0)}

  @media (max-width:560px){
    .wrap{padding:16px 12px calc(36px + env(safe-area-inset-bottom))}
    .grid{grid-template-columns:1fr;gap:12px}
    .hero{padding:28px 14px 22px}
    .controls{gap:8px}
    .search{flex:1 1 100%}
  }
</style>
</head>
<body>
  <div class="wrap">
    <header class="hero">
      <h1>⌘ Clash 模块一键导入</h1>
      <p>从 <b>luestr/ProxyResource</b> 收集的代理配置 / 模块资源。点击下方「一键导入」即可在浏览器中拉起 Stash（Hako）安装模块。</p>
      <div class="src">数据来源 · <b>github.com/luestr/ProxyResource</b> · 共 <span id="total">0</span> 项</div>
    </header>

    <div class="controls">
      <div class="search">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/></svg>
        <input id="q" type="search" placeholder="搜索模块名称 / 文件名…" autocomplete="off" />
      </div>
      <div class="chips" id="chips"></div>
    </div>

    <div class="count" id="count"></div>
    <div class="grid" id="grid"></div>
    <div class="empty" id="empty" style="display:none">没有匹配的模块，换个关键词试试 🔍</div>
    <div class="pager" id="pager"></div>

    <footer>
      本页仅作资源索引，所有内容版权归原作者所有（CC BY-NC-SA 4.0）。<br/>
      点击「一键导入」会尝试调用 <code>hako://</code> 协议；若未安装 Stash(Hako) 将无法拉起。<br/>
      也可使用「复制链接」手动在客户端中导入。
    </footer>
  </div>

  <div id="toast"></div>

<script>
const MODULES = /*__MODULES_DATA__*/;
const PAGE_SIZE = 9;
let state = { q:"", client:"全部", page:1 };

const grid = document.getElementById('grid');
const empty = document.getElementById('empty');
const pager = document.getElementById('pager');
const countEl = document.getElementById('count');
document.getElementById('total').textContent = MODULES.length;

// 客户端分类
const clients = ["全部", ...Array.from(new Set(MODULES.map(m=>m.client)))];
const chipsEl = document.getElementById('chips');
clients.forEach(c=>{
  const el = document.createElement('div');
  el.className = 'chip' + (c==="全部"?" active":"");
  el.textContent = c;
  el.dataset.client = c;
  el.onclick = ()=>{ state.client=c; state.page=1; [...chipsEl.children].forEach(x=>x.classList.toggle('active',x.dataset.client===c)); render(); };
  chipsEl.appendChild(el);
});

function filtered(){
  const q = state.q.trim().toLowerCase();
  return MODULES.filter(m=>{
    if(state.client!=="全部" && m.client!==state.client) return false;
    if(!q) return true;
    return (m.name+" "+m.file+" "+m.client).toLowerCase().includes(q);
  });
}

function esc(s){return s.replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));}

function badgeClass(c){return 'badge '+(c==='Quantumult X'?'QuantumultX':c.replace(/\s/g,''));}

function render(){
  const list = filtered();
  const totalPages = Math.max(1, Math.ceil(list.length/PAGE_SIZE));
  if(state.page>totalPages) state.page=totalPages;
  const start=(state.page-1)*PAGE_SIZE;
  const pageItems = list.slice(start, start+PAGE_SIZE);

  grid.innerHTML = pageItems.map(m=>`
    <div class="card">
      <div class="top">
        <span class="${badgeClass(m.client)}">${esc(m.client)}</span>
        <span class="size">${esc(m.sizeText)}</span>
      </div>
      <h3>${esc(m.name)}</h3>
      <div class="fname">${esc(m.file)}</div>
      <div class="acts">
        <a class="btn primary" href="${esc(m.install)}">一键导入</a>
        <button class="btn ghost" data-copy="${esc(m.raw)}" title="复制原始链接">⧉</button>
        <a class="btn ghost" href="${esc(m.raw)}" target="_blank" rel="noopener" title="查看源码">↗</a>
      </div>
    </div>`).join('');

  empty.style.display = list.length? 'none':'block';
  countEl.textContent = `显示 ${list.length? start+1:0}–${Math.min(start+PAGE_SIZE,list.length)} / 共 ${list.length} 项`;

  // pager
  pager.innerHTML='';
  if(totalPages>1){
    const mk=(label,page,opts={})=>{
      const b=document.createElement('button');
      b.textContent=label;
      if(opts.active) b.classList.add('active');
      if(opts.disabled) b.disabled=true;
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

// 复制链接
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

document.getElementById('q').addEventListener('input',e=>{
  state.q=e.target.value;state.page=1;render();
});

render();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
