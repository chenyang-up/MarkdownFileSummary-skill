"""汇总文件组装：把 AI 撰写的摘要与综合，按 content.mode 排成最终 Markdown。

说明：本模块只做「排版」，不生成任何语义内容。凡是摘要、要点、引用、
主题脉络等字段缺失，都会显式标注为待补充，避免退化成「统计 + 拼接」。
"""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

_UNSAFE_RE = re.compile(r"[^\w\u4e00-\u9fff.-]+")
_CN_NUM = "一二三四五六七八九十"


def slugify(text: str) -> str:
    slug = _UNSAFE_RE.sub("-", text.strip().lower()).strip("-.")
    return slug or "summary"


def human_size(num: int) -> str:
    value = float(num)
    for unit in ("B", "KB", "MB"):
        if value < 1024:
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024.0
    return f"{value:.1f} GB"


def _truncate(text: str, limit: int) -> str:
    text = (text or "").strip()
    if limit and len(text) > limit:
        return text[:limit].rstrip() + " …"
    return text


def _bullets(items, prefix="- ") -> str:
    return "\n".join(f"{prefix}{str(x).strip()}" for x in items if str(x).strip())


def _as_list(value) -> list:
    if not value:
        return []
    if isinstance(value, str):
        return [value]
    return list(value)


def resolve_scope(cfg: dict, root_path: Path) -> str:
    raw = cfg["output"].get("scope", "auto")
    return root_path.name if raw in (None, "", "auto") else str(raw)


def resolve_output_dir(cfg: dict, root_path: Path) -> Path:
    """解析输出目录。

    规则：
    - `~` 开头或绝对路径 → 按原样使用（默认 `~/Desktop`，即桌面）；
    - 相对路径 → 相对 `input.root` 解析（便于把产物留在项目内）。
    """
    raw = str(cfg["output"].get("dir") or "~/Desktop")
    base = Path(raw).expanduser()
    return base if base.is_absolute() else (root_path / base).resolve()


def compute_output_path(cfg: dict, root_path: Path, file_count: int) -> Path:
    out_cfg = cfg["output"]
    scope = resolve_scope(cfg, root_path)
    timestamp = datetime.now().strftime(out_cfg.get("timestamp_format", "%Y%m%d-%H%M%S"))
    name = (
        out_cfg.get("name_template", "SUMMARY-{scope}-{timestamp}.md")
        .format(scope=slugify(scope), timestamp=timestamp, count=file_count)
    )
    out_dir = resolve_output_dir(cfg, root_path)
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / name

    on_exists = out_cfg.get("on_exists", "suffix")
    if target.exists():
        if on_exists == "overwrite":
            return target
        if on_exists == "fail":
            raise FileExistsError(f"输出文件已存在: {target}")
        stem, suffix, i = target.stem, target.suffix, 2
        while target.exists():
            target = out_dir / f"{stem}-{i}{suffix}"
            i += 1
    return target


# ---------------------------------------------------------------- 全局

def _global_block(summaries: dict) -> dict:
    """兼容 v1 的 global_summary 字段。"""
    g = dict(summaries.get("global") or {})
    if not g.get("overview") and summaries.get("global_summary"):
        g["overview"] = summaries["global_summary"]
    return g


def _global_section(cfg, summary: dict) -> str:
    gcfg = cfg["content"]["global"]
    overview = (summary.get("overview") or "").strip()
    lines = [overview or "> （待 AI 补充全局综述：跨文件的总体判断、主要结论与阅读建议）", ""]

    if gcfg.get("include_findings", True) and summary.get("key_findings"):
        lines += ["### 关键发现", "", _bullets(summary["key_findings"]), ""]
    if gcfg.get("include_conflicts", True) and summary.get("conflicts"):
        lines += ["### 分歧 / 待确认", "", _bullets(summary["conflicts"]), ""]
    if gcfg.get("include_actions", True) and summary.get("actions"):
        lines += ["### 行动项 / 后续", "", _bullets(summary["actions"], prefix="- [ ] "), ""]
    return "\n".join(lines)


