# PROBE 协议 — 各阶段详细步骤

> 本文件是 SKILL.md 的执行蓝图，Skill 激活后**第一步**即读取本文件。
> 各阶段的门控指令在下文内嵌。顺序执行是为了让结论建立在证据链上，而不是第一反应上。

---

## P — PROFILE 阶段

**前置验证**
1. 确认 `$repo_path` 目录存在
2. 检查 `$repo_path/.git` 是否存在
   - 存在：执行 git 热点分析
   - 不存在：记录 `git analysis skipped`，继续进行 AST 与文件树探测

**执行步骤**

```bash
# 步骤 1: 运行 AST 提取器（同时生成过滤后的文件树）
python $SKILL_DIR/scripts/extract_ast.py $repo_path [--max-nodes 500] \
  --file-tree-out .nexus-map/raw/file_tree.txt \
  > $repo_path/.nexus-map/raw/ast_nodes.json

# 若仓库包含内置未覆盖的语言，通过命令行参数补充支持
python $SKILL_DIR/scripts/extract_ast.py $repo_path [--max-nodes 500] \
  --add-extension .templ=templ \
  --add-query templ struct "(component_declaration name: (identifier) @class.name) @class.def" \
  --file-tree-out .nexus-map/raw/file_tree.txt \
  > $repo_path/.nexus-map/raw/ast_nodes.json

# 或使用显式 JSON 配置文件（配置较复杂时）
python $SKILL_DIR/scripts/extract_ast.py $repo_path [--max-nodes 500] \
  --language-config /custom/path/to/language-config.json \
  --file-tree-out .nexus-map/raw/file_tree.txt \
  > $repo_path/.nexus-map/raw/ast_nodes.json

# 步骤 2: 运行 git 热点分析（仅在存在 .git 时）
python $SKILL_DIR/scripts/git_detective.py $repo_path --days 90 \
  > $repo_path/.nexus-map/raw/git_stats.json
```

> `$SKILL_DIR` 为本 Skill 的安装路径（`.agent/skills/nexus-mapper` 或独立 repo 路径）。
> `$repo_path` 为目标仓库的绝对路径。
> `extract_ast.py --file-tree-out` 默认排除 `.git/`、`.nexus-map/`、`node_modules/`、`__pycache__/`、`.venv/`、`dist/`、`build/` 等噪音目录及文件。

**完成检查（任一失败 → 停止，不进入 REASON）**
- [ ] `raw/ast_nodes.json` 已写入（`nodes` 为空列表也属正常降级）
- [ ] `raw/file_tree.txt` 非空
- [ ] 若存在 git 历史：`raw/git_stats.json` 非空，包含 `hotspots` 字段
- [ ] 若不存在 git 历史：已明确记录这是一次无 git 降级探测
- [ ] 若 `ast_nodes.json.stats.known_unsupported_file_counts` 非空：已记录语言覆盖降级
- [ ] 若 `ast_nodes.json.stats.module_only_file_counts` 非空：已记录哪些语言只有 Module 级覆盖
- [ ] 若 `ast_nodes.json.stats.configured_but_unavailable_file_counts` 非空：已记录这部分视为未覆盖

---

## R — REASON 阶段

> [!IMPORTANT]
> **阶段门控**：开始阅读项目文件之前，必须先读：
> `references/03-edge-cases.md`
> 目的：提前识别边界场景（无 git 历史、monorepo 等），避免后续阶段错误执行。

**阅读策略（优先级从高到低）**
1. `README.md` / `README.rst` — 项目总体描述
2. `pyproject.toml` / `package.json` / `pom.xml` — 技术栈与依赖
3. 主入口文件（`main.py`, `index.ts`, `Application.java`）
4. `raw/file_tree.txt` — 目录结构感知
5. `raw/git_stats.json` hotspots Top 5 — 最活跃文件（仅 git 数据可用时）
6. 测试目录 — 建立静态测试面，不需要运行测试

**执行要求**
- 进行深度思考，逐步推演足够支撑结论的关键决策点，通常 3-5 个
- 识别仓库的主要 System 级节点，通常 1-5 个；不要为凑数量把纯技术细节拆成独立系统
- **[推荐]** 运行 hub-analysis 用扇入/扇出数据验证核心系统假说：
  ```bash
  python $SKILL_DIR/scripts/query_graph.py $repo_path/.nexus-map/raw/ast_nodes.json --hub-analysis
  ```

**记录格式**（工作记忆，不写文件）
```
[REASON LOG]
- System A: 推断职责=X, implementation_status=implemented, code_path=Y （置信度: 高/中/低）
- System B: 推断职责=X, implementation_status=planned, evidence_path=Y （置信度: 高/中/低）
- Evidence gap: Z 目录归属缺少直接证据（将在 OBJECT 中质疑）
```

---

## O — OBJECT 阶段

> [!IMPORTANT]
> **阶段门控**：提出任何质疑点之前，必须先读：
> `references/04-object-framework.md`
> 三维度框架（Structure / Evolution / Dependency）是本阶段的执行依据，不是装饰。

**质疑协议** — 提出足以挑战当前假设的最少一组高价值质疑，通常 1-3 个，每个附证据线索

