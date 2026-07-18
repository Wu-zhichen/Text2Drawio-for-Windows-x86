# 科研配图规范与提示词模板

## 1. 风格规格的使用顺序

1. 优先使用 `style-references/user/` 中论文或图片提取出的临时风格规格。
2. 用户目录为空且用户同意时，使用 `style-references/default/style-profile.yaml`。
3. 用户的文字要求始终高于参考素材和默认配置。
4. 只借鉴视觉语言，不复制参考图的研究内容或独特表达。

下面的 Text2CAD 类规格是当前默认值，不应覆盖用户自定义风格。

## 2. 默认 Text2CAD 类视觉语言

使用以下基础参数，并根据参考 PDF 实际观察结果微调：

| 角色 | 推荐颜色 | 用途 |
|---|---|---|
| 主流程 | `#6C63FF` | 模型、智能体、核心生成步骤 |
| 输入/警示 | `#E07A5F` | 用户输入、异常、约束失败 |
| 数据/表示 | `#56B4E9` | JSON/YAML、中间表示、日志 |
| 执行/系统 | `#2A9D8F` | 仿真器、工具、运行环境 |
| 评测/输出 | `#E9C46A` | 指标、报告、归档产物 |
| 面板背景 | `#F4F6F8` | 分区、泳道、注释框 |
| 描边/正文 | `#263238` | 轮廓、连接线、标签 |

版式规则：

- 使用白色画布、浅灰面板、1—2 px 深灰描边和小圆角。
- 用 12 栏网格或等距卡片组织结构；同级模块等宽或视觉等重。
- 主箭头从左到右；反馈箭头走外侧回路，不穿过主流程。
- 连接线尽量只使用水平和垂直线段；必要转折保持 90°。
- 每个标签控制在 1—4 个词；说明文字控制在一行或两行。
- 同一张图只使用一种图标语言：线性图标或极简等距图标，不混用照片。
- 不使用重阴影、玻璃拟态、霓虹、强渐变或装饰性背景纹理。

## 3. 通用生成提示词

将方括号内容替换为具体图结构：

```text
Create a publication-quality scientific systems diagram using the selected visual style profile below. Use the style only; do not copy any original figure or paper content.

Selected style source: [USER REFERENCE FILES / CONFIRMED DEFAULT PROFILE].
Style profile: [CANVAS, LAYOUT, SHAPES, CONNECTORS, TYPOGRAPHY, PALETTE, ICON LANGUAGE, INFORMATION DENSITY].

Canvas: landscape [3:2 / 16:9], high resolution, pure white background.
Visual system: [EXACT RULES EXTRACTED FROM THE SELECTED STYLE].

Subject: [ONE-SENTENCE PURPOSE].
Layout: [LEFT-TO-RIGHT MAIN FLOW OR LAYERED ARCHITECTURE].
Modules:
1. [MODULE + SUBELEMENTS]
2. [MODULE + SUBELEMENTS]
3. [MODULE + SUBELEMENTS]
4. [MODULE + SUBELEMENTS]
Feedback path: [EXACT RETURN PATH, IF ANY].
Text labels: [EXACT SHORT LABEL LIST].

Hard layout constraints:
- Use orthogonal connectors with dedicated routing lanes.
- No arrow or line may cross text, icons, cards, or another arrow.
- Keep generous spacing between modules and equal outer margins.
- Keep every label fully inside its box; no clipping or tiny text.
- Make the hierarchy readable at Word-document size.
- Do not include a figure number, caption, watermark, page frame, logo, fabricated metric, or unsupported result.
- Flat vector-infographic appearance, not a poster, not photorealistic, not 3D.
```

## 4. 局部编辑提示词

```text
Edit only [PRECISE REGION]. Preserve all other modules, colors, spacing, labels, and line routing exactly.

Fix these issues:
1. [ARROW/TEXT/OVERLAP ISSUE]
2. [SPELLING OR LABEL ISSUE]
3. [MISSING DETAIL]

Route the corrected connector through empty whitespace using orthogonal segments. Do not move unrelated cards. Do not add new metrics, claims, captions, or decorative elements.
```

## 5. 九类图的结构建议

### 场景原理图

分为海面/水体/海床三层；展示浮标、网关、传感器、AUV、声学链路、业务流和物理影响因素。把环境参数放入侧边信息卡，不让声线路径穿过说明文字。

### 中间表示图

按“多层自然语言—字段抽取—结构化表示—模板实例”组织；字段组覆盖拓扑、协议、信道、业务、移动、能耗、随机种子和指标。

### 约束校验图

按“能力扫描—知识库—规则验证—参数补全—可执行计划”组织；把不支持协议分支以珊瑚色引向拒绝/修复，不直接进入执行器。

### 参数追溯图

用来源标签连接“用户显式值、默认值、知识库值、修复值”与最终配置；加入审计日志和版本信息，但不显示真实敏感值。

### 总体架构图

采用四层：交互层、智能编排层、仿真执行层、数据与报告层；在右侧设置安全边界和能力注册表。

### 智能体闭环图

主流程为“理解—规划—校验—生成—运行—解析—评价”；反馈线从失败解析绕外侧返回修复节点，并标注有限重试。

### 分级评测图

左侧展示简单/中等/复杂三级任务，右侧展示语义正确性、可执行性、结果完整性和鲁棒性。结果位置使用 `Pending`、`Not Reported` 或破折号。

### 指标处理图

按“事件日志—字段解析—流级聚合—指标公式—缺失检测—图表/报告”组织；明确缺失数据不推断、不补造。

### 软件与产物图

展示界面、工作流模块、执行环境、配置/日志/图表/报告目录，以及可复现实验所需的种子、版本和命令记录。

## 6. 视觉验收清单

- 放大到 100% 后逐字检查全部标签。
- 缩小至 Word 中的实际显示尺寸后仍能分辨一级模块和主箭头。
- 任何两条连接线不得相交；任何箭头不得压住卡片边框上的文字。
- 反馈回路与主流程使用不同颜色或线型，并有明确起点和终点。
- 同级模块的圆角、描边、内边距和标题位置保持一致。
- 所有性能字段必须来自正文或真实实验；否则显示空值状态。