def _themes_section(cfg, summary: dict):
    if not cfg["content"]["global"].get("include_themes", True):
        return None
    themes = summary.get("themes") or []
    if not themes:
        return None
    lines = []
    for i, theme in enumerate(themes, 1):
        if isinstance(theme, str):
            lines += [f"#### {i}. {theme}", ""]
            continue
        lines += [f"#### {i}. {theme.get('title', '未命名主题')}", ""]
        if theme.get("summary"):
            lines += [str(theme["summary"]).strip(), ""]
        points = _as_list(theme.get("points"))
        if points:
            lines += [_bullets(points), ""]
        sources = _as_list(theme.get("sources"))
        if sources:
            lines += ["- 来源：" + "、".join(f"`{s}`" for s in sources), ""]
    return "\n".join(lines)


def _index_section(cfg, manifest, summaries) -> str:
    icfg = cfg["content"]["index"]
    lines = []
    if icfg.get("include_stats", True):
        total_bytes = sum(f["size"] for f in manifest)
        total_lines = sum(f["lines"] for f in manifest)
        lines += [
            f"- 纳入文件：**{len(manifest)}** 个",
            f"- 总行数：**{total_lines}** 行",
            f"- 总体积：**{human_size(total_bytes)}**",
            "",
        ]
    if icfg.get("include_index", True):
        lines += ["| # | 文件 | 标题 | 重要度 | 行数 | 摘要 |", "| --- | --- | --- | --- | --- | --- |"]
        for i, f in enumerate(manifest, 1):
            rel = f["rel_path"]
            info = summaries["files"].get(rel, {})
            title = str(info.get("title") or info.get("one_liner") or "").replace("|", "\\|")[:30]
            star = str(info.get("importance") or "-")
            brief = _truncate(info.get("one_liner") or info.get("summary", ""), 50).replace("|", "\\|")
            lines.append(f"| {i} | [{rel}](#{slugify(rel)}) | {title} | {star} | {f['lines']} | {brief} |")
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------- 分文件

def _per_file_section(cfg, manifest, parsed, summaries) -> str:
    pf = cfg["content"]["per_file"]
    limit = int(pf.get("max_summary_chars") or 0)
    blocks = []
    for i, f in enumerate(manifest, 1):
        rel = f["rel_path"]
        info = summaries["files"].get(rel, {})
        lines = [f'<a id="{slugify(rel)}"></a>', "", f"#### {i}. {info.get('title') or rel}", ""]

        if pf.get("include_metadata", True):
            meta = f"- 路径：`{rel}` ｜ {f['lines']} 行 ｜ {human_size(f['size'])} ｜ 修改于 {f['mtime']}"
            if info.get("importance"):
                meta += f" ｜ 重要度：{info['importance']}"
            lines.append(meta)
        if info.get("tags"):
            lines.append("- 标签：" + "、".join(str(t) for t in _as_list(info["tags"])))

        if pf.get("include_one_liner", True):
            one = (info.get("one_liner") or "").strip()
            lines += ["", f"**一句话**：{one or '（待补充）'}"]

        summary = (info.get("summary") or "").strip()
        if not summary:
            hint = "（待 AI 精读原文后撰写详细摘要，禁止留空或仅做统计拼接）"
            if f.get("lead"):
                hint = f"> 原文开头（未经加工，仅供参考）：{_truncate(f['lead'], 120)}"
            summary = hint
        lines += ["", "**内容摘要**：", "", _truncate(summary, limit), ""]

        if pf.get("include_key_points", True):
            points = _as_list(info.get("key_points"))
            lines += ["**核心要点**：", "", _bullets(points) or "- （待补充）", ""]

        if pf.get("include_details", True):
            details = _as_list(info.get("details"))
            if details:
                lines += ["**重要细节 / 数据**：", "", _bullets(details), ""]

        if pf.get("include_quotes", True):
            quotes = _as_list(info.get("quotes"))
            if quotes:
                lines += ["**原文关键引用**：", ""]
                lines += ["> " + str(q).strip().replace("\n", "\n> ") for q in quotes]
                lines += [""]

        if pf.get("include_conclusions", True):
            conclusions = _as_list(info.get("conclusions"))
            if conclusions:
                lines += ["**结论 / 影响**：", "", _bullets(conclusions), ""]

        if pf.get("include_original_headings", True):
            headings = parsed.get(rel, {}).get("headings") or []
            if headings:
                lines += ["<details><summary>原文标题大纲</summary>", ""]
                lines += [f"{'  ' * (h['level'] - 1)}- {h['text']}" for h in headings]
                lines += ["", "</details>", ""]
        blocks.append("\n".join(lines))
    return "\n---\n\n".join(blocks)


