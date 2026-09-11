---
name: markdown-file-summary
display_name: 多文档汇总助手
display_name_en: Markdown File Summary
description_zh: >-
  读取指定目录下的多个 Markdown 文件，由 AI 逐篇精读全文后提炼要点，生成一份详细的汇总性Markdown 文件，包含全局综述、主题脉络、文件索引与分文件摘要。适用于汇总 Markdown、总结多个 md 文件、提炼多篇文档重点或生成文档综述等场景。（仅支持本地文件或者通过工具上传的附件文件，http/https 远程地址拒绝并终止）
description_en: >-
  Reads multiple Markdown files from a given directory, has the AI read each file in full to extract key points, and produces one detailed aggregated Markdown file containing a global overview, thematic threads, a file index and per-file summaries. Use it for aggregating Markdown, summarizing multiple md files, or extracting highlights across documents.
version: 2.2.0
description: 读取指定目录下的多个 Markdown 文件，由 AI 逐篇精读原文后提炼要点，生成一份详细的汇总/总结性 Markdown 文件。当用户提出「汇总 Markdown」「总结多个 md 文件」「把目录里的笔记/文档合并成摘要」「对比多篇文档、提炼重点」「生成 md 综述或报告」等需求时使用。产出包含全局综述、主题脉络、文件索引与分文件详细摘要，可配置输入范围、输出命名与详略程度。
license: MIT
metadata:
  version: 2.2.0
  entrypoints:
    - scripts/main.py
  requires:
    - python3 >= 3.9（仅标准库，无第三方依赖）
---

# Markdown 文件汇总

把「一个目录里的多个 Markdown 文件」逐篇读懂、提炼，输出**一份详细的新 Markdown 汇总文件**。

## 核心原则（必读）

本技能**不是统计 + 拼接**。分工是固定的：

- **脚本**：发现文件、读取全文、解析结构、排版输出。
- **AI（你）**：逐篇精读全文，理解内容，提炼要点，撰写摘要与跨文件综述。

三条铁律：

1. **必须读全文**再写摘要，不能只看标题或首段下结论；
2. **禁止把原文段落搬进摘要**充当内容，必须是重新组织的语言；
3. **禁止编造**原文没有的信息。

若某文件为空或无法读取，在摘要中说明，而不是留空。

## 何时使用

- 用户想汇总/总结/合并某个目录下的一批 `.md` 文件。
- 用户**点名了几篇具体文档**（填了多个文件地址、或拖入了多个附件），要求汇总成一篇。
- 用户想提炼多篇文档的重点、做横向对比或形成综述。
- 用户想把零散笔记整理成一份结构化、可独立阅读的报告。

不适用：单个文件的改写、翻译、格式转换（直接编辑该文件即可）；远程 URL 抓取（仅支持本地文件）。

## 路径约定（重要）

本技能会被安装到任意位置（例如用户级 `~/.workbuddy/skills/markdown-file-summary/`），
**所有脚本调用都必须使用技能的绝对路径，不要依赖当前工作目录**：

- 记 `$SKILL_DIR` = **本 `SKILL.md` 所在目录**（即技能根目录）。
- 入口固定为 `"$SKILL_DIR/scripts/main.py"`。
- 未指定 `--config` 时，脚本会读取**自带的** `config/default.yaml`（按脚本位置解析），因此**无需传 `--config`**；只有需要自定义配置时才显式传。
- `--root` 与中间产物路径（`--out manifest.json` 等）按**当前工作目录**解析——这是刻意的：用户想汇总哪个目录，就在哪里执行。中间产物建议写到临时目录，避免污染用户目录。

反面示例（会失败）：在用户目录下执行 `python3 scripts/main.py ...` —— `scripts/main.py` 不在那里。

## 工作流

五步。前两步是脚本的活，第三步是**你的核心工作**。

1. **发现（discover）**：确定汇总哪些文件。两种来源，**清单优先于目录**：

   ```bash
   # 目录来源：汇总整个目录（递归）
   python3 "$SKILL_DIR/scripts/main.py" discover --root <目录> --out <临时目录>/manifest.json

   # 清单来源：用户点名了具体文件、或拖入了附件（可重复传、支持逗号分隔）
   python3 "$SKILL_DIR/scripts/main.py" discover \
     --files <文件1> <文件2> --files "<文件3>,<文件4>" --out <临时目录>/manifest.json
   ```

   - 用户**同时**给了清单与目录时：默认**只用清单**（`input.merge_files_and_root: true` 可改为合并）。
   - **只支持本地文件**：`http://` / `https://`（含 OSS 地址）会被拒绝并终止；路径不存在同理。
   - 附件这类 root 外的文件，其**本地绝对路径**作为唯一标识写入 manifest，并在最终汇总里渲染成 `file://` 链接。
   - 受 `input.max_file_bytes`（默认 30 MiB）与 `input.max_files`（默认 30）限制，
     被跳过的文件在 `manifest.json.skipped` 中列明原因，需在交付时告知用户。

