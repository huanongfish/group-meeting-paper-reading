#!/usr/bin/env python3
"""把组会解读 HTML 关联回 Zotero 条目，并打上“已解读”标签。

用法：
  python3 link_to_zotero.py <解读.html> --doi 10.xxxx/xxxx [--dry-run]
  python3 link_to_zotero.py <解读.html> --key ABCD1234   [--dry-run]
可选：--pdf-key KEY（条目有多个 PDF 时指定）  --tag 标签名
      --label 名称（同一篇论文有多份解读时区分，如 --label 结合某项目）

前提：Zotero 正在运行；本地 API（23119）已启用；Zotero MCP Plugin 已开写权限（23120）。

规则：
  - PDF 是链接文件 → HTML 复制到 PDF 同一文件夹，名为“<PDF名>_组会解读.html”，挂链接附件；
  - PDF 在 Zotero storage → HTML 导入为存储附件（自带子文件夹，会随文件同步）；
  - 重跑只覆盖本条目已挂的那份解读，不重复挂附件；
  - 同名文件已存在、但不是本条目挂的解读且内容不同 → 停下，不覆盖；
  - DOI 找不到或命中多条、条目没有 PDF 或有多个 PDF → 停下报告，不猜；
  - 只加标签，不删除任何标签（/unread 等保持原样）。
"""
import argparse, filecmp, json, shutil, sys
import urllib.error, urllib.parse, urllib.request
from pathlib import Path

API = "http://127.0.0.1:23119/api/users/0"
MCP = "http://127.0.0.1:23120/mcp"
TITLE = "🌐 HTML · 组会解读"
SUFFIX = "_组会解读"
DEFAULT_TAG = "📖 状态:已精读"


def stop(msg):
    sys.exit("停止：" + msg)


def http(url, data=None, headers=None, timeout=60):
    try:
        req = urllib.request.Request(url, data=data, headers=headers or {})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        stop(f"{url} 返回 HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:300]}")
    except OSError as e:
        stop(f"连不上 {url}（Zotero 是否在运行？）：{e}")


def get(path, **params):
    q = "?" + urllib.parse.urlencode(params) if params else ""
    return json.loads(http(API + path + q))


def mcp(tool, args):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                       "params": {"name": tool, "arguments": args}}).encode()
    res = json.loads(http(MCP, body, {"Content-Type": "application/json",
                                      "Accept": "application/json, text/event-stream"}))
    if res.get("error") or res.get("result", {}).get("isError"):
        stop(f"插件 {tool} 报错：{json.dumps(res, ensure_ascii=False)[:500]}")
    text = "".join(c.get("text", "") for c in res["result"].get("content", []))
    try:
        out = json.loads(text)
    except ValueError:
        stop(f"插件 {tool} 返回无法解析：{text[:300]}")
    if isinstance(out, dict) and (out.get("success") is False or out.get("error")):
        stop(f"插件 {tool} 失败：{text[:500]}")
    return out


def norm_doi(s):
    s = (s or "").strip().lower()
    for p in ("https://doi.org/", "http://doi.org/", "http://dx.doi.org/", "https://dx.doi.org/", "doi:"):
        if s.startswith(p):
            s = s[len(p):].strip()
    return s


def find_item(doi):
    want = norm_doi(doi)
    hits = [x for x in get("/items", q=want, qmode="everything", limit=100)
            if norm_doi(x["data"].get("DOI")) == want and not x["data"].get("deleted")]
    if len(hits) != 1:
        stop(f"DOI {want} 命中 {len(hits)} 个条目" +
             ("：" + ", ".join(h["key"] for h in hits) + "；请用 --key 指定" if hits else ""))
    return hits[0]


def children(key):
    return [c for c in get(f"/items/{key}/children", limit=100)
            if c["data"]["itemType"] == "attachment" and not c["data"].get("deleted")]


def file_path(att_key):
    u = http(f"{API}/items/{att_key}/file/view/url").strip()
    return Path(urllib.parse.unquote(urllib.parse.urlparse(u).path))


