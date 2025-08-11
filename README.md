# Terminal Controller

一个跨平台的终端应用启动器和窗口管理器，支持通过简短命令快速启动应用程序、管理窗口，并提供全局快捷键支持。

## 特性

- 🚀 **快速应用启动** - 通过简短的命令快速启动配置的应用程序
- 🌐 **网站快速访问** - 预配置网站的快速打开
- 🪟 **窗口管理** - 激活、最小化、关闭应用程序窗口
- ⌨️ **全局快捷键** - 支持全局快捷键唤起终端
- 🔧 **高度可配置** - YAML配置文件，易于自定义
- 🖥️ **跨平台支持** - macOS、Linux、Windows (WSL)
- 📋 **智能窗口选择** - 多窗口应用的智能选择界面
- 🔄 **记忆功能** - 记住最后使用的窗口

## 系统要求

- Python 3.8+
- 支持的操作系统：
  - macOS 10.14+
  - Linux (Ubuntu 18.04+, CentOS 7+, 或其他现代发行版)
  - Windows 10+ (通过WSL或Git Bash)

### 平台特定依赖

**macOS:**
- 无额外依赖 (使用内置的 AppleScript 和 Cocoa)

**Linux:**
- `wmctrl` - 窗口管理
- `xdotool` - 窗口控制
- `python3-dev` - Python开发头文件

**Windows:**
- `pywin32` - Windows API访问 (自动安装)

## 安装

### 自动安装 (推荐)

```bash
git clone https://github.com/your-username/terminalController.git
cd terminalController
chmod +x install.sh
./install.sh
```

安装脚本将：
1. 检测操作系统并安装依赖
2. 创建 Python 虚拟环境
3. 安装 Python 依赖包
4. 创建命令行工具 `tc`
5. 配置系统路径

### 手动安装

```bash
# 1. 克隆仓库
git clone https://github.com/your-username/terminalController.git
cd terminalController

# 2. 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# 或 venv\Scripts\activate  # Windows

# 3. 安装依赖
pip install -r requirements.txt

# 4. 运行测试
python -m pytest tests/

# 5. 启动应用
python main.py
```

## 快速开始

### 1. 配置应用程序

编辑 `config/apps.yaml` 添加你的应用程序：

```yaml
apps:
  c:
    name: "Google Chrome"
    executable:
      macos: "/Applications/Google Chrome.app"
      linux: "google-chrome"
      windows: "chrome.exe"
    type: "browser"
  
  cur:
    name: "Cursor"
    executable:
      macos: "/Applications/Cursor.app"
      linux: "cursor"
      windows: "cursor.exe"
    type: "editor"
```

### 2. 配置网站

编辑 `config/websites.yaml` 添加常用网站：

```yaml
websites:
  g:
    name: "Google"
    url: "https://www.google.com"
  
  gh:
    name: "GitHub"
    url: "https://github.com"
```

### 3. 启动守护进程

```bash
tc daemon &
```

### 4. 使用命令

```bash
# 交互模式
tc

# 直接执行命令（完整版）
tc run c g        # 用Chrome打开Google
tc run cur        # 启动Cursor
tc run c --new gh # 用Chrome新窗口打开GitHub

# 单字母快捷命令（推荐）
c                 # 启动Chrome
c g               # 用Chrome打开Google
c --new gh        # 用Chrome新窗口打开GitHub
e                 # 启动Cursor
t                 # 启动Terminal
p                 # 启动Postman
v                 # 启动VS Code
```

## 使用说明

### 命令格式

```
<app_id> [website_id|url] [options]
```

### 基本命令

**应用启动（推荐使用单字母命令）:**
```bash
# 单字母快捷命令
c                    # 启动Chrome
c g                  # 用Chrome打开Google
c https://github.com # 用Chrome打开GitHub
c --new             # 强制新窗口启动Chrome
e                    # 启动Cursor
t                    # 启动Terminal
p                    # 启动Postman
v                    # 启动VS Code

# 完整命令格式（也可使用）
tc run c             # 启动Chrome
tc run c g           # 用Chrome打开Google
tc run cur           # 启动Cursor
```

**窗口控制:**
```bash
c list              # 列出Chrome的所有窗口
c activate 12345    # 激活指定ID的Chrome窗口
c minimize          # 最小化Chrome的所有窗口
c close 12345       # 关闭指定ID的窗口
```

**系统命令:**
```bash
help                # 显示帮助
help apps           # 显示可用应用程序
config              # 显示当前配置
config reload       # 重新加载配置
quit                # 退出程序
```

### 快捷键

- **macOS:** `Cmd+Shift+T` - 唤起终端
- **Linux:** `Ctrl+Alt+T` - 唤起终端  
- **Windows:** `Ctrl+Shift+T` - 唤起终端

可在 `config/settings.yaml` 中自定义快捷键。

## 配置

### 应用程序配置 (config/apps.yaml)

```yaml
apps:
  app_id:
    name: "应用程序显示名称"
    executable:
      macos: "/Applications/App.app"
      linux: "app-command"
      windows: "app.exe"
    type: "应用类型"  # browser, editor, terminal, etc.
    description: "应用描述"
    args: ["--启动参数"]
```

