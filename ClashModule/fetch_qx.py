#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
采集 Quantumult X 资源，生成 ClashModule 页面用的 quantumult.json。

数据来源（三个 GitHub 仓库，用户指定）：
  A. deezertidal/QuantumultX-Rewrite   —— 重写库（以仓库 README 的精选索引为准，映射到 rewrite/*.conf）
  B. ddgksf2013/Rewrite + Filter       —— 墨鱼手记（34 个重写 conf + 11 个分流 list）
  C. limbopro/Adblock4limbo            —— 毒奶特供（4 个重写 conf + 6 个规则 list）

依赖 /tmp 下的目录树缓存（dee.json / ddg_rewrite.json / ddg_filter.json / adblock.json）
与 README 缓存（dee_readme.md），由前置 curl 步骤生成；本脚本只做选择 + 头部抓取 + 组装。
"""
import json
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

PROXY = "http://127.0.0.1:7890"
HERE = os.path.dirname(os.path.abspath(__file__))

REPOS = {
    "dee": ("deezertidal/QuantumultX-Rewrite", "master"),
    "ddg_rw": ("ddgksf2013/Rewrite", "master"),
    "ddg_filter": ("ddgksf2013/Filter", "master"),
    "adblock": ("limbopro/Adblock4limbo", "main"),
}


def load_tree(key):
    """读目录树缓存；缓存缺失时实时拉取 GitHub API（需本机代理 127.0.0.1:7890）。"""
    path = os.path.join("/tmp", {
        "dee": "dee.json", "ddg_rw": "ddg_rewrite.json",
        "ddg_filter": "ddg_filter.json", "adblock": "adblock.json",
    }[key])
    if not os.path.exists(path):
        repo, branch = REPOS[key]
        tok = os.environ.get("GITHUB_TOKEN", "")
        headers = ["-H", f"Authorization: token {tok}"] if tok else []
        out = subprocess.run(
            ["curl", "-s", "-x", PROXY, *headers,
             f"https://api.github.com/repos/{repo}/git/trees/{branch}?recursive=1"],
            capture_output=True, text=True, timeout=60,
        ).stdout
        with open(path, "w", encoding="utf-8") as f:
            f.write(out)
        print(f"[{key}] 目录树缓存缺失，已实时拉取 -> {path}")
    with open(path, encoding="utf-8") as f:
        return [t["path"] for t in json.load(f)["tree"] if t["type"] == "blob"]


def raw_url(key, path):
    repo, branch = REPOS[key]
    return f"https://raw.githubusercontent.com/{repo}/{branch}/{path}"


def fetch_head(key, path, lines=60):
    """抓取文件头部用于解析 #!name= / // @ScriptName 等元数据（带磁盘缓存）。"""
    cache_dir = "/tmp/qx_head_cache"
    os.makedirs(cache_dir, exist_ok=True)
    ckey = re.sub(r"[^\w.-]", "_", f"{key}__{path}") + ".txt"
    cpath = os.path.join(cache_dir, ckey)
    if os.path.exists(cpath):
        with open(cpath, encoding="utf-8") as f:
            return f.read()
    url = raw_url(key, path)
    try:
        out = subprocess.run(
            ["curl", "-s", "--max-time", "25", "-x", PROXY, url],
            capture_output=True, text=True, timeout=30,
        ).stdout
        head = "\n".join(out.splitlines()[:lines])
        with open(cpath, "w", encoding="utf-8") as f:
            f.write(head)
        return head
    except Exception as e:
        print(f"  [warn] fetch fail {path}: {e}", file=sys.stderr)
        return ""


def parse_meta(text):
    """兼容三种头部格式：#!k=v / // @k v / # k = v"""
    meta = {}
    for line in text.splitlines()[:80]:
        line = line.strip()
        m = re.match(r"#!\s*(\w+)\s*=\s*(.+)$", line)
        if m:
            meta.setdefault(m.group(1).lower(), m.group(2).strip())
            continue
        m = re.match(r"//\s*@(\w+)\s+(.+)$", line)
        if m:
            meta.setdefault(m.group(1).lower(), m.group(2).strip())
    return meta


def clean_name(s):
    s = re.sub(r"\(\d{4}年\d{1,2}月\d{1,2}日更新\)", "", s or "").strip()
    s = re.sub(r"\s+", " ", s)
    return s


def shorten(s, n=90):
    s = (s or "").strip().replace("\n", " ")
    return s if len(s) <= n else s[: n - 1] + "…"


# ---------- A. deezertidal：README 精选索引 → 仓库 rewrite/*.conf ----------
def collect_dee():
    tree = set(load_tree("dee"))
    readme_path = "/tmp/dee_readme.md"
    if not os.path.exists(readme_path):
        subprocess.run(
            ["curl", "-s", "-x", PROXY,
             "https://raw.githubusercontent.com/deezertidal/QuantumultX-Rewrite/master/README.md",
             "-o", readme_path], timeout=60,
        )
        print("[dee] README 缓存缺失，已实时拉取")
    with open(readme_path, encoding="utf-8") as f:
        readme = f.read()
    pat = re.compile(
        r"^\|\s*(:[^|:]+:)?\s*([^|]+?)\s*\|\s*\[:link:链接地址\]\(https://yfamilys\.com/rewrite/([^)#]+)\)",
        re.M,
    )
    picked, skipped = [], []
    for m in pat.finditer(readme):
        badge, name, fname = m.group(1) or "", m.group(2).strip(), m.group(3).strip()
        if ":x:" in badge:            # 作者标记失效的条目
            skipped.append((name, "作者标记失效"))
            continue
        repo_path = f"rewrite/{fname}"
        if repo_path not in tree:
            skipped.append((name, f"仓库无 {fname}"))
            continue
        picked.append({"name": name, "path": repo_path})
    # 去重（README 偶有重复行）
    seen, uniq = set(), []
    for p in picked:
        if p["path"] not in seen:
            seen.add(p["path"])
            uniq.append(p)
    print(f"[dee] README 命中 {len(uniq)} 个仓库文件；跳过 {len(skipped)} 条")
    for n, why in skipped[:10]:
        print(f"       skip: {n} ({why})")

    def build(item):
        head = fetch_head("dee", item["path"])
        meta = parse_meta(head)
        name = clean_name(item["name"]) or clean_name(meta.get("name")) or item["path"]
        desc = shorten(meta.get("desc") or meta.get("description"))
        author = meta.get("author") or "deezertidal"
        icon = meta.get("icon") or ""
        return {
            "name": name,
            "desc": desc or "可莉重写库 · Quantumult X 重写脚本",
            "author": author,
            "icon": icon,
            "url": raw_url("dee", item["path"]),
            "kind": "rewrite",
            "repo": "可莉重写库",
            "tags": ["可莉重写库", categorize(name, desc)],
        }

    return uniq, build


def categorize(name, desc):
    s = f"{name} {desc}"
    if re.search(r"去广告|净化|adblock|AdBlock|广告", s, re.I):
        return "去广告"
    if re.search(r"解锁|会员|VIP|Svip|SVIP|Pro\b|免费|黄金|数字专辑|倍速|加速", s):
        return "解锁"
    if re.search(r"分流|规则|list", s, re.I):
        return "分流规则"
    return "工具脚本"


# ---------- B. ddgksf2013 ----------
DDG_FILTER_META = {
    "AppleIntelligence.list": ("Apple Intelligence 分流", "Apple 智能功能分流规则"),
    "BlockiOSUpdate.list": ("屏蔽 iOS 系统更新", "屏蔽 iOS OTA 更新检测"),
    "Emby.list": ("Emby 分流", "Emby 媒体服务器分流"),
    "GoogleVoice.list": ("Google Voice 分流", "Google Voice 号码分流"),
    "NeteaseMusic.list": ("网易云音乐分流", "网易云音乐解锁分流"),
    "Streaming.list": ("国际流媒体分流", "Netflix / Disney+ 等国际流媒体分流"),
    "StreamingSE.list": ("东南亚流媒体分流", "东南亚区域流媒体分流"),
    "TikTok.list": ("TikTok 分流", "TikTok 区域分流"),
    "Unbreak.list": ("Unbreak 分流", "Unbreak 规则分流"),
    "WeChat.list": ("微信分流", "微信语音视频分流"),
    "anti-ip-attribution.list": ("IP 归属隐藏分流", "修改出口 IP 归属地（作者不建议使用）"),
}


def collect_ddg():
    rw_paths = [p for p in load_tree("ddg_rw") if p.endswith(".conf")]
    fl_paths = [p for p in load_tree("ddg_filter") if p.endswith(".list")]
    print(f"[ddg] 重写 {len(rw_paths)} 个，分流 {len(fl_paths)} 个")

    def build_rw(path):
        head = fetch_head("ddg_rw", path)
        meta = parse_meta(head)
        name = clean_name(meta.get("scriptname") or meta.get("name") or os.path.basename(path)[:-5])
        name = re.sub(r"\[墨鱼版\]\s*$", "", name).strip()   # 仓库标签已标明来源，去掉冗余后缀
        fn = meta.get("function") or meta.get("description") or ""
        if "addRequest" in fn or "共享表格" in fn:   # 通用客套，非真实描述
            fn = ""
        desc = shorten(fn) or "墨鱼手记出品的 Quantumult X 重写"
        return {
            "name": name,
            "desc": desc,
            "author": meta.get("author") or "ddgksf2013",
            "icon": meta.get("icon") or "",
            "url": raw_url("ddg_rw", path),
            "kind": "rewrite",
            "repo": "墨鱼手记",
            "tags": ["墨鱼手记", categorize(name, desc)],
        }

    rw_items = sorted(rw_paths)

    def build_fl(path):
        base = os.path.basename(path)
        name, desc = DDG_FILTER_META.get(base, (base[:-5], "墨鱼手记分流规则"))
        return {
            "name": name,
            "desc": desc,
            "author": "ddgksf2013",
            "icon": "",
            "url": raw_url("ddg_filter", path),
            "kind": "rule",
            "repo": "墨鱼手记",
            "tags": ["墨鱼手记", "分流规则"],
        }

    fl_items = sorted(fl_paths)
    return rw_items, build_rw, fl_items, build_fl


# ---------- C. Adblock4limbo ----------
ADBLOCK_RULE_META = {
    "Adblock4limbo.list": ("Adblock4limbo 主规则", "毒奶去广告计划主规则（合并 BanAD / EasyList 等）"),
    "BanAD.list": ("BanAD 去广告规则", "国内 App 去广告规则（BanAD）"),
    "easylist.list": ("EasyList 国际规则", "国际通用去广告规则（EasyList）"),
    "easylistchina.list": ("EasyList China 中文规则", "中文网站去广告规则（EasyList China）"),
    "easyprivacy.list": ("EasyPrivacy 隐私规则", "隐私跟踪屏蔽规则（EasyPrivacy）"),
    "Peter_Lowe_adservers.list": ("Peter Lowe 广告服务器规则", "广告服务器域名屏蔽规则"),
}

# 文件头无 #!name 的重写，手工补名与描述
ADBLOCK_RW_META = {
    "YouTubeAds.conf": ("YouTube 去广告", "毒奶特供 · YouTube 视频广告屏蔽"),
    "Zhihu.conf": ("知乎网页净化", "毒奶特供 · 知乎网页 UA 替换 + 直读"),
    "contentFarm.conf": ("内容农场清除", "毒奶特供 · Google 搜索结果内容农场清除"),
}


def collect_adblock():
    tree = load_tree("adblock")
    rw_paths = [p for p in tree
                if p.startswith("QuantumultX/rewrite/") and p.endswith(".conf")
                and not p.endswith("sample.conf")]
    fl_paths = [p for p in tree
                if p.startswith("QuantumultX/rule/") and p.endswith(".list")]
    print(f"[adblock] 重写 {len(rw_paths)} 个，规则 {len(fl_paths)} 个")

    def build_rw(path):
        base = os.path.basename(path)[:-5]
        meta_name, meta_desc = ADBLOCK_RW_META.get(os.path.basename(path), (None, None))
        if meta_name:
            return {
                "name": meta_name, "desc": meta_desc, "author": "limbopro", "icon": "",
                "url": raw_url("adblock", path), "kind": "rewrite", "repo": "毒奶特供",
                "tags": ["毒奶特供", "去广告"],
            }
        head = fetch_head("adblock", path)
        meta = parse_meta(head)
        name = clean_name(meta.get("name") or base)
        desc = shorten(meta.get("desc") or meta.get("description"))
        return {
            "name": name,
            "desc": desc or f"毒奶特供 · {base}",
            "author": "limbopro",
            "icon": meta.get("icon") or "",
            "url": raw_url("adblock", path),
            "kind": "rewrite",
            "repo": "毒奶特供",
            "tags": ["毒奶特供", categorize(name, desc) or "去广告"],
        }

    rw_items = sorted(rw_paths)

    def build_fl(path):
        base = os.path.basename(path)
        name, desc = ADBLOCK_RULE_META.get(base, (base[:-5], "毒奶特供规则"))
        return {
            "name": name,
            "desc": desc,
            "author": "limbopro",
            "icon": "",
            "url": raw_url("adblock", path),
            "kind": "rule",
            "repo": "毒奶特供",
            "tags": ["毒奶特供", "分流规则"],
        }

    fl_items = sorted(fl_paths)
    return rw_items, build_rw, fl_items, build_fl


def parallel_build(items, build):
    with ThreadPoolExecutor(max_workers=8) as ex:
        return list(ex.map(build, items))


def main():
    dee_items, dee_build = collect_dee()
    ddg_rw_items, ddg_rw_build, ddg_fl_items, ddg_fl_build = collect_ddg()
    ab_rw_items, ab_rw_build, ab_fl_items, ab_fl_build = collect_adblock()

    modules = []
    modules += parallel_build(dee_items, dee_build)
    modules += parallel_build(ddg_rw_items, ddg_rw_build)
    modules += parallel_build(ddg_fl_items, ddg_fl_build)
    modules += parallel_build(ab_rw_items, ab_rw_build)
    modules += parallel_build(ab_fl_items, ab_fl_build)

    # 去掉空名字 / 空 URL 的异常条目
    modules = [m for m in modules if m["name"] and m["url"]]

    out = {
        "name": "Quantumult X 资源合集",
        "sources": [
            {"key": "dee", "label": "可莉重写库", "home": "https://github.com/deezertidal/QuantumultX-Rewrite"},
            {"key": "ddg", "label": "墨鱼手记", "home": "https://github.com/ddgksf2013"},
            {"key": "adblock", "label": "毒奶特供", "home": "https://github.com/limbopro/Adblock4limbo"},
        ],
        "modules": modules,
    }
    dst = os.path.join(HERE, "quantumult.json")
    with open(dst, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"\n共 {len(modules)} 个 QX 资源 -> {dst}")
    for label in ("可莉重写库", "墨鱼手记", "毒奶特供"):
        n = sum(1 for m in modules if m["repo"] == label)
        r = sum(1 for m in modules if m["repo"] == label and m["kind"] == "rule")
        print(f"  {label}: {n} 个（规则 {r}）")
    print("\n样例：")
    for m in modules[:3] + modules[-3:]:
        print(f"  [{m['repo']}] {m['name']} | {m['desc'][:40]}")


if __name__ == "__main__":
    main()
