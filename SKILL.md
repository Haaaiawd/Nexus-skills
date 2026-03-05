---
name: nexus-mapper
description: 当用户要求「分析项目」「生成项目地图」「建立项目知识库」或指定本地 repo 路径并希望 AI 理解其结构时触发。对 Git 仓库执行 SKIP 五阶段探测，产出 .nexus-map/ 知识库供后续 AI 会话冷启动。不适用于：无 shell 执行能力的纯 API 环境、非 Python 主力的仓库、只查询单个文件/函数的场景。
---

# nexus-mapper — AI 项目探测协议

> "你不是在写代码文档。你是在为下一个接手的 AI 建立思维基础。"

本 Skill 指导 AI Agent 使用 **SKIP 五阶段协议**，对任意本地 Git 仓库执行系统性探测，产出 `.nexus-map/` 分层知识库。

---

## ⚠️ CRITICAL — 五阶段不可跳过

> [!IMPORTANT]
> **五阶段必须严格按序执行。任何阶段缺失 → 视为不完整执行，`INDEX.md` 禁止生成。**

❌ **禁止行为**：
- 跳过 CHALLENGE 直接写输出资产
- 在 EVIDENCE 完成前生成 `concept_model.json`
- SCAN 阶段脚本失败后继续执行后续阶段

✅ **必须做到**：
- 每个阶段完成后显式确认「✅ 阶段名 完成」再进入下一阶段
- CHALLENGE 必须提出 ≥3 个有代码引证的质疑点
- 所有节点 `code_path` 必须在仓库中真实存在（亲手验证，见守则2）

---

## 📌 何时调用 / 何时不调用

| 场景 | 调用 |
|------|:----:|
| 用户提供本地 repo 路径，希望 AI 理解其架构 | ✅ |
| 需要生成 `.nexus-map/INDEX.md` 供后续 AI 会话冷启动 | ✅ |
| 用户说「帮我分析项目」「建立项目知识库」「让 AI 了解这个仓库」 | ✅ |
| 运行环境无 shell 执行能力（纯 API 调用模式，无 `run_command` 工具） | ❌ |
| 宿主机无本地 Python 3.10+ | ❌ |
| 目标仓库主语言不是 Python（当前版本限制） | ❌ |
| 用户只想查询某个特定文件/函数 → 直接用 `view_file` / `grep_search` | ❌ |

---

## ⚠️ 前提检查（缺一 → 立即停止，告知用户具体缺失项）

| 前提 | 检查方式 |
|------|---------|
| 本地 Git 仓库 | `$repo_path/.git` 目录存在 |
| Python 3.10+ | `python --version` >= 3.10 |
| 脚本依赖已安装 | `python -c "import tree_sitter"` 无报错 |
| 有 shell 执行能力 | Agent 环境支持 `run_command` 工具调用 |

---

## 📥 输入契约

```
repo_path: 目标仓库的本地绝对路径（必填）
```

**当前限制**：仅支持 Python 语言代码库（`.py` 文件为主）。

---

## 📤 输出格式

执行完成后，目标仓库根目录下将产出：

```text
.nexus-map/
├── INDEX.md                    ← AI 冷启动主入口（< 2000 tokens）
├── arch/
│   ├── systems.md              ← 系统边界 + 代码位置
│   └── dependencies.md         ← Mermaid 依赖图 + 时序图
├── concepts/
│   ├── concept_model.json      ← Schema V1 机器可读图谱
│   └── domains.md              ← 核心领域概念说明
├── hotspots/
│   └── git_forensics.md        ← Git 热点 + 耦合对分析
└── raw/
    ├── ast_nodes.json          ← Tree-sitter 解析原始数据
    ├── git_stats.json          ← Git 热点与耦合数据
    └── file_tree.txt           ← 过滤后的文件树
```

---

## 🔄 SKIP 五阶段协议

| 阶段 | 核心动作 | 完成标志 |
|------|---------|---------|
| **S**CAN | 运行脚本，产出 `raw/` 三个文件 | 三文件均非空 |
| **H**YPOTHESIS | 阅读 README/热点/文件树，识别 ≥3 个系统 | 每个系统有 1 句职责描述 + 初步 `code_path` |
| **C**HALLENGE | 提出 ≥3 个反驳点，每点附代码引证 | 所有质疑有具体文件/行号证据 |
| **E**VIDENCE | 逐一验证质疑，修正错误节点 | 所有节点 `code_path` 已亲手验证存在 |
| **C**RYSTALLIZE | 原子写入全部 `.nexus-map/` 文件 | 全部文件通过 Schema 校验 |