def is_ours(c, title):
    d = c["data"]
    return (d["linkMode"] in ("linked_file", "imported_file")
            and d.get("contentType") == "text/html" and d.get("title") == title)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("html")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--doi")
    g.add_argument("--key")
    ap.add_argument("--pdf-key")
    ap.add_argument("--label", default="")
    ap.add_argument("--tag", default=DEFAULT_TAG)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    label = a.label.strip().replace("/", "-")
    title = TITLE + (f" · {label}" if label else "")
    suffix = SUFFIX + (f"_{label}" if label else "")

    src = Path(a.html).expanduser().resolve()
    if not src.is_file() or src.suffix.lower() != ".html":
        stop(f"找不到 HTML：{src}")

    item = get(f"/items/{a.key}") if a.key else find_item(a.doi)
    key = item["key"]
    if item["data"]["itemType"] in ("attachment", "note", "annotation"):
        stop(f"{key} 不是文献条目")
    print(f"条目 {key}：{item['data'].get('title')}")

    kids = children(key)
    ours = [c for c in kids if is_ours(c, title)]
    if len(ours) > 1:
        stop("条目下已有多份同名解读附件，请先人工清理：" + ", ".join(c["key"] for c in ours))

    if ours:
        mode, target = "update", file_path(ours[0]["key"])
    else:
        pdfs = [c for c in kids if c["data"].get("contentType") == "application/pdf"
                and c["data"]["linkMode"] in ("linked_file", "imported_file", "imported_url")]
        if a.pdf_key:
            pdfs = [c for c in pdfs if c["key"] == a.pdf_key]
        if len(pdfs) != 1:
            stop(f"条目有 {len(pdfs)} 个可用 PDF" +
                 ("：" + ", ".join(c["key"] for c in pdfs) + "；请用 --pdf-key 指定" if pdfs else ""))
        pdf = file_path(pdfs[0]["key"])
        if not pdf.is_file():
            stop(f"PDF 文件不在本机：{pdf}")
        if pdfs[0]["data"]["linkMode"] == "linked_file":
            mode, target = "link", pdf.with_name(pdf.stem + suffix + ".html")
            if target.exists() and target != src and not filecmp.cmp(src, target, shallow=False):
                stop(f"目标已存在且内容不同，未覆盖：{target}")
        else:
            mode, target = "import", None

    has_tag = a.tag in [t["tag"] for t in item["data"]["tags"]]
    print(f"方式：{mode}；目标：{target or 'Zotero storage（导入）'}")
    print(f"标签：{a.tag}（{'已有' if has_tag else '将添加'}）")
    if a.dry_run:
        print("dry-run：未写入")
        return

    if target and target != src:
        shutil.copy2(src, target)
    if mode != "update":
        mcp("write_item", {"action": "import", "parentItemKey": key, "title": title,
                           "filePath": str(target or src),
                           "linkMode": "linked_file" if mode == "link" else "imported_file"})
    if not has_tag:
        mcp("write_tag", {"action": "add", "itemKey": key, "tags": [a.tag]})

    # 读回核对（经 Zotero 本地 API，与写入途径相互独立）
    ours = [c for c in children(key) if is_ours(c, title)]
    tags = [t["tag"] for t in get(f"/items/{key}")["data"]["tags"]]
    if len(ours) != 1:
        stop(f"读回时解读附件数为 {len(ours)}，应为 1")
    real = file_path(ours[0]["key"])
    if not real.is_file() or not filecmp.cmp(src, real, shallow=False):
        stop(f"附件文件与解读不一致：{real}")
    if a.tag not in tags:
        stop("读回时没有看到标签")
    lost = {t["tag"] for t in item["data"]["tags"]} - set(tags)
    if lost:
        stop(f"原有标签丢失：{lost}")
    print(f"完成：附件 {ours[0]['key']}（{ours[0]['data']['linkMode']}）→ {real}")
    print(f"现有标签：{tags}")


if __name__ == "__main__":
    main()
