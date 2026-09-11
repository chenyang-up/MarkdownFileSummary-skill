# 输入筛选规则

脚本在 `input.root` 下递归遍历，满足以下全部条件才会纳入汇总。

## 1. 扩展名 / 路径范围

- 由 `input.include` 控制，默认 `["**/*.md", "**/*.markdown"]`。
- glob 采用 posix 风格：
  - `**` 匹配任意层级目录（含零层）；
  - `*` 只匹配单层内的任意字符；
  - `?` 匹配单个字符。
- 示例：只汇总 `docs/` 且不含草稿：

```yaml
input:
  root: "."
  include: ["docs/**/*.md"]
  exclude: ["docs/**/draft-*.md"]
```

## 2. 排除规则

`input.exclude` 命中即跳过，默认排除依赖、构建、缓存与历史输出目录：

```
**/node_modules/**   **/.git/**      **/.workbuddy/**   **/.idea/**
**/dist/**           **/build/**     **/vendor/**
**/_summary/**       **/SUMMARY-*.md  **/*.tmp.md
```

> 默认排除 `SUMMARY-*.md`，避免把上一次生成的汇总再汇总一遍。

## 3. 文件级约束

| 字段 | 默认 | 说明 |
| --- | --- | --- |
| `min_bytes` | 32 | 小于该字节数视为空文件，跳过 |
| `max_file_bytes` | 31457280（30 MiB） | **单文件体积上限**，超过则跳过；`0` 表示不限制 |
| `max_files` | 30 | **单次处理文件数量上限**，超出部分按排序截断；`0` 表示不限制 |
| `follow_symlinks` | false | 是否跟随符号链接（软链文件默认跳过） |
| `sort` | `path_asc` | 排序：`path_asc` / `mtime_desc` / `size_desc` |

### 体积上限的判定顺序

先 `stat()` 取体积，命中 `min_bytes` / `max_file_bytes` 任一条即跳过，**不读取文件内容**，
避免为超限大文件付出 IO 代价。被跳过的文件会记入 `manifest.json` 的 `skipped` 字段，
并在命令行输出一行汇总。

### 数量上限的截断时机

`max_files` 的截断发生在**排序之后**（见第 4 节），因此保留的是排序靠前的文件，
结果是确定的、可复现的。被截断的文件同样记入 `skipped`，`reason` 为 `over_max_files`。

### 跳过原因

| reason | 含义 |
| --- | --- |
| `too_small` | 小于 `min_bytes` |
| `too_large` | 超过 `max_file_bytes` |
| `over_max_files` | 排序后超过 `max_files` |

## 4. 边界与排序

- 路径一律以 `input.root` 为基准取**相对路径**（posix 形式）作为唯一键。
- 排序稳定；`max_files` 截断发生在排序之后（见第 3 节）。
- 隐藏目录不特殊处理，如需排除请显式写入 `exclude`。

## 5. 冲突处理

- 同一文件被 include 多次命中只计一次。
- 若某文件既被 include 命中又被 exclude 命中，**exclude 优先**。

## 6. 限制类配置示例

```yaml
input:
  root: "./docs"
  min_bytes: 32
  max_file_bytes: 10485760   # 单文件不超过 10 MiB
  max_files: 30              # 最多 30 篇
  sort: size_desc            # 先处理大文件，超量时优先保留大文件
```

