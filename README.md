# fde-comms · v0.1.0

FDE Skill 系列的沟通篇：准备与复盘与人的关键对话。首版只含两个模式——**访谈**（会前提纲、会后纪要与复述、种子问题）和**上行**（高管一页纸、坏消息稿）。预期管理、给总部/研发的需求翻译、集成商与组织阻力计划在后续版本，见 [ROADMAP.md](ROADMAP.md)。

与系列其他 Skill 的分工：fde-ramp 管见客户前的行业认知；fde-problem-framing 管把需求变成有证据的问题定义；本 Skill 管信息怎样从人那里拿出来、结论怎样送上去。衔接见 [handoff.md](references/handoff.md)。没装另外两个也可独立运行。

## FDE Skill 系列

各 Skill 独立运行，通过手动读取的产物衔接，不互相依赖安装。典型顺序：ramp → problem-framing → route-selection → knowledge-base（场景含文档检索时）→ demo → pilot，comms 贯穿各阶段。

| Skill | 管什么 | 结论词 |
|---|---|---|
| [fde-ramp](https://github.com/meiluosi/fde-ramp) | 见客户前搭起行业基本盘，拿图去被一线改 | 自检分数 |
| [fde-problem-framing](https://github.com/meiluosi/fde-problem-framing) | 把需求变成有证据的业务问题，比较 AI 与非 AI | Proceed / Investigate / Non-AI / Stop-Defer |
| [fde-route-selection](https://github.com/meiluosi/fde-route-selection) | 业务问题定义之后，先过滤合规与部署等硬约束，再选适配路线，最后用客户样本比选模型 | 见该仓库 |
| [fde-knowledge-base](https://github.com/meiluosi/fde-knowledge-base) | 路线含文档检索（RAG）时，判断知识够不够、怎么治、怎么评、质量卡在哪 | Proceed / Investigate / Pivot / Stop-Defer |
| [fde-comms](https://github.com/meiluosi/fde-comms) | 与人的关键沟通：访谈、向上汇报、坏消息 | 无（产出文稿） |
| [fde-demo](https://github.com/meiluosi/fde-demo) | 设计并复盘一次客户 Demo，换验证与信任 | Proceed / Iterate / Pivot / Stop-Defer |
| [fde-pilot](https://github.com/meiluosi/fde-pilot) | 把 Demo 通过的方案做成可检验的试点并判定成效 | Proceed / Iterate / Pivot / Stop-Defer |

跨 Skill 引用时加前缀保留原编号（`ramp:S01`、`framing:V2`、`kb:Q01`、`demo:L3`、`pilot:M2`）；同名结论词含义随阶段不同，引用时写 `framing:Proceed`、`demo:Proceed`。编号、结论词、边界与回写规则的完整约定见 [fde-demo 的 references/series.md](https://github.com/meiluosi/fde-demo/blob/main/references/series.md)。

## 安装
把整个 `fde-comms` 文件夹（含 references/、templates/）放入宿主 skills 目录，开新会话。

## 可直接说
- “用 $fde-comms 准备明天对理赔一线的访谈，先判断这场会的主要目的。”
- “这是我的访谈笔记，整理成待确认纪要，带复述句。”
- “把这个项目状态写成给 CEO 的一页纸。”
- “第三周发现数据问题，帮我写给老板的坏消息稿。”

## 内容
- SKILL.md：入口与模式路由
- references/：核心、访谈、上行、衔接
- templates/：提纲、纪要、一页汇报、坏消息
- tests/：行为回归协议与包结构测试
- DEVELOPMENT.md：来源材料与方法修订

## 验证
```sh
python3 -m unittest discover -s tests -v
```
结构测试只检查链接、前置信息与模板存在；它不能证明模型遵守流程，更不能证明真实访谈有效。行为测试见 tests/behavioral-cases.md，尚未实际运行。