# ---------------------------------------------------------------- 合并正文

def _merged_section(cfg, manifest, parsed) -> str:
    mg = cfg["content"]["merged"]
    separator = mg.get("separator", "\n\n---\n\n")
    blocks = []
    for f in manifest:
        rel = f["rel_path"]
        data = parsed.get(rel, {})
        body = data.get("body", "")
        if not mg.get("strip_frontmatter", True) and data.get("frontmatter_raw"):
            body = f"---\n{data['frontmatter_raw']}\n---\n\n{body}"
        if mg.get("source_anchor", True):
            body = f'<a id="body-{slugify(rel)}"></a>\n\n#### 来源：`{rel}`\n\n{body}'
        blocks.append(body.rstrip())
    return separator.join(blocks) + "\n"


# ---------------------------------------------------------------- 入口

def _numbered(sections) -> str:
    out = []
    for i, (title, body) in enumerate(sections):
        num = _CN_NUM[i] if i < len(_CN_NUM) else str(i + 1)
        out.append(f"## {num}、{title}\n\n{body.strip()}\n")
    return "\n".join(out)


def build_document(cfg, root_path: Path, manifest, parsed, summaries, generated_at=None) -> str:
    generated_at = generated_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    scope = resolve_scope(cfg, root_path)
    mode = cfg["content"].get("mode", "digest")
    title_cfg = cfg["output"].get("title", "auto")
    title = f"{scope} 汇总" if title_cfg in (None, "", "auto") else str(title_cfg)
    gsummary = _global_block(summaries)

    sections = []
    if mode in ("overview", "digest", "full"):
        sections.append(("全局综述", _global_section(cfg, gsummary)))
        themes = _themes_section(cfg, gsummary)
        if themes:
            sections.append(("主题脉络", themes))
    if mode in ("digest", "full"):
        sections.append(("文件索引", _index_section(cfg, manifest, summaries)))
        sections.append(("分文件详细摘要", _per_file_section(cfg, manifest, parsed, summaries)))
    if mode in ("full", "merged"):
        sections.append(("合并正文（附录）", _merged_section(cfg, manifest, parsed)))

    parts = []
    if cfg["output"].get("frontmatter", True):
        parts.append(
            "\n".join(
                [
                    "---",
                    f"title: {title}",
                    f"generated_at: {generated_at}",
                    f"source_root: {root_path}",
                    f"file_count: {len(manifest)}",
                    f"mode: {mode}",
                    "generator: markdown-file-summary",
                    "---",
                    "",
                ]
            )
        )
    parts.append(f"# {title}\n")
    parts.append(
        f"> 来源目录：`{root_path}` ｜ 文件数：{len(manifest)} ｜ 生成时间：{generated_at} ｜ "
        f"模式：{mode}（摘要由 AI 精读生成）\n"
    )
    parts.append(_numbered(sections))
    return "\n".join(parts).rstrip() + "\n"


def validate(cfg, manifest, summaries) -> list:
    """检查摘要覆盖度与详实度，返回问题列表。"""
    issues = []
    min_chars = int(cfg["content"]["per_file"].get("min_summary_chars") or 0)
    for f in manifest:
        rel = f["rel_path"]
        info = summaries["files"].get(rel)
        if not info:
            issues.append(f"缺少摘要：{rel}")
            continue
        length = len((info.get("summary") or "").strip())
        if min_chars and length < min_chars:
            issues.append(f"摘要过简（{length} < {min_chars} 字）：{rel}")
        if not info.get("key_points"):
            issues.append(f"缺少核心要点：{rel}")
    if not _global_block(summaries).get("overview"):
        issues.append("缺少全局综述（global.overview）")
    return issues
