# AGENTS.md

## Markdown 文件汇总（AI 精读版）

当需要汇总 / 总结 / 对比一个目录下的多个 Markdown 文件时，使用本技能。
核心是 **AI 逐篇读全文后提炼**，不是统计拼接。

**路径约定**：`$SKILL_DIR` = 本技能根目录（即 `SKILL.md` 所在目录，与当前工作目录无关）。
所有命令用绝对路径调用；未传 `--config` 时自动使用技能自带的 `config/default.yaml`。

- 规范入口：`$SKILL_DIR/SKILL.md`
- 执行入口：`$SKILL_DIR/scripts/main.py`（子命令 `discover` / `extract` / `validate` / `assemble`）
- 撰写标准：`$SKILL_DIR/references/summarization-guide.md`（写摘要前必读）
- 配置：`$SKILL_DIR/config/default.yaml`
- 细则：`references/filter-rules.md`、`references/output-format.md`、`references/config-schema.md`

```bash
SKILL_DIR=/path/to/MarkdownFileSummary-skill   # 例如 ~/.workbuddy/skills/markdown-file-summary

# 输入二选一：扫目录 / 用显式清单（用户点名文件或拖入附件时用 --files；清单优先于目录，仅本地文件）
python3 "$SKILL_DIR/scripts/main.py" discover --root ./docs --out /tmp/md-summary/manifest.json
# python3 "$SKILL_DIR/scripts/main.py" discover --files a.md /data/b.md --out /tmp/md-summary/manifest.json
# 注意：后续各步要传同一套输入参数（--root 或 --files）

python3 "$SKILL_DIR/scripts/main.py" extract  --root ./docs --out /tmp/md-summary/extract.json
# AI 逐篇精读原文后撰写 summaries.json（结构见 references/output-format.md）
python3 "$SKILL_DIR/scripts/main.py" validate --root ./docs \
  --manifest /tmp/md-summary/manifest.json --summaries /tmp/md-summary/summaries.json
python3 "$SKILL_DIR/scripts/main.py" assemble --root ./docs \
  --manifest /tmp/md-summary/manifest.json --summaries /tmp/md-summary/summaries.json
# 默认输出到桌面 ~/Desktop；指定位置用 --out <完整路径> 或 --out-dir <目录>
```

铁律：必须读全文；禁止把原文段落搬进摘要充当内容；禁止编造原文没有的信息。
