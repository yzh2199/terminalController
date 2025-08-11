# Terminal Controller Enhanced Daemon 使用指南

## 🚀 快速开始

### 1. 安装守护进程
```bash
# 运行安装脚本
./install_daemon.sh

# 重新加载shell环境
source ~/.zshrc  # 或 source ~/.bashrc
```

### 2. 启动守护进程
```bash
# 启动守护进程
tcd start

# 检查状态
tcd status
```

### 3. 开始使用超快命令
```bash
# 基础用法
t help           # 显示帮助
t g              # 打开Chrome (< 1ms!)
t c              # 打开Cursor
t t              # 打开终端
t p              # 打开Postman
t i              # 打开IntelliJ IDEA
t py             # 打开PyCharm
t w              # 打开WeChat
t k              # 打开Kim
```

## 📋 命令工具说明

### 核心命令工具

| 命令 | 功能 | 使用场景 |
|------|------|----------|
| `tc` | 完整功能的主命令 | 完整操作、配置管理 |
| `tcd` | 守护进程管理 | 启动/停止/状态检查 |
| `t` | 超快速命令 | 日常应用切换 (需守护进程) |
| `tc-benchmark` | 性能测试 | 测试系统性能 |

### 守护进程管理 (`tcd`)
```bash
tcd start      # 启动守护进程
tcd stop       # 停止守护进程  
tcd status     # 检查状态和性能
tcd restart    # 重启守护进程
```

## ⚡ 超快应用切换

### 应用启动 (< 1ms 执行时间)
```bash
# 基础应用启动
t g            # Chrome
t c            # Cursor  
t py           # PyCharm
t i            # IntelliJ IDEA
t t            # 终端
t p            # Postman
t w            # WeChat
t k            # Kim

# 强制新窗口
t g --new      # 新Chrome窗口
t c --new      # 新Cursor窗口
```

### 网站快速打开
```bash
# 预配置网站
t g google     # Chrome + Google
t g github     # Chrome + GitHub  
t g youtube    # Chrome + YouTube

# 直接URL
t g https://github.com/your-repo
```

### 窗口管理 (超快切换!)
```bash
# 列出窗口
t g list       # Chrome所有窗口
t c list       # Cursor所有窗口

# 激活窗口
t g activate   # 激活Chrome最新窗口
t c activate   # 激活Cursor最新窗口

# 最小化窗口  
t g minimize   # 最小化Chrome
t c minimize   # 最小化Cursor

# 关闭窗口
t g close      # 关闭Chrome窗口
```

### 精确窗口控制
```bash
# 通过窗口ID操作
t activate 12345    # 激活指定窗口ID
t minimize 12345    # 最小化指定窗口
t close 12345       # 关闭指定窗口

# 列出所有窗口
t list             # 显示系统所有窗口
```

## 🔥 高级用法

### 配置管理
```bash
# 查看配置
t config                # 显示当前配置
t config list apps      # 列出所有应用
t config list websites  # 列出所有网站
t config reload         # 重新加载配置
```

### 性能监控
```bash
# 详细性能信息
t help --verbose       # 显示执行时间统计
t c --verbose          # 显示详细性能数据

# 运行基准测试
tc-benchmark           # 完整性能测试
```

### 命令组合和批处理
```bash
# 快速开发环境启动
t cur && t c && t t    # 依次启动Cursor, Chrome, 终端

# 工作区切换
t c activate && t cur activate  # 快速在Chrome和Cursor间切换
```

## ⌨️ 热键功能

### 默认热键设置
- **Ctrl+;** - 启动终端应用 (全局热键)

### 自定义热键
编辑配置文件 `~/.terminal-controller/config/settings.yaml`:
```yaml
hotkeys:
  terminal:
    key: "ctrl+;"
    action: "launch"
    target: "t"
```

### 热键使用场景
1. **快速回到终端**: 无论在任何应用中，按 `Ctrl+;` 立即切换到终端
2. **开发者工作流**: 编码时快速切换到终端执行命令
3. **系统管理**: 快速访问命令行进行系统操作

## 📂 应用ID速查表

### 常用应用ID (已优化)
```bash
# 开发工具
c      # Cursor
py     # PyCharm
i      # IntelliJ IDEA
t      # 终端/iTerm

# 浏览器
g      # Chrome (Google)

# 工具应用
p      # Postman

# 通讯工具
w      # WeChat
k      # Kim

# 备用编辑器
vs     # Visual Studio Code
```

### 网站ID速查表
```bash
# 搜索引擎
g      # Google
b      # Bing

# 开发相关
gh     # GitHub
so     # Stack Overflow
mdn    # MDN Web Docs

# 常用网站  
yt     # YouTube
tw     # Twitter
```

