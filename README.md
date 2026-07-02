### resume-tailor — 简历定制 agent

一个"只改你已有的真实经历、绝不串台、每条可追溯"的简历定制工具。给一段 JD，把你真实做过的事重新组织、措辞、命中关键词，产出一份定制简历。**通用工具**——领域知识靠可替换的 archetype preset（默认 `ai_builder`），换个职业就换个 yaml。

两条路：① **文本管线**（结构化档案 → 定制文本 + 追溯报告）；② **HTML 编辑器**（contenteditable 活文档 + Playwright 出 A4 PDF，WYSIWYG）。

### 现在能干什么

- **Phase 0 · 文本管线（done）**：YAML 档案进、定制文本出。fact-locker 锁事实 → JD 分析 → 模块选择 → scope-bound 改写 → verifier 审核 + 自动修复闭环。每条 bullet 都挂回真实经历原话。
- **Phase 1 · 渲染（done）**：contenteditable HTML 活文档（浏览器打开点哪改哪，Cmd+P 直接导 PDF）+ `html2pdf.py`（Playwright 无头 Chromium 出 A4 PDF，Maple Mono 字体 base64 内联）。屏幕视图就是 A4 真实尺寸（WYSIWYG），所见即所印。
- **对话式 agent（done）**：三个模块落地——提问式挖掘 `miner.py`（从 JD 视角追问补材料）、narrative synthesis `narrative.py`（推断职业主线 + heavy/light/drop 取舍）、面试官视角 stress-test `stress_test.py`（debate 求逻辑严密，抓过度拔高 / 概念偷换 / 因果跳跃）。`agent.py` 串成"理解全局 → 再隔离动笔"两段式对话流。

### 跑起来

用运行者自己的 LLM API（读环境变量，provider 无关）。

文本管线：

```bash
python main.py sample_data/example_profile.yaml --jd sample_data/example_jd.txt
# 也可：--archetype ai_builder --out resume.txt
```

输出两块：定制简历 + 追溯/审核报告（每条 bullet 挂来源事实、违规数）。

HTML 编辑 → PDF：

1. 把定制结果（或手写）填进一份 HTML（contenteditable，浏览器打开即改）。
2. 命令行出锁定 PDF（headless、字体内联、可移植）：

```bash
python html2pdf.py [input.html] [output.pdf]
```

对话式 agent（挖掘 + 主线确认 + 改写 + 压测）：

```bash
python agent.py sample_data/example_profile.yaml --jd sample_data/example_jd.txt
# 非交互（自动采纳推断主线，测试 / CI 用）：加 --auto
```

### 依赖

`anthropic`、`openai`、`pydantic`、`pyyaml`、`playwright`、`json-repair`。

```bash
uv pip install --python <你的 python> anthropic openai pydantic pyyaml playwright json-repair
python -m playwright install chromium
```

### 输入：简历档案 YAML

```yaml
bg_type: product          # product | tech，影响模块优先级
jd: |
  岗位/职责/要求……（也可用 --jd 覆盖）
experiences:
  - id: exp0              # 可省略，自动 exp0/exp1…
    type: work            # work | practice | community
    role: AI 产品经理
    org: 某公司
    dates: 2023 至今
    original_text: |
      你这段经历的原话。越具体越好（带数字、带产出）。
```

### 怎么保证不编造、不串台（技术心脏）

流水线五个工位：

1. **采集即隔离（fact-locker）**：每条经历一进来，先把原文抽成原子事实，锁进自己的容器（带 id）。从这一刻起，这段经历的事实就和别段隔离。
2. **JD 分析**：抽必须技能/关键词/职责 + 判断岗位原型。
3. **模块选择**：按 archetype preset + 岗类命中率选模块、写定位。
4. **scope-bound 改写**：逐条经历改写，**只能引用自己容器里的事实**，每条 bullet 标注依据的原子事实。
5. **审核员（verifier）+ 自动修复**：独立复查每条 bullet，抓"跨项目腾挪"（claim 来自别条经历）和"凭空编造"。抓到就把违规反馈给改写器重写、再审，违规归零为止。

所以你看到的每条 bullet，都能在追溯栏里挂回某条真实经历的原话。

### 项目结构

