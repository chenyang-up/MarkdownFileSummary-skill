"""Markdown 结构解析：抽离 frontmatter、章节树、块级结构与基础统计。

设计要点
--------
1. **单遍逐行状态机**负责识别围栏代码块（其余结构都依赖它，否则代码块里的
   `#`、`|`、`[a](b)` 会被误判）。
2. **掩码文本**：围栏内的行整行不做结构识别；行内代码用等长空格覆盖，保住字符
   偏移与行号，于是「掩码后定位、原行取文本」是安全的。
3. 所有 `line` 均为**原文件（含 frontmatter）的 1-based 行号**。

单层识别原则
------------
引用块内部的围栏 / 表格 / 列表**不递归识别**，整体降级为引用文本。这是刻意的：
递归解析会显著抬高复杂度与误判率，而本技能的用途是「给 AI 提供结构线索」，
不是做完整的 CommonMark 实现。
"""
from __future__ import annotations

import re
import types

_FRONTMATTER_RE = re.compile(r"^---[ \t]*\n(.*?)\n---[ \t]*\n?", re.DOTALL)
_FENCE_RE = re.compile(r"^(`{3,}|~{3,})\s*(.*)$")
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
_SETEXT_H1_RE = re.compile(r"^-{0,3}\s*={2,}\s*$")
_SETEXT_H2_RE = re.compile(r"^-{0,3}\s*-{2,}\s*$")
_TABLE_SEP_RE = re.compile(r"^-{0,3}\s*\|?\s*:?-{2,}:?\s*(?:\|\s*:?-{2,}:?\s*)*\|?\s*$")
_LIST_RE = re.compile(r"^(\s*)([-*+]|\d+[.)])\s+(.*)$")
_TASK_RE = re.compile(r"^\[([ xX])\]\s*(.*)$")
_QUOTE_RE = re.compile(r"^\s{0,3}((?:>\s?)+)(.*)$")
_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(\s*([^)\s]*)")
_LINK_INLINE_RE = re.compile(r"(?<!!)\[([^\]]*)\]\(\s*([^)\s]*)")
_LINK_FULL_REF_RE = re.compile(r"(?<!!)\[([^\]]+)\]\[([^\]]*)\]")
_AUTOLINK_RE = re.compile(r"<((?:https?|mailto):[^>\s]+)>")
_LINK_REF_DEF_RE = re.compile(r"^\s{0,3}\[([^\]]+)\]:\s*(\S+)")
_FOOTNOTE_DEF_RE = re.compile(r"^\s{0,3}\[\^([^\]]+)\]:\s*(.*)$")
_FOOTNOTE_REF_RE = re.compile(r"\[\^([^\]]+)\]")
_INLINE_CODE_RE = re.compile(r"(`+)(.+?)\1")
_HR_RE = re.compile(r"^(?:\s{0,3})(?:(?:\*\s*){3,}|(?:-\s*){3,}|(?:_\s*){3,})$")
_CJK_RE = re.compile(r"[\u4e00-\u9fff]")
_WORD_RE = re.compile(r"[A-Za-z0-9_]+")


# ---------------------------------------------------------------- frontmatter

def _parse_frontmatter_kv(raw: str) -> dict:
    """仅解析顶层 key: value，避免引入 YAML 依赖。"""
    data = {}
    for line in raw.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.startswith((" ", "\t", "-")):
            continue
        key, sep, value = line.partition(":")
        if not sep:
            continue
        value = value.strip().strip("'\"")
        data[key.strip()] = value
    return data


# ---------------------------------------------------------------- 行扫描

def _mask_inline(line: str) -> str:
    """把行内代码替换成等长空格，保住偏移与行号。"""
    return _INLINE_CODE_RE.sub(lambda m: " " * len(m.group(0)), line)


