# 衡练 AI 助手（HengLian Agent）

> **一句话介绍**：面向规律训练的健身爱好者与运动入门者的**自然语言运动健康 Agent**——用户用一句话描述训练与身体状态，Agent 通过 LLM Tool Calling 调用 10 个本地业务工具（训练负荷评估、互补训练规划、疲劳模型、Mifflin-St Jeor 饮食规划、1RM 估算、What-if 模拟等），给出可解释的训练/恢复/营养建议，并能按 Skill 规范生成 Markdown 周报写入 `output/` 目录。
>
> **选题路径**：**路径 B**（在业务应用中加入 Agent 能力），同时达到路径 A 最低配置 7 项中的 6 项（模型调用 ✅ / 自定义工具 10 个 ✅ / Agent Skill ✅ / 交互界面 ✅ / 多轮对话与会话保存 ✅ / 文件产出物 ✅，仅未用第三方 Agent 框架——工具调用循环为自主实现，便于口头解释原理）。

## 一、解决什么问题、用户是谁

- **用户**：每周训练 3–5 次的大学生健身爱好者 / 运动入门者，没有请私教，训练后不知道练得够不够、该恢复多久、怎么吃、明天练什么。
- **痛点**：专业训练知识（负荷量化、疲劳管理、营养配比）散落在教练脑子和付费 App 里；普通问答型 AI 只能"凭空说话"，算不出基于你数据的准确数值。
- **方案**：把本人 HarmonyOS 端侧项目「衡练 SportHealthAgent」的确定性规则算法（负荷公式、疲劳加权模型、双公式 1RM、Mifflin-St Jeor 营养计算等）封装为**本地工具**，由 LLM Agent 用自然语言驱动——既有对话的灵活性，又有规则引擎的精确性。

## 二、技术栈

| 层 | 技术 | 说明 |
| --- | --- | --- |
| 模型 | 阿里百炼 通义千问 `qwen-plus`（OpenAI 兼容接口） | 可通过环境变量切换 Ollama / ModelScope 等任意兼容端点 |
| Agent | **自研 Tool Calling 循环**（`agent/core.py`，基于 openai SDK） | LLM → 工具调用 → 结果回传 → 循环，最多 8 轮防失控 |
| 工具 | 10 个本地业务工具（`agent/tools/`） | 全部为纯 Python 函数，含 JSON Schema 注册表，失败可解释 |
| Skill | `skills/weekly-report/SKILL.md` | 符合 Agent Skills 规范：name/description 元数据 + 步骤 + 模板 |
| 界面 | Streamlit | 多轮对话 + **执行过程面板**（可视化每次工具调用与返回） + 会话保存/加载 |
| 测试 | pytest，14 个用例 | 覆盖公式边界值、三档阈值、参数校验、写入沙箱 |

### 工具清单（10 个）

| 工具 | 功能 | 来源 |
| --- | --- | --- |
| `evaluate_training` | 负荷估算公式 + 三档评估（超标/正常/偏低）+ 恢复时长 | 移植自鸿蒙项目 `TrainingEvaluator` |
| `plan_next_workout` | 互补训练规划（12 类运动映射表，负荷≥80 强制主动恢复） | 移植自 `NextWorkoutPlanner` |
| `compute_fatigue` | 7 天负荷加权疲劳指数（0–100）+ 恢复系数 | 移植自 `FatigueModel` |
| `plan_daily_diet` | Mifflin-St Jeor BMR/TDEE + 增肌减脂修正 + 双碳水方案 | 移植自 `DietPlanner.dailyPlan` |
| `recovery_meal_plan` | 运动后恢复餐宏量配比（超标时热量下调 60%） | 移植自 `DietPlanner.plan` |
| `estimate_one_rep_max` | Epley / Brzycki 双公式 1RM 估算 | 移植自 `StrengthCalculator` |
| `effective_sets` | RPE/RIR 双轨有效组数与容量统计 | 移植自 `StrengthCalculator` |
| `what_if_simulate` | 4/8 周体重与负荷推算（7700 kcal ≈ 1kg） | 移植自 `WhatIfSimulator` |
| `read_skill` | 读取 SKILL.md（白名单校验） | 本项目新增 |
| `write_weekly_report` | 周报写入 `output/`（**文件名清洗 + 目录白名单 = 权限隔离**） | 本项目新增 |

## 三、环境要求

- **Python 3.9+**（开发环境：Windows 11 + Python 3.13）
- 网络可访问阿里百炼 API（或本地 Ollama）

## 四、安装与启动（Windows 命令）

```bat
:: 1. 进入项目目录
cd /d D:\henglian-agent

:: 2. 创建虚拟环境并安装依赖
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt

:: 3. 配置密钥（复制模板后编辑，填入你的 DASHSCOPE_API_KEY）
copy .env.example .env

:: 4. 启动
.venv\Scripts\streamlit run app.py
```

也可直接双击 `run.bat` 一键完成上述步骤。

运行测试：

```bat
.venv\Scripts\python -m pytest tests/ -v
```

