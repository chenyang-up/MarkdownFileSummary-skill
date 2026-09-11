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

<!-- mode ∈ {full, merged} -->
## 五、合并正文（附录）

<a id="body-{{FILE_ANCHOR}}"></a>

#### 来源：`{{FILE_PATH}}`

{{FILE_BODY}}
