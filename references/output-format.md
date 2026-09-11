# 输出格式与命名约定

## 1. 命名约定

默认文件名模板：`SUMMARY-{scope}-{timestamp}.md`

| 占位符 | 含义 | 默认 |
| --- | --- | --- |
| `{scope}` | 作用域标识 | `output.scope: auto` → 输入根目录名 slug 化 |
| `{timestamp}` | 生成时间 | `%Y%m%d-%H%M%S` |
| `{count}` | 纳入文件数 | 由脚本注入 |

- 输出目录：`output.dir`，**默认桌面 `~/Desktop`**。
- 输出位置优先级（高 → 低）：`--out`（完整文件路径）> `--out-dir`（目录）> `output.dir`。
- `output.dir` 取值规则：`~` 开头或绝对路径按原样使用；**相对路径相对 `input.root` 解析**（便于把产物留在项目内，如 `../reports`）。
- 重名策略 `output.on_exists`：`suffix`（默认，追加 `-2`）/ `overwrite` / `fail`。
- slug 规则：转小写，非 `[\w\u4e00-\u9fff.-]` 字符替换为 `-`，去首尾 `-.`。

示例：

```
（默认）      ~/Desktop/SUMMARY-my-docs-20260911-103608.md
--out-dir     /data/reports/SUMMARY-my-docs-20260911-103608.md
--out         ./out/final.md
```

## 2. 文档骨架

```markdown
---
title: <scope> 汇总
generated_at: <YYYY-MM-DD HH:MM:SS>
source_root: <绝对路径>
file_count: <N>
mode: digest | full | overview | merged
generator: markdown-file-summary
---

# <scope> 汇总

> 来源目录：`…` ｜ 文件数：N ｜ 生成时间：… ｜ 模式：…（摘要由 AI 精读生成）

## 一、全局综述          # mode ∈ {overview, digest, full}
## 二、主题脉络          # 有 themes 时出现
## 三、文件索引          # mode ∈ {digest, full}
## 四、分文件详细摘要    # mode ∈ {digest, full}
## 五、合并正文（附录）  # mode ∈ {full, merged}
```

各节由 `content.mode` 决定，序号自动编排；`digest` 为推荐默认值，
强调「AI 语义汇总」而非「拼接」。

## 3. 各节内容

### 全局综述（`content.global`）

- `overview`：跨文件的总体综述，可多段，**必填**。
- `include_findings`：关键发现列表。
- `include_conflicts`：分歧 / 待确认列表。
- `include_actions`：行动项 / 后续，渲染为 `- [ ]` 复选框。

### 主题脉络（`content.global.include_themes`）

跨文件聚类出的主题，每项含 `title` / `summary` / `points` / `sources`，
`title` 相同主题的文档被归并到一条，便于横向对照。

### 文件索引（`content.index`）

- `include_stats`：文件数、总行数、总体积。
- `include_index`：索引表 `| # | 文件 | 标题 | 重要度 | 行数 | 摘要 |`，文件名链到分文件锚点。

### 分文件详细摘要（`content.per_file`）

每篇一节，字段按开关渲染：

| 字段 | 说明 | 开关 |
| --- | --- | --- |
| `title` | 该文件的标题 | 用于节标题 |
| 元信息 | 路径 / 行数 / 体积 / 修改时间 / 重要度 | `include_metadata` |
| `tags` | 标签 | — |
| `one_liner` | 一句话概括 | `include_one_liner` |
| `summary` | 详细摘要（多段） | — |
| `key_points` | 核心要点 | `include_key_points` |
| `details` | 重要细节 / 数据 / 事实 | `include_details` |
| `quotes` | 原文关键引用 | `include_quotes` |
| `conclusions` | 结论 / 影响 | `include_conclusions` |
| 原文标题大纲 | 可折叠 | `include_original_headings` |
| 文档结构信息 | 脚本解析出的章节/代码块/表格/列表/链接等统计，可折叠 | `include_structure`（默认开） |
| 章节要点 | AI 为各章节写的要点，取自 `files.<rel>.sections` | `include_section_points`（默认关） |

超过 `max_summary_chars` 的摘要会截断；低于 `min_summary_chars` 会被 `validate` 标为过简。
**摘要字段为空时，脚本会显式输出「待补充」而不是用正文首段冒充摘要。**

#### 文档结构信息块

完全由脚本从解析结果生成，不含任何摘要文字；各项为 0 时省略对应行，全部为空时整块不出现。
渲染示例：

```
<details><summary>文档结构信息</summary>

- 章节：5 个（H1×1｜H2×3｜H3×1）
- 代码块：2 个（python×1｜无语言×1｜未闭合 0）
- 表格：1 个（3行×3列）
- 列表：4 个（有序 1｜无序 3｜最深 3 层｜任务 2/3）
- 引用块：2 处（最深 2 层）
- 图片 1 张｜链接 6 个｜行内代码 12 处｜脚注 定义 1 / 引用 2｜分隔线 1 条
- 篇幅：约 1234 字｜42 行

</details>
```

> 解析是**单层识别**：引用块内部的围栏 / 表格 / 列表不递归识别，整体计入引用块。

### 合并正文（`content.merged`）

- 按 `sort` 顺序拼接各文件正文，作为附录；
- `strip_frontmatter` 控制是否去掉原 frontmatter（解析阶段已剥离）；
- `separator` 为文件间分隔符，默认 `\n\n---\n\n`；
- `source_anchor` 为每段插入来源锚点与小标题。

## 4. summaries.json 结构

AI 精读后按此结构填写，`files` 的键为相对路径：

```json
{
  "global": {
    "overview": "跨文件综述（多段，必填）",
    "key_findings": ["跨文件结论"],
    "themes": [
      {"title": "主题", "summary": "主题说明", "points": ["要点"], "sources": ["a.md"]}
    ],
    "conflicts": ["分歧或待确认事项"],
    "actions": ["行动项"]
  },
  "files": {
    "path/to/a.md": {
      "title": "文档标题",
      "one_liner": "一句话概括",
      "summary": "详细摘要，多段",
      "key_points": ["核心要点"],
      "details": ["重要细节或数据"],
      "quotes": ["原文关键句"],
      "conclusions": ["结论或影响"],
      "tags": ["分类"],
      "importance": "high",
      "sections": [
        {"heading": "小节标题", "points": ["该节要点"]}
      ]
    }
  }
}
```

- `importance` 取值 `high` / `medium` / `low`，用于索引表排序参考。
- `sections` 为**可选**字段，用于 `include_section_points` 开启时渲染「章节要点」。
  用列表而非以标题为 key 的对象，避免同名标题互相覆盖。章节名建议对齐 `extract` 输出里
  `sections[].breadcrumb`，便于对照。**`validate` 不校验该字段**，缺失不报错、不阻塞。
- 未出现在 `files` 中的文件会被 `validate` 报为「缺少摘要」。
- 撰写要求见 [summarization-guide.md](summarization-guide.md)。
