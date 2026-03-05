# SKIP 协议 — 各阶段详细步骤

> L1 技术层 — 在执行对应阶段时按需加载

---

## S — SCAN 阶段

**前置验证**
1. 确认 `$repo_path` 目录存在
2. 确认 `$repo_path/.git` 目录存在 → 否则 `[!ERROR: NOT_A_GIT_REPO]` 停止

**执行步骤**

```bash
# 步骤 1: 运行 AST 提取器
python $SKILL_DIR/scripts/extract_ast.py $repo_path [--max-nodes 500] \
  > $repo_path/.nexus-map/raw/ast_nodes.json

# 步骤 2: 运行 git 热点分析
python $SKILL_DIR/scripts/git_detective.py $repo_path --days 90 \
  > $repo_path/.nexus-map/raw/git_stats.json

# 步骤 3: 生成文件树（AI Agent 执行，使用 list_dir 工具）
# 遍历目录，排除: .git/, node_modules/, __pycache__/, .venv/, dist/, build/, .nexus-map/
# 写入 $repo_path/.nexus-map/raw/file_tree.txt
```

> `$SKILL_DIR` 为本 Skill 的安装路径（`.agent/skills/nexus-mapper` 或独立 repo 路径）。
> `$repo_path` 为目标仓库的绝对路径。

**完成检查（任一失败 → 停止，不进入 HYPOTHESIS）**
- [ ] `raw/ast_nodes.json` 非空，包含 `nodes` 字段
- [ ] `raw/git_stats.json` 非空，包含 `hotspots` 字段
- [ ] `raw/file_tree.txt` 非空

---

## H — HYPOTHESIS 阶段

**阅读策略（优先级从高到低）**
1. `README.md` / `README.rst` — 项目总体描述
2. `pyproject.toml` / `package.json` / `pom.xml` — 技术栈与依赖
3. 主入口文件（`main.py`, `index.ts`, `Application.java`）
4. `raw/file_tree.txt` — 目录结构感知
5. `raw/git_stats.json` hotspots Top 5 — 最活跃文件

**执行要求**
- 使用 `sequentialthinking` 思考 3-5 步
- 识别 **≥3 个 System 级节点**，每个有初步的 `code_path` 假设和置信度标注

**记录格式**（工作记忆，不写文件）
```
[HYPOTHESIS LOG]
- System A: 推断职责=X, code_path=Y （置信度: 高/中/低）
- System B: 推断职责=X, code_path=Y （置信度: 高/中/低）
- 疑问: Z 目录归属不确定（将在 CHALLENGE 中质疑）
```

---

## C — CHALLENGE 阶段

**质疑协议 — 必须提出 ≥3 个质疑点，每个附代码引证**

每个质疑点格式：
```
Q{N}: [具体的矛盾或可疑之处]
证据线索: [在哪里发现的矛盾 — 文件路径/行号/git 数据]
验证计划: [EVIDENCE 阶段如何验证]
```

**质量判定**

❌ **不合格质疑（禁止提交，必须替换）**：
```
Q1: 也许我对系统结构理解得不够深入
Q2: 需要进一步确认 xxx 目录的职责
Q3: 不确定 yyy 是否真的是入口
```
▲ 上述质疑使用了禁止词，且没有代码引证，无法在 EVIDENCE 阶段验证。

✅ **合格示例**：
```
Q1: git_stats 显示 tasks/analysis_tasks.py 变更 21 次（high risk），
    但 HYPOTHESIS 认为编排入口是 evolution/detective_loop.py。
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

## E — EVIDENCE 阶段

**对每个质疑点执行验证**
1. 用 `grep_search` / `view_file` 查找具体证据
2. 判断结果：
   - 质疑成立 → 修正节点的 `code_path` 或 `responsibility`，在 LOG 中标记「修正」
   - 质疑不成立 → 确认原假说，标记「验证通过」

**全局节点校验（全部 System 节点逐一执行）**
- [ ] 每个节点 `code_path` 在 repo 中实际存在（`ls` 或 `view_file` 确认）
- [ ] `responsibility` 无禁止词，表意清晰，10-100 字
- [ ] 节点 `id` 全局唯一，kebab-case，全部小写

> 发现关键系统完全识别错误 → 允许返回 HYPOTHESIS 重建模型，并重新执行 CHALLENGE。

---

## C — CRYSTALLIZE 阶段

**幂等性检查（写入前必做）**

| 检查结果 | 处理方式 |
|---------|----------|
| `.nexus-map/` 不存在 | 直接继续 |
| `.nexus-map/` 存在且 `INDEX.md` 有效 | 询问用户：「检测到已有分析结果，是否覆盖？[y/n]」 |
| `.nexus-map/` 存在但文件不完整 | 「检测到未完成分析，将重新生成」，继续 |

**写入顺序（先写 `.tmp/`，全部成功后整体移动）**
```
1. .nexus-map/.tmp/concepts/concept_model.json   ← Schema V1
2. .nexus-map/.tmp/INDEX.md                       ← L0 摘要, < 2000 tokens
3. .nexus-map/.tmp/arch/systems.md                ← 各 System 边界
4. .nexus-map/.tmp/arch/dependencies.md           ← Mermaid 依赖图
5. .nexus-map/.tmp/concepts/domains.md            ← Domain 概念说明
6. .nexus-map/.tmp/hotspots/git_forensics.md      ← Git 热点摘要
```

全部写入成功 → 移动 `.tmp/` 内容到 `.nexus-map/` → 删除 `.tmp/`

**edges 合并协议（写入 concept_model.json 前执行）**
1. 导入 `raw/ast_nodes.json` 中的 edges（`imports`/`contains`，机器层精确）
2. 追加 EVIDENCE 阶段推断的语义边（`depends_on`/`calls`）
3. 去重：`(source, target, type)` 三元组相同的边保留一条

**完成自检**
- [ ] `INDEX.md` 存在，无禁止词，< 2000 tokens
- [ ] `concept_model.json` 所有 System 节点有非空 `code_path`
- [ ] `arch/dependencies.md` 包含 ≥1 个 Mermaid 图