每个质疑点格式：
```
Q{N}: [具体的矛盾或可疑之处]
证据线索: [在哪里发现的矛盾 — 文件路径/行号/git 数据]
验证计划: [BENCHMARK 阶段如何验证]
```

不合格质疑（禁止提交，必须替换）：
```
Q1: 我对系统结构的把握还不够扎实
Q2: xxx 目录的职责暂时没有直接证据
```
问题不在措辞，而在于没有代码引证，也没有可执行的验证计划。

合格示例：
```
Q1: git_stats 显示 tasks/analysis_tasks.py 变更 21 次（high risk），
    但 REASON 认为编排入口是 evolution/detective_loop.py。
    矛盾：若 detective_loop 是入口，analysis_tasks 为何热度更高？
    证据线索: raw/git_stats.json hotspots[0]
    验证计划: view tasks/analysis_tasks.py 的 class 定义 + import 树，
              对比 evolution/detective_loop.py 的调用方关系
```

---

## B — BENCHMARK 阶段

**对每个质疑点执行验证**
1. 用 `grep_search` / `view_file` 查找具体证据
2. **[推荐]** 用 `query_graph.py --impact` 查看目标文件的真实上下游依赖：
   ```bash
   python $SKILL_DIR/scripts/query_graph.py $repo_path/.nexus-map/raw/ast_nodes.json \
     --impact <目标文件> --git-stats $repo_path/.nexus-map/raw/git_stats.json
   ```
3. 判断结果：
   - 质疑成立 → 修正节点的 `code_path` 或 `responsibility`，在 LOG 中标记「修正」
   - 质疑不成立 → 确认原假设，标记「验证通过」

**全局节点校验（全部 System 节点逐一执行）**
- [ ] `implemented` 节点的 `code_path` 在 repo 中实际存在（`ls` 或 `view_file` 确认）
- [ ] `planned/inferred` 节点不伪造 `code_path`，改用 `evidence_path + evidence_gap`
- [ ] 每个 `planned/inferred` 节点的 `evidence_path` 在 repo 中实际存在
- [ ] `responsibility` 表意清晰、具体；若证据不足，明确记录 evidence gap
- [ ] 节点 `id` 全局唯一，kebab-case，全部小写

> 发现关键系统完全识别错误 → 允许返回 REASON 重建模型，并重新执行 OBJECT。

---

## E — EMIT 阶段

> [!IMPORTANT]
> **阶段门控**：写入任何文件之前，必须先读：
> `references/02-output-schema.md`
> 未读取该文件即写入 → 产出的 JSON/Markdown 结构无法通过 Schema 校验，视为无效。

**幂等性检查（写入前必做）**

| 检查结果                             | 处理方式                                          |
| ------------------------------------ | ------------------------------------------------- |
| `.nexus-map/` 不存在                 | 直接继续                                          |
| `.nexus-map/` 存在且 `INDEX.md` 有效 | 询问用户：「检测到已有分析结果，是否覆盖？[y/n]」 |
| `.nexus-map/` 存在但文件不完整       | 「检测到未完成分析，将重新生成」，继续            |

**[推荐] 写入前先获取结构摘要**
```bash
python $SKILL_DIR/scripts/query_graph.py $repo_path/.nexus-map/raw/ast_nodes.json --summary
```

**写入顺序（先写 `.tmp/`，全部成功后整体移动）**
```
1. .nexus-map/.tmp/concepts/concept_model.json   ← Schema V1
2. .nexus-map/.tmp/INDEX.md                       ← L0 摘要, < 2000 tokens
3. .nexus-map/.tmp/arch/systems.md                ← 各 System 边界
4. .nexus-map/.tmp/arch/dependencies.md           ← Mermaid 依赖图
5. .nexus-map/.tmp/arch/test_coverage.md          ← 静态测试面与证据缺口
6. .nexus-map/.tmp/concepts/domains.md            ← Domain 概念说明
7. .nexus-map/.tmp/hotspots/git_forensics.md      ← Git 热点摘要
```

全部写入成功 → 移动 `.tmp/` 内容到 `.nexus-map/` → 删除 `.tmp/`

**INDEX.md 写入要求**
- token 数 < 2000，超过就重写
- 结论具体，不使用模糊词搪塞；证据不足时明确写 `evidence gap` 或 `unknown`
- **必须包含 SKILL.md 守则4 定义的「操作指南」硬路由块**

**每个 Markdown 文件的头部最少包含**
```markdown
> generated_by: nexus-mapper v2
> verified_at: 2026-03-07
> provenance: AST-backed except where explicitly marked inferred
```

**edges 合并协议（写入 concept_model.json 前执行）**
1. 导入 `raw/ast_nodes.json` 中的 edges（`imports`/`contains`，机器层精确）
2. 追加 BENCHMARK 阶段推断的语义边（`depends_on`/`calls`）
3. 去重：`(source, target, type)` 三元组相同的边保留一条

**完成校验**
- [ ] `INDEX.md` 存在，结论具体且对证据缺口诚实，< 2000 tokens，包含硬路由块
- [ ] `concept_model.json` 中 `implemented` 节点都有已验证 `code_path`
- [ ] `arch/dependencies.md` 包含 >= 1 个 Mermaid 图
- [ ] `arch/test_coverage.md` 说明了静态测试面，并明确未运行测试的证据缺口
