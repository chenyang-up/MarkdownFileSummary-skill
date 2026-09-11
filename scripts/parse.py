"""Markdown 结构解析：抽离 frontmatter、标题大纲、正文与基础统计。"""
from __future__ import annotations

import re

_FRONTMATTER_RE = re.compile(r"^---[ \t]*\n(.*?)\n---[ \t]*\n?", re.DOTALL)
_FENCE_RE = re.compile(r"^(`{3,}|~{3,})")
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
_LINK_RE = re.compile(r"!?\[[^\]]*\]\([^)]*\)")
_CJK_RE = re.compile(r"[\u4e00-\u9fff]")
_WORD_RE = re.compile(r"[A-Za-z0-9_]+")


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


def parse_markdown(text: str) -> dict:
    frontmatter_raw = ""
    body = text
    match = _FRONTMATTER_RE.match(text)
    body_start_line = 1
    if match:
        frontmatter_raw = match.group(1)
        body = text[match.end():]
        body_start_line = text[: match.end()].count("\n") + 1

    headings = []
    code_blocks = 0
    in_fence = False
    lead_lines = []
    for idx, line in enumerate(body.split("\n")):
        if _FENCE_RE.match(line.lstrip()):
            if not in_fence:
                in_fence = True
                code_blocks += 1
            else:
                in_fence = False
            continue
        if in_fence:
            continue
        m = _HEADING_RE.match(line)
        if m:
            headings.append(
                {"level": len(m.group(1)), "text": m.group(2).strip(), "line": body_start_line + idx}
            )
        elif line.strip() and not lead_lines:
            lead_lines.append(line.strip())

    lead = " ".join(lead_lines)[:200]
    return {
        "frontmatter": _parse_frontmatter_kv(frontmatter_raw),
        "frontmatter_raw": frontmatter_raw,
        "body": body,
        "headings": headings,
        "outline": " > ".join(h["text"] for h in headings[:12]),
        "code_blocks": code_blocks,
        "link_count": len(_LINK_RE.findall(body)),
        "char_count": len(body),
        "words": len(_WORD_RE.findall(body)) + len(_CJK_RE.findall(body)),
        "lead": lead,
    }


def parse_file(path) -> dict:
    return parse_markdown(open(path, "r", encoding="utf-8", errors="replace").read())