### 网站配置 (config/websites.yaml)

```yaml
websites:
  site_id:
    name: "网站名称"
    url: "https://example.com"
    description: "网站描述"
```

### 系统设置 (config/settings.yaml)

```yaml
hotkeys:
  terminal: "cmd+shift+t"        # macOS终端快捷键
  terminal_linux: "ctrl+alt+t"  # Linux终端快捷键
  terminal_windows: "ctrl+shift+t" # Windows终端快捷键

behavior:
  auto_focus: true                # 自动聚焦窗口
  show_window_selection: true     # 显示窗口选择界面
  remember_last_used: true        # 记住最后使用的窗口
  window_selection_timeout: 10    # 窗口选择超时(秒)

terminal:
  default: "t"                    # 默认终端应用ID
  startup_command: ""             # 启动时执行的命令
  work_directory: "~"             # 工作目录

logging:
  level: "INFO"                   # 日志级别
  file: "terminalController.log"  # 日志文件
  max_size: "10MB"               # 最大日志文件大小
  backup_count: 3                # 备份文件数量
```

## 开发

### 项目结构

```
terminalController/
├── main.py                 # 主程序入口
├── config/                 # 配置文件目录
│   ├── apps.yaml          # 应用程序配置
│   ├── websites.yaml      # 网站配置
│   └── settings.yaml      # 系统设置
├── src/                   # 源代码
│   ├── config_manager.py  # 配置管理
│   ├── app_manager.py     # 应用程序管理
│   ├── window_manager.py  # 窗口管理
│   ├── command_parser.py  # 命令解析
│   ├── hotkey_manager.py  # 快捷键管理
│   ├── terminal_manager.py # 终端管理
│   └── platform/          # 平台适配
│       ├── base.py        # 基础抽象类
│       ├── macos.py       # macOS实现
│       ├── linux.py       # Linux实现
│       └── windows.py     # Windows实现
├── tests/                 # 测试文件
│   ├── unit/             # 单元测试
│   └── integration/      # 集成测试
├── requirements.txt       # Python依赖
├── install.sh            # 安装脚本
└── README.md             # 文档
```

### 运行测试

```bash
# 运行所有测试
python -m pytest

# 运行单元测试
python -m pytest tests/unit/

# 运行特定测试文件
python -m pytest tests/unit/test_config_manager.py

# 生成覆盖率报告
python -m pytest --cov=src --cov-report=html
```

### 代码检查

```bash
# 安装开发依赖
pip install flake8 black isort mypy

# 代码格式化
black src/ tests/
isort src/ tests/

# 代码检查
flake8 src/ tests/
mypy src/
```

### 添加新平台支持

1. 在 `src/platform/` 下创建新的平台实现文件
2. 继承 `PlatformAdapter` 抽象基类
3. 实现所有必需的方法
4. 在 `src/platform/__init__.py` 中注册新平台
5. 添加相应的测试

### 添加新功能

1. 在相应的管理模块中添加功能
2. 更新配置文件模式（如需要）
3. 添加命令解析支持（如需要）
4. 编写单元测试
5. 更新文档

## 常见问题

### Q: 快捷键不工作
A: 确保：
1. 守护进程正在运行 (`tc daemon &`)
2. 系统权限允许监听全局快捷键，需要为运行tc的虚拟环境中的python设置允许隐私中的辅助功能和输入监控
3. 快捷键没有被其他应用占用

### Q: 应用启动失败
A: 检查：
1. 应用程序路径是否正确
2. 应用程序是否已安装
3. 权限是否足够

### Q: 窗口检测不到
A: 可能原因：
1. 应用程序名称配置不正确
2. 缺少平台特定的依赖工具
3. 应用程序使用了特殊的窗口管理方式

### Q: Linux下某些功能不工作
A: 确保安装了依赖：
```bash
# Ubuntu/Debian
sudo apt-get install wmctrl xdotool

# CentOS/RHEL
sudo yum install wmctrl xdotool

# Arch
sudo pacman -S wmctrl xdotool
```

## 贡献

欢迎贡献代码、报告问题或提出建议！

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

### 贡献指南

- 遵循现有的代码风格
- 为新功能添加测试
- 更新相关文档
- 确保所有测试通过

## 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 更新日志

### v1.0.0 (2025-08-11)
- 初始版本发布
- 支持 macOS、Linux、Windows
- 基本的应用启动和窗口管理
- 配置化的应用和网站管理
- 全局快捷键支持
- 交互式和命令行模式

## 路线图

- [ ] GUI 配置界面
- [ ] 更多窗口操作（调整大小、移动位置等）
- [ ] 应用工作区管理
- [ ] 插件系统
- [ ] 云配置同步
- [ ] 主题支持
- [ ] 多显示器支持

## 致谢

感谢以下开源项目：
- [pynput](https://github.com/moses-palmer/pynput) - 全局输入监听
- [psutil](https://github.com/giampaolo/psutil) - 系统和进程信息
- [PyYAML](https://github.com/yaml/pyyaml) - YAML解析
- [click](https://github.com/pallets/click) - 命令行界面
