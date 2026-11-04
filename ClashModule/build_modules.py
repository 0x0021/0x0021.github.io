#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 Surge 模块源 surge.qingr.moe（即 GitHub 仓库 QingRex/LoonKissSurge）生成 ClashModule 页面。

关键设计：免维护 / 自动同步
  - index.html 内联一份「原始快照」(lists/name/srcUrl) 作为离线兜底；
  - 页面在浏览器加载时，先渲染快照（秒开），再实时 fetch 同域自托管 qingr.json；
  - 拉取成功则用最新数据重渲染，失败则保留快照并提示；
  - qingr.json 由本脚本从 GitHub 仓库树枚举 .sgmodule 生成，随构建更新推送即可刷新。

用法:
    1. 生成页面(联网从 GitHub 仓库树枚举模块，失败时回退本地缓存):  python3 build_modules.py
    2. 部署:  将 index.html 与 qingr.json 一并推送到站点 ClashModule 目录

产出:
    - qingr.json     同域实时源（浏览器直连即可刷新，免 CORS / 免代理）
    - modules.json   纯数据（静态导出，供参考/离线）
    - index.html     自包含、移动端适配、运行时自动同步、带搜索 / 标签筛选 / 分页的导入页面
"""
import json
import os
import datetime
import urllib.request
from collections import Counter
from urllib.parse import urlparse, parse_qs, quote

SRC_NAME = "Surge"
SRC_URL = "https://surge.qingr.moe"
SRC_REPO = "QingRex/LoonKissSurge"
RAW_BASE = "https://raw.githubusercontent.com/QingRex/LoonKissSurge/main"
SRC_REPO_URL = "https://github.com/QingRex/LoonKissSurge"
SRC_NOTE = "公开 Surge 模块集合，随上游仓库更新同步"
LIVE_JSON = "qingr.json"            # 自托管实时源（与页面同域，免 CORS / 免代理）
QINGR_CACHE = "qingr_cache.json"   # 联网失败时的本地回退

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
    """把源站条目转换为页面模块对象（与前端 JS 保持同一逻辑）。"""
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


def fetch_qingr_lists():
    """从 GitHub 仓库树枚举 .sgmodule 模块，构造 lists 结构；失败回退本地缓存。"""
    def parse_tree():
        api = f"https://api.github.com/repos/{SRC_REPO}/git/trees/main?recursive=1"
        req = urllib.request.Request(
            api,
            headers={"User-Agent": "ClashModule-Builder",
                     "Accept": "application/vnd.github+json"},
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            tree = json.loads(r.read().decode("utf-8"))
        items = []
        for node in tree.get("tree", []):
            p = node.get("path", "")
            if not p.endswith(".sgmodule"):
                continue
            fname = p.rsplit("/", 1)[-1]
            name = fname.replace(".beta", "").replace(".sgmodule", "").replace("可莉", "")
            is_beta = "/Beta/" in p
            items.append({
                "name": name,
                "url": f"{RAW_BASE}/{quote(p, safe='/')}",
                "desc": "Surge 模块",
                "tag": ["Beta"] if is_beta else ["Surge"],
                "icon": "",
                "date": "",
                "author": [],
                "src": {"name": SRC_NAME, "url": SRC_REPO_URL, "note": SRC_NOTE},
            })
        items.sort(key=lambda m: m["name"])
        return items

    here = os.path.dirname(os.path.abspath(__file__))
    try:
        items = parse_tree()
        if items:
            with open(os.path.join(here, QINGR_CACHE), "w", encoding="utf-8") as f:
                json.dump(items, f, ensure_ascii=False, indent=2)
            return items
    except Exception as e:  # noqa: BLE001
        print(f"⚠️ 抓取 GitHub 仓库树失败（{e}），尝试本地缓存")
    if os.path.exists(os.path.join(here, QINGR_CACHE)):
        with open(os.path.join(here, QINGR_CACHE), encoding="utf-8") as f:
            return json.load(f)
    return []


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    items = fetch_qingr_lists()
    modules = transform(items)
    tags = top_tags(modules)
    with open(os.path.join(here, "modules.json"), "w", encoding="utf-8") as f:
        json.dump(modules, f, ensure_ascii=False, indent=2)
    # 自托管实时源：与页面同域，浏览器直连即可刷新，无需代理
    with open(os.path.join(here, LIVE_JSON), "w", encoding="utf-8") as f:
        json.dump({"lists": items, "name": SRC_NAME, "srcUrl": SRC_URL,
                   "buildDate": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")},
                  f, ensure_ascii=False, indent=2)
    print(f"共收集 {len(modules)} 个模块（来自 {SRC_URL}）；热门标签 {len(tags)} 个")

    # 内联到页面的是「原始快照」(lists/name)，前端负责转换 + 实时拉取
    snapshot = {
        "lists": items,
        "name": SRC_NAME,
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
<title>代理模块一键导入 Clash</title>
<meta name="description" content="收录 Loon / Clash 模块，浏览器一键导入 Clash，支持 hako:// 协议导入与复制链接手动导入。" />
<meta property="og:type" content="website" />
<meta property="og:title" content="代理模块一键导入 Clash" />
<meta property="og:description" content="收录 Loon / Clash 模块，浏览器一键导入 Clash，支持 hako:// 协议导入与复制链接手动导入。" />
<meta property="og:url" content="https://0x0021.github.io/ClashModule/" />
<meta property="og:site_name" content="0x0021" />
<meta name="twitter:card" content="summary" />
<meta name="theme-color" content="#f5f5f7" />
<style>
  :root{
    --bg:#f5f5f7; --bg2:rgba(255,255,255,.72); --card:rgba(255,255,255,.78); --card2:rgba(255,255,255,.95);
    --line:rgba(0,0,0,.08); --text:#1d1d1f; --muted:#6e6e73; --accent:#0071e3; --accent2:#34c759;
    --radius:18px; --shadow:0 2px 10px rgba(0,0,0,.05); --shadow-lg:0 12px 40px rgba(0,0,0,.10);
    --maxw:1040px; --on-accent:#fff;
    --glass:blur(20px) saturate(180%); --ease:cubic-bezier(.4,0,.2,1);
  }
  :root[data-theme="dark"]{
    --bg:#000; --bg2:rgba(28,28,30,.66); --card:rgba(28,28,30,.66); --card2:rgba(44,44,46,.9);
    --line:rgba(255,255,255,.12); --text:#f5f5f7; --muted:#98989d; --accent:#0a84ff; --accent2:#30d158;
    --shadow:0 2px 10px rgba(0,0,0,.4); --shadow-lg:0 16px 50px rgba(0,0,0,.6);
  }
  *{box-sizing:border-box}
  html,body{margin:0;padding:0;overflow-x:clip}
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

  /* ---------- 顶部标语（通栏） ---------- */
  .motto{
    padding:16px 20px;text-align:center;
    font-size:clamp(13.5px,2.3vw,16px);font-weight:500;letter-spacing:.14em;line-height:1.7;
    color:var(--muted);
    background:linear-gradient(90deg,rgba(0,113,227,.05),rgba(94,92,230,.10),rgba(10,132,255,.05));
    border-bottom:1px solid var(--line);
  }
  .motto span{
    background:linear-gradient(120deg,#0071e3,#5e5ce6,#0a84ff);
    -webkit-background-clip:text;background-clip:text;color:transparent;
  }
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

  .toolbar{position:static;z-index:30;margin:0 0 18px;padding:14px;border-radius:20px;
    background:var(--bg2);border:1px solid var(--line);box-shadow:var(--shadow);
    -webkit-backdrop-filter:var(--glass);backdrop-filter:var(--glass);}
  .controls{display:flex;gap:12px;flex-wrap:wrap;align-items:center;margin-bottom:14px;}
  .search{flex:1 1 260px;min-width:0;position:relative;}
  .search input{width:100%;padding:13px 42px 13px 44px;border-radius:980px;border:1px solid var(--line);
    background:var(--bg2);color:var(--text);font-size:15px;outline:none;transition:.25s var(--ease);}
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
    position:relative;overflow:hidden;}
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
    white-space:nowrap;border:1px solid transparent;}
  .card .src-badge[data-r="surge"],.card .src-badge[data-r="rewrite"]{color:#0071e3;background:rgba(0,113,227,.10);border-color:rgba(0,113,227,.22)}
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
  .acts{display:flex;gap:10px;margin-top:auto}
  .btn{display:inline-flex;align-items:center;justify-content:center;gap:7px;text-align:center;
    padding:11px 14px;border-radius:12px;font-size:14px;font-weight:600;
    cursor:pointer;border:1px solid var(--line);background:var(--bg2);color:var(--text);transition:.2s var(--ease);min-width:0;white-space:nowrap;
    -webkit-tap-highlight-color:transparent;}
  .btn svg{flex:0 0 auto}
  .btn.primary{flex:2 1 0;background:var(--accent);color:#fff;border-color:transparent;box-shadow:0 4px 16px rgba(0,113,227,.28)}
  .btn.primary:hover{filter:brightness(1.06);transform:translateY(-1px)}
  .btn.primary:active{transform:scale(.985)}
  .btn.secondary{flex:1 1 0;font-size:13.5px;color:var(--text);font-weight:500;background:var(--bg2);}
  .btn.secondary:hover{color:var(--accent);border-color:var(--accent)}
  .btn.secondary:active{transform:scale(.985)}

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

  /* 模块卡片可点击打开详情弹窗 */
  .grid .card{cursor:pointer}
  .grid .card:hover{transform:translateY(-3px);box-shadow:var(--shadow-lg);border-color:rgba(0,113,227,.25)}

  /* 详情弹窗 */
  .modal{position:fixed;inset:0;z-index:200;display:flex;align-items:flex-start;justify-content:center;
    padding:8vh 16px;opacity:0;visibility:hidden;transition:opacity .22s var(--ease),visibility .22s var(--ease);}
  .modal.show{opacity:1;visibility:visible}
  .modal-backdrop{position:absolute;inset:0;background:rgba(0,0,0,.42);-webkit-backdrop-filter:var(--glass);backdrop-filter:var(--glass)}
  .modal-dialog{position:relative;width:100%;max-width:540px;max-height:84vh;overflow:auto;
    background:var(--card2);border:1px solid var(--line);border-radius:var(--radius);box-shadow:var(--shadow-lg);
    padding:24px 24px 20px;transform:translateY(14px) scale(.98);transition:transform .24s var(--ease)}
  .modal.show .modal-dialog{transform:none}
  .modal-close{position:absolute;top:12px;right:14px;width:30px;height:30px;border:none;border-radius:980px;
    background:var(--bg2);color:var(--text);font-size:20px;line-height:1;cursor:pointer;transition:.2s var(--ease)}
  .modal-close:hover{background:var(--line)}
  .modal-body{display:flex;flex-direction:column;gap:14px}
  .m-head{display:flex;gap:13px;align-items:center}
  .m-head .icon{flex:0 0 50px;width:50px;height:50px;border-radius:14px;background:var(--bg2);border:1px solid var(--line);
    display:flex;align-items:center;justify-content:center;font-size:26px;overflow:hidden}
  .m-head .icon img{width:100%;height:100%;object-fit:cover}
  .m-head h3{font-size:18px;font-weight:700;margin:0;word-break:break-word}
  .m-desc{font-size:14px;line-height:1.65;color:var(--text)}
  .m-src{border:1px solid var(--line);border-radius:14px;padding:13px 14px;background:var(--bg2);display:flex;flex-direction:column;gap:6px}
  .m-src-head{font-size:11px;font-weight:700;letter-spacing:.08em;color:var(--muted);text-transform:uppercase}
  .m-src-link{display:inline-flex;align-items:center;gap:6px;color:var(--accent);font-weight:600;font-size:14px;text-decoration:none;word-break:break-all}
  .m-src-link:hover{text-decoration:underline}
  .m-src-note{font-size:12.5px;color:var(--muted);line-height:1.5}
  .m-src-url{font-size:11.5px;color:var(--muted);word-break:break-all}
  .m-src-url a{color:var(--muted);text-decoration:none}
  .m-src-url a:hover{text-decoration:underline}
  .m-acts{display:flex;gap:10px;margin-top:2px}
  .m-acts .btn{flex:1 1 0;justify-content:center}
  @media(max-width:560px){ .modal{padding:5vh 10px} .modal-dialog{padding:20px 18px 16px} }

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
/* 看门狗：主脚本若 4s 内未完成初始化（如部署瞬间拿到截断 HTML），自动刷新一次（仅一次，防循环） */
(function(){
  window.__cmReady=false;
  setTimeout(function(){
    if(window.__cmReady) return;
    try{
      var el=document.getElementById('sync'), tx=document.getElementById('syncText');
      if(sessionStorage.getItem('cm-reloaded')){
        if(tx) tx.textContent='页面数据加载异常，请手动刷新重试';
        if(el) el.className='sync warn';
      }else{
        sessionStorage.setItem('cm-reloaded','1');
        if(tx) tx.textContent='页面数据加载异常，正在自动刷新…';
        if(el) el.className='sync warn';
        setTimeout(function(){ location.reload(); },900);
      }
    }catch(e){}
  },4000);
})();
</script>
</head>
<body>
  <div class="motto"><span>源于互联网，回馈互联网</span>；崇尚开放共享，拒绝封闭垄断。</div>
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
      <h1>代理模块一键导入 Clash</h1>
      <p>收录 Surge 模块与 GitHub 重写规则，浏览器一键导入 Clash，未装客户端可复制链接手动导入。</p>
      <div class="src">数据来源 · GitHub 资源合集 · 共 <span id="total">0</span> 个模块</div>
      <div class="sync load" id="sync"><span class="dot"></span><span id="syncText">正在同步源站最新模块…</span></div>
    </header>

    <div class="toolbar">
      <div class="sources" id="sources">
        <span class="src-label">来源</span>
        <div class="chip active" data-src="all">全部</div>
        <div class="chip" data-src="surge">Surge</div>
        <div class="chip" data-src="qx">GitHub</div>
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
      <div>模块版权归原作者所有（CC&nbsp;BY-NC-SA&nbsp;4.0）</div>
      <div>数据来源 · GitHub 资源合集</div>
      <div>「导入 Clash」使用 <code>hako://install-module</code> 协议；未安装客户端可用「复制链接」手动导入。</div>
      <span class="recommend">友情推荐 · <a href="https://xn--4gqx1hgtfdmt.com/#/register?code=ayOVtXLb" target="_blank" rel="noopener">一分机场</a>（高速稳定，注册即送流量）</span>
    </footer>
  </div>

  <div id="toast"></div>

  <div class="modal" id="modal" aria-hidden="true">
    <div class="modal-backdrop" data-close></div>
    <div class="modal-dialog" role="dialog" aria-modal="true" aria-labelledby="modalTitle">
      <button class="modal-close" data-close aria-label="关闭">×</button>
      <div class="modal-body" id="modalBody"></div>
    </div>
  </div>

<script>
/* 内联兜底快照（构建时写入），实时拉取失败时使用 */
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
/* 基础清洗：去除首尾空白；上游个别模块名含「可莉」字样，统一剔除避免源站品牌名外泄 */
function fixBrand(s){
  return String(s||'').replace(/可莉/g,'').trim();
}
function transformLists(lists){
  const mods=[];
  for(const it of (lists||[])){
    const lpx=extractResource(it.url||'');
    const install='hako://install-module?url='+pyQuote(lpx);
    const authors=it.author||[];
    const a0=authors[0]||{};
    const tags=(it.tag||[]).map(fixBrand);
    mods.push({
      name:fixBrand(it.name||''), desc:fixBrand((it.desc||'').trim()), tags, icon:it.icon||'',
      date:it.date||'', author:fixBrand(a0.name||''), authorHome:a0.homepage||'',
      lpx, install, loon:it.url||'', src:it.src||null
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
/* 描述统一以 Clash 为主：其它客户端名（Quantumult X / Surge / Loon 等）一律替换或剔除 */
function cleanDesc(s){
  return (s||'')
    .replace(/Quantumult\s*X|QuantumultX|圈X/gi,'Clash')
    .replace(/(Surge4?|Loon2?|Shadowrocket|小火箭|Stash|Loon|Surge)[、，,]?\s*/gi,'')
    .replace(/[、，,]\s*的/g,'的')
    .replace(/[、，,]\s*(?=[、，,])|[、，,]\s*$/g,'')
    .trim();
}
/* 各 GitHub 来源的中文名 / 主页 / 说明，供模块弹窗展示「来源」 */
const REPO_SRC={
  '重写库':{name:'重写库',url:'https://github.com/deezertidal/QuantumultX-Rewrite',note:'Quantumult X 重写规则合集，随上游仓库更新'},
  '墨鱼手记':{name:'墨鱼手记',url:'https://github.com/ddgksf2013/Rewrite',note:'墨鱼手记重写与分流规则'},
  '毒奶特供':{name:'毒奶特供',url:'https://github.com/limbopro/Adblock4limbo',note:'毒奶特供广告拦截规则'},
  '红果广告过滤':{name:'红果广告过滤',url:'https://github.com/k6nfmm7dbr-commits/hongguo-lite',note:'红果短剧去广告模块'}
};
function repoSrc(repo){
  return REPO_SRC[repo] || {name:repo||'GitHub', url:'https://github.com', note:''};
}
function transformQx(qx){
  if(!qx || !qx.modules) return [];
  /* 仅保留重写模块（kind=rewrite）；规则 / 分流订阅（kind=rule）不是模块，hako:// 也不适用，剔除 */
  return qx.modules.filter(m=>m.kind!=='rule').map(m=>({
    name:fixBrand(m.name||''), desc:cleanDesc(fixBrand((m.desc||'').trim())), tags:(m.tags||[]).map(fixBrand), icon:m.icon||'',
    date:'', author:fixBrand(m.author||''), authorHome:'',
    lpx:m.url||'', raw:m.url||'', kind:m.kind||'rewrite', repo:fixBrand(m.repo||''),
    source:'qx', src:repoSrc(fixBrand(m.repo||'')),
    install:qxInstall(m.url||'', m.kind, m.name),
    hako:'hako://install-module?url='+pyQuote(m.url||''),
    loon:'loon://import?plugin='+encodeURIComponent(m.url||'')
  }));
}

/* 手动收录：红果短剧去广告（Surge 模块，raw 直链，hako:// 导入） */
const HONGGUO_BASE='https://raw.githubusercontent.com/k6nfmm7dbr-commits/hongguo-lite/main';
const EXTRA_MODS=[
  {name:'红果短剧去广告 · Lite',repo:'红果广告过滤',author:'Minis',date:'2026-10-06',
   icon:HONGGUO_BASE+'/icon.png',tags:['去广告','红果短剧','短剧'],
   desc:'拦截红果短剧的穿山甲广告 SDK、广告素材签名域与埋点上报，减少开屏广告等待与剧集插播广告。基础版，无需 MITM 与证书。',
   url:HONGGUO_BASE+'/surge/hongguo-lite.sgmodule'},
  {name:'红果短剧去广告 · Plus',repo:'红果广告过滤',author:'Minis',date:'2026-10-06',
   icon:HONGGUO_BASE+'/icon.png',tags:['去广告','红果短剧','短剧'],
   desc:'基础版全部规则 + 广告请求接口拦截（Map Local 返回空 JSON），拦截更彻底。需要 MITM 并信任证书。',
   url:HONGGUO_BASE+'/surge/hongguo-lite-plus.sgmodule'},
].map(m=>({
  name:m.name, desc:m.desc, tags:m.tags, icon:m.icon, date:m.date, author:m.author, authorHome:'',
  lpx:m.url, raw:m.url, kind:'rewrite', repo:m.repo, source:'qx', src:repoSrc(m.repo),
  install:'', hako:'hako://install-module?url='+pyQuote(m.url), loon:''
}));

let SURGE = transformLists(SNAPSHOT.lists);
let QX = transformQx(SNAPSHOT.qx).concat(EXTRA_MODS);
let MODULES = SURGE.concat(QX);
let TOP_TAGS = computeTopTags(MODULES, 16);
let state = { q:"", tag:"全部", page:1, source:"all" };
let byId = {};   /* lpx -> 模块对象，供卡片点击打开弹窗 */

/* 全部视图下两类资源交替排列，保证两边都能被看到 */
function interleave(a,b){
  const out=[]; const n=Math.max(a.length,b.length);
  for(let i=0;i<n;i++){ if(i<a.length) out.push(a[i]); if(i<b.length) out.push(b[i]); }
  return out;
}
function currentSet(){
  if(state.source==='surge') return SURGE;
  if(state.source==='qx') return QX;
  return interleave(SURGE,QX);
}

const grid=document.getElementById('grid');
const empty=document.getElementById('empty');
const pager=document.getElementById('pager');
const countEl=document.getElementById('count');
const totalEl=document.getElementById('total');
const chipsEl=document.getElementById('chips');
const syncEl=document.getElementById('sync');
const syncText=document.getElementById('syncText');
const SRC_NAME=SNAPSHOT.name||'Surge';

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
  const rk = isQx ? ({'墨鱼手记':'ddg','毒奶特供':'adblock','重写库':'rewrite'}[m.repo]||'qx') : 'surge';
  const rlabel = isQx ? (m.repo||'GitHub') : 'Surge';
  const primary=`<a class="btn primary" href="${esc(isQx?m.hako:m.install)}">${SVG_DOWN}导入 Clash</a>`;
  const copy=`<button class="btn secondary" data-copy="${esc(m.lpx)}" title="复制资源链接，可手动导入任意客户端">${SVG_COPY}复制链接</button>`;
  return `
  <div class="card" data-id="${esc(m.lpx)}" title="点击查看详情">
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
      ${copy}
    </div>
  </div>`;
}

function render(){
  const list=filtered();
  const totalPages=Math.max(1,Math.ceil(list.length/PAGE_SIZE));
  if(state.page>totalPages) state.page=totalPages;
  const start=(state.page-1)*PAGE_SIZE;
  const pageItems=list.slice(start,start+PAGE_SIZE);
  byId={}; MODULES.forEach(m=>{ if(m.lpx) byId[m.lpx]=m; });
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
  if(t){ const url=t.dataset.copy; navigator.clipboard?.writeText(url).then(()=>toast('链接已复制 ✓')).catch(()=>toast('复制失败，请手动复制')); return; }
  if(e.target.closest('.acts')) return;            /* 导入 / 复制按钮自行处理，不触发弹窗 */
  const cardEl=e.target.closest('.card');
  if(!cardEl) return;
  const m=byId[cardEl.dataset.id];
  if(m) openModal(m);
});

/* ===== 模块详情弹窗 ===== */
const modal=document.getElementById('modal');
const modalBody=document.getElementById('modalBody');
function openModal(m){
  const isQx=m.source==='qx';
  const tags=(m.tags||[]).slice(0,8).map(t=>`<span class="tag">${esc(t)}</span>`).join('');
  const author=m.author?esc(m.author):'';
  const when=m.date?esc(String(m.date).slice(0,10)):'';
  const meta=[author,when].filter(Boolean).join(' · ');
  const rk=isQx?({'墨鱼手记':'ddg','毒奶特供':'adblock','重写库':'rewrite'}[m.repo]||'qx'):'surge';
  const rlabel=isQx?(m.repo||'GitHub'):'Surge';
  const primary=`<a class="btn primary" href="${esc(isQx?m.hako:m.install)}" target="_blank" rel="noopener">${SVG_DOWN}导入 Clash</a>`;
  const copy=`<button class="btn secondary" data-copy="${esc(m.lpx)}">${SVG_COPY}复制链接</button>`;
  const src=m.src||null;
  const srcHtml=src?`<div class="m-src">
      <div class="m-src-head">来源</div>
      <a class="m-src-link" href="${esc(src.url)}" target="_blank" rel="noopener">${SVG_LINK}${esc(src.name)} ↗</a>
      ${src.note?`<div class="m-src-note">${esc(src.note)}</div>`:''}
      <div class="m-src-url"><a href="${esc(m.lpx)}" target="_blank" rel="noopener">${esc(m.lpx)}</a></div>
    </div>`:'';
  modalBody.innerHTML=`
    <span class="src-badge" data-r="${rk}">${esc(rlabel)}</span>
    <div class="m-head">
      <div class="icon"><span>🧩</span><img src="${esc(m.icon)}" alt="" onerror="this.remove()"></div>
      <div style="min-width:0"><h3 id="modalTitle">${esc(m.name)}</h3>${meta?`<div class="meta">${meta}</div>`:''}</div>
    </div>
    <div class="m-desc">${esc(m.desc)||'—'}</div>
    ${tags?`<div class="tags">${tags}</div>`:''}
    ${srcHtml}
    <div class="m-acts">${primary}${copy}</div>`;
  modal.classList.add('show');
  modal.setAttribute('aria-hidden','false');
  document.body.style.overflow='hidden';
}
function closeModal(){
  modal.classList.remove('show');
  modal.setAttribute('aria-hidden','true');
  document.body.style.overflow='';
}
modal.addEventListener('click',e=>{
  if(e.target.closest('[data-close]')){ closeModal(); return; }
  const t=e.target.closest('[data-copy]');
  if(t){ const url=t.dataset.copy; navigator.clipboard?.writeText(url).then(()=>toast('链接已复制 ✓')).catch(()=>toast('复制失败，请手动复制')); }
});
document.addEventListener('keydown',e=>{ if(e.key==='Escape' && modal.classList.contains('show')) closeModal(); });

function toast(msg){
  const el=document.getElementById('toast');
  el.textContent=msg;el.classList.add('show');
  clearTimeout(el._t);el._t=setTimeout(()=>el.classList.remove('show'),1600);
}

const qEl=document.getElementById('q');
const clearBtn=document.getElementById('clearBtn');
let qTimer;
function syncClear(){ clearBtn.classList.toggle('show', qEl.value.length>0); }
qEl.addEventListener('input',e=>{state.q=e.target.value;state.page=1;syncClear();clearTimeout(qTimer);qTimer=setTimeout(render,200);});
clearBtn.addEventListener('click',()=>{ qEl.value=''; state.q=''; state.page=1; render(); syncClear(); qEl.focus(); });

/* 来源筛选：全部 / Surge / GitHub */
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
window.__cmReady=true; /* 通知看门狗：初始化完成 */

let surgeSync={cls:'load',text:'正在同步源站最新模块…'};
function setSync(cls,text,remember){
  syncEl.className='sync '+cls; syncText.textContent=text;
  if(remember!==false) surgeSync={cls,text};
}
function updateSyncForSource(){
  if(state.source==='qx'){
    setSync('ok',`GitHub 资源共 ${QX.length} 个（构建于 ${SNAPSHOT.buildDate||'—'}），导入链接直连仓库，始终拉取最新版`,false);
  }else{
    setSync(surgeSync.cls,surgeSync.text,false);
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
  SURGE=live;                        /* 实时同步只替换 Surge 部分，QX 为静态快照 */
  MODULES=SURGE.concat(QX);
  refreshTags(); totalEl.textContent=MODULES.length; render();
  if(extra) setSync(extra.cls,extra.text);
  return true;
}

/* 实时同步：qingr.json 与页面同域自托管，浏览器直连即可刷新（免 CORS / 免代理）；
   若 liveUrl 被覆盖为外部绝对地址，再走支持 CORS 的代理兜底 */
const LIVE_URL=SNAPSHOT.liveUrl||'qingr.json';
const LIVE_SOURCES=[
  {url:LIVE_URL, parse:r=>r.json()},                                   /* 同域直连（自托管 qingr.json） */
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
