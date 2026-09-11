"""输入发现与筛选：按 include/exclude glob、大小、数量上限挑选待汇总的 Markdown 文件。"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path


def glob_to_regex(pattern: str) -> re.Pattern:
    """把含 ** 的 glob 转为正则。** 匹配任意层级目录，* 只匹配单层。"""
    p = pattern.replace("\\", "/")
    out = []
    i, n = 0, len(p)
    while i < n:
        ch = p[i]
        if ch == "*":
            if i + 1 < n and p[i + 1] == "*":
                if i + 2 < n and p[i + 2] == "/":
                    out.append("(?:.*/)?")
                    i += 3
                else:
                    out.append(".*")
                    i += 2
            else:
                out.append("[^/]*")
                i += 1
        elif ch == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(ch))
            i += 1
    return re.compile("^" + "".join(out) + "$")


def _sort_key(mode: str):
    if mode == "mtime_desc":
        return lambda f: (-f["mtime_ts"], f["rel_path"])
    if mode == "size_desc":
        return lambda f: (-f["size"], f["rel_path"])
    return lambda f: f["rel_path"]


def discover(cfg: dict, root=None):
    """返回 (根目录 Path, 文件清单 list[dict], 跳过清单 list[dict])。

    先按 stat 判断体积，再读取内容，避免读入超限的大文件。
    跳过的文件记录原因，供调用方提示用户。
    """
    in_cfg = cfg["input"]
    root_path = Path(root or in_cfg["root"]).expanduser().resolve()
    if not root_path.is_dir():
        raise NotADirectoryError(f"输入目录不存在或不是目录: {root_path}")

    include = [glob_to_regex(p) for p in in_cfg["include"]]
    exclude = [glob_to_regex(p) for p in in_cfg["exclude"]]
    min_bytes = int(in_cfg.get("min_bytes") or 0)
    max_file_bytes = int(in_cfg.get("max_file_bytes") or 0)
    max_files = int(in_cfg.get("max_files") or 0)
    follow = bool(in_cfg.get("follow_symlinks"))

    files = []
    skipped = []
    for path in root_path.rglob("*"):
        if not path.is_file():
            continue
        if path.is_symlink() and not follow:
            continue
        rel = path.relative_to(root_path).as_posix()
        if not any(r.match(rel) for r in include):
            continue
        if any(r.match(rel) for r in exclude):
            continue

        size = path.stat().st_size
        if size < min_bytes:
            skipped.append({"rel_path": rel, "reason": "too_small", "size": size})
            continue
        if max_file_bytes and size > max_file_bytes:
            skipped.append({"rel_path": rel, "reason": "too_large", "size": size})
            continue

        data = path.read_bytes()
        stat = path.stat()
        files.append(
            {
                "rel_path": rel,
                "abs_path": str(path),
                "size": len(data),
                "lines": data.count(b"\n") + (0 if data.endswith(b"\n") else 1),
                "sha1": hashlib.sha1(data).hexdigest()[:12],
                "mtime": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
                .astimezone()
                .strftime("%Y-%m-%d %H:%M:%S"),
                "mtime_ts": stat.st_mtime,
            }
        )

    files.sort(key=_sort_key(in_cfg.get("sort", "path_asc")))
    if max_files and len(files) > max_files:
        for extra in files[max_files:]:
            skipped.append({"rel_path": extra["rel_path"], "reason": "over_max_files", "size": extra["size"]})
        files = files[:max_files]
    return root_path, files, skipped


def summarize_skipped(skipped) -> str:
    """把跳过原因汇总成一行人类可读文案。"""
    if not skipped:
        return ""
    labels = {
        "too_large": "超过单文件体积上限",
        "too_small": "小于最小体积",
        "over_max_files": "超过文件数量上限",
    }
    buckets = {}
    for item in skipped:
        buckets[item["reason"]] = buckets.get(item["reason"], 0) + 1
    parts = "，".join(f"{labels.get(k, k)} {v} 个" for k, v in sorted(buckets.items()))
    detail = "、".join(f"{item['rel_path']}（{labels.get(item['reason'], item['reason'])}）" for item in skipped[:5])
    more = " 等" if len(skipped) > 5 else ""
    return f"已跳过 {len(skipped)} 个文件：{parts}。明细：{detail}{more}"