def _scan(body: str, body_start_line: int):
    """逐行扫描，返回 (records, code_blocks, indented_code_blocks)。

    record = {raw, masked, fence, indented}
    """
    records = []
    code_blocks = []
    fence_char = None
    fence_len = 0
    fence_start = None
    current = None
    indented_runs = 0
    in_indent_run = False
    prev_was_list = False

    for idx, raw in enumerate(body.split("\n")):
        line_no = body_start_line + idx
        stripped = raw.lstrip()
        m = _FENCE_RE.match(stripped)

        if fence_char is None and m:
            fence_char = m.group(1)[0]
            fence_len = len(m.group(1))
            fence_start = idx
            info = m.group(2).strip()
            current = {
                "lang": info.split()[0] if info else "",
                "info": info,
                "line": line_no,
                "end_line": None,
                "lines": 0,
                "closed": False,
                "fence": fence_char * fence_len,
            }
            code_blocks.append(current)
            records.append({"raw": raw, "masked": raw, "fence": True, "indented": False})
            prev_was_list = False
            in_indent_run = False
            continue

        if fence_char is not None:
            closing = (
                m
                and m.group(1)[0] == fence_char
                and len(m.group(1)) >= fence_len
                and not m.group(2).strip()
            )
            if closing:
                current["end_line"] = line_no
                current["lines"] = idx - fence_start - 1
                current["closed"] = True
                fence_char = None
                current = None
            records.append({"raw": raw, "masked": raw, "fence": True, "indented": False})
            prev_was_list = False
            in_indent_run = False
            continue

        indented = bool(raw.startswith("    ") or raw.startswith("\t")) and not prev_was_list
        records.append(
            {"raw": raw, "masked": _mask_inline(raw), "fence": False, "indented": indented}
        )
        if indented:
            if not in_indent_run:
                indented_runs += 1
                in_indent_run = True
        else:
            in_indent_run = False
        prev_was_list = bool(_LIST_RE.match(raw.strip()))

    if fence_char is not None and current is not None:
        current["lines"] = len(records) - fence_start - 1
    return (
        [types.SimpleNamespace(**r) for r in records],
        code_blocks,
        indented_runs,
    )


def _usable(rec) -> bool:
    return not rec.fence and not rec.indented


# ---------------------------------------------------------------- 表格

def _cell_ranges(masked_line: str):
    """按未被转义的 `|` 求单元格的字符区间。"""
    ranges, start, esc = [], 0, False
    for idx, ch in enumerate(masked_line):
        if esc:
            esc = False
        elif ch == "\\":
            esc = True
        elif ch == "|":
            ranges.append((start, idx))
            start = idx + 1
    ranges.append((start, len(masked_line)))
    raw = masked_line
    if ranges and not raw[ranges[0][0]:ranges[0][1]].strip():
        ranges = ranges[1:]
    if ranges and not raw[ranges[-1][0]:ranges[-1][1]].strip():
        ranges = ranges[:-1]
    return ranges


def _cells(raw_line: str, masked_line: str):
    return [raw_line[a:b].strip().replace("\\|", "|") for a, b in _cell_ranges(masked_line)]


def _align_of(sep_cell: str) -> str:
    cell = sep_cell.strip()
    left, right = cell.startswith(":"), cell.endswith(":")
    if left and right:
        return "center"
    if left:
        return "left"
    if right:
        return "right"
    return "none"


# ---------------------------------------------------------------- 章节

def _build_sections(headings, body, body_start_line):
    lines = body.split("\n")
    if not headings and not body.strip():
        return []

    last_line = body_start_line + len(lines) - 1
    offsets, pos = [], 0
    for ln in lines:
        offsets.append(pos)
        pos += len(ln) + 1
    total = len(body)

    def char_off(line_no: int) -> int:
        idx = line_no - body_start_line
        if idx < 0:
            return 0
        if idx >= len(offsets):
            return total
        return offsets[idx]

    def slice_of(start_line: int, end_line: int):
        start = char_off(start_line)
        end = total if end_line >= last_line else char_off(end_line + 1)
        return start, max(start, end)

    if not headings:
        start, end = char_off(body_start_line), total
        return [
            {
                "index": 0,
                "level": 0,
                "text": "(全文)",
                "synthetic": True,
                "line": body_start_line,
                "end_line": last_line,
                "subtree_end_line": last_line,
                "parent": -1,
                "start": start,
                "end": end,
                "chars": max(0, end - start),
                "breadcrumb": "(全文)",
            }
        ]

    n = len(headings)
    parents = []
    for i in range(n):
        p = -1
        for j in range(i - 1, -1, -1):
            if headings[j]["level"] < headings[i]["level"]:
                p = j
                break
        parents.append(p)

    preamble = None
    first_line = headings[0]["line"]
    has_preamble = any(
        lines[k].strip()
        for k in range(0, first_line - body_start_line)
        if 0 <= k < len(lines)
    )
    if has_preamble:
        start, end = slice_of(body_start_line, first_line - 1)
        preamble = {
            "index": 0,
            "level": 0,
            "text": "(前言)",
            "synthetic": True,
            "line": body_start_line,
            "end_line": first_line - 1,
            "subtree_end_line": first_line - 1,
            "parent": -1,
            "start": start,
            "end": end,
            "chars": max(0, end - start),
        }

    base = 1 if preamble else 0
    out = []
    for i, h in enumerate(headings):
        j = i + 1
        while j < n and headings[j]["level"] > h["level"]:
            j += 1
        end_line = (headings[i + 1]["line"] - 1) if i + 1 < n else last_line
        subtree_end = (headings[j]["line"] - 1) if j < n else last_line
        start, end = slice_of(h["line"], end_line)
        p = parents[i]
        out.append(
            {
                "index": i + base,
                "level": h["level"],
                "text": h["text"],
                "synthetic": False,
                "line": h["line"],
                "end_line": end_line,
                "subtree_end_line": subtree_end,
                "parent": (p + base) if p >= 0 else (0 if preamble else -1),
                "start": start,
                "end": end,
                "chars": max(0, end - start),
            }
        )

    sections = ([preamble] if preamble else []) + out
    for s in sections:
        chain, cur, guard = [], s["parent"], 0
        while cur is not None and cur >= 0 and guard < 32:
            chain.append(sections[cur]["text"])
            cur = sections[cur]["parent"]
            guard += 1
        s["breadcrumb"] = " > ".join(reversed(chain)) if chain else s["text"]
    return sections