各阶段详细步骤 → [`references/01-skip-protocol.md`](./references/01-skip-protocol.md)  
输出 Schema 规范 → [`references/02-output-schema.md`](./references/02-output-schema.md)  
边界案例处理 → [`references/03-edge-cases.md`](./references/03-edge-cases.md)

---

## 🛡️ 执行守则

### 守则1: CHALLENGE 拒绝形式主义

CHALLENGE 的存在意义是打破 HYPOTHESIS 的幸存者偏差。大量工程事实隐藏在目录命名和 git 热点背后，第一直觉几乎总是错的。

❌ **无效质疑（禁止提交）**：
```
Q1: 也许我对系统结构理解得不够深入
Q2: 需要进一步确认 xxx 目录的职责
```

✅ **有效质疑格式**：
```
Q1: git_stats 显示 tasks/analysis_tasks.py 变更 21 次（high risk），
    但 HYPOTHESIS 认为编排入口是 evolution/detective_loop.py。
    矛盾：若 detective_loop 是入口，为何 analysis_tasks 热度更高？
    证据线索: git_stats.json hotspots[0].path
    验证计划: view tasks/analysis_tasks.py 的 class 定义 + import 树
```

---

### 守则2: code_path 不存在则节点无效

> [!IMPORTANT]
> 写入 `concept_model.json` 前，**每一个节点的 `code_path` 都必须亲手验证存在**。

```bash
# EVIDENCE 阶段验证方式
ls $repo_path/src/nexus/application/weaving/   # ✅ 目录存在 → 节点有效
ls $repo_path/src/nexus/application/nonexist/  # ❌ [!ERROR] → 修正或删除此节点
```

❌ 禁止：`code_path: "src/nexus/unknown/"` 或 `code_path: ""`（未验证路径/空路径）

---

### 守则3: CRYSTALLIZE 原子性

先全部写入 `.nexus-map/.tmp/`，全部成功后整体移动到正式目录，删除 `.tmp/`。

**目的**：中途失败不留半成品。下次执行检测到 `.tmp/` 存在 → 清理后重新生成。

✅ 幂等性规则：

| 状态 | 处理方式 |
|------|----------|
| `.nexus-map/` 不存在 | 直接继续 |
| `.nexus-map/` 存在且 `INDEX.md` 有效 | 询问用户：「是否覆盖？[y/n]」 |
| `.nexus-map/` 存在但文件不完整 | 「检测到未完成分析，将重新生成」，直接继续 |

---

### 守则4: INDEX.md 是唯一冷启动入口

`INDEX.md` 的读者是**从未见过这个仓库的 AI**。两个硬约束：
- **< 2000 tokens** — 超过就重写，不是截断
- **无禁止词** — 任一出现即 `[!ERROR]`，整页返工

写完后执行 token 估算：行数 × 平均 30 tokens/行 = 粗估值。

---

## 🚫 禁止词（任意输出文件中出现 → `[!ERROR]` 必须返工）

```
中文：待确认 · 可能是 · 疑似 · 也许 · 待定 · 暂不清楚 · 需要进一步 · 不确定
英文：pending · maybe · possibly · perhaps · TBD · to be confirmed
```

---

## 🛠️ 脚本工具链

```bash
# 设置 SKILL_DIR（根据实际安装路径）
# 场景 A: 作为 .agent/skills 安装
SKILL_DIR=".agent/skills/nexus-mapper"
# 场景 B: 独立 repo（开发/调试时）
SKILL_DIR="/path/to/nexus-mapper"

# SCAN 阶段调用
python $SKILL_DIR/scripts/extract_ast.py <repo_path> [--max-nodes 500] \
  > <repo_path>/.nexus-map/raw/ast_nodes.json

python $SKILL_DIR/scripts/git_detective.py <repo_path> --days 90 \
  > <repo_path>/.nexus-map/raw/git_stats.json
```

**依赖安装（首次使用）**：
```bash
pip install -r $SKILL_DIR/scripts/requirements.txt
```

---

## ✅ 质量自检（CRYSTALLIZE 前必须全部通过）

- [ ] 五个阶段均已完成，每阶段有显式「✅ 完成」标记
- [ ] CHALLENGE 提出了 ≥3 个有代码引证的质疑点
- [ ] 每个节点的 `code_path` 已亲手验证存在（守则2）
- [ ] `responsibility` 字段：无禁止词，10-100 字
- [ ] `INDEX.md` 全文 < 2000 tokens，无禁止词（守则4）
- [ ] 无任何系统节点的 `code_path` 为空或占位符
