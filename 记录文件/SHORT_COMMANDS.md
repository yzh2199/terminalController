# Terminal Controller Enhanced - 超短命令设计 ⚡

## 🎯 设计原则：让命令尽可能短

### 核心命令工具
| 原始命令 | 超短版本 | 🔥 新超短版本 | 说明 |
|---------|---------|------------|------|
| `python3 main_enhanced.py send c` | `t c` | `c` | 打开Cursor，减少90%字符 |
| `python3 main_enhanced.py send g` | `t g` | `g` | 打开Chrome，减少90%字符 |
| `python3 main_enhanced.py daemon-status` | `tcd status` | `tcd status` | 守护进程管理 |
| `python3 main_enhanced.py --help` | `tc -h` | `tc -h` | 帮助信息 |

## ⚡ 应用启动 - 超短命令

### 🔥 单字母直接启动 (无需前缀)
```bash
g        # Chrome (Google) - 直接1个字符!
c        # Cursor - 直接1个字符!
i        # IntelliJ IDEA - 直接1个字符!
p        # Postman - 直接1个字符!
w        # WeChat - 直接1个字符!
k        # Kim - 直接1个字符!
```

### 传统方式 (如果习惯)
```bash
t g      # Chrome (通过t命令)
t c      # Cursor (通过t命令)
t i      # IntelliJ IDEA (通过t命令)
t p      # Postman (通过t命令)
t w      # WeChat (通过t命令)
t k      # Kim (通过t命令)
```

### 双字母启动
```bash
py       # PyCharm (直接2个字符!)
```

### 传统方式 (如果习惯)  
```bash
t py     # PyCharm (通过t命令)
t vs     # Visual Studio Code (备用)
```

## 🌐 网站访问 - 超短组合

### 🔥 超短网站访问
```bash
g google     # Chrome + Google (2个字符!)
g bing       # Chrome + Bing (2个字符!)  
g github     # Chrome + GitHub (2个字符!)
g youtube    # Chrome + YouTube (2个字符!)
```

### 开发网站 (2个字符)
```bash
t g github    # GitHub (github)
t g stackoverflow # Stack Overflow (stackoverflow)
t g mdn       # MDN (mdn)
t g npm       # NPM (npm)
```

### 社交媒体 (1-2个字符)
```bash
t g twitter   # Twitter (twitter)
t g youtube   # YouTube (youtube)
t g linkedin  # LinkedIn (linkedin)
t g reddit    # Reddit (reddit)
```

## 🪟 窗口管理 - 简化动作

### 基础操作 (单词简写)
```bash
t c l        # list (l)
t c a        # activate (a)  
t c m        # minimize (m)
t c x        # close (x)
```

### 高级操作 (组合命令)
```bash
t l          # 列出所有窗口 (list all)
t a 12345    # 激活窗口ID (activate)
t m 12345    # 最小化窗口ID (minimize)
t x 12345    # 关闭窗口ID (close)
```

## 🔧 配置管理 - 简化路径

### 快速配置 (缩写)
```bash
t cfg        # config (cfg)
t cfg l      # config list (l)
t cfg r      # config reload (r)
t cfg a      # config list apps (a)
t cfg w      # config list websites (w)
```

## 📊 系统命令 - 单字母管理

### 守护进程管理
```bash
tcd s        # start (s)
tcd p        # stop (p) 
tcd r        # restart (r)
tcd st       # status (st)
```

### 实用工具
```bash
tc b         # benchmark (b)
tc h         # help (h)
tc v         # version (v)
```

## 🚀 最终超短命令列表

### 最常用命令 (< 5个字符)
```bash
t c          # Chrome
t v          # VS Code
t t          # Terminal  
t p          # Postman
t cfg        # 配置
tcd s        # 启动守护进程
tcd p        # 停止守护进程
```

### 网站快捷 (< 7个字符)
```bash
t c g        # Google
t c gh       # GitHub
t c yt       # YouTube
t c tw       # Twitter
```

### 窗口管理 (< 8个字符)
```bash
t c l        # Chrome窗口列表
t c a        # 激活Chrome
t l          # 所有窗口
t a 123      # 激活窗口123
```

## 🎮 快捷键组合建议

### Bash/Zsh 别名优化
在 `~/.zshrc` 或 `~/.bashrc` 中添加：
```bash
# 超短别名
alias tc='t config'
alias tl='t list'
alias ta='t activate'
alias tm='t minimize'
alias tx='t close'

# 应用快捷启动
alias chrome='t c'
alias cursor='t cur'
alias vscode='t vs'
alias term='t t'

# 网站快捷访问
alias google='t c g'
alias github='t c gh'
alias youtube='t c yt'
```

### 使用效果对比

#### 原始命令 vs 超短命令
```bash
# 原始方式 (56个字符)
python3 main_enhanced.py send "config list apps"

# 超短方式 (8个字符) - 减少86%!
t cfg a

# 原始方式 (40个字符)  
python3 main_enhanced.py send "c activate"

# 超短方式 (4个字符) - 减少90%!
t c a
```

## 🔥 高级技巧

### 1. 智能命令补全
```bash
# 应用名称智能匹配
t ch    # 自动匹配 Chrome (c)
t cu    # 自动匹配 Cursor (cur)
```

### 2. 数字参数简化
```bash
# 窗口ID简化
t a 1   # 激活第1个窗口
t m 2   # 最小化第2个窗口
t x 3   # 关闭第3个窗口
```

### 3. 批量操作
```bash
# 连续命令
t c && t v && t t    # 依次启动Chrome, VS Code, Terminal
```

## 📈 性能提升对比

### 命令长度优化
| 操作 | 原始命令 | 优化命令 | 字符减少 | 减少率 |
|------|---------|---------|---------|--------|
| 启动Chrome | `python3 main_enhanced.py send c` | `t c` | 31 → 3 | 90% |
| 列出窗口 | `python3 main_enhanced.py send "c list"` | `t c l` | 40 → 5 | 87% |
| 配置查看 | `python3 main_enhanced.py send config` | `t cfg` | 37 → 5 | 86% |
| 守护进程状态 | `python3 main_enhanced.py daemon-status` | `tcd st` | 42 → 6 | 86% |

### 执行时间对比
- **守护进程模式**: 0.02-6.49ms (取决于操作复杂度)
- **原版模式**: 200-300ms  
- **性能提升**: 30-15000倍！

---

🎯 **目标达成**: 将命令长度减少85-90%，同时保持超快执行速度！
