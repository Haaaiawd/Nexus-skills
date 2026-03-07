---
name: nexus-mapper
description: Analyze a local repository and generate a persistent `.nexus-map/` knowledge base for future AI sessions. Use whenever the user asks to map a codebase, understand project architecture, build repo knowledge, create cold-start context, or assess change impact across an unfamiliar repository. Requires shell execution and local Python. Do not use for single-file questions, pure API environments, or tasks that only need a quick grep/read.
---

# nexus-mapper — AI 项目探测协议

> "你不是在写代码文档。你是在为下一个接手的 AI 建立思维基础。"

本 Skill 指导 AI Agent 使用 **PROBE 五阶段协议**，对任意本地 Git 仓库执行系统性探测，产出 `.nexus-map/` 分层知识库。

---

## ⚠️ CRITICAL — 五阶段不可跳过

> [!IMPORTANT]
> **在 PROFILE、REASON、OBJECT、BENCHMARK 完成前，不得产出最终 `.nexus-map/`。**
>
> 这不是为了形式完整，而是为了防止 AI 把第一眼假设直接写成结论。最终产物必须建立在脚本输出、仓库结构、反证挑战和回查验证之上。

❌ **禁止行为**：
- 跳过 OBJECT 直接写输出资产
- 在 BENCHMARK 完成前生成 `concept_model.json`
- PROFILE 阶段脚本失败后继续执行后续阶段

✅ **必须做到**：
- 每个阶段完成后显式确认「✅ 阶段名 完成」再进入下一阶段
- OBJECT 提出足以推翻当前假设的最少一组高价值质疑，通常为 1-3 条，绝不凑数
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
| 目标仓库无任何已知语言源文件（`.py/.ts/.java/.go/.rs/.cpp` 等均无） | ❌ |
| 用户只想查询某个特定文件/函数 → 直接用 `view_file` / `grep_search` | ❌ |

---

## ⚠️ 前提检查（缺失项要显式告知；可降级时优先降级而不是中止）

| 前提 | 检查方式 |
|------|---------|
| 目标路径存在 | `$repo_path` 可访问 |
| Python 3.10+ | `python --version` >= 3.10 |
| 脚本依赖已安装 | `python -c "import tree_sitter"` 无报错 |
| 有 shell 执行能力 | Agent 环境支持 `run_command` 工具调用 |

`git` 历史是加分项，不是硬阻塞项。没有 `.git` 或历史过少时，跳过热点分析，并在输出中明确记录这是一次降级探测。

---

## 📥 输入契约

```
repo_path: 目标仓库的本地绝对路径（必填）
```

**语言支持**：自动按文件扩展名 dispatch，支持 Python/JavaScript/TypeScript/TSX/Java/Go/Rust/C#/C/C++/Kotlin/Ruby/Swift/Scala/PHP/Lua/Elixir（基于 `tree-sitter-language-pack`）。

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

## 🔄 PROBE 五阶段协议

> [!IMPORTANT]
> **Reference 文件不是附录，而是阶段执行说明。** 进入对应阶段前先读对应 reference，
> 是为了减少漏判边界场景、误写 schema 和跳过自我校验的概率。

| 阶段 | 开始前必须读取（硬门控） | 核心动作 | 完成标志 |
|------|------------------------|---------|--------|
| **P**ROFILE | ⛔ `read_file references/01-probe-protocol.md` | 运行脚本，产出 `raw/` 核心输入 | `ast_nodes.json` 与 `file_tree.txt` 可用；git 数据按条件生成 |
| **R**EASON | ⛔ `read_file references/03-edge-cases.md`（检查是否触发边界场景） | 阅读 README/热点/文件树，识别主要系统 | 每个系统有职责描述 + 初步 `code_path` |
| **O**BJECT | ⛔ `read_file references/04-object-framework.md` | 按三维度提出最少一组高价值反驳点 | 每条质疑都有具体证据线索和验证计划 |
| **B**ENCHMARK | （无额外文件，使用已加载的协议） | 逐一验证异议，修正错误节点 | 所有节点 `code_path` 已亲手验证存在 |
| **E**MIT | ⛔ `read_file references/02-output-schema.md`（校验 Schema 后才能写文件） | 原子写入全部 `.nexus-map/` 文件 | 全部文件通过 Schema 校验 |

