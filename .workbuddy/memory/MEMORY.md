# MEMORY.md — MarkdownFileSummary-skill 长期约定

## 项目定位
对一批 Markdown 文件做**语义汇总**：AI 逐篇精读全文后提炼详细摘要，并做跨文件综述。
**不是**统计 + 拼接。用户对此有明确要求，任何改动都不得退回成拼接。

## 不可动摇的分工
- 脚本（`scripts/`）：发现、读取、解析、排版、校验。**不生成任何摘要文字**。
- AI：读全文、写摘要、写跨文件综述。
- 摘要字段缺失时，输出必须显式标注「待补充」，禁止用正文首段冒充摘要。

## 技术约束
- 仅用 Python 3.9+ 标准库，不引入第三方依赖（含 PyYAML，配置用自研 YAML 子集解析）。
- `SKILL.md` 是跨工具规范入口；`adapters/` 只做薄封装，不得复制业务逻辑。

## 路径约定（重要，勿回退）
- `$SKILL_DIR` = `SKILL.md` 所在目录（技能根目录）。技能会被安装到任意位置，**SKILL.md / README / adapters 里的命令一律写 `python3 "$SKILL_DIR/scripts/main.py"`，不得写相对路径**。
- `--config` 默认 `None`；省略时 `main.py` 按脚本位置解析技能自带的 `config/default.yaml`。不要再把默认值写成相对字符串。
- `--root` 与中间产物（`--out`）仍相对 cwd 解析，这是刻意设计（用户想汇总哪个目录就在哪执行）。
- 禁止在任何技能文件里硬编码本机绝对路径（如 `/Users/ccccc/...`）。

## CLI 契约
`discover` → `extract` →（AI 写 summaries.json）→ `validate` → `assemble`。
`validate` 失败返回 exit code 1，用于卡住质量不达标的产出。

## 输出位置（用户明确要求）
- 默认输出到**桌面 `~/Desktop`**；用户指定位置时以指定为准。
- 优先级：`--out`（完整文件路径）> `--out-dir`（目录）> `output.dir`。
- `output.dir` 解析：`~`/绝对路径按原样，相对路径相对 `input.root`。
- 交付时必须把完整输出路径回报给用户。

## 输入上限（用户明确要求，勿擅自放宽）
- 单文件 ≤ 30 MiB：`input.max_file_bytes`（默认 31457280）。
- 单次 ≤ 30 个文件：`input.max_files`（默认 30）。
- 超限不报错，跳过并记入 `manifest.json.skipped`，必须向用户说明被跳过的文件。

## 数据结构
- `summaries.json` = `global`{overview,key_findings,themes,conflicts,actions} + `files`{title,one_liner,summary,key_points,details,quotes,conclusions,tags,importance}
- 配置 `config/default.yaml`，当前 `version: 2`，`content.mode` 默认 `digest`。