# ---------------------------------------------------------------- 主入口

def parse_markdown(text: str) -> dict:
    frontmatter_raw = ""
    body = text
    match = _FRONTMATTER_RE.match(text)
    body_start_line = 1
    if match:
        frontmatter_raw = match.group(1)
        body = text[match.end():]
        body_start_line = text[: match.end()].count("\n") + 1

    records, code_blocks, indented_code_blocks = _scan(body, body_start_line)
    n = len(records)

    def line_no(i: int) -> int:
        return body_start_line + i

    # ATX 标题（用原始行取文本，保留标题里的行内代码）
    headings = []
    for i, rec in enumerate(records):
        if not _usable(rec):
            continue
        m = _HEADING_RE.match(rec.raw)
        if m:
            headings.append({"level": len(m.group(1)), "text": m.group(2).strip(), "line": line_no(i)})

    # 表格（优先级最高）
    tables, in_table = [], set()
    i = 0
    while i < n:
        if _usable(records[i]) and "|" in records[i].masked:
            if i + 1 < n and _usable(records[i + 1]) and _TABLE_SEP_RE.match(records[i + 1].masked):
                head_cells = _cells(records[i].raw, records[i].masked)
                sep_cells = _cells(records[i + 1].raw, records[i + 1].masked)
                if len(head_cells) >= 2 and len(sep_cells) == len(head_cells):
                    rows, j = [], i + 2
                    while j < n and _usable(records[j]) and "|" in records[j].masked:
                        if _TABLE_SEP_RE.match(records[j].masked):
                            break
                        rows.append(_cells(records[j].raw, records[j].masked))
                        j += 1
                    tables.append(
                        {
                            "line": line_no(i),
                            "end_line": line_no(j - 1),
                            "col_count": len(head_cells),
                            "row_count": len(rows),
                            "headers": head_cells,
                            "aligns": [_align_of(c) for c in sep_cells],
                            "rows": rows,
                        }
                    )
                    in_table.update(range(i, j))
                    i = j
                    continue
        i += 1

    # setext 标题（次优先）
    setext_lines = set()
    for i in range(1, n):
        rec, prev = records[i], records[i - 1]
        if not _usable(rec) or not _usable(prev):
            continue
        if not prev.raw.strip() or i in in_table or i - 1 in in_table:
            continue
        if _HEADING_RE.match(prev.masked) or _LIST_RE.match(prev.masked) or _QUOTE_RE.match(prev.masked):
            continue
        if _TABLE_SEP_RE.match(rec.masked) and "|" in rec.masked:
            continue
        level = None
        if _SETEXT_H1_RE.match(rec.masked):
            level = 1
        elif _SETEXT_H2_RE.match(rec.masked):
            level = 2
        if level:
            setext_lines.add(i)
            headings.append({"level": level, "text": prev.raw.strip(), "line": line_no(i - 1)})
            in_table.add(i - 1)

    headings.sort(key=lambda h: h["line"])

    # 列表（一层记录一条，含各层级项数分布）
    lists = []
    i = 0
    while i < n:
        rec = records[i]
        m = _LIST_RE.match(rec.masked) if _usable(rec) else None
        if m:
            base_indent = len(m.group(1).expandtabs(4))
            ordered = bool(re.match(r"\d", m.group(2)))
            items = tasks = checked = 0
            by_depth, max_depth = {}, 1
            start = i
            while i < n and _usable(records[i]):
                mm = _LIST_RE.match(records[i].masked)
                if not mm:
                    cur_indent = len(records[i].raw) - len(records[i].raw.lstrip())
                    if records[i].raw.strip() and cur_indent > base_indent:
                        i += 1
                        continue
                    break
                indent = len(mm.group(1).expandtabs(4))
                if indent < base_indent:
                    break
                depth = indent // 2 + 1
                max_depth = max(max_depth, depth)
                by_depth[str(depth)] = by_depth.get(str(depth), 0) + 1
                items += 1
                tm = _TASK_RE.match(mm.group(3))
                if tm:
                    tasks += 1
                    if tm.group(1).lower() == "x":
                        checked += 1
                i += 1
            if items:
                lists.append(
                    {
                        "line": line_no(start),
                        "end_line": line_no(i - 1),
                        "ordered": ordered,
                        "depth": base_indent // 2 + 1,
                        "max_depth": max_depth,
                        "item_count": items,
                        "task_total": tasks,
                        "task_checked": checked,
                        "by_depth": by_depth,
                    }
                )
                continue
        i += 1

    # 引用块
    blockquotes = []
    i = 0
    while i < n:
        m = _QUOTE_RE.match(records[i].masked) if _usable(records[i]) else None
        if m:
            start = i
            depth = m.group(1).count(">")
            max_depth, count = depth, 0
            while i < n and _usable(records[i]) and _QUOTE_RE.match(records[i].masked):
                max_depth = max(max_depth, _QUOTE_RE.match(records[i].masked).group(1).count(">"))
                count += 1
                i += 1
            blockquotes.append(
                {
                    "line": line_no(start),
                    "end_line": line_no(i - 1),
                    "depth": depth,
                    "max_depth": max_depth,
                    "lines": count,
                }
            )
            continue
        i += 1

    # 链接 / 图片 / 脚注 / 引用式定义 / 行内代码 / hr
    images, links, link_ref_defs, footnote_defs, footnote_refs = [], [], [], [], []
    inline_code_count = 0
    hr_count = 0
    for i, rec in enumerate(records):
        if not _usable(rec):
            continue
        for m in _IMAGE_RE.finditer(rec.masked):
            images.append({"line": line_no(i), "alt": m.group(1), "src": m.group(2)})
        for m in _LINK_INLINE_RE.finditer(rec.masked):
            links.append({"line": line_no(i), "kind": "inline", "text": m.group(1), "url": m.group(2)})
        for m in _LINK_FULL_REF_RE.finditer(rec.masked):
            links.append(
                {"line": line_no(i), "kind": "ref", "text": m.group(1), "url": m.group(2).strip()}
            )
        fd = _FOOTNOTE_DEF_RE.match(rec.masked)
        d = None if fd else _LINK_REF_DEF_RE.match(rec.masked)
        if d:
            link_ref_defs.append({"line": line_no(i), "label": d.group(1), "url": d.group(2)})
        if fd:
            footnote_defs.append({"line": line_no(i), "label": fd.group(1), "text": fd.group(2).strip()})
        else:
            for m in _FOOTNOTE_REF_RE.finditer(rec.masked):
                footnote_refs.append({"line": line_no(i), "label": m.group(1)})
        for m in _AUTOLINK_RE.finditer(rec.masked):
            links.append({"line": line_no(i), "kind": "auto", "text": m.group(1), "url": m.group(1)})
        inline_code_count += len(_INLINE_CODE_RE.findall(rec.raw))
        if _HR_RE.match(rec.masked.strip()) and i not in setext_lines:
            hr_count += 1

    sections = _build_sections(headings, body, body_start_line)
    lead = next((rec.raw.strip() for rec in records if _usable(rec) and rec.raw.strip()), "")[:200]

    return {
        "frontmatter": _parse_frontmatter_kv(frontmatter_raw),
        "frontmatter_raw": frontmatter_raw,
        "body": body,
        "headings": headings,
        "sections": sections,
        "outline": " > ".join(h["text"] for h in headings[:12]),
        "tables": tables,
        "lists": lists,
        "code_blocks": code_blocks,
        "code_block_count": len(code_blocks),
        "blockquotes": blockquotes,
        "images": images,
        "links": links,
        "link_count": len(links),
        "link_ref_defs": link_ref_defs,
        "footnote_defs": footnote_defs,
        "footnote_refs": footnote_refs,
        "inline_code_count": inline_code_count,
        "indented_code_blocks": indented_code_blocks,
        "hr_count": hr_count,
        "char_count": len(body),
        "words": len(_WORD_RE.findall(body)) + len(_CJK_RE.findall(body)),
        "lead": lead,
    }


def parse_file(path) -> dict:
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return parse_markdown(fh.read())
