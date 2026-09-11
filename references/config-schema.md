# 配置字段说明（config/default.yaml）

配置为 YAML（也兼容 JSON）。缺失字段自动用内置默认值补齐；命令行参数
（`--root` / `--mode` / `--out-dir` / `--out`）优先级高于配置文件。

## 配置文件位置

- 不传 `--config` 时，读取技能自带的 `config/default.yaml`。该默认值按
  **脚本所在位置**解析为绝对路径，因此从任意工作目录调用都能命中，不依赖 cwd。
- 需要自定义时显式传 `--config /path/to/my.yaml`。
- `config.default.yaml` 里的**相对路径**（`input.root`、`output.dir`）仍按原有规则解析：
  `input.root` 相对 cwd，`output.dir` 相对 `input.root`。

## input

| 字段 | 类型 | 默认 | 说明 |
| --- | --- | --- | --- |
| `root` | str | `.` | 输入根目录，相对路径基于执行命令时的工作目录；**给了 `files` 时默认不扫描它** |
| `files` | list[str] | `[]` | 显式文件清单：填写的文件地址 + 附件本地地址。仅本地文件，远程地址报错。非空时优先于 `root` |
| `merge_files_and_root` | bool | false | `files` 与 `root` 同时存在时：false 只用清单，true 合并（按绝对路径去重） |
| `include` | list[str] | `["**/*.md","**/*.markdown"]` | 纳入的 glob（显式清单也走这个校验） |
| `exclude` | list[str] | 见默认文件 | 排除的 glob，优先级高于 include |
| `min_bytes` | int | 32 | 最小字节数，过滤空文件 |
| `max_file_bytes` | int | 31457280（30 MiB） | 单文件体积上限，超过则跳过；`0` 为不限 |
| `max_files` | int | 30 | 处理数量上限，超出按排序截断；`0` 为不限 |
| `follow_symlinks` | bool | false | 是否跟随符号链接 |
| `sort` | enum | `path_asc` | `path_asc` / `mtime_desc` / `size_desc` |

> 超过限制的文件不会报错中断，而是记入 `manifest.json` 的 `skipped` 并在命令行提示。
> 判定细节见 [filter-rules.md](filter-rules.md)。

## output

| 字段 | 类型 | 默认 | 说明 |
| --- | --- | --- | --- |
| `dir` | str | `~/Desktop` | 输出目录。`~` 或绝对路径按原样；相对路径相对 `input.root` |
| `name_template` | str | `SUMMARY-{scope}-{timestamp}.md` | 支持 `{scope}` `{timestamp}` `{count}` |
| `scope` | str | `auto` | `auto` 取输入根目录名，否则为固定值 |
| `timestamp_format` | str | `%Y%m%d-%H%M%S` | 时间格式 |
| `on_exists` | enum | `suffix` | `suffix` / `overwrite` / `fail` |
| `frontmatter` | bool | true | 是否输出 YAML frontmatter |
| `title` | str | `auto` | `auto` 为「{scope} 汇总」 |

> 输出位置优先级：`--out` > `--out-dir` > `output.dir`（默认桌面）。用户指定位置时以指定为准。

## content

| 字段 | 类型 | 默认 | 说明 |
| --- | --- | --- | --- |
| `mode` | enum | `digest` | `digest` 语义汇总（推荐）/ `full` 加附录 / `overview` 仅综述 / `merged` 纯拼接 |
| `global.include_themes` | bool | true | 输出主题脉络 |
| `global.include_findings` | bool | true | 输出关键发现 |
| `global.include_conflicts` | bool | true | 输出分歧 / 待确认 |
| `global.include_actions` | bool | true | 输出行动项 |
| `index.include_stats` | bool | true | 输出统计 |
| `index.include_index` | bool | true | 输出索引表 |
| `per_file.include_metadata` | bool | true | 输出文件元信息与重要度 |
| `per_file.include_one_liner` | bool | true | 输出一句话概括 |
| `per_file.include_key_points` | bool | true | 输出核心要点 |
| `per_file.include_details` | bool | true | 输出重要细节 / 数据 |
| `per_file.include_quotes` | bool | true | 输出原文关键引用 |
| `per_file.include_conclusions` | bool | true | 输出结论 / 影响 |
| `per_file.include_original_headings` | bool | true | 输出原文标题大纲 |
| `per_file.include_structure` | bool | true | 输出「文档结构信息」块（章节/代码块/表格/列表等，脚本自动生成） |
| `per_file.include_section_points` | bool | false | 输出「章节要点」块（需 AI 在 summaries 里写 `sections`） |
| `per_file.max_summary_chars` | int | 2000 | 单篇摘要渲染软上限 |
| `per_file.min_summary_chars` | int | 200 | 质量下限，低于此值被 `validate` 标为过简 |
| `merged.strip_frontmatter` | bool | true | 合并正文去掉原 frontmatter |
| `merged.separator` | str | `\n\n---\n\n` | 文件间分隔符 |
| `merged.source_anchor` | bool | true | 每段插入来源锚点 |

摘要字段的撰写要求见 [summarization-guide.md](summarization-guide.md)。

## 自定义配置示例

```yaml
input:
  root: "./docs"
  include: ["**/*.md"]
  exclude: ["**/archive/**"]
  sort: mtime_desc
output:
  dir: "../reports"
  name_template: "文档汇总-{timestamp}.md"
  scope: "产品文档"
content:
  mode: digest
  per_file:
    max_summary_chars: 1200
    min_summary_chars: 300
  merged:
    separator: "\n\n---\n\n"
```

用法：

```bash
python3 "$SKILL_DIR/scripts/main.py" discover --config ./my.yaml --root ./docs --out /tmp/manifest.json
```
