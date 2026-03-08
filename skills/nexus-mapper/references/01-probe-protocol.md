# PROBE 协议 — 各阶段详细步骤

> 本文件是 SKILL.md 的执行蓝图，Skill 激活后**第一步**即读取本文件。
> 各阶段的 ⛔ 门控指令在下文中内嵌。顺序执行是为了让结论建立在证据链上，而不是第一反应上。

---

## P — PROFILE 阶段

**前置验证**
1. 确认 `$repo_path` 目录存在
2. 检查 `$repo_path/.git` 是否存在
  - 存在：执行 git 热点分析
  - 不存在：记录 `git analysis skipped`，继续进行 AST 与文件树探测

**执行步骤**

```bash
# 步骤 1: 运行 AST 提取器
python $SKILL_DIR/scripts/extract_ast.py $repo_path [--max-nodes 500] \
  > $repo_path/.nexus-map/raw/ast_nodes.json

# 若仓库包含内置未覆盖的语言，可先通过命令行参数补充支持
python $SKILL_DIR/scripts/extract_ast.py $repo_path [--max-nodes 500] \
  --add-extension .templ=templ \
  --add-query templ struct "(component_declaration name: (identifier) @class.name) @class.def" \
  > $repo_path/.nexus-map/raw/ast_nodes.json

# 若扩展项较多，也可显式传入自定义语言配置文件
python $SKILL_DIR/scripts/extract_ast.py $repo_path [--max-nodes 500] \
  [--language-config /custom/path/to/language-config.json] \
  > $repo_path/.nexus-map/raw/ast_nodes.json

# 若希望同时生成过滤后的文件树，可直接复用同一套排除规则
python $SKILL_DIR/scripts/extract_ast.py $repo_path [--max-nodes 500] \
  [--file-tree-out .nexus-map/raw/file_tree.txt] \
  > $repo_path/.nexus-map/raw/ast_nodes.json

# 步骤 2: 运行 git 热点分析（仅在存在 .git 时）
python $SKILL_DIR/scripts/git_detective.py $repo_path --days 90 \
  > $repo_path/.nexus-map/raw/git_stats.json

# 步骤 3: 若步骤 1 未带 --file-tree-out，则补生成 file_tree.txt
python $SKILL_DIR/scripts/extract_ast.py $repo_path [--max-nodes 500] \
  --file-tree-out .nexus-map/raw/file_tree.txt \
  > $repo_path/.nexus-map/raw/ast_nodes.json
```

> `$SKILL_DIR` 为本 Skill 的安装路径（`.agent/skills/nexus-mapper` 或独立 repo 路径）。
> `$repo_path` 为目标仓库的绝对路径。
> `extract_ast.py --file-tree-out` 默认排除 `.git/`、`.nexus-map/`、`node_modules/`、`__pycache__/`、`.venv/`、`dist/`、`build/`、`.mypy_cache/`、`.pytest_cache/`、`.ruff_cache/`、`.godot/`，以及 `*.import`、`*.vulkan.cache` 等噪音文件。

**完成检查（任一失败 → 停止，不进入 REASON）**
- [ ] `raw/ast_nodes.json` 已写入（即使 `nodes` 为空列表也属正常——不支持的语言降级为空）
- [ ] `raw/file_tree.txt` 非空
- [ ] 若存在 git 历史：`raw/git_stats.json` 非空，包含 `hotspots` 字段
- [ ] 若不存在 git 历史：已明确记录这是一次无 git 降级探测
- [ ] 若 `ast_nodes.json.stats.known_unsupported_file_counts` 非空：已记录本次语言覆盖降级，后续输出必须显式标注 provenance
- [ ] 若 `ast_nodes.json.stats.module_only_file_counts` 非空：已记录哪些语言只有 Module 级覆盖，后续输出不得把这些语言描述为完整结构 AST 覆盖
- [ ] 若 `ast_nodes.json.stats.configured_but_unavailable_file_counts` 非空：已记录哪些语言虽然通过 CLI 或显式配置声明，但当前环境没有可用 parser，后续输出必须把这部分视为未覆盖

---

## R — REASON 阶段

> [!IMPORTANT]
> **⛔ 阶段门控**：在开始阅读项目文件之前，必须先执行：
> ```
> read_file  references/03-edge-cases.md
> ```
> 目的：提前识别是否命中任何边界场景（无 git 历史、monorepo、非 git 仓库等），避免后续阶段错误执行。

**阅读策略（优先级从高到低）**
1. `README.md` / `README.rst` — 项目总体描述
2. `pyproject.toml` / `package.json` / `pom.xml` — 技术栈与依赖
3. 主入口文件（`main.py`, `index.ts`, `Application.java`）
4. `raw/file_tree.txt` — 目录结构感知
5. `raw/git_stats.json` hotspots Top 5 — 最活跃文件（仅在 git 数据可用时）
6. `tests/`, `test/`, `spec/` 等测试目录 — 建立静态测试面，不需要运行测试

