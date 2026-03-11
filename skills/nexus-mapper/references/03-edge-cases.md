# 边界案例与处理规范

> **REASON 阶段硬门控**：本文件由 `01-probe-protocol.md` 的 REASON 阶段门控强制触发读取，
> 开始阅读项目文件前必须完成本文阅读，以提前识别边界场景。

---

## §1 合法的"跳过"情况

### 无 git 历史的新仓库
- 现象：`$repo_path/.git` 存在但只有 1 次提交
- 处理：跳过 `git_detective.py`，在执行日志或最终输出中写明 `git analysis skipped: insufficient history`
- PROFILE 仍然完成（只需 `ast_nodes.json` + `file_tree.txt` 非空即可通过检查）

### 非 git 仓库
- 现象：`$repo_path/.git` 不存在
- 处理：跳过 `git_detective.py`，继续执行后续阶段
- 在最终输出中明确标注：`hotspots skipped because repository has no git metadata`

---

## §2 大型 Monorepo

- 文件数 > 1000 时：
  - 告知用户建议使用 `--max-nodes 200 --max-depth 3`
  - 命令：`python extract_ast.py $repo_path --max-nodes 200`
  - `stats.truncated=true` 是预期行为，不是错误

- Git 历史过长（> 3000 commits）时：
  - 使用 `--days 30` 缩短分析窗口代替默认 90 天
  - 命令：`python git_detective.py $repo_path --days 30`

---

## §3 截断行为（truncation）

当 `stats.truncated=true` 时：
- `extract_ast.py` **优先保留 Module 和 Class 节点**
- Function 节点被直接丢弃，`stats.truncated_nodes` 记录丢弃数量
- EMIT 阶段仍可基于 Module/Class 节点产出完整的 `concept_model.json`

> [!DEVIATION]
> **已知实现偏差**：截断的 Function 节点被**直接丢弃**，**不会生成** `raw/functions.json`。
> 如任何文档描述截断节点写入单独文件，均以本实际行为为准。

---

## §4 多语言混合 repo

- `extract_ast.py` 按文件扩展名自动 dispatch，支持 30+ 语言
- **未知扩展名**：静默跳过，不报错；`stats.languages` 仅记录实际解析到节点的语言
- 若所有已知语言文件数 < 3 → stderr 输出警告，仍继续，但分析质量可能偏低
- `ast_nodes.json` 每个 Module 节点含 `"lang"` 字段，方便后续按语言过滤

> [!NOTE]
> **不支持的语言** 在 `ast_nodes.json` 中表现为 `nodes: []`（空列表）。这是正常降级行为，
> PROFILE 完成检查只要求 `ast_nodes.json` 文件非空，空节点列表视为合法。

### 已知但未接入 AST 的语言

- 现象：仓库中存在当前脚本不会解析的文件类型
- 处理：继续执行，不中止；但必须在 `ast_nodes.json.stats.known_unsupported_file_counts` 中显式暴露
- EMIT 要求：
  - `INDEX.md` 标注本次语言覆盖降级
  - `dependencies.md` 中相关区域加 `inferred` 或 `manual inspection` 说明
  - `concept_model.json` 中受影响节点优先使用 `implementation_status=inferred`

### grammar 可加载但只有 Module 级覆盖的语言

- 现象：文件进入 `ast_nodes.json`，但 `stats.module_only_file_counts` 记录了该语言
- 处理：继续执行，不中止
- EMIT 要求：
  - 不得把这部分语言描述为"完整 AST 结构覆盖"
  - `systems.md` 和 `dependencies.md` 里涉及该语言的细粒度结构结论要保守表述
  - 允许产出 Module 级边界，但类/函数级结论需补充 provenance 说明

### 通过 CLI 或显式配置补充了语言，但当前环境没有可用 parser

- 现象：agent 通过 `--add-extension` / `--language-config` 补充了语言映射，但 `configured_but_unavailable_file_counts` 非空
- 处理：继续执行，不中止；但必须把这部分视为**未覆盖**，而不是 `module-only`
- EMIT 要求：
  - `INDEX.md` 和 `systems.md` 说明本次确实尝试补充语言支持，但对应 parser 不可用
  - `dependencies.md` 中涉及该语言的结论只能写成 `manual inspection` 或 `inferred`

### 通过 CLI 或显式配置补充了语言 query

- 现象：agent 通过 `--add-query` 或 `--language-config` 补充了 query，且 `languages_with_custom_queries` 非空
- 处理：继续执行，不中止；这属于正式能力，不应当被视为"实验性旁路"
- EMIT 要求：
  - 对自定义 query 覆盖的语言保持与内建语言同等标准
  - 若 query 能提取类/函数，就按 `structural coverage` 对待
  - 若 query 为空或只补了扩展名映射，就按 `module-only` 或 `configured-but-unavailable` 诚实落地

---

## §5 特殊目录结构

### 无 README 的项目
- REASON 阶段直接跳至 `pyproject.toml` / `package.json`
- 假说日志中注明：「无 README，evidence gap 在项目入口说明，OBJECT 阶段需额外质疑入口点」

### 目录过深嵌套
- Python 文件超过 8 层嵌套：AST 解析正常工作，不受目录层级影响
- `file_tree.txt` 行数 > 500 时：REASON 阶段仅读取前 300 行感知结构

### 带有路线图 / Sprint 状态的仓库
- 现象：README、ROADMAP、TASKS 等文档包含时间敏感状态（`Sprint 1/2/3`、`in progress` 等）
- 处理：允许摘要，但必须附 `verified_at` 和源文档路径
- 禁止：把无日期的进度状态写成当前事实

---

## §6 EMIT 幂等性保障

- 多次执行会触发覆盖确认，不会静默覆盖已有分析
- 写入路径：先写 `.nexus-map/.tmp/`，全部成功后整体移动 → 避免中途失败留半成品
- 中途中断（如 Agent 超时）：下次执行检测到 `.tmp/` 目录 → 清理后重新生成
