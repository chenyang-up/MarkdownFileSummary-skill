# MarkdownFileSummary-skill

读取指定目录下的多个 Markdown 文件，由 AI **逐篇精读原文**后提炼要点，生成一份**详细的汇总 / 总结性 Markdown 文件**。
不是统计拼接：摘要与跨文件综述全部来自对内容的语义理解。零第三方依赖，可在多种 coding 工具（Claude、Cursor、Codex 等）中复用。

## 特性

- **AI 逐篇精读**：脚本负责发现、读取、解析、排版；AI 负责理解与提炼，职责清晰。
- **详细的分篇摘要**：每篇含一句话、多段内容摘要、核心要点、重要细节/数据、原文关键引用、结论/影响。
- **跨文件综合**：全局综述 + 主题脉络 + 分歧/待确认 + 行动项，而非各篇摘要的堆叠。
- **质量校验**：`validate` 检查覆盖度与详实度，摘要过简会明确指出。
- **输入筛选**：glob 规则控制范围，自动跳过依赖/构建/缓存目录与空文件。
- **输入上限**：单文件默认不超过 **30 MiB**（`input.max_file_bytes`），单次最多 **30 个文件**（`input.max_files`）；超限文件跳过并记入 `manifest.json.skipped`，命令行会提示。
- **输出位置**：默认写入**桌面 `~/Desktop`**；可用 `--out`（完整路径）或 `--out-dir`（目录）指定，用户指定优先。
- **跨工具**：`SKILL.md` 为规范入口，`scripts/` 仅用 Python 标准库。

## 目录结构

```
MarkdownFileSummary-skill/
├── SKILL.md                 # 规范入口（跨工具识别的技能定义）
├── README.md                # 本文件
├── config/default.yaml      # 默认配置：筛选规则 / 输出命名 / 内容组织
├── scripts/
│   ├── main.py              # CLI 编排：discover / extract / validate / assemble
│   ├── config.py            # 配置加载（零依赖）
│   ├── collect.py           # 输入发现与筛选
│   ├── parse.py             # Markdown 结构解析
│   └── build.py             # 汇总文件组装 + 摘要校验
├── references/              # 规范细则
│   ├── summarization-guide.md  # 摘要撰写标准（必读）
│   ├── filter-rules.md      # 输入筛选规则
│   ├── output-format.md     # 输出格式与命名约定
│   └── config-schema.md     # 配置字段说明
├── assets/templates/        # 输出模板
│   ├── summary.md
│   └── index.md
├── examples/                # 输入 / 摘要 / 输出样例
│   ├── input/
│   ├── output/
│   └── summaries.example.json
└── adapters/                # 跨工具适配（Cursor / Codex）
```

## 安装到 WorkBuddy（用户级测试）

```bash
# 方式一：软链（改代码即时生效，适合调试）
ln -s /path/to/MarkdownFileSummary-skill ~/.workbuddy/skills/markdown-file-summary

# 方式二：复制（每次改完需重新复制）
cp -R /path/to/MarkdownFileSummary-skill ~/.workbuddy/skills/markdown-file-summary
```

安装后重载 WorkBuddy，技能即可被识别。目录名建议与 `SKILL.md` 的 `name: markdown-file-summary` 保持一致。

## 快速开始

下面用 `$SKILL_DIR` 表示**本技能根目录**（即 `SKILL.md` 所在目录）。所有命令都用绝对路径调用，
**与当前工作目录无关**；未传 `--config` 时自动使用技能自带的 `config/default.yaml`。

```bash
SKILL_DIR=/path/to/MarkdownFileSummary-skill   # 例如 ~/.workbuddy/skills/markdown-file-summary

# 1. 发现待汇总的 Markdown 文件
python3 "$SKILL_DIR/scripts/main.py" discover --root ./docs --out /tmp/md-summary/manifest.json

# 2. 读取全文与结构（供 AI 精读）
python3 "$SKILL_DIR/scripts/main.py" extract --root ./docs --out /tmp/md-summary/extract.json

# 3. AI 逐篇精读原文，按 references/summarization-guide.md 撰写 summaries.json
#    结构参考 examples/summaries.example.json

# 4. 校验摘要覆盖度与详实度
python3 "$SKILL_DIR/scripts/main.py" validate --root ./docs \
  --manifest /tmp/md-summary/manifest.json --summaries /tmp/md-summary/summaries.json

# 5. 组装最终汇总文件（默认输出到桌面 ~/Desktop）
python3 "$SKILL_DIR/scripts/main.py" assemble --root ./docs \
  --manifest /tmp/md-summary/manifest.json --summaries /tmp/md-summary/summaries.json
```

指定输出位置时，用 `--out` 或 `--out-dir` 覆盖默认值：

```bash
# 指定完整文件路径
python3 "$SKILL_DIR/scripts/main.py" assemble ... --out /data/reports/final.md
# 指定目录（相对路径相对输入根目录）
python3 "$SKILL_DIR/scripts/main.py" assemble ... --out-dir ../reports
```

仅需机械合并、不要语义摘要时，把 `content.mode` 设为 `merged` 并跳过第 3、4 步。

## 输出内容

`content.mode: digest`（默认）产出四节：

1. **全局综述**：总体判断、关键发现、分歧/待确认、行动项；
2. **主题脉络**：跨文件聚类同一主题，标注来源；
3. **文件索引**：文件 / 标题 / 重要度 / 行数 / 一句话摘要对照表；
4. **分文件详细摘要**：每篇的详细提炼，含核心要点、重要细节、原文引用与结论。

`mode: full` 会追加「合并正文（附录）」。

## 配置

所有可调项集中在 `$SKILL_DIR/config/default.yaml`，字段含义见
[`references/config-schema.md`](references/config-schema.md)。

- 不传 `--config` 即使用该文件（默认值按脚本位置解析为绝对路径，与 cwd 无关）。
- 需要自定义时用 `--config /path/to/my.yaml` 指定。
- 命令行参数（`--root` / `--mode` / `--out-dir` / `--out`）优先级高于配置文件。

## 文档

- 摘要撰写标准：[`references/summarization-guide.md`](references/summarization-guide.md)
- 输入筛选规则：[`references/filter-rules.md`](references/filter-rules.md)
- 输出格式与命名：[`references/output-format.md`](references/output-format.md)
- 跨工具适配：[`adapters/README.md`](adapters/README.md)

## 许可证

MIT
