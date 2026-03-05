---
name: nexus-mapper
description: 对本地代码仓库进行结构化探测，生成供 AI 冷启动阅读的 `.nexus-map/` 知识库。当用户要求「分析项目」「生成项目地图」「让 AI 了解这个仓库」「建立项目知识库」或指定一个本地 repo 路径并希望 AI 理解其结构时触发。不适用于：纯 API 调用环境（无 run_command 工具）、无本地 Python 3.10+ 的机器、或用户只想了解某个特定文件/函数（用 view_file 即可）。
---

# nexus-mapper — AI 项目探测协议

> "你不是在写代码文档。你是在为下一个接手的 AI 建立思维基础。"

本 Skill 指导 AI Agent 使用 **SKIP 五阶段协议**，对任意本地 Git 仓库执行系统性探测，产出 `.nexus-map/` 分层知识库。

---

## 📌 何时调用 / 何时不调用

**✅ 调用此 Skill 的场景**：
- 用户提供了一个本地 repo 路径，希望 AI 理解其架构
- 需要生成 `.nexus-map/INDEX.md` 供后续 AI 会话冷启动使用
- 用户说「帮我分析项目」「建立项目知识库」「让 AI 了解这个仓库」

**❌ 不调用此 Skill 的场景**：
- 运行环境无 shell 执行能力（纯 API 调用模式，无 `run_command` 工具）
- 宿主机无本地 Python 3.10+（脚本无法运行）
- 用户只想了解某个特定文件/函数 → 直接用 `view_file` / `grep_search`
- 目标仓库主语言**不是 Python**（当前版本仅支持 Python）

---

## ⚠️ 前提检查（满足以上调用场景后，验证以下条件）

> [!IMPORTANT]
> **缺少任一前提 → 立即停止，告知用户具体缺失项**

| 前提 | 检查方式 |
|------|---------|
| ✅ 本地 Git 仓库 | `$repo_path/.git` 目录存在 |
| ✅ Python 3.10+ 可用 | `python --version` 或 `python3 --version` >= 3.10 |
| ✅ 脚本依赖已安装 | `python -c "import tree_sitter"` 无报错（详见 `scripts/requirements.txt`） |
| ✅ 有 shell 执行能力 | Agent 环境支持 `run_command` 工具调用 |

---

## 📥 输入契约

```
repo_path: 目标仓库的本地绝对路径（必填）
```

**当前版本限制**：仅支持 Python 语言代码库（`.py` 文件为主）。

---

## 📤 输出格式

执行完成后，目标仓库根目录下将产出：

```text
.nexus-map/
├── INDEX.md              ← AI 冷启动主入口（< 2000 tokens）
├── arch/
│   └── systems.md        ← 系统边界 + 代码位置（< 1500 tokens）
├── concepts/
│   └── concept_model.json  ← Schema V1 机器可读图谱
└── raw/
    ├── ast_nodes.json    ← Tree-sitter 解析原始数据
    ├── git_stats.json    ← Git 热点与耦合数据
    └── file_tree.txt     ← 过滤后的文件树
```

---

## 🔄 SKIP 五阶段协议（不可跳过）

> [!IMPORTANT]
> **五个阶段必须严格按序执行。禁止跳步，禁止在 CHALLENGE 完成之前写任何输出资产。**
> 缺少任何阶段 → 视为不完整执行，`INDEX.md` 禁止生成。

| 阶段 | 代号 | 核心动作 | 完成标志 |
|------|------|---------|---------|
| **S**CAN | 扫描机械数据 | 运行脚本，产出 `raw/` 三个文件 | 三文件均非空 |
| **H**YPOTHESIS | 提出系统假说 | 阅读 README/入口/热点，识别 ≥3 个系统/域 | 每个假说系统有 1 句职责描述 |
| **C**HALLENGE | 主动质疑假说 | 列出 ≥3 个对 HYPOTHESIS 结论的反驳点 | 每个质疑有具体代码引证 |
| **E**VIDENCE | 验证与修正 | 用 grep/view_file 逐一验证质疑，修正错误节点 | 所有节点有真实存在的 `code_path` |
| **C**RYSTALLIZE | 写入输出资产 | 一次性写入全部 `.nexus-map/` 文件 | 全部文件通过 Schema 校验 |

### 各阶段详细步骤
→ 加载 [`references/01-skip-protocol.md`](./references/01-skip-protocol.md)

### 输出 Schema 规范
→ 加载 [`references/02-output-schema.md`](./references/02-output-schema.md)

### 边界案例处理
→ 加载 [`references/03-edge-cases.md`](./references/03-edge-cases.md)

---

## 🚫 禁止词（Forbidden Words）

> [!IMPORTANT]
> 以下词语出现在任何输出文件中均视为 `[!ERROR]`，必须返工：

`待确认` · `可能是` · `疑似` · `也许` · `待定` · `暂不清楚` · `需要进一步` · `不确定`

---

## 🛠️ 脚本工具链

脚本位于本 Skill 目录的 `scripts/` 子目录：

```bash
# SCAN 阶段调用
python .agent/skills/nexus-mapper/scripts/extract_ast.py <repo_path> [--max-nodes 500]
python .agent/skills/nexus-mapper/scripts/git_detective.py <repo_path> --days 90
```

**依赖安装**（首次使用）：
```bash
# 独立使用（任何项目）
pip install -r .agent/skills/nexus-mapper/scripts/requirements.txt

# 在 Nexus 项目内（依赖已由 poetry 环境覆盖，使用 poetry run）
poetry run python .agent/skills/nexus-mapper/scripts/extract_ast.py <repo_path>
```

---

## ✅ 质量自检（CRYSTALLIZE 前必须通过）

- [ ] 所有 5 个阶段均已完成（SCAN → CRYSTALLIZE）
- [ ] CHALLENGE 提出了 ≥3 个质疑点
- [ ] 每个节点的 `code_path` 在仓库中真实存在
- [ ] `responsibility` 字段无禁止词，长度 10-100 字
- [ ] `INDEX.md` 全文 < 2000 tokens
- [ ] 无任何系统节点的 `code_path` 为空或占位符