**强制阅读顺序总览**（按触发时间排列，不得颠倒或跳过）：

```
[Skill 激活时]     → 读  01-probe-protocol.md   （阶段步骤蓝图）
[REASON 前]        → 读  03-edge-cases.md        （确认是否命中边界场景）
[OBJECT 前]        → 读  04-object-framework.md  （三维度质疑模板）
[EMIT 前]          → 读  02-output-schema.md     （Schema 校验规范）
```

---

## 🛡️ 执行守则

### 守则1: OBJECT 拒绝形式主义

OBJECT 的存在意义是打破 REASON 的幸存者偏差。大量工程事实隐藏在目录命名和 git 热点背后，第一直觉几乎总是错的。

❌ **无效质疑（禁止提交）**：
```
Q1: 我对系统结构的把握还不够扎实
Q2: xxx 目录的职责暂时没有直接证据
```

▲ 问题不在于用了某几个词，而在于这类表述没有证据线索，也无法在 BENCHMARK 阶段验证。

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
# BENCHMARK 阶段验证方式
ls $repo_path/src/nexus/application/weaving/   # ✅ 目录存在 → 节点有效
ls $repo_path/src/nexus/application/nonexist/  # ❌ [!ERROR] → 修正或删除此节点
```

❌ 禁止：`code_path: "src/nexus/unknown/"` 或 `code_path: ""`（未验证路径/空路径）

---

### 守则3: EMIT 原子性

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
- **结论必须具体** — 不要用空泛的模糊词搪塞；证据不足时明确写出 `evidence gap` 或 `unknown`，并说明缺了什么证据

写完后执行 token 估算：行数 × 平均 30 tokens/行 = 粗估值。

---

## 🧭 不确定性表达规范

```
避免只写：待确认 · 可能是 · 疑似 · 也许 · 待定 · 暂不清楚 · 需要进一步 · 不确定
避免只写：pending · maybe · possibly · perhaps · TBD · to be confirmed
```

如果证据不足，可以这样写：
- `unknown: 未发现直接证据表明 api/ 是主入口，当前仅能确认 cli.py 被 README 引用`
- `evidence gap: 仓库没有 git 历史，因此 hotspots 部分跳过`

原则：允许诚实地写不确定，但必须解释不确定来自哪一条缺失证据，而不是把模糊词当结论。

---

### 守则5: 最小执行面与敏感信息保护

> [!IMPORTANT]
> 默认只运行本 Skill 自带脚本和必要的只读检查。不要因为“想更懂仓库”就执行目标仓库里的构建脚本、测试脚本或自定义命令。

- 默认允许：`extract_ast.py`、`git_detective.py`、目录遍历、文本搜索、只读文件查看
- 默认禁止：执行目标仓库的 `npm install`、`pnpm dev`、`python main.py`、`docker compose up` 等命令，除非用户明确要求
- 遇到 `.env`、密钥文件、凭据配置时：只记录其存在和用途，不抄出具体值

---

## 🛠️ 脚本工具链

```bash
# 设置 SKILL_DIR（根据实际安装路径）
# 场景 A: 作为 .agent/skills 安装
SKILL_DIR=".agent/skills/nexus-mapper"
# 场景 B: 独立 repo（开发/调试时）
SKILL_DIR="/path/to/nexus-mapper"

# PROFILE 阶段调用
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

## ✅ 质量自检（EMIT 前必须全部通过）

- [ ] 五个阶段均已完成，每阶段有显式「✅ 完成」标记
- [ ] OBJECT 的质疑数量没有凑数；每条都带证据线索和可执行验证计划
- [ ] 每个节点的 `code_path` 已亲手验证存在（守则2）
- [ ] `responsibility` 字段：具体、可验证；证据不足时明确说明缺口
- [ ] `INDEX.md` 全文 < 2000 tokens，结论具体不过度装确定（守则4）
- [ ] 无任何系统节点的 `code_path` 为空或占位符