**执行要求**
- 进行深度思考，逐步推演足够支撑结论的关键决策点，通常为 3-5 个
- 识别仓库的主要 System 级节点，通常为 1-5 个；不要为了凑数量把纯技术细节拆成独立系统
- **[推荐]** 运行 hub-analysis 用扇入/扇出数据验证核心系统假说，而不是仅凭目录名猜测：
  ```bash
  python $SKILL_DIR/scripts/query_graph.py $repo_path/.nexus-map/raw/ast_nodes.json --hub-analysis
  ```
  该查询会自动兼容常见 `src-layout` Python/Java/Kotlin 项目的包名与文件路径差异；若结果仍为空，优先怀疑仓库内部本就缺少可解析的内部 import，而不是直接怀疑系统边界判断。

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
> **⛔ 阶段门控**：在提出任何质疑点之前，必须先执行：
> ```
> read_file  references/04-object-framework.md
> ```
> 未读取该文件即提出质疑，极易把第一眼印象当成问题。三维度框架（Structure / Evolution / Dependency）是本阶段的执行依据，不是装饰。

**质疑协议 — 提出足以挑战当前假设的最少一组高价值质疑，通常 1-3 个，每个附证据线索**

每个质疑点格式：
```
Q{N}: [具体的矛盾或可疑之处]
证据线索: [在哪里发现的矛盾 — 文件路径/行号/git 数据]
验证计划: [BENCHMARK 阶段如何验证]
```

**质量判定**

❌ **不合格质疑（禁止提交，必须替换）**：
```
Q1: 我对系统结构的把握还不够扎实
Q2: xxx 目录的职责暂时没有直接证据
Q3: yyy 是否是入口目前没有验证
```
▲ 上述质疑的问题不在于措辞本身，而在于没有代码引证，也没有可执行的验证计划。

✅ **合格示例**：
```
Q1: git_stats 显示 tasks/analysis_tasks.py 变更 21 次（high risk），
    但 REASON 认为编排入口是 evolution/detective_loop.py。
    矛盾：若 detective_loop 是入口，analysis_tasks 为何热度更高？
    证据线索: raw/git_stats.json hotspots[0]
    验证计划: view tasks/analysis_tasks.py 的 class 定义 + import 树，
              对比 evolution/detective_loop.py 的调用方关系

Q2: application/weaving/ 目录命名暗示「语义织入」，但其下
    treesitter_parser.py 的命名偏向「解析」。可能存在分层理解错误。
    证据线索: raw/file_tree.txt 中 application/weaving/ 下的文件列表
    验证计划: view treesitter_parser.py 的 class 职责，
              检查 infrastructure/parsing/ 是否存在并承担原始解析
```

---

## B — BENCHMARK 阶段

**对每个质疑点执行验证**
1. 用 `grep_search` / `view_file` 查找具体证据
2. **[推荐]** 用 `query_graph.py --impact` 查看目标文件的真实上下游依赖，可叠加 `--git-stats` 获取变更热度和耦合信息：
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
> **⛔ 阶段门控**：在写入任何文件之前，必须先执行：
> ```
> read_file  references/02-output-schema.md
> ```
> 未读取该文件即写入 → 产出的 JSON/Markdown 结构无法通过 Schema 校验，视为无效。

**幂等性检查（写入前必做）**

| 检查结果 | 处理方式 |
|---------|----------|
| `.nexus-map/` 不存在 | 直接继续 |
| `.nexus-map/` 存在且 `INDEX.md` 有效 | 询问用户：「检测到已有分析结果，是否覆盖？[y/n]」 |
| `.nexus-map/` 存在但文件不完整 | 「检测到未完成分析，将重新生成」，继续 |

**[推荐] 写入前先获取结构摘要**
```bash
python $SKILL_DIR/scripts/query_graph.py $repo_path/.nexus-map/raw/ast_nodes.json --summary
```
此命令按目录聚合模块/类/函数计数和关键导入方向，为写 `systems.md` 和 `dependencies.md` 提供数据支撑。对需要详细描述的系统，可进一步用 `--file <path>` 查看具体文件结构。

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

**每个 Markdown 文件的头部最少包含**
```markdown
> generated_by: nexus-mapper v2
> verified_at: 2026-03-07
> provenance: AST-backed except where explicitly marked inferred
```

若存在未支持语言或人工推断区域，`provenance` 行必须扩展说明：
- 哪些语言未被 AST 覆盖
- 哪些章节/图是人工推断
- 任何进度快照的来源日期

**edges 合并协议（写入 concept_model.json 前执行）**
1. 导入 `raw/ast_nodes.json` 中的 edges（`imports`/`contains`，机器层精确）
2. 追加 BENCHMARK 阶段推断的语义边（`depends_on`/`calls`）
3. 去重：`(source, target, type)` 三元组相同的边保留一条

**完成自检**
- [ ] `INDEX.md` 存在，结论具体且对证据缺口诚实，< 2000 tokens
- [ ] `concept_model.json` 中 `implemented` 节点都有已验证 `code_path`，`planned/inferred` 节点不伪造路径
- [ ] `arch/dependencies.md` 包含 ≥1 个 Mermaid 图
- [ ] `arch/test_coverage.md` 说明了静态测试面，并明确未运行测试或未获取覆盖率的证据缺口