## 🎯 使用技巧

### 1. 超短命令设计
所有命令都设计得尽可能短：
- 单字母应用ID: `c`, `t`, `p`
- 常用动作简写: `list` → `l`, `activate` → `a`
- 快速工具: `t` 命令一键发送

### 2. 智能默认行为
- `t c` - 如果Chrome未运行则启动，如果运行则激活
- `t c activate` - 自动激活最近活动的Chrome窗口
- `t list` - 智能格式化显示窗口列表

### 3. 错误处理和提示
```bash
# 守护进程未启动时的提示
$ t c
❌ 守护进程未运行，请先执行: tcd start

# 无效命令的智能提示
$ t xyz
❌ 未知应用: xyz
💡 可用应用: c, cur, vs, t, p
💡 使用 't help' 查看完整帮助
```

### 4. 性能优化建议
- 保持守护进程运行以获得最佳性能
- 使用 `t` 命令而不是 `tc run` 获得最快速度
- 定期运行 `tc-benchmark` 检查系统性能

## 🛠️ 故障排除

### 常见问题

#### 1. 命令找不到
```bash
# 解决方案
source ~/.zshrc  # 重新加载环境变量
# 或
export PATH="$HOME/.terminal-controller/bin:$PATH"
```

#### 2. 守护进程启动失败
```bash
# 检查日志
tail -f ~/.terminal-controller/logs/terminalController.log

# 清理并重启
tcd stop
rm -f /tmp/terminal_controller.sock
tcd start
```

#### 3. 权限问题 (macOS)
- 在 `系统偏好设置` → `安全性与隐私` → `辅助功能` 中添加终端应用
- 重启守护进程: `tcd restart`

#### 4. 性能下降
```bash
# 运行诊断
tc-benchmark

# 检查系统资源
tcd status

# 重启守护进程
tcd restart
```

### 日志文件位置
- 主日志: `~/.terminal-controller/logs/terminalController.log`
- 错误日志: `~/.terminal-controller/logs/daemon.error.log`
- 守护进程日志: `~/.terminal-controller/logs/daemon.log`

## 🔧 自定义配置

### 添加新应用
编辑 `~/.terminal-controller/config/apps.yaml`:
```yaml
apps:
  idea:  # 新的应用ID
    name: "IntelliJ IDEA"
    type: "editor"
    path: "/Applications/IntelliJ IDEA.app"
    description: "Java IDE"
```

### 添加新网站
编辑 `~/.terminal-controller/config/websites.yaml`:
```yaml
websites:
  chatgpt:  # 新的网站ID
    name: "ChatGPT"
    url: "https://chat.openai.com"
    description: "AI助手"
```

### 使用新配置
```bash
t config reload    # 重新加载配置
t idea             # 使用新应用ID
t c chatgpt        # 使用新网站ID
```

## 🚀 高级工作流示例

### 开发者日常工作流
```bash
# 1. 启动开发环境
tcd start          # 确保守护进程运行
t c                # 打开Cursor代码编辑器
t g github         # 打开GitHub
t t                # 打开终端

# 2. 快速切换调试
t g list           # 查看浏览器标签页
t g activate 12345 # 切换到特定页面
t c activate       # 回到代码编辑器

# 3. 多IDE开发
t py               # 打开PyCharm (Python项目)
t i                # 打开IntelliJ IDEA (Java项目)
```

### 系统管理员工作流
```bash
# 快速系统检查
t t                # 打开终端
# Ctrl+; 随时快速回到终端
t p                # 打开系统监控工具
```

### 内容创作者工作流
```bash
# 多媒体工作环境
t c yt             # YouTube
t n                # 笔记应用
t m                # 音乐播放器
```

## 📊 性能数据

### 实测性能 (vs 原版)
- **命令执行时间**: < 1ms (原版: ~300ms)
- **性能提升**: 99.7%
- **内存占用**: 守护进程模式约20MB
- **响应时间**: 平均1.84ms (包含IPC开销)

### 基准测试结果
```bash
$ tc-benchmark
🚀 开始性能基准测试 (5次迭代)
--------------------------------------------------

📋 测试命令: 'help'
  📊 平均总耗时: 3.39ms
  ⚡ 平均守护进程执行: 0.07ms

📋 测试命令: 'config list apps'  
  📊 平均总耗时: 1.45ms
  ⚡ 平均守护进程执行: 0.82ms

🎯 总体性能:
  平均响应时间: 1.84ms
  性能评级: 优秀
```

---

🎉 **享受超快的应用程序切换体验！** ⚡

有问题？查看日志文件或运行 `tcd status` 进行诊断。
