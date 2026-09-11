---
title: {{TITLE}}
generated_at: {{GENERATED_AT}}
source_root: {{SOURCE_ROOT}}
file_count: {{FILE_COUNT}}
mode: {{MODE}}
generator: markdown-file-summary
---

# {{TITLE}}

> 来源目录：`{{SOURCE_ROOT}}` ｜ 文件数：{{FILE_COUNT}} ｜ 生成时间：{{GENERATED_AT}} ｜ 模式：{{MODE}}（摘要由 AI 精读生成）

<!-- mode ∈ {overview, digest, full} -->
## 一、全局综述

{{GLOBAL_OVERVIEW}}

### 关键发现

- {{KEY_FINDING}}

### 分歧 / 待确认

- {{CONFLICT}}

### 行动项 / 后续

- [ ] {{ACTION}}

<!-- 有 themes 时出现 -->
## 二、主题脉络

#### 1. {{THEME_TITLE}}

{{THEME_SUMMARY}}

- {{THEME_POINT}}

- 来源：`{{THEME_SOURCE}}`

<!-- mode ∈ {digest, full} -->
## 三、文件索引

- 纳入文件：**{{FILE_COUNT}}** 个
- 总行数：**{{TOTAL_LINES}}** 行
- 总体积：**{{TOTAL_SIZE}}**

{{INDEX_TABLE}}

<!-- mode ∈ {digest, full} -->
## 四、分文件详细摘要

<a id="{{FILE_ANCHOR}}"></a>

#### {{INDEX}}. {{FILE_TITLE}}

- 路径：`{{FILE_PATH}}` ｜ {{FILE_LINES}} 行 ｜ {{FILE_SIZE}} ｜ 修改于 {{FILE_MTIME}} ｜ 重要度：{{IMPORTANCE}}
- 标签：{{TAGS}}

**一句话**：{{ONE_LINER}}

**内容摘要**：

{{SUMMARY}}

**核心要点**：

- {{KEY_POINT}}

**重要细节 / 数据**：

- {{DETAIL}}

**原文关键引用**：

> {{QUOTE}}

**结论 / 影响**：

- {{CONCLUSION}}

<details><summary>原文标题大纲</summary>

{{OUTLINE}}

</details>

<!-- per_file.include_structure：默认开，由脚本从解析结果生成，各项为 0 则省略该行 -->
<details><summary>文档结构信息</summary>

- 章节：{{SECTION_COUNT}}（{{HEADING_LEVEL_BREAKDOWN}}）
- 代码块：{{CODE_BLOCK_COUNT}}（{{CODE_LANGS}}｜未闭合 {{CODE_UNCLOSED}}）
- 表格：{{TABLE_COUNT}}（{{TABLE_DIMS}}）
- 列表：{{LIST_COUNT}}（有序 {{LIST_ORDERED}}｜无序 {{LIST_UNORDERED}}｜最深 {{LIST_MAX_DEPTH}} 层｜任务 {{TASK_DONE}}/{{TASK_TOTAL}}）
- 引用块：{{QUOTE_COUNT}} 处（最深 {{QUOTE_MAX_DEPTH}} 层）
- 图片 {{IMAGE_COUNT}} 张｜链接 {{LINK_COUNT}} 个｜行内代码 {{INLINE_CODE_COUNT}} 处｜脚注 定义 {{FOOTNOTE_DEFS}} / 引用 {{FOOTNOTE_REFS}}｜分隔线 {{HR_COUNT}} 条
- 篇幅：约 {{WORDS}} 字｜{{FILE_LINES}} 行

</details>

<!-- per_file.include_section_points：默认关；开启需 summaries 里写了 sections -->
**章节要点**：

- **{{SECTION_HEADING}}**
  - {{SECTION_POINT}}

<!-- mode ∈ {full, merged} -->
## 五、合并正文（附录）

<a id="body-{{FILE_ANCHOR}}"></a>

#### 来源：`{{FILE_PATH}}`

{{FILE_BODY}}
