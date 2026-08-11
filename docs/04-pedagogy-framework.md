# 教学框架

## 目标

本阶段把 `Teach, don't solve` 从一句理念转化为可执行、可测试的软件规则。
核心实现位于 `backend/app/ai/pedagogy.py`，共享类型位于 `backend/app/ai/types.py`。

教学算法是纯函数：它不读取数据库、环境变量或网络，不调用语言模型。相同输入总会得到
相同输出，因此可以用单元测试复算、审查和回归。

## 三类教学状态

每个学科维度分别记录：

1. `difficulty`：当前问题对该维度的难度，范围为 1 至 5。
2. `effective_level`：学生在该维度的当前有效能力，范围为 1.0 至 5.0。
3. `hint_level`：当前允许提供多少帮助，范围为 1 至 5。

编程与数学必须独立保存。例如，学生可能理解抛体运动公式，却不熟悉 Python 循环；
也可能会写程序，但不理解数值方法。把两者合成一个分数会掩盖这种差异。

`StudentState` 使用冻结的数据类。更新状态时创建新值，而不是在未知位置原地修改，
这样更容易追踪一次对话前后发生了什么。

## 提示等级

| 等级 | 名称 | 允许的帮助 |
| --- | --- | --- |
| 1 | Socratic | 提出一个针对性问题，不给公式、代码或完整步骤 |
| 2 | Conceptual | 解释相关概念，不给代码或完整步骤 |
| 3 | Structural | 给出结构化策略，不给完整实现 |
| 4 | Concrete | 给局部示例，保留关键整合工作 |
| 5 | Full solution | 给完整解法、解释和边界情况 |

等级映射由代码控制，不能完全交给 LLM 自行决定。LLM 输出具有随机性，也可能服从学生
“直接给答案”的请求；后端算法提供了可审计的教学上限。

## 新问题公式

`compute_hint_levels(..., same_problem=False)` 使用：

```text
gap = difficulty - round(effective_level)
hint = clamp(1 + gap, 1, 4)
```

首次回答最高只能到等级 4。即使问题远超学生能力，也应先保留一个需要学生完成的关键步骤；
等级 5 留给学生在同一问题上经过多轮求助后使用。

示例：学生编程能力为 2，问题编程难度为 4：

```text
gap = 4 - round(2) = 2
hint = clamp(1 + 2, 1, 4) = 3
```

实现当前使用 Python 的 `round`。如果未来能力模型大量产生 `.5`，需要明确评估 Python
银行家舍入是否符合教学意图，而不是在没有数据时随意更换规则。

## 同一问题公式

`compute_hint_levels(..., same_problem=True)` 不重新根据难度跳级，而是在两个维度各自的
已有提示等级上增加一级：

```text
hint = min(5, previous_hint + 1)
```

如果编程提示为 2、数学提示为 4，下一轮分别变为 3 和 5。两个结果互不覆盖。

## 能力更新

`update_effective_level` 使用提示加权的指数移动平均。输入首先被限制到安全范围：

```text
safe_current = clamp(current_level, 1, 5)
safe_difficulty = clamp(difficulty, 1, 5)
demonstrated_level = safe_difficulty * (6 - final_hint_level) / 5
learning_rate = 0.2 * min(1, safe_difficulty / safe_current)
updated = safe_current * (1 - learning_rate) + demonstrated_level * learning_rate
result = clamp(updated, 1, 5)
```

提示越少，`demonstrated_level` 越高；简单题对高水平学生的影响被降低；`0.2` 的基础学习率
防止一次答题让长期画像剧烈变化。

数值案例：当前能力 2、难度 4、最终提示等级 2：

```text
demonstrated_level = 4 * (6 - 2) / 5 = 3.2
learning_rate = 0.2
updated = 2 * 0.8 + 3.2 * 0.2 = 2.24
```

该公式是第一版可测试假设，不是已经证明有效的教育测量模型。后续需要通过用户试验校准。

## 元数据边界

`coerce_pedagogy_metadata` 接收分类器或未来 LLM 产生的结构化数据，并在进入教学算法前检查：

- 四个必填字段全部存在。
- `same_problem` 和 `is_elaboration` 必须是精确布尔类型。
- 两个难度必须是整数；由于 Python 中 `bool` 是 `int` 的子类，需要显式拒绝布尔值。
- 难度被限制在 1 至 5。
- 没有历史对话时，不能把首条消息判为同一问题或补充说明。
- `same_problem=False` 时，`is_elaboration` 必须降级为 `False`。

非法结构抛出 `ValueError`，可安全修正的范围或历史冲突采用确定性降级。

## 失败边界

- 模型分类失败：不让原始字典直接进入业务算法，应在应用边界返回错误或采用保守默认值。
- 缺少历史：强制视为新问题，首次提示不达到等级 5。
- 不确定是否同一问题：采用较保守等级，不直接泄露完整答案。
- 输入超出范围：能力与难度被限制到 1 至 5。
- 模型或网络失败：不得修改已保存的学生能力状态，也不得显示虚假成功。

## 测试证据

`backend/tests/test_pedagogy.py` 覆盖：

- 类型范围和不可变状态。
- 新问题的五组难度差案例。
- 编程与数学输入不同的独立计算。
- 同一问题的独立逐级提示。
- EMA 数值和输出边界。
- 元数据合法、缺失、错误类型、布尔整数陷阱和历史降级。

运行：

```bash
.venv/bin/python -m pytest backend/tests/test_pedagogy.py -v
```
