"""输入发现与筛选。

三种输入来源，优先级：显式文件清单 > 目录扫描（`input.merge_files_and_root` 可改为合并）。
仅支持本地文件；http/https 远程地址一律拒绝。
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path

_REMOTE_PREFIXES = ("http://", "https://")


class InputError(Exception):
    """用户显式指定的输入不合法（远程地址、文件不存在等），需终止并提示。"""

    def __init__(self, items):
        self.items = list(items)
        super().__init__("；".join(self.items))


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


def is_remote(raw: str) -> bool:
    return str(raw).strip().lower().startswith(_REMOTE_PREFIXES)


def display_id(path: Path, root_path: Path, source: str) -> str:
    """唯一标识 / 输出展示路径。

    - 位于 root 内 → 相对 root 的路径
    - 落在 root 外（或显式清单里的外部文件）→ 本地绝对路径（即「本地上传地址」）
    """
    try:
        return path.relative_to(root_path).as_posix()
    except ValueError:
        return str(path)


def split_tokens(raw) -> list:
    """把一条输入拆成若干文件路径。

    兼容三种写法：单个路径、逗号分隔、换行分隔（用户从工具里粘贴列表的常见形态）。
    若整条本身就是存在的文件，则原样保留，避免误拆含逗号的文件名。
    """
    text = str(raw).strip().strip('"').strip("'")
    if not text:
        return []
    if Path(text).expanduser().exists():
        return [text]
    return [p.strip().strip('"').strip("'") for p in re.split(r"[,\n]", text) if p.strip()]


def resolve_explicit(raw_items):
    """把显式清单解析成绝对路径列表。返回 (路径列表, 错误列表)。

    仅接受本地文件；http/https 直接报错，不静默跳过——用户是显式指定的。
    """
    resolved, errors = [], []
    for raw in raw_items:
        for text in split_tokens(raw):
            if is_remote(text):
                errors.append(f"不支持的远程地址（仅支持本地文件）：{text}")
                continue
            candidate = Path(text).expanduser()
            if not candidate.is_absolute():
                candidate = Path.cwd() / candidate
            candidate = candidate.resolve()
            if not candidate.exists():
                errors.append(f"文件不存在：{text}")
                continue
            if not candidate.is_file():
                errors.append(f"不是文件：{text}")
                continue
            resolved.append(candidate)
    return resolved, errors


def _make_entry(path: Path, root_path: Path, source: str, min_bytes: int, max_file_bytes: int, include):
    """构造清单条目。返回 (entry, skip)；体积/类型不符时 entry 为 None。"""
    rel = display_id(path, root_path, source)
    size = path.stat().st_size

    if not any(r.match(rel) for r in include):
        return None, {"rel_path": rel, "reason": "unsupported_ext", "size": size}
    if size < min_bytes:
        return None, {"rel_path": rel, "reason": "too_small", "size": size}
    if max_file_bytes and size > max_file_bytes:
        return None, {"rel_path": rel, "reason": "too_large", "size": size}

    data = path.read_bytes()
    stat = path.stat()
    return (
        {
            "rel_path": rel,
            "abs_path": str(path),
            "source": source,
            "size": len(data),
            "lines": data.count(b"\n") + (0 if data.endswith(b"\n") else 1),
            "sha1": hashlib.sha1(data).hexdigest()[:12],
            "mtime": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
            .astimezone()
            .strftime("%Y-%m-%d %H:%M:%S"),
            "mtime_ts": stat.st_mtime,
        },
        None,
    )


def discover(cfg: dict, root=None):
    """返回 (根目录 Path, 文件清单 list[dict], 跳过清单 list[dict])。

    输入来源规则：
    - 给了 `input.files`（显式清单，含填写的地址与附件本地地址）→ 默认只用它，忽略目录；
      置 `input.merge_files_and_root: true` 则两者合并（按绝对路径去重）。
    - 没给清单 → 扫描 `input.root` 目录。
    """
    in_cfg = cfg["input"]
    root_path = Path(root or in_cfg["root"]).expanduser().resolve()

    explicit_raw = [x for x in (in_cfg.get("files") or []) if str(x).strip()]
    merge = bool(in_cfg.get("merge_files_and_root"))
    include = [glob_to_regex(p) for p in in_cfg["include"]]
    exclude = [glob_to_regex(p) for p in in_cfg["exclude"]]
    min_bytes = int(in_cfg.get("min_bytes") or 0)
    max_file_bytes = int(in_cfg.get("max_file_bytes") or 0)
    max_files = int(in_cfg.get("max_files") or 0)
    follow = bool(in_cfg.get("follow_symlinks"))

    files, skipped, seen = [], [], set()

    # 来源一：显式文件清单（填写的地址 + 工具添加的附件，两者合并去重）
    if explicit_raw:
        resolved, errors = resolve_explicit(explicit_raw)
        if errors:
            raise InputError(errors)
        for path in resolved:
            key = str(path)
            if key in seen:
                continue
            seen.add(key)
            entry, skip = _make_entry(path, root_path, "files", min_bytes, max_file_bytes, include)
            if entry:
                files.append(entry)
            else:
                skipped.append(skip)

    # 来源二：目录扫描（无清单时必做；有清单时仅在 merge 模式下补做）
    if not explicit_raw or merge:
        if not root_path.is_dir():
            raise NotADirectoryError(f"输入目录不存在或不是目录: {root_path}")
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
            key = str(path.resolve())
            if key in seen:
                continue
            seen.add(key)
            entry, skip = _make_entry(path, root_path, "scan", min_bytes, max_file_bytes, include)
            if entry:
                files.append(entry)
            else:
                skipped.append(skip)

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
        "unsupported_ext": "不支持的扩展名",
    }
    buckets = {}
    for item in skipped:
        buckets[item["reason"]] = buckets.get(item["reason"], 0) + 1
    parts = "，".join(f"{labels.get(k, k)} {v} 个" for k, v in sorted(buckets.items()))
    detail = "、".join(f"{item['rel_path']}（{labels.get(item['reason'], item['reason'])}）" for item in skipped[:5])
    more = " 等" if len(skipped) > 5 else ""
    return f"已跳过 {len(skipped)} 个文件：{parts}。明细：{detail}{more}"
