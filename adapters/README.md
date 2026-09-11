# 跨工具适配层

`SKILL.md` 是本技能的规范入口，绝大多数支持 Agent Skills 的工具可直接识别。
`adapters/` 只放**薄封装**，把工具特定的入口指向同一套 `SKILL.md` 与 `scripts/`，
不改动任何逻辑。

## 已提供的适配

| 工具 | 适配文件 | 用法 |
| --- | --- | --- |
| Claude / 支持 SKILL.md 的工具 | 无需适配 | 直接识别 `SKILL.md` |
| Cursor | `cursor/.cursor/rules/md-summary.mdc` | 复制到项目 `.cursor/rules/` |
| OpenAI Codex / 读取 AGENTS.md 的工具 | `codex/AGENTS.md` | 复制到项目根目录 |

## 新增一个工具的适配

1. 新建 `adapters/<tool>/` 目录；
2. 放入该工具的入口文件，内容只需说明三件事：
   - 何时触发（读取一批 Markdown 生成汇总）；
   - 路径约定：`$SKILL_DIR` = 技能根目录，命令一律用绝对路径，不依赖 cwd；
   - 执行入口（`python3 "$SKILL_DIR/scripts/main.py" discover|extract|validate|assemble`）；
3. 在 `SKILL.md` 的触发描述里补充该工具的关键词，避免适配层与主逻辑漂移。

## 约束

- 适配层不得复制业务逻辑，只做「触发条件 + 指向入口」。
- 适配层不得硬编码技能安装路径，一律用 `$SKILL_DIR` 占位。
- 所有适配共用技能自带的 `config/default.yaml`（不需传 `--config`），如需差异用配置覆盖，而非改写脚本。
