# OBJECT 阶段 — 三维度质疑框架

> ⛔ **OBJECT 阶段硬门控**：本文件由 `01-probe-protocol.md` 的 OBJECT 阶段门控强制触发读取，
> 提出任何质疑点前必须完成本文阅读，三维度框架（Structure / Evolution / Dependency）是质疑的执行依据。
>
> 来源：SEI QUASAR 方法论 + MSR '26 hotspot 研究 + 架构审查最佳实践

---

## 为什么需要三维度？

第一直觉建立的系统假说有三类典型偏差：
1. **目录名 ≠ 职责**：目录命名可能误导，实际代码可能散落在其他位置
2. **热点揭示真正的核心**：git 变更频率比目录结构更能反映系统的实际权重
3. **依赖方向揭示层次错误**：`import` 边的方向与假设的分层可能相反

三维度系统性覆盖这三类偏差。

---

## 维度1: Structure（结构维度）

**质疑对象**: 目录/文件组织是否与边界假设一致？

**数据来源**:
- `raw/file_tree.txt` — 目录树全貌
- `raw/ast_nodes.json` edges（`contains` 类型）— 模块包含关系

**典型质疑模式**:
```
Q: 假设 System X 的边界是 src/xxx/，但 file_tree.txt 显示 src/utils/ 下有
   多个与 xxx 业务同名的文件（如 xxx_helper.py）。
   这些文件的职责是否应归入 System X，还是独立的跨功能模块？
   证据线索: raw/file_tree.txt L{N}
   验证计划: view src/utils/xxx_helper.py 的 class 定义和 import 来源
```

**高价值结构质疑**:
- 假设的"基础设施层"目录下出现了业务命名的文件
- 某 System 的 `code_path` 是一个深层子目录，但父目录下有同层的其他模块未被归类
- 多个 System 的文件都出现在同一个 `utils/` 或 `common/` 目录（边界模糊）

---

## 维度2: Evolution（演化维度）

**质疑对象**: git 热点和耦合对是否支持假设的核心系统判断？

**数据来源**:
- `raw/git_stats.json` — `hotspots`（变更频率）+ `coupling_pairs`（co-change 对）

**典型质疑模式**:
```
Q: git_stats 显示 tasks/xxx.py 变更 21 次（high risk），
   是热点榜首，但我将其归入了次要系统。
   若它真的是次要系统，为何比假设的核心系统变更更频繁？
   证据线索: raw/git_stats.json hotspots[0]
   验证计划: view tasks/xxx.py 的类定义，确认是否承担调度/编排职责
```

**高价值演化质疑**:
- 热点 Top3 的文件中，有 ≥1 个不在假设的"核心系统"内
- 某两个文件的 `coupling_score > 0.7`，但分属假设的不同 System（暗示边界划错）
- 假设的"核心系统"在热点榜上排名靠后（该系统真的是核心吗？）

---

## 维度3: Dependency（依赖维度）

**质疑对象**: AST import 方向是否符合假设的层级关系？

**数据来源**:
- `raw/ast_nodes.json` edges（`imports` 类型）— 模块 import 关系

**典型质疑模式**:
```
Q: 假设 infrastructure/ 是底层，application/ 是上层，
   但 ast_nodes.json 中有 edge:
   {"source": "infrastructure.xxx", "target": "application.yyy", "type": "imports"}
   这是反向依赖，违反了假设的分层方向。
   证据线索: raw/ast_nodes.json edges（source 包含 infrastructure 且 target 包含 application）
   验证计划: view infrastructure/xxx.py 的 import 语句，确认是真实导入还是 TYPE_CHECKING 块
```

**高价值依赖质疑**:
- 假设的"基础设施层"模块 import 了"应用层"模块（循环依赖 / 分层错误）
- 假设为 System A 依赖 System B，但 import 边方向相反
- 某 System 有大量 imports 指向它，但自身几乎不 import 其他模块（可能是实际的入口/协调层）

---

## 质疑分级（对应 BENCHMARK 阶段验证优先级）

| 级别 | 定义 | BENCHMARK 优先级 |
|------|------|:-------:|
| 🔴 **Critical** | 假设的系统边界完全错误，`code_path` 应指向完全不同的位置 | 立即验证，验证前不得进入 EMIT |
| 🟡 **High** | 核心系统的 `code_path` 可能有误或遗漏了重要子目录 | BENCHMARK 首批验证 |
| 🔵 **Medium** | 子目录职责划分模糊，可能影响 `responsibility` 的准确性 | BENCHMARK 第二批验证 |

> **注意**：每次 OBJECT 执行中，至少应有 ≥1 个 Critical 或 High 级质疑。
> 如果所有质疑都是 Medium，说明 REASON 假说过于保守，需要更大胆地提出系统判断。

---

## 完整三维度执行检查单

执行 OBJECT 阶段时，依次过以下检查项：

**Structure（结构）**
- [ ] file_tree.txt 是否有与假设系统无法匹配的文件/目录？
- [ ] 是否有跨系统的 `utils/` 或 `common/` 目录存在模糊地带？

**Evolution（演化）**
- [ ] hotspots Top3 是否都在假设的"高重要性系统"内？
- [ ] coupling_pairs 中是否有跨你假设系统边界的强耦合对（score > 0.5）？

**Dependency（依赖）**
- [ ] 是否有违反假设分层方向的 import 边（下层 imports 上层）？
- [ ] 是否有 System 的 imports 方向与假设的"依赖者-被依赖者"关系相反？
