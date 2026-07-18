# Windows x64 便携版构建说明

本发行包使用官方 Windows 运行时交叉组装，目标为 Windows 10/11 x64。

- CPython 3.12.10 embeddable x64
- Electron 42.7.0 win32-x64
- `draw.io` 与管理器使用 `resources/app.asar` 手工分发结构
- Python 依赖以 `cp312-win_amd64` 或纯 Python wheel 安装到内置运行时

用户运行入口是顶层 `开始使用 Text2Drawio.cmd`，实际启动
`Text2Drawio Manager/Text2Drawio Manager.exe`。管理器负责写入用户配置、
安装 draw.io 插件、启动本地 Agent Server 及打开定制 draw.io。

定制 draw.io 使用独立应用名 `text2drawio-drawio`，避免与电脑上已经运行的
普通 draw.io 争用单实例锁。`text2drawio-plugin.js` 同时内置在应用的
`drawio/src/main/webapp/plugins/` 中，并由 `ElectronApp.js` 在每次启动时自动注册；
因此不依赖新用户配置中的插件列表。

Windows 1.1.0 保留桌面启动顺序修正：渲染器 User-Agent 保留 draw.io 桌面
识别标记，`bootstrap.js` 等待 ElectronApp、桌面扩展和内置插件全部完成后再调用
`App.main()`。管理器可将简体中文或英文同步给 draw.io 和插件；模型在插件内按请求
实时切换。最终窗口关闭时 Windows 主进程强制退出。

运行时固定校验值：

- `python-3.12.10-embed-amd64.zip`:
  `4acbed6dd1c744b0376e3b1cf57ce906f9dc9e95e68824584c8099a63025a3c3`
- `electron-v42.7.0-win32-x64.zip`:
  `56ef74c90fd8d145a5b41a7d3be6e2207fcc838538f8e92a713cecce54a7d667`

由于当前构建主机为 macOS，Windows PE 文件在这里做格式、依赖结构、
ASAR 内容、哈希及压缩包完整性检查；发行包另附 `验证Windows运行时.cmd`
供 Windows 机器执行真实导入检查。
