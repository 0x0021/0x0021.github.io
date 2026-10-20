#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从可莉的插件中心 (https://hub.kelee.one) 的 list.json 生成 ClashModule 页面数据。

用法:
    1. 抓取数据:  curl -L https://hub.kelee.one/list.json > list.json
    2. 生成页面:  python3 build_modules.py

产出:
    - modules.json   纯数据
    - index.html     自包含、移动端适配、带搜索 / 标签筛选 / 分页的导入页面
"""
import json
import os
from collections import Counter
from urllib.parse import urlparse, parse_qs, quote

SRC_NAME = "可莉的插件中心"
SRC_URL = "https://hub.kelee.one"
LIST_JSON = "list.json"

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


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, LIST_JSON), encoding="utf-8") as f:
        data = json.load(f)

    items = data.get("lists", [])
    modules = []
    tag_counter = Counter()
    for it in items:
        url = it.get("url", "")
        lpx = extract_resource(url)
        install = "hako://install-module?url=" + quote(lpx, safe="")
        authors = it.get("author", []) or []
        author_name = authors[0].get("name", "") if authors else ""
        author_home = authors[0].get("homepage", "") if authors else ""
        tags = it.get("tag", []) or []
        for t in tags:
            tag_counter[t] += 1
        modules.append({
            "name": it.get("name", ""),
            "desc": (it.get("desc", "") or "").strip(),
            "tags": tags,
            "icon": it.get("icon", ""),
            "date": it.get("date", ""),
            "author": author_name,
            "authorHome": author_home,
            "lpx": lpx,
            "install": install,
            "loon": url,
        })

    # 稳定排序：按日期倒序（新→旧），无日期的排后
    modules.sort(key=lambda m: m["date"] or "", reverse=True)

    # 热门标签
    top_tags = [t for t, _ in tag_counter.most_common(TOP_TAGS)]

    with open(os.path.join(here, "modules.json"), "w", encoding="utf-8") as f:
        json.dump(modules, f, ensure_ascii=False, indent=2)

    print(f"共收集 {len(modules)} 个模块；热门标签 {len(top_tags)} 个")

    build_html(here, modules, top_tags,
               notice=data.get("notice", []),
               src_name=data.get("name", SRC_NAME))


def build_html(here, modules, top_tags, notice, src_name):
    payload = {
        "modules": modules,
        "topTags": top_tags,
        "notice": notice,
        "srcName": src_name,
        "srcUrl": SRC_URL,
    }
    data_js = json.dumps(payload, ensure_ascii=False)
    html = HTML_TEMPLATE.replace("/*__DATA__*/", data_js)
    html = html.replace("__SRCURL__", SRC_URL).replace("__SRCNAME__", src_name)
    with open(os.path.join(here, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)
    print("已生成 index.html")


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover" />
<title>Clash / Loon 模块导入 · 可莉插件中心</title>
<meta name="description" content="从可莉的插件中心收集的 Loon / Clash 模块，浏览器一键拉起 Stash(Hako) 或 Loon 导入。" />
<style>
  :root{
    --bg:#0f1117; --bg2:#161a23; --card:#1b2030; --card2:#20283a;
    --line:#2a3245; --text:#e7ebf3; --muted:#9aa6bd; --accent:#6c8cff;
    --accent2:#48d1a0; --radius:16px; --shadow:0 8px 30px rgba(0,0,0,.35);
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
    -webkit-font-smoothing:antialiased;line-height:1.5;min-height:100vh;
  }
  a{color:inherit;text-decoration:none}
  .wrap{max-width:var(--maxw);margin:0 auto;padding:24px 16px calc(40px + env(safe-area-inset-bottom));}

  .hero{
    text-align:center;padding:34px 16px 26px;margin-bottom:20px;
    background:linear-gradient(135deg,rgba(108,140,255,.16),rgba(72,209,160,.10));
    border:1px solid var(--line);border-radius:var(--radius);box-shadow:var(--shadow);position:relative;overflow:hidden;
  }
  .hero::after{content:"";position:absolute;inset:0;background:radial-gradient(400px 200px at 30% 0%,rgba(108,140,255,.18),transparent 70%);pointer-events:none;}
  .hero h1{margin:0 0 8px;font-size:clamp(22px,5vw,32px);font-weight:800;letter-spacing:.5px;}
  .hero p{margin:6px auto 0;color:var(--muted);max-width:720px;font-size:14px;}
  .src{display:inline-flex;gap:6px;align-items:center;margin-top:14px;font-size:12.5px;color:var(--muted);
    background:var(--bg2);border:1px solid var(--line);padding:6px 13px;border-radius:999px;}
  .src b{color:var(--accent2);font-weight:600}
  .src a{color:var(--accent)}

  .notice{margin:0 0 18px;padding:12px 14px;border-radius:12px;border:1px solid var(--line);
    background:rgba(255,182,72,.08);color:#ffcf8a;font-size:12.5px;line-height:1.6}
  .notice div{margin:2px 0}

  .controls{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-bottom:10px;}
  .search{flex:1 1 240px;min-width:0;position:relative;}
  .search input{width:100%;padding:12px 14px 12px 40px;border-radius:12px;border:1px solid var(--line);
    background:var(--bg2);color:var(--text);font-size:15px;outline:none;transition:.2s;}
  .search input:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(108,140,255,.18)}
  .search svg{position:absolute;left:13px;top:50%;transform:translateY(-50%);opacity:.6}

  .chips{display:flex;gap:7px;flex-wrap:wrap;margin-bottom:14px;max-height:none}
  .chip{padding:7px 12px;border-radius:999px;border:1px solid var(--line);background:var(--bg2);
    color:var(--muted);font-size:12.5px;cursor:pointer;transition:.15s;user-select:none;white-space:nowrap}
  .chip:hover{color:var(--text);border-color:var(--accent)}
  .chip.active{background:linear-gradient(135deg,var(--accent),#8aa0ff);color:#0b0e16;border-color:transparent;font-weight:600}

  .count{color:var(--muted);font-size:13px;margin:0 2px 14px}

  .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:14px;}
  .card{background:linear-gradient(180deg,var(--card),var(--card2));border:1px solid var(--line);
    border-radius:var(--radius);padding:15px;display:flex;flex-direction:column;gap:10px;transition:.18s;position:relative;overflow:hidden}
  .card:hover{transform:translateY(-3px);border-color:var(--accent);box-shadow:var(--shadow)}
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
  .acts{display:flex;gap:8px;margin-top:2px;flex-wrap:wrap}
  .btn{flex:1 1 auto;text-align:center;padding:10px 10px;border-radius:11px;font-size:13.5px;font-weight:600;
    cursor:pointer;border:1px solid var(--line);background:var(--bg2);color:var(--text);transition:.15s;min-width:0}
  .btn.primary{background:linear-gradient(135deg,var(--accent),#7d94ff);color:#0b0e16;border-color:transparent;flex:2 1 auto}
  .btn.primary:hover{filter:brightness(1.07)}
  .btn:hover{border-color:var(--accent)}
  .btn.ghost{flex:0 0 auto;padding:10px 12px}

  .empty{text-align:center;color:var(--muted);padding:50px 10px;font-size:15px}

  .pager{display:flex;justify-content:center;align-items:center;gap:6px;margin-top:26px;flex-wrap:wrap}
  .pager button{min-width:38px;height:38px;padding:0 10px;border-radius:10px;border:1px solid var(--line);
    background:var(--bg2);color:var(--text);font-size:14px;cursor:pointer;transition:.15s}
  .pager button:hover:not(:disabled){border-color:var(--accent)}
  .pager button.active{background:linear-gradient(135deg,var(--accent),#7d94ff);color:#0b0e16;border-color:transparent;font-weight:700}
  .pager button:disabled{opacity:.35;cursor:not-allowed}
  .pager .ellipsis{color:var(--muted);padding:0 4px}

  footer{margin-top:34px;text-align:center;color:var(--muted);font-size:12px;line-height:1.8}
  footer a{color:var(--accent)}

  #toast{position:fixed;left:50%;bottom:24px;transform:translateX(-50%) translateY(20px);
    background:var(--accent2);color:#06281f;padding:11px 18px;border-radius:12px;font-weight:600;font-size:14px;
    opacity:0;pointer-events:none;transition:.25s;z-index:99;box-shadow:var(--shadow)}
  #toast.show{opacity:1;transform:translateX(-50%) translateY(0)}

  @media (max-width:560px){
    .wrap{padding:16px 12px calc(36px + env(safe-area-inset-bottom))}
    .grid{grid-template-columns:1fr;gap:12px}
    .hero{padding:28px 14px 22px}
    .search{flex:1 1 100%}
    .btn.primary{flex:1 1 100%}
  }
</style>
</head>
<body>
  <div class="wrap">
    <header class="hero">
      <h1>⚡ Clash / Loon 模块导入</h1>
      <p>从「可莉的插件中心」收集的代理模块资源。点击「导入 Stash」在浏览器中拉起 Stash（Hako）安装，或点「Loon」用 Loon 直接导入。</p>
      <div class="src">数据来源 · <a href="__SRCURL__" target="_blank" rel="noopener"><b>__SRCNAME__</b></a> · 共 <span id="total">0</span> 个模块</div>
    </header>

    <div class="notice" id="notice"></div>

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
      「导入 Stash」使用 <code>hako://install-module</code> 协议；「Loon」使用 <code>loon://import</code> 协议。<br/>
      若设备未安装对应客户端，链接将无法拉起，可使用「复制」按钮手动导入。
    </footer>
  </div>

  <div id="toast"></div>

<script>
const PAYLOAD = /*__DATA__*/;
const MODULES = PAYLOAD.modules;
const PAGE_SIZE = 12;
let state = { q:"", tag:"全部", page:1 };

const grid = document.getElementById('grid');
const empty = document.getElementById('empty');
const pager = document.getElementById('pager');
const countEl = document.getElementById('count');
document.getElementById('total').textContent = MODULES.length;

// 公告
const noticeEl = document.getElementById('notice');
if(PAYLOAD.notice && PAYLOAD.notice.length){
  noticeEl.innerHTML = PAYLOAD.notice.map(n=>`<div>• ${esc(n)}</div>`).join('');
}else{ noticeEl.style.display='none'; }

// 标签筛选
const chipsEl = document.getElementById('chips');
["全部", ...PAYLOAD.topTags].forEach(t=>{
  const el=document.createElement('div');
  el.className='chip'+(t==="全部"?" active":"");
  el.textContent=t;
  el.dataset.tag=t;
  el.onclick=()=>{ state.tag=t; state.page=1; [...chipsEl.children].forEach(x=>x.classList.toggle('active',x.dataset.tag===t)); render(); };
  chipsEl.appendChild(el);
});

function esc(s){return String(s==null?'':s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));}

function filtered(){
  const q=state.q.trim().toLowerCase();
  return MODULES.filter(m=>{
    if(state.tag!=="全部" && !(m.tags||[]).includes(state.tag)) return false;
    if(!q) return true;
    const hay=(m.name+" "+(m.desc||"")+" "+(m.tags||[]).join(" ")+" "+(m.author||"")).toLowerCase();
    return hay.includes(q);
  });
}

function card(m){
  const tags=(m.tags||[]).slice(0,4).map(t=>`<span class="tag">${esc(t)}</span>`).join('');
  const author=m.author?`${esc(m.author)}`+(m.date?` · ${esc(m.date.slice(0,10))}`:''):(m.date?esc(m.date.slice(0,10)):'');
  return `
  <div class="card">
    <div class="head">
      <div class="icon"><span>🧩</span><img src="${esc(m.icon)}" alt="" loading="lazy" onload="this.previousElementSibling.remove()" onerror="this.remove()"></div>
      <div style="min-width:0">
        <h3>${esc(m.name)}</h3>
        <div class="meta">${author}</div>
      </div>
    </div>
    <div class="desc">${esc(m.desc)||'—'}</div>
    <div class="tags">${tags}</div>
    <div class="acts">
      <a class="btn primary" href="${esc(m.install)}">⚡ 导入 Stash</a>
      <a class="btn" href="${esc(m.loon)}">Loon</a>
      <button class="btn ghost" data-copy="${esc(m.lpx)}" title="复制资源链接">⧉</button>
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

render();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