2. **读取与解析（extract）**：脚本输出每个文件的全文与结构化信息。
   ```bash
   python3 "$SKILL_DIR/scripts/main.py" extract --root <目录> --out <临时目录>/extract.json
   ```
   每个文件除 frontmatter / 标题 / 正文外，还带以下解析结果，**用来指导你怎么读**：

   | 字段 | 用途 |
   | --- | --- |
   | `sections` | 按标题切好的章节树，含 `line` / `end_line` / `subtree_end_line` / `parent` / `breadcrumb` / `chars`，**只存行号范围，不含正文** |
   | `tables` / `lists` / `code_blocks` / `blockquotes` | 表格（行列与对齐）、列表（层级与任务勾选）、代码块（语言与是否闭合）、引用块 |
   | `images` / `links` / `footnote_defs` / `link_ref_defs` | 图片、链接、脚注与引用式定义 |
   | `char_count` / `words` / `inline_code_count` / `indented_code_blocks` / `hr_count` | 篇幅与计数 |

   > **段落级信息只需按行号取正文**：`sections` 给的是范围，用所在工具的读文件能力按
   > `line`–`end_line` 读原文即可，不必让脚本把正文复制一遍。
   > 解析是**单层识别**：引用块内部的围栏 / 表格 / 列表不递归识别。

3. **逐篇精读并撰写（你）**：为每篇写详细摘要，再做跨文件综合，写入 `summaries.json`。
   字段定义见 `references/output-format.md`，撰写标准见 **`references/summarization-guide.md`**（必读）。
   硬性要求：
   - 每篇 `summary` 覆盖「主旨 → 结构脉络 → 关键论证 → 数据/结论」，不少于 `min_summary_chars`（默认 200 字）；
   - 每篇至少 3 条 `key_points`，写**判断**而非话题名；
   - `global.overview` 必须包含**至少两篇文档之间的对照关系**，不是各篇摘要的堆叠。
   - **推荐按 `sections` 逐节精读**再合成整篇摘要（见 summarization-guide 第 3 节）；
     想让输出带「章节要点」块，额外写 `sections: [{heading, points}]` 并开启对应开关。

4. **校验（validate）**：检查覆盖度与详实度，未通过就回到第 3 步补写。
   ```bash
   python3 "$SKILL_DIR/scripts/main.py" validate --root <目录> \
     --manifest <临时目录>/manifest.json --summaries <临时目录>/summaries.json
   ```

5. **组装并交付（assemble）**：排版为最终文件，把**完整输出路径**、覆盖文件数与主要内容构成回报给用户。
   ```bash
   python3 "$SKILL_DIR/scripts/main.py" assemble --root <目录> \
     --manifest <临时目录>/manifest.json --summaries <临时目录>/summaries.json
   ```
   默认输出到**桌面 `~/Desktop`**；用户指定了输出位置时以指定为准：
   - `--out /path/to/汇总.md` 指定完整文件路径（最高优先级）；
   - `--out-dir /path/to/dir` 指定目录；
   - 修改配置 `output.dir`（相对路径相对输入根目录）。

> 只有用户明确要求「纯合并、不要摘要」时，才把 `content.mode` 设为 `merged` 并跳过第 3 步；此时应说明该产物不含语义提炼。

## 内容组织形式（`content.mode`）

| 模式 | 输出内容 |
| --- | --- |
| `digest`（默认，推荐） | 全局综述 + 主题脉络 + 文件索引 + 分文件详细摘要 |
| `full` | 在 `digest` 基础上追加「合并正文（附录）」 |
| `overview` | 仅全局综述与主题脉络 |
| `merged` | 仅按序拼接原文，无语义摘要（不推荐） |

## 输出里包含什么

