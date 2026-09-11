"""配置加载：零第三方依赖。

优先尝试 PyYAML；不可用时回退到内置的 YAML 子集解析器（覆盖本技能的配置语法），
并支持直接用 JSON 作为配置。所有缺失字段用 DEFAULTS 补齐。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

DEFAULTS = {
    "version": 3,
    "input": {
        "root": ".",
        "files": [],
        "merge_files_and_root": False,
        "include": ["**/*.md", "**/*.markdown"],
        "exclude": [
            "**/node_modules/**",
            "**/.git/**",
            "**/.workbuddy/**",
            "**/.idea/**",
            "**/dist/**",
            "**/build/**",
            "**/vendor/**",
            "**/_summary/**",
            "**/SUMMARY-*.md",
            "**/*.tmp.md",
        ],
        "min_bytes": 32,
        "max_file_bytes": 30 * 1024 * 1024,
        "max_files": 30,
        "follow_symlinks": False,
        "sort": "path_asc",
    },
    "output": {
        "dir": "~/Desktop",
        "name_template": "SUMMARY-{scope}-{timestamp}.md",
        "scope": "auto",
        "timestamp_format": "%Y%m%d-%H%M%S",
        "on_exists": "suffix",
        "frontmatter": True,
        "title": "auto",
    },
    "content": {
        "mode": "digest",
        "global": {
            "include_themes": True,
            "include_findings": True,
            "include_conflicts": True,
            "include_actions": True,
        },
        "index": {"include_stats": True, "include_index": True},
        "per_file": {
            "include_metadata": True,
            "include_one_liner": True,
            "include_key_points": True,
            "include_details": True,
            "include_quotes": True,
            "include_conclusions": True,
            "include_original_headings": True,
            "include_structure": True,
            "include_section_points": False,
            "max_summary_chars": 2000,
            "min_summary_chars": 200,
        },
        "merged": {"strip_frontmatter": True, "separator": "\n\n---\n\n", "source_anchor": True},
    },
}


def _strip_comment(line: str) -> str:
    """删除行内注释（忽略引号内的 #）。"""
    quote = None
    for i, ch in enumerate(line):
        if quote:
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
        elif ch == "#":
            return line[:i]
    return line


def _split_flow(body: str) -> list:
    """按顶层逗号切分 flow 序列内容，忽略引号内的逗号。"""
    items, buf, quote = [], [], None
    for ch in body:
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
            buf.append(ch)
        elif ch == ",":
            items.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    if buf:
        items.append("".join(buf))
    return [i.strip() for i in items if i.strip()]


def _coerce(scalar: str):
    s = scalar.strip()
    if s == "" or s in ("null", "~", "None"):
        return None
    # flow 序列：[] / [a, b] / ["a", "b"]（配置示例里常见，必须支持）
    if len(s) >= 2 and s[0] == "[" and s[-1] == "]":
        inner = s[1:-1].strip()
        return [] if not inner else [_coerce(x) for x in _split_flow(inner)]
    if s == "{}":
        return {}
    if s.lower() in ("true", "false"):
        return s.lower() == "true"
    if re.fullmatch(r"-?\d+", s):
        return int(s)
    if re.fullmatch(r"-?\d+\.\d+", s):
        return float(s)
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        body = s[1:-1]
        if s[0] == '"':
            return body.encode("utf-8").decode("unicode_escape")
        return body
    return s


def _parse_map(lines, i, indent):
    result = {}
    while i < len(lines):
        ind, text = lines[i]
        if ind < indent:
            break
        if ind > indent:
            break
        key, sep, rest = text.partition(":")
        if not sep:
            break
        key = key.strip().strip("'\"")
        rest = rest.strip()
        i += 1
        if rest == "":
            if i < len(lines) and lines[i][0] > indent:
                value, i = _parse_node(lines, i, lines[i][0])
            else:
                value = None
            result[key] = value
        else:
            result[key] = _coerce(rest)
    return result, i


def _parse_list(lines, i, indent):
    result = []
    while i < len(lines):
        ind, text = lines[i]
        if ind != indent or not (text == "-" or text.startswith("- ")):
            break
        item = text[1:].strip()
        i += 1
        if item == "":
            if i < len(lines) and lines[i][0] > indent:
                value, i = _parse_node(lines, i, lines[i][0])
            else:
                value = None
            result.append(value)
        elif ":" in item and not item.startswith(("'", '"')):
            sub = [(indent + 2, item)]
            while i < len(lines) and lines[i][0] > indent:
                sub.append(lines[i])
                i += 1
            value, _ = _parse_map(sub, 0, indent + 2)
            result.append(value)
        else:
            result.append(_coerce(item))
    return result, i


def _parse_node(lines, i, indent):
    if i >= len(lines):
        return None, i
    text = lines[i][1]
    if text == "-" or text.startswith("- "):
        return _parse_list(lines, i, indent)
    return _parse_map(lines, i, indent)


def _parse_yaml(text: str):
    lines = []
    for raw in text.splitlines():
        stripped = _strip_comment(raw).rstrip()
        if not stripped.strip():
            continue
        indent = len(stripped) - len(stripped.lstrip(" "))
        lines.append((indent, stripped.strip()))
    if not lines:
        return {}
    node, _ = _parse_node(lines, 0, lines[0][0])
    return node if isinstance(node, dict) else {}


def _deep_merge(base: dict, override: dict) -> dict:
    out = dict(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        elif value is not None:
            out[key] = value
    return out


def load_config(path=None) -> dict:
    """读取配置并与 DEFAULTS 深度合并。path 为 None 时只用默认值。"""
    data = {}
    if path:
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"配置文件不存在: {path}")
        raw = p.read_text(encoding="utf-8")
        if p.suffix.lower() == ".json":
            data = json.loads(raw)
        else:
            try:
                import yaml  # type: ignore

                data = yaml.safe_load(raw) or {}
            except Exception:
                data = _parse_yaml(raw)
    return _deep_merge(DEFAULTS, data if isinstance(data, dict) else {})