```
resume-tailor/
  config.py           读 env、provider 无关、模型名 sanitize（剥 [1m] 这类 router 标记）
  llm.py              LLM 客户端，结构化输出（strict-JSON + pydantic + json-repair + 重试 + 内容安全重试）
  models.py           数据模型（Experience / Fact / JDAnalysis / RewriteResult / Verdict）
  intake.py           工位0：读档案 YAML
  fact_locker.py      工位2：抽原子事实、采集即隔离
  jd_analyzer.py      工位1：JD 分析 + 岗位原型
  module_selector.py  工位3a：按 preset 选模块
  tailor.py           工位3b：scope-bound 改写 + 自动修复
  verifier.py         工位3c：抓腾挪 / 编造
  pipeline.py         编排 + 组装简历文本 / 报告（含 stress-test）
  main.py             CLI（文本管线）
  agent.py            对话式 agent CLI（理解全局 → 再隔离动笔）
  miner.py            提问式挖掘：JD 视角追问补材料
  narrative.py        narrative synthesis：推断主线 + heavy/light/drop 取舍
  stress_test.py      面试官视角 stress-test：debate 求逻辑严密
  html2pdf.py         HTML → PDF 渲染器（Playwright + base64 内联 Maple Mono）
  archetypes/
    ai_builder.yaml   AI builder preset（模块目录 / 命中率 / 选模块指引）
  sample_data/        匿名样例（example_*）；真实简历已 gitignore，不上传
```

> `render_pdf.py` 是早期的"dict → HTML → PDF"生成器，内嵌了真实简历全文且已被 `html2pdf.py` 取代，暂不上传（见 `.gitignore`）。

### 换 LLM / 换 provider

工具不绑死厂商。优先读 anthropic 兼容 env（`ANTHROPIC_AUTH_TOKEN` / `ANTHROPIC_BASE_URL` / `ANTHROPIC_MODEL`），没有就读 openai 兼容 env（`OPENAI_API_KEY` / `OPENAI_BASE_URL` / `OPENAI_MODEL`）。模型名带 `[1m]` 这类 router 标记会自动剥掉（智谱 BigModel 的 anthropic 端点实测可用）。

### 开发进展小结

- **Phase 0（done）**：文本管线 + 防幻觉架构（scope-bound + verifier + fact-locker + 自动修复闭环）。在真实简历 11 段经历上压测：0 跨项目腾挪、0 凭空编造、0 空产出。
- **Phase 1（done）**：HTML contenteditable 活文档 + `html2pdf.py` + WYSIWYG A4 渲染。解决了 headless Chromium 不加载系统字体（file:// / page.route 均无效，最终用 base64 data: URL 内联 Regular+Italic 两字重）和"屏幕宽度 ≠ 打印宽度"（屏幕 `.page` 设成真 A4 尺寸，所见即所印）两个坑。
- **对话式 agent（done）**：miner + narrative + stress-test 三模块落地，`agent.py` 串成"理解全局（提问式挖掘 + 主线确认）→ 再隔离动笔（按 heavy/light/drop 改写 + 审核 + 压测）"。example 数据验证：miner 生成 JD 针对性追问、narrative 推断主线 + 取舍、stress-test 抓出过度拔高 / 概念偷换 / 因果跳跃等真问题。
- **踩过并修好的坑**：GLM 偶发内容安全拦截 `[1301]`（`chat` 里对内容过滤类错误重试）、偶发坏 JSON（换 json-repair + schema 感知修复兜底）、改写偶发空 bullet（pipeline 加空值保护）、模型名带 router 标记被 API 拒（config 里 sanitize）。
- **核心设计思想**：两层模型——理解层（全真深度，含负面）供职业主线 / 面试 prep / 压力面试；简历表层从面试官提问视角出发，把每行写成经得起追问的论点。原则：**每一行简历都是未来的一个面试问题**。

### 之后计划

短期（打磨对话式 agent）：

- 挖掘到的回答目前作为独立"挖掘补全"经历入库；后续智能归并到最相关的原有经历。
- narrative 的 heavy/light/drop 目前只驱动 bullet 数量与取舍；后续让定位也参与 module_selector 的模块取舍。
- 压力测试发现的"defend 不住"claim，后续接回改写器自动降措辞（闭环，类似 verifier 的自动修复）。

中期：

- **Phase 2**：排版优先的自适应（超页先压行距/字号/页边距，再砍内容）。
- **Phase 3**：多 JD 批量分类 + 差异化输出。
- **多模板 UI**：把 CSS / 版式抽成可切换 theme（单栏 / 双栏 / 极简）；"好工程师项目结构"（项目描述 / 技术栈 / 难点 / 方案 / 成果）作为其中一种 bullet 范式。

长期：

- 从"生成器"重做成**对话式 agent**——"理解全局 → 再隔离动笔"三步对话系统。最终形态目标：一个 Claude Code skill。

### 隐私

`sample_data/` 下真实简历（`syq_*`、`deepseek_jd.txt`）和个人档案均已 `.gitignore`，仓库只含通用代码 + 匿名样例。