- **全局综述**：跨文件总体判断、关键发现、分歧/待确认、行动项。
- **主题脉络**：把不同文档中同一主题的内容聚在一起，标注来源。
- **文件索引**：文件、标题、重要度、行数与一句话摘要的对照表。
- **分文件详细摘要**：每篇含一句话、多段内容摘要、核心要点、重要细节/数据、原文关键引用、结论/影响。
- **文档结构信息**：脚本从解析结果自动生成的折叠块（章节分布、代码块语言、表格行列、列表层级与任务勾选、引用块、图片/链接/行内代码/脚注计数、篇幅），默认开启。
- **章节要点**：AI 写的分节要点，默认关闭（需 `include_section_points: true` 且 summaries 里有 `sections`）。
- **合并正文（附录）**：仅在 `full` 模式下出现。

## 关键约定

- **输入来源**：显式文件清单（`--files` / `input.files`，含用户填写的地址与附件本地地址）> 目录扫描（`input.root`）。清单存在时默认忽略目录；`input.merge_files_and_root: true` 可改为合并。**仅支持本地文件，http/https 远程地址拒绝并终止。**详见 `references/filter-rules.md`。
- **输入筛选**：默认递归匹配 `**/*.md`、`**/*.markdown`，排除 `node_modules/.git/dist/build/vendor/_summary` 等，忽略小于 `min_bytes` 的空文件。详见 `references/filter-rules.md`。
- **输入上限**（均可配置）：
  - `input.max_file_bytes`：**单个文件不得超过 30 MiB**（默认 31457280 字节），超限跳过，不读取内容；
  - `input.max_files`：**单次最多处理 30 个文件**（默认 30），超出部分按 `sort` 顺序截断。
  - 被跳过的文件记入 `manifest.json.skipped`（`reason`: `too_large` / `over_max_files` / `too_small`），命令行会打印汇总。**跳过的文件不会进入摘要，需向用户说明。**
- **输出位置**：默认写入**桌面 `~/Desktop`**；用户指定则以指定为准，优先级 `--out` > `--out-dir` > `output.dir`。`output.dir` 为 `~`/绝对路径时按原样使用，相对路径相对输入根目录。详见 `references/output-format.md`。
- **输出命名**：默认 `SUMMARY-{scope}-{timestamp}.md`，`scope` 取输入根目录名；重名追加序号。详见 `references/output-format.md`。
- **配置**：集中在 `$SKILL_DIR/config/default.yaml`，字段见 `references/config-schema.md`；不传 `--config` 即使用它（按脚本位置解析，与 cwd 无关），命令行参数优先级高于配置。
- **详略控制**：`per_file.max_summary_chars`（上限）与 `min_summary_chars`（下限，`validate` 依据）。
- **结构信息开关**：`per_file.include_structure`（默认 **开**，脚本自动生成的「文档结构信息」块）与 `include_section_points`（默认 **关**，需 AI 写 `sections` 的「章节要点」块）。解析为**单层识别**，引用块内部结构不递归。
- **可移植性**：`SKILL.md` 是规范入口；`scripts/` 仅用 Python 标准库；调用时用 `$SKILL_DIR` 绝对路径，不依赖 cwd；`adapters/` 提供 Cursor / Codex 等薄封装。

## 目录结构

```
MarkdownFileSummary-skill/
├── SKILL.md                 # 规范入口（本文件）
├── README.md                # 人类可读说明
├── config/default.yaml      # 默认配置：筛选规则 / 输出命名 / 内容组织
├── scripts/
│   ├── main.py              # CLI 编排：discover / extract / validate / assemble
│   ├── config.py            # 配置加载（零依赖，兼容 YAML 子集与 JSON）
│   ├── collect.py           # 输入发现与筛选
│   ├── parse.py             # Markdown 结构解析
│   └── build.py             # 汇总文件组装 + 摘要校验
├── references/              # 规范细则（供模型按需读取）
│   ├── summarization-guide.md  # 摘要撰写标准（必读）
│   ├── filter-rules.md
│   ├── output-format.md
│   └── config-schema.md
├── assets/templates/        # 输出模板
│   ├── summary.md
│   └── index.md
├── examples/                # 输入 / 摘要 / 输出样例
│   ├── input/
│   ├── output/
│   └── summaries.example.json
└── adapters/                # 跨工具适配层
```

## 参考

- 摘要撰写标准：`references/summarization-guide.md`（撰写前必读）
- 输入筛选规则：`references/filter-rules.md`
- 输出格式与命名：`references/output-format.md`
- 配置字段：`references/config-schema.md`
- 完整示例：`examples/summaries.example.json` + `examples/output/SUMMARY-example.md`
