# Text2Draw.io Desktop Agent for Windows

[中文](#中文说明) · [English](#english)

Text2Draw.io 是面向 Windows 10/11 的便携式 draw.io AI 绘图助手。它能够根据自然语言和常见办公文件生成可编辑的 draw.io 矢量图，并通过图形化管理器完成 API、语言、插件和本地服务配置。

Text2Draw.io is a portable AI diagram assistant for Windows 10/11. It converts natural-language requests and common office documents into editable draw.io vector diagrams and includes a graphical setup manager.

---

## 中文说明

### 功能亮点

- 根据自然语言生成流程图、架构图、知识图谱、论文总结图和数据分析图。
- 支持 PDF、Excel、CSV、Word、PowerPoint、Markdown、JSON、XML 等参考文件。
- 输出为原生 draw.io 节点、文字和正交连接线，可继续编辑、撤销和重新排版。
- 自动增强简短提示词，并使用确定性布局控制对齐、间距、对称性与避障排线。
- 内置 6 种布局配色选项。
- 模型选择位于 draw.io 插件内，可随每次生成请求即时切换。
- 管理器提供全局中英文设置，同时控制 draw.io 与 Text2Draw.io 插件语言。
- 可选调用 OpenAI 图片 API，在主要节点内部加入 AI 小配图。
- 便携包已内置 draw.io、Python 和运行依赖，无需安装 Node.js、npm 或 Python。

### 系统要求

- Windows 10 或 Windows 11
- 64 位 x86 处理器（x64）
- 建议至少 8 GB 内存
- 可访问所配置 AI API 的网络连接
- DeepSeek API Key
- OpenAI API Key 为可选项，仅用于节点小配图

当前便携版不支持 Windows on ARM 和 32 位 Windows。

### 下载与安装

1. 在 GitHub 仓库右侧打开 **Releases**。
2. 下载 `Text2Drawio-for-Windows-x64.zip`。
3. 右键 ZIP 并选择“全部解压”。不要直接在压缩包窗口中运行。
4. 保持解压后的文件夹结构不变。
5. 双击顶层的 `开始使用 Text2Drawio.cmd`。

也可以直接打开：

```text
Text2Drawio Manager\Text2Drawio Manager.exe
```

### Windows SmartScreen 提示

当前分享版可能没有商业代码签名。首次启动时，Windows 可能显示“Windows 已保护你的电脑”。确认下载来源和 Release 校验值可信后：

1. 点击“更多信息”。
2. 检查应用名称和发布来源。
3. 点击“仍要运行”。

这类提示不代表运行依赖缺失。不要对来源不明的压缩包执行上述操作。

### 首次配置

在 Text2Draw.io 管理器中依次完成：

1. 填写自己的 DeepSeek API Key。
2. 选择全局语言：`简体中文` 或 `English`。
3. 点击“保存配置”，再点击“测试连接”。
4. 如需节点 AI 小配图，在“AI 配置”中填写 OpenAI API Key；这是可选项。
5. 点击“一键安装”安装插件。
6. 点击“启动并打开 draw.io”。

以后使用时，从 `开始使用 Text2Drawio.cmd` 或管理器启动即可。

### 语言与模型

- **全局语言**：在管理器中保存语言后，完全关闭 draw.io，再通过管理器重新打开。该设置会同时应用到 draw.io 编辑器和 Text2Draw.io 插件。
- **生成模型**：管理器只负责 API 配置，不固定模型。请在 draw.io 左侧插件输入区下方实时选择 DeepSeek 模型；下一次生成会直接使用新选择，无需重启服务。

### 生成第一张图

1. 在 draw.io 左侧找到 `Text2Draw.io Agent` 面板。
2. 输入要求，例如：

   > 生成一个电商订单处理流程，包含库存校验、支付、风控、仓库拣货、物流发货、签收和退款异常分支。

3. 选择模型和布局配色模板。
4. 点击生成按钮。
5. 检查结构摘要后点击“插入画布”。
6. 插入后的节点、文字、图标和连接线都可以分别选择和编辑。

### 从本地文件生成

点击插件输入框旁的附件按钮，选择文件，再输入要求。例如：

> 根据这份 Excel 生成季度经营分析图，突出收入、成本、毛利率、客户增长、渠道占比和异常指标。

支持的常见格式：

- PDF
- XLSX、XLSM、XLS、CSV、TSV
- DOCX
- PPTX
- TXT、Markdown
- JSON、XML

默认一次最多选择 5 个文件，单个文件最大 15 MB。扫描版 PDF 需要预先执行 OCR，加密 PDF 需要先解密。

### 节点 AI 小配图

1. 在管理器“AI 配置”中保存 OpenAI API Key。
2. 停止并重新启动本地服务。
3. 在插件“高级选项”中勾选“为主要节点生成 AI 小配图”。

小配图仅作为节点内部元素。未配置图片 API 或生成失败时，系统会退回纯矢量节点，不影响主要生成流程。

### 便携包目录

```text
Text2Drawio 1.1.0 Windows x64\
├─ 开始使用 Text2Drawio.cmd
├─ 验证Windows运行时.cmd
├─ Text2Drawio Manager\
├─ Text2Drawio draw.io\
├─ agent-server\
├─ desktop-plugin\
└─ runtime\python\
```

不要单独移动管理器或 draw.io 可执行文件；管理器需要通过相对路径找到内置服务和运行时。

### 配置与隐私

配置和日志保存在当前 Windows 用户目录：

```text
%APPDATA%\Text2Drawio\.env
%APPDATA%\Text2Drawio\service.log
%APPDATA%\Text2Drawio\drawio.log
```

- API Key 不会写入 `.drawio` 文件。
- 插件不会直接读取 API Key。
- 本地 Agent Server 只监听 `127.0.0.1:8765`。
- 参考文件先由本地服务解析。
- 提示词与提取出的参考内容会按生成需要发送给用户配置的 AI API。
- 请勿处理无权上传或包含高度敏感信息的文件。

### 故障排查

#### 左侧没有 Text2Draw.io 插件

返回管理器点击“一键安装”，关闭全部 draw.io 窗口，然后通过管理器重新启动定制 draw.io。不要从电脑上另一套普通 draw.io 快捷方式启动。

#### 窗口无法正常关闭

请确认使用的是最新 Release 中的 1.1.0 版本，并且完整解压后运行。不要把新版管理器复制到旧版目录中混合使用。

#### 界面语言没有变化

保存语言设置后，需要彻底关闭 draw.io 进程再重新打开。管理器中保存的语言不会让已经运行的编辑器即时切换完整界面。

#### 显示“服务不可用”

在管理器中点击“启动本地服务”。若仍失败，检查旧版服务是否占用 `127.0.0.1:8765`，然后从“安装与诊断”页面打开日志。

#### 验证便携运行时

双击顶层的：

```text
验证Windows运行时.cmd
```

该工具会检查内置 Python、后端依赖、管理器和 draw.io 文件是否完整。

#### 更新 API Key 后仍使用旧配置

保存新 Key 后，先在管理器停止本地服务，再重新启动。确认使用的是 DeepSeek API Key，并检查账户余额、网络和 API 地址。

### 从源码开发

开发环境需要 Python 3.10+ 和 Node.js。普通便携版用户无需执行以下命令：

```powershell
py -3 -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
npm --prefix desktop-plugin install
npm --prefix desktop-plugin run typecheck
npm --prefix desktop-plugin run build
.venv\Scripts\python -m pytest
```

Windows 分享包包含预组装的 Electron、CPython 和 Agent Server。发布前应在真实 Windows 10/11 x64 电脑上运行 `验证Windows运行时.cmd`，并实际测试启动、关闭、插件显示、语言切换和图表插入。

不要提交真实 `.env`、API Key、日志、下载的运行时或个人参考文件。仓库提供的 `.gitignore` 已覆盖常见敏感文件和大型构建产物。

### 第三方组件与许可

本项目包含或调用 draw.io Desktop、Electron、CPython 及多个开源依赖。第三方组件继续遵循各自的许可证。draw.io / diagrams.net 项目采用 Apache License 2.0。公开发布时请保留项目许可证和所有必要的第三方许可声明。

---

## English

### Highlights

- Creates flowcharts, architecture diagrams, knowledge maps, paper summaries, and data visualizations from natural language.
- Accepts PDF, Excel, CSV, Word, PowerPoint, Markdown, JSON, XML, and other common reference files.
- Produces native editable draw.io shapes, text, and orthogonal connectors.
- Enhances short prompts and applies deterministic rules for alignment, spacing, symmetry, and obstacle-aware routing.
- Includes six layout and color options.
- Lets you change the model per request directly inside the draw.io plugin.
- Provides a global Chinese/English setting for both draw.io and the Text2Draw.io plugin.
- Optionally creates small OpenAI-generated illustrations inside key nodes.
- Bundles draw.io, Python, and runtime dependencies; no Node.js, npm, or Python installation is required.

### Requirements

- Windows 10 or Windows 11
- A 64-bit x86 processor (x64)
- 8 GB of RAM recommended
- Network access to the configured AI API
- A DeepSeek API key
- An OpenAI API key is optional and is used only for node illustrations

The current portable release does not support Windows on ARM or 32-bit Windows.

### Download and installation

1. Open **Releases** on the GitHub repository page.
2. Download `Text2Drawio-for-Windows-x64.zip`.
3. Right-click the ZIP and select **Extract All**. Do not run it from the archive window.
4. Keep the extracted directory structure unchanged.
5. Double-click `开始使用 Text2Drawio.cmd` at the top level.

You can also open:

```text
Text2Drawio Manager\Text2Drawio Manager.exe
```

### Windows SmartScreen

The shared build may not have a commercial code-signing certificate. Windows may display “Windows protected your PC” on first launch. After verifying the Release source and checksum:

1. Click **More info**.
2. Check the application name and source.
3. Click **Run anyway**.

Do not bypass SmartScreen for archives from an untrusted source.

### First-time setup

Complete these steps in Text2Draw.io Manager:

1. Enter your DeepSeek API key.
2. Select the global language: `简体中文` or `English`.
3. Click **Save Configuration**, then **Test Connection**.
4. To use AI node illustrations, add an OpenAI API key under **AI Configuration**. This is optional.
5. Click **One-click Install**.
6. Click **Start and Open draw.io**.

For future sessions, use `开始使用 Text2Drawio.cmd` or open the Manager directly.

### Language and model selection

- **Global language:** Save the language in the Manager, fully close draw.io, and reopen it from the Manager. The setting controls both the draw.io editor and the Text2Draw.io plugin.
- **Generation model:** The Manager configures APIs only. Select the DeepSeek model in real time below the plugin prompt box. The next request uses the new model without restarting the service.

### Create your first diagram

1. Open the `Text2Draw.io Agent` panel in draw.io's left sidebar.
2. Enter a request, for example:

   > Create an e-commerce order workflow with inventory checks, payment, risk control, warehouse picking, shipping, delivery confirmation, and refund exception branches.

3. Select a model and layout/color theme.
4. Click Generate.
5. Review the structure summary and click **Insert into canvas**.
6. Every inserted shape, label, illustration, and connector remains independently editable.

### Generate from local files

Use the attachment button next to the prompt box, select a file, and enter a request such as:

> Turn this spreadsheet into a quarterly business analysis diagram highlighting revenue, cost, gross margin, customer growth, channel mix, and anomalies.

Common supported formats:

- PDF
- XLSX, XLSM, XLS, CSV, TSV
- DOCX
- PPTX
- TXT and Markdown
- JSON and XML

The default limits are five files per request and 15 MB per file. Scanned PDFs require OCR first, and encrypted PDFs must be decrypted.

### Optional AI node illustrations

1. Save an OpenAI API key under **AI Configuration** in the Manager.
2. Stop and restart the local service.
3. Enable **Generate small AI illustrations for key nodes** in the plugin's Advanced options.

Illustrations are placed inside nodes only. If image generation is unavailable or fails, Text2Draw.io falls back to vector-only nodes without blocking the main workflow.

### Portable package layout

```text
Text2Drawio 1.1.0 Windows x64\
├─ 开始使用 Text2Drawio.cmd
├─ 验证Windows运行时.cmd
├─ Text2Drawio Manager\
├─ Text2Drawio draw.io\
├─ agent-server\
├─ desktop-plugin\
└─ runtime\python\
```

Do not move the Manager or draw.io executable out of this directory. The Manager uses relative paths to locate the bundled server and runtime.

### Configuration and privacy

Configuration and logs are stored under the current Windows user profile:

```text
%APPDATA%\Text2Drawio\.env
%APPDATA%\Text2Drawio\service.log
%APPDATA%\Text2Drawio\drawio.log
```

- API keys are never written to `.drawio` files.
- The plugin does not directly read API keys.
- The local Agent Server listens on `127.0.0.1:8765` only.
- Reference files are first parsed by the local service.
- Prompts and extracted content are sent to the configured AI API when required for generation.
- Do not process files that you are not authorized to upload or that contain highly sensitive information.

### Troubleshooting

#### The Text2Draw.io sidebar is missing

Click **One-click Install** in the Manager, close every draw.io window, and launch the customized draw.io from the Manager. Do not use a shortcut for a different draw.io installation.

#### A window will not close normally

Make sure you are using version 1.1.0 from the latest Release and that the entire archive was extracted. Do not mix new executables with an older portable directory.

#### The language did not change

After saving the language, fully close the draw.io process and launch it again. An already-running editor cannot switch the complete interface language dynamically.

#### The sidebar says “Service unavailable”

Click **Start Local Service** in the Manager. If it still fails, check whether an older process is using `127.0.0.1:8765`, then inspect the log under **Installation and Diagnostics**.

#### Validate the portable runtime

Double-click:

```text
验证Windows运行时.cmd
```

It verifies the bundled Python runtime, backend imports, Manager, and draw.io executable.

#### A new API key is not being used

Save the new key, stop the local service, and start it again. Verify that it is a DeepSeek API key, then check the account balance, network access, and API endpoint.

### Development from source

Contributors need Python 3.10+ and Node.js. Portable-release users do not need these commands:

```powershell
py -3 -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
npm --prefix desktop-plugin install
npm --prefix desktop-plugin run typecheck
npm --prefix desktop-plugin run build
.venv\Scripts\python -m pytest
```

The Windows release combines Electron, CPython, and the Agent Server into a portable directory. Before publishing, test `验证Windows运行时.cmd`, launch and close behavior, plugin visibility, language switching, and diagram insertion on a real Windows 10/11 x64 machine.

Never commit a populated `.env`, API keys, logs, downloaded runtimes, or private reference files. The provided `.gitignore` excludes common secrets and large build artifacts.

### Third-party components and licenses

This project includes or integrates draw.io Desktop, Electron, CPython, and other open-source dependencies. Each third-party component remains subject to its own license. draw.io / diagrams.net is licensed under the Apache License 2.0. Keep the project license and all required third-party notices in public distributions.
