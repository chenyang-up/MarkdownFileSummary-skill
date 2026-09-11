#!/usr/bin/env python3
"""Markdown 文件汇总 CLI。

本技能不是「统计 + 拼接」：脚本负责发现、读取、解析与排版，
摘要与综合必须由 AI 逐篇精读后写入 summaries.json。

子命令：
  discover  发现并筛选输入文件，输出 manifest.json
  extract   解析每个文件的结构与正文，输出 extract.json（供 AI 精读）
  validate  检查 summaries.json 的覆盖度与详实度
  assemble  合并 manifest + summaries + 正文，写出最终汇总 Markdown

示例（$SKILL_DIR 指本技能根目录，即 SKILL.md 所在目录，与当前工作目录无关）：
  python3 "$SKILL_DIR/scripts/main.py" discover --root ./docs
  python3 "$SKILL_DIR/scripts/main.py" extract  --root ./docs --out extract.json
  python3 "$SKILL_DIR/scripts/main.py" validate --root ./docs \
      --manifest manifest.json --summaries summaries.json
  python3 "$SKILL_DIR/scripts/main.py" assemble --root ./docs \
      --manifest manifest.json --summaries summaries.json

未指定 --config 时，默认读取本技能自带的 config/default.yaml（按脚本所在位置解析）。
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
SKILL_DIR = _SCRIPTS_DIR.parent
DEFAULT_CONFIG = SKILL_DIR / "config" / "default.yaml"

sys.path.insert(0, str(_SCRIPTS_DIR))

import build  # noqa: E402
import collect  # noqa: E402
import parse  # noqa: E402
from config import load_config  # noqa: E402


def _load_cfg(args):
    """加载配置：--config 优先，否则用技能自带的 config/default.yaml。

    默认值按脚本位置解析为绝对路径，因此从任意工作目录调用都能命中，
    不依赖当前工作目录。命令行 --files 会追加进 input.files。
    """
    cfg = load_config(args.config or str(DEFAULT_CONFIG))
    cli_files = []
    for group in (getattr(args, "files", None) or []):
        cli_files.extend(group if isinstance(group, (list, tuple)) else [group])
    if cli_files:
        existing = list(cfg["input"].get("files") or [])
        cfg["input"]["files"] = existing + cli_files
    return cfg


def _info(msg: str = ""):
    """人读信息一律走 stderr，保证 stdout 只有机器可读输出（`--out -` 时是纯 JSON）。"""
    print(msg, file=sys.stderr)


def _dump(data, out: str):
    text = json.dumps(data, ensure_ascii=False, indent=2)
    if out == "-":
        print(text)
        return
    target = Path(out)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text + "\n", encoding="utf-8")
    _info(f"已写入 {out}")


def _load_json(path: str):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _apply_cli_overrides(cfg, args):
    if getattr(args, "mode", None):
        cfg["content"]["mode"] = args.mode
    if getattr(args, "out_dir", None):
        cfg["output"]["dir"] = args.out_dir
    return cfg


def _discover(cfg, root, quiet=False):
    """发现文件；有文件被排除时打印一行提示。"""
    root_path, files, skipped = collect.discover(cfg, root)
    if skipped and not quiet:
        _info(collect.summarize_skipped(skipped))
    return root_path, files, skipped


def _input_source_desc(cfg) -> str:
    explicit = [x for x in (cfg["input"].get("files") or []) if str(x).strip()]
    if explicit and cfg["input"].get("merge_files_and_root"):
        return f"显式文件清单 + 目录扫描（合并）"
    if explicit:
        return "显式文件清单（忽略目录）"
    return "目录扫描"


def cmd_discover(args):
    cfg = _apply_cli_overrides(_load_cfg(args), args)
    root, files, skipped = _discover(cfg, args.root)
    _dump(
        {
            "root": str(root),
            "input_source": _input_source_desc(cfg),
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "count": len(files),
            "skipped_count": len(skipped),
            "skipped": skipped,
            "files": files,
        },
        args.out,
    )
    if args.out != "-":
        limits = cfg["input"]
        max_bytes = int(limits.get("max_file_bytes") or 0)
        max_files = int(limits.get("max_files") or 0)
        size_txt = build.human_size(max_bytes) if max_bytes else "不限"
        _info(
            f"发现 {len(files)} 个 Markdown 文件"
            f"（来源：{_input_source_desc(cfg)}；上限：单文件 {size_txt}，数量 {max_files or '不限'}）"
        )


def cmd_extract(args):
    cfg = _load_cfg(args)
    root, files, _ = _discover(cfg, args.root)
    parsed = {f["rel_path"]: parse.parse_file(f["abs_path"]) for f in files}
    _dump({"root": str(root), "count": len(parsed), "files": parsed}, args.out)
    if args.out != "-":
        _info(
            f"已解析 {len(parsed)} 个文件的结构与正文。"
            "请逐篇精读正文，按 references/summarization-guide.md 撰写 summaries.json。"
        )


def _load_summaries(path):
    if not path:
        return {"global": {}, "files": {}}
    data = _load_json(path)
    data.setdefault("files", {})
    data.setdefault("global", {})
    return data


def cmd_validate(args):
    cfg = _load_cfg(args)
    _, files, _ = _discover(cfg, args.root, quiet=bool(args.manifest))
    manifest = _load_json(args.manifest)["files"] if args.manifest else files
    issues = build.validate(cfg, manifest, _load_summaries(args.summaries))
    if not issues:
        _info(f"校验通过：{len(manifest)} 个文件均已有达标摘要与全局综述")
        return 0
    _info(f"发现 {len(issues)} 个问题：")
    for item in issues:
        _info(f"  - {item}")
    return 1


def cmd_assemble(args):
    cfg = _apply_cli_overrides(_load_cfg(args), args)
    root, files, _ = _discover(cfg, args.root, quiet=bool(args.manifest))
    manifest = _load_json(args.manifest)["files"] if args.manifest else files
    summaries = _load_summaries(args.summaries)
    parsed = {f["rel_path"]: parse.parse_file(f["abs_path"]) for f in manifest}

    issues = build.validate(cfg, manifest, summaries)
    if issues:
        _info(f"提示：{len(issues)} 项摘要尚未达标（详见 validate），输出将标注待补充。")

    doc = build.build_document(cfg, root, manifest, parsed, summaries)
    if args.out and args.out != "-":
        target = Path(args.out)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(doc, encoding="utf-8")
    else:
        target = build.compute_output_path(cfg, root, len(manifest))
        target.write_text(doc, encoding="utf-8")
    _info(f"汇总完成：{target}（{len(manifest)} 个文件，{len(doc)} 字符）")
    return 0


def build_parser():
    parser = argparse.ArgumentParser(prog="markdown-file-summary", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--config",
        default=None,
        help="配置文件路径；省略则用技能自带的 config/default.yaml（按脚本位置解析，与 cwd 无关）",
    )
    common.add_argument(
        "--files",
        action="append",
        nargs="+",
        default=None,
        metavar="PATH",
        help=(
            "显式文件清单（可重复传，支持一次给多个）：用户填写的文件地址、工具添加附件的本地地址。"
            "仅支持本地文件，http/https 远程地址会被拒绝。给清单后默认忽略 --root 目录"
            "（配置 input.merge_files_and_root 可改为合并）"
        ),
    )

    p1 = sub.add_parser("discover", parents=[common], help="发现并筛选输入文件")
    p1.add_argument("--root", default=None, help="输入根目录（覆盖配置）；给了 --files 时默认不扫描它")
    p1.add_argument("--out", default="manifest.json", help="manifest 输出路径，- 表示标准输出")
    p1.set_defaults(func=cmd_discover)

    p2 = sub.add_parser("extract", parents=[common], help="解析文件结构与正文")
    p2.add_argument("--root", default=None, help="输入根目录（覆盖配置）")
    p2.add_argument("--out", default="extract.json", help="解析结果输出路径，- 表示标准输出")
    p2.set_defaults(func=cmd_extract)

    p3 = sub.add_parser("validate", parents=[common], help="校验摘要覆盖度与详实度")
    p3.add_argument("--root", default=None, help="输入根目录（覆盖配置）")
    p3.add_argument("--manifest", default=None, help="discover 生成的 manifest.json")
    p3.add_argument("--summaries", default=None, help="AI 撰写的 summaries.json")
    p3.set_defaults(func=cmd_validate)

    p4 = sub.add_parser("assemble", parents=[common], help="组装最终汇总 Markdown")
    p4.add_argument("--root", default=None, help="输入根目录（覆盖配置）")
    p4.add_argument("--manifest", default=None, help="discover 生成的 manifest.json")
    p4.add_argument("--summaries", default=None, help="AI 撰写的 summaries.json")
    p4.add_argument("--out", default=None, help="最终文件完整路径；省略则输出到输出目录（默认桌面）")
    p4.add_argument("--mode", default=None, choices=["digest", "full", "overview", "merged"])
    p4.add_argument(
        "--out-dir",
        default=None,
        help="输出目录（覆盖配置，默认 ~/Desktop）；~ 或绝对路径按原样使用，相对路径相对输入根目录",
    )
    p4.set_defaults(func=cmd_assemble)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except collect.InputError as exc:
        _info(f"输入有误，已终止（{len(exc.items)} 项）：")
        for item in exc.items:
            _info(f"  - {item}")
        return 1
    except NotADirectoryError as exc:
        _info(f"输入有误，已终止：{exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