> **密钥管理**：`.env` 已被 `.gitignore` 排除，仓库中只有 `.env.example` 模板；演示时展示 `.env.example`，绝不展示 `.env` 真值。

## 五、推荐演示话术

1. **多工具链式调用**：「我今天练了 90 分钟力量，平均心率 125，消耗大概 500 千卡，帮我评估一下，安排明天的训练，再告诉我今天该怎么吃」
   → 观察 `evaluate_training` → `plan_next_workout` → `recovery_meal_plan` 三个工具依次被调用。
2. **个性化饮食规划**：「我男，70 公斤，175 厘米，25 岁，想减脂，平时久坐，帮我算每天的饮食安排」→ `plan_daily_diet`。
3. **力量科学**：「我卧推 80 公斤做了 5 次，我的极限大概是多少？」→ `estimate_one_rep_max` 双公式结果。
4. **Skill + 产出物 + 写入确认**：「用示例数据帮我生成一份周训练报告」→ Agent 先 `read_skill` 读取周报技能，再调用 `compute_fatigue` 等计算，展示全文并**征得同意后**才调用 `write_weekly_report` 写入 `output/`。
5. **What-if 模拟**：「我现在 75 公斤，如果每周练 4 次、每天少吃 500 千卡，8 周后体重大概多少？」→ `what_if_simulate`。

## 六、与课堂实验的关系（增量说明）

| 课堂实验 | 本项目用了什么 | 自己加了什么（增量） |
| --- | --- | --- |
| demo_1 | Streamlit 界面 | 从单轮页面改为带执行过程面板的多轮 Agent 对话；会话 JSON 落盘 |
| demo_2 | OpenAI 兼容接口、Tool Calling、流式思路 | 工具从演示用天气/计算器换成 **10 个自研运动科学工具**；自研多轮工具调用循环（含异常兜底、轮次上限、失败可解释） |
| demo_3/4 | 阿里百炼调用、密钥与环境变量管理 | 同一套 `.env` 配置支持切换任意 OpenAI 兼容端点 |
| demo_5 | Agent、Skill 概念 | 无框架依赖的极简实现；Skill 采用规范 frontmatter 结构；**权限隔离**（Agent 只能写 `output/`，文件名清洗防路径逃逸，有单元测试证明） |

**核心增量一句话**：业务算法全部来自本人的 HarmonyOS 端侧项目「衡练 SportHealthAgent」（ArkTS 规则引擎，独立开发），本项目将其移植为 Python 工具并用 LLM 串联成自然语言驱动的业务闭环——不是 demo_5 换皮。

## 七、目录结构

```
henglian-agent/
├── app.py                    # Streamlit 界面（对话 + 执行过程面板 + 会话管理）
├── run.bat                   # Windows 一键启动
├── agent/
│   ├── core.py               # 自研 Tool Calling 循环 + 系统提示词
│   └── tools/
│       ├── registry.py       # 工具 JSON Schema 注册表与 dispatch 路由
│       ├── training.py       # 训练评估/互补规划/疲劳模型
│       ├── diet.py           # Mifflin-St Jeor 饮食规划
│       ├── strength.py       # 1RM 双公式/有效组数
│       ├── whatif.py         # What-if 模拟
│       └── skills.py         # Skill 读取 + 沙箱化文件写入
├── skills/weekly-report/SKILL.md   # Agent Skill（周报生成规范）
├── output/                   # 周报产出物目录（Agent 唯一可写目录）
├── sessions/                 # 保存的会话 JSON
├── tests/test_tools.py       # 14 个单元测试
├── slides/index.html         # 汇报用 HTML 幻灯片（自包含，双击打开）
├── .env.example              # 环境变量模板（不含真实密钥）
└── requirements.txt
```

## 八、思政与合规说明

- **健康边界**：所有饮食/营养建议由工具与系统提示词强制附带「以上为日常营养参考，非医疗诊断；如有基础疾病请遵医嘱」；伤病问题只建议休息与就医，不做诊断。
- **隐私**：不采集任何真实个人信息；周报演示使用 SKILL.md 中声明的**虚构样例数据**；会话仅存本地 `sessions/`。
- **权限隔离**：Agent 写文件能力被限制在 `output/` 目录内（白名单 + 文件名清洗，`tests/test_tools.py::test_write_sandbox` 验证路径逃逸被拦截）。
- **学术诚信**：工具算法移植自本人另一独立项目（鸿蒙端「衡练」），课堂 demo 仅作为能力基线参考，已在 README 与幻灯片中如实说明。

## 九、不足与后续改进

1. 未接入真实运动手环/Health Kit 数据源（当前靠自然语言口述或示例数据）——后续可接华为 Health Kit REST API 作为第 11 个工具。
2. 工具调用过程当前为"按轮展示"，未做 token 级流式输出（openai SDK stream + 前端逐字渲染）。
3. 暂未 Docker 化；可用一份 Dockerfile + streamlit 基础镜像补齐一键部署。
4. 长期记忆仅靠会话 JSON，可引入用户画像持久化（性别/体重/目标）减少重复输入。
