# 边界案例与处理规范

> ⛔ **REASON 阶段硬门控**：本文件由 `01-probe-protocol.md` 的 REASON 阶段门控强制触发读取，
> 开始阅读项目文件前必须完成本文阅读，以提前识别边界场景（无 git 历史、monorepo 等）。

---

## §1 合法的"跳过"情况

### 无 git 历史的新仓库
- 现象：`$repo_path/.git` 存在但只有 1 次提交
- 处理：跳过 `git_detective.py`，`raw/git_stats.json` **不生成**
- PROFILE 仍然完成（只需 `ast_nodes.json` + `file_tree.txt` 非空即可通过检查）

### 非 git 仓库
- 现象：`$repo_path/.git` 不存在
- 处理：**立即停止** → 输出 `[!ERROR: NOT_A_GIT_REPO]`
- 不继续执行任何后续阶段

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

- 当前版本仅解析 **Python**（`.py` 文件）
- 非 Python 文件直接跳过，不报错
- 若 Python 文件数 < 3 → stderr 输出警告，仍继续，但分析质量可能偏低
- 不适合以 JavaScript/TypeScript/Java 为主语言的仓库（见 SKILL.md「不调用场景」）

---

## §5 特殊目录结构

### 无 README 的项目
- REASON 阶段直接跳至 `pyproject.toml` / `package.json`
- 假说日志中注明：「无 README，置信度降低，OBJECT 阶段需额外质疑入口点」

### 目录过深嵌套
- Python 文件超过 8 层嵌套：AST 解析正常工作，不受目录层级影响
- `file_tree.txt` 行数 > 500 时：REASON 阶段仅读取前 300 行感知结构

---

## §6 EMIT 幂等性保障

- 多次执行会触发覆盖确认，不会静默覆盖已有分析
- 写入路径：先写 `.nexus-map/.tmp/`，全部成功后整体移动 → 避免中途失败留半成品
- 中途中断（如 Agent 超时）：下次执行检测到 `.tmp/` 目录 → 清理后重新生成
