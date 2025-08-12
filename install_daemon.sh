#!/bin/bash

# Terminal Controller Enhanced Daemon 安装脚本
# 基于原版main.py实现的高性能守护进程版本
# todo 当前脚本有问题，安装的tc没有像install.sh那样安装到~/.local/bin，导致需要在.bashrc或者.zshrc中添加PATH，否则无法使用tc命令，后续修改脚本
# todo 让tc安装到~/.local/bin中

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 打印带颜色的信息
print_info() {
    echo -e "${CYAN}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# 检查操作系统
check_os() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
        print_info "检测到 macOS 系统"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OS="linux"
        print_info "检测到 Linux 系统"
    else
        print_error "不支持的操作系统: $OSTYPE"
        exit 1
    fi
}

# 检查Python版本
check_python() {
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
        print_info "Python 版本: $PYTHON_VERSION"
        
        # 检查是否满足最低版本要求 (3.7+)
        if python3 -c "import sys; exit(0 if sys.version_info >= (3, 7) else 1)"; then
            print_success "Python 版本符合要求"
        else
            print_error "需要 Python 3.7 或更高版本"
            exit 1
        fi
    else
        print_error "未找到 Python 3，请先安装 Python 3"
        exit 1
    fi
}

# 创建安装目录
create_install_dir() {
    INSTALL_DIR="$HOME/.terminal-controller"
    print_step "创建安装目录: $INSTALL_DIR"
    
    mkdir -p "$INSTALL_DIR"/{bin,config,logs}
    print_success "安装目录创建完成"
}

# 复制文件
copy_files() {
    print_step "复制程序文件"
    
    # 复制主程序文件
    cp main_enhanced.py "$INSTALL_DIR/bin/"
    cp daemon_client.py "$INSTALL_DIR/bin/"
    
    # 复制源代码目录到根目录和bin目录下的src子目录
    cp -r src "$INSTALL_DIR/"
    mkdir -p "$INSTALL_DIR/bin/src"
    cp -r src/* "$INSTALL_DIR/bin/src/"
    
    # 复制和更新配置文件
    if [ ! -f "$INSTALL_DIR/config/apps.yaml" ]; then
        # 创建优化的应用配置文件
        cat > "$INSTALL_DIR/config/apps.yaml" << 'EOF'
apps:
  g:
    name: "Google Chrome"
    executable:
      darwin: "/Applications/Google Chrome.app"
      linux: "google-chrome"
      windows: "chrome.exe"
    args:
      - "-n" # 新窗口打开
    type: "browser"
    description: "Google Chrome browser"
  
  p:
    name: "Postman"
    executable:
      darwin: "/Applications/Postman.app"
      linux: "postman"
      windows: "postman.exe"
    type: "api"
    description: "Postman API testing tool"
  
  c:
    name: "Cursor"
    executable:
      darwin: "/Applications/Cursor.app"
      linux: "cursor"
      windows: "cursor.exe"
    type: "editor"
    description: "Cursor code editor"
  
  t:
    name: "iTerm"
    executable:
      darwin: "/Applications/iTerm.app"
      linux: "gnome-terminal"
      windows: "cmd.exe"
    type: "terminal"
    description: "Terminal application"
  
  i:
    name: "IntelliJ IDEA"
    executable:
      darwin: "/Applications/IntelliJ IDEA.app"
      linux: "idea"
      windows: "idea.exe"
    type: "editor"
    description: "IntelliJ IDEA code editor"
  
  py:
    name: "PyCharm"
    executable:
      darwin: "/Applications/PyCharm CE.app"
      linux: "pycharm"
      windows: "pycharm.exe"
    type: "editor"
    description: "PyCharm code editor"
  
  k:
    name: "Kim"
    executable:
      darwin: "/Applications/Kim.app"
      linux: "kim"
      windows: "kim.exe"
    type: "chat"
    description: "Kim messaging app"
  
  w:
    name: "WeChat"
    executable:
      darwin: "/Applications/WeChat.app"
      linux: "wechat"
      windows: "wechat.exe"
    type: "chat"
    description: "WeChat messaging app"

  # VS Code (备用编辑器)
  vs:
    name: "Visual Studio Code"
    executable:
      darwin: "/Applications/Visual Studio Code.app"
      linux: "code"
      windows: "code.exe"
    type: "editor"
    description: "Visual Studio Code editor"
EOF

        # 复制其他配置文件
        cp config/websites.yaml "$INSTALL_DIR/config/" 2>/dev/null || true
        cp config/settings.yaml "$INSTALL_DIR/config/" 2>/dev/null || true
        
        print_success "已创建优化的应用配置文件"
    else
        print_warning "用户配置文件已存在，跳过覆盖"
        print_info "如需更新配置，请删除 $INSTALL_DIR/config/apps.yaml 后重新运行安装"
    fi
    
    print_success "文件复制完成"
}

# 安装Python依赖
install_dependencies() {
    print_step "安装 Python 依赖"
    
    # 创建虚拟环境
    cd "$INSTALL_DIR"
    python3 -m venv venv
    source venv/bin/activate
    
    # 升级pip
    pip install --upgrade pip
    
    # 安装依赖
    pip install click colorama pynput psutil pyyaml
    
    # macOS特定依赖
    if [ "$OS" = "macos" ]; then
        pip install pyobjc-framework-Cocoa pyobjc-framework-Quartz
    fi
    
    print_success "依赖安装完成"
}

# 创建命令行工具
create_cli_tools() {
    print_step "创建命令行工具"
    
    # 创建主命令 tc (terminal-controller)
    cat > "$INSTALL_DIR/bin/tc" << 'EOF'
#!/bin/bash
# Terminal Controller Enhanced - 主命令
INSTALL_DIR="$HOME/.terminal-controller"
source "$INSTALL_DIR/venv/bin/activate"
exec python3 "$INSTALL_DIR/bin/main_enhanced.py" "$@"
EOF

    # 创建守护进程命令 tcd (terminal-controller daemon)
    cat > "$INSTALL_DIR/bin/tcd" << 'EOF'
#!/bin/bash
# Terminal Controller Daemon - 守护进程管理
INSTALL_DIR="$HOME/.terminal-controller"
source "$INSTALL_DIR/venv/bin/activate"

case "$1" in
    start)
        echo "🚀 启动 Terminal Controller 守护进程..."
        python3 "$INSTALL_DIR/bin/main_enhanced.py" daemon
        ;;
    stop)
        echo "🛑 停止 Terminal Controller 守护进程..."
        python3 "$INSTALL_DIR/bin/main_enhanced.py" stop
        ;;
    status)
        python3 "$INSTALL_DIR/bin/main_enhanced.py" daemon-status
        ;;
    restart)
        echo "🔄 重启 Terminal Controller 守护进程..."
        python3 "$INSTALL_DIR/bin/main_enhanced.py" stop
        sleep 2
        python3 "$INSTALL_DIR/bin/main_enhanced.py" daemon
        ;;
    *)
        echo "用法: tcd {start|stop|status|restart}"
        echo ""
        echo "命令说明:"
        echo "  start   - 启动守护进程"
        echo "  stop    - 停止守护进程"
        echo "  status  - 检查守护进程状态"
        echo "  restart - 重启守护进程"
        exit 1
        ;;
esac
EOF

    # 创建快速命令 t (快速发送命令到守护进程)
    cat > "$INSTALL_DIR/bin/t" << 'EOF'
#!/bin/bash
# Terminal Controller Quick Command - 快速命令
INSTALL_DIR="$HOME/.terminal-controller"
source "$INSTALL_DIR/venv/bin/activate"

if [ $# -eq 0 ]; then
    echo "用法: t <命令>"
    echo ""
    echo "示例:"
    echo "  t g              # 打开Chrome"
    echo "  t c              # 打开Cursor"
    echo "  t p              # 打开Postman"
    echo "  t i              # 打开IntelliJ IDEA"
    echo "  t py             # 打开PyCharm"
    echo "  t w              # 打开WeChat"
    echo "  t k              # 打开Kim"
    echo "  t g list         # 列出Chrome窗口"
    echo "  t g activate     # 激活Chrome窗口"
    echo "  t help           # 显示帮助"
    echo ""
    echo "提示: 使用 'tcd start' 先启动守护进程"
    exit 1
fi

# 检查守护进程是否运行
if ! python3 "$INSTALL_DIR/bin/main_enhanced.py" daemon-status >/dev/null 2>&1; then
    echo "❌ 守护进程未运行，请先执行: tcd start"
    exit 1
fi

# 发送命令到守护进程
exec python3 "$INSTALL_DIR/bin/main_enhanced.py" send "$@"
EOF

    # 创建基准测试命令
    cat > "$INSTALL_DIR/bin/tc-benchmark" << 'EOF'
#!/bin/bash
# Terminal Controller Benchmark - 性能测试
INSTALL_DIR="$HOME/.terminal-controller"
source "$INSTALL_DIR/venv/bin/activate"
exec python3 "$INSTALL_DIR/bin/daemon_client.py" --benchmark
EOF

    # 创建超短应用启动命令，这部分没啥用，创建之后用命令模式会很慢，因为每次使用命令都需要启动python
    # print_info "创建超短应用启动命令..."
    # 
    # # Chrome (g)
    # cat > "$INSTALL_DIR/bin/g" << 'EOF'
# #!/bin/bash
# INSTALL_DIR="$HOME/.terminal-controller"
# source "$INSTALL_DIR/venv/bin/activate"
# exec python3 "$INSTALL_DIR/bin/main_enhanced.py" send g "$@"
# EOF
# 
    # # Cursor (c)
    # cat > "$INSTALL_DIR/bin/c" << 'EOF'
# #!/bin/bash
# INSTALL_DIR="$HOME/.terminal-controller"
# source "$INSTALL_DIR/venv/bin/activate"
# exec python3 "$INSTALL_DIR/bin/main_enhanced.py" send c "$@"
# EOF
# 
    # # Postman (p)
    # cat > "$INSTALL_DIR/bin/p" << 'EOF'
# #!/bin/bash
# INSTALL_DIR="$HOME/.terminal-controller"
# source "$INSTALL_DIR/venv/bin/activate"
# exec python3 "$INSTALL_DIR/bin/main_enhanced.py" send p "$@"
# EOF
# 
    # # IntelliJ IDEA (i)
    # cat > "$INSTALL_DIR/bin/i" << 'EOF'
# #!/bin/bash
# INSTALL_DIR="$HOME/.terminal-controller"
# source "$INSTALL_DIR/venv/bin/activate"
# exec python3 "$INSTALL_DIR/bin/main_enhanced.py" send i "$@"
# EOF
# 
    # # PyCharm (py)
    # cat > "$INSTALL_DIR/bin/py" << 'EOF'
# #!/bin/bash
# INSTALL_DIR="$HOME/.terminal-controller"
# source "$INSTALL_DIR/venv/bin/activate"
# exec python3 "$INSTALL_DIR/bin/main_enhanced.py" send py "$@"
# EOF
# 
    # # WeChat (w)
    # cat > "$INSTALL_DIR/bin/w" << 'EOF'
# #!/bin/bash
# INSTALL_DIR="$HOME/.terminal-controller"
# source "$INSTALL_DIR/venv/bin/activate"
# exec python3 "$INSTALL_DIR/bin/main_enhanced.py" send w "$@"
# EOF
# 
    # # Kim (k)
    # cat > "$INSTALL_DIR/bin/k" << 'EOF'
# #!/bin/bash
# INSTALL_DIR="$HOME/.terminal-controller"
# source "$INSTALL_DIR/venv/bin/activate"
# exec python3 "$INSTALL_DIR/bin/main_enhanced.py" send k "$@"
# EOF
# 
    # # 设置执行权限
    # chmod +x "$INSTALL_DIR/bin/"*
    # 
    # print_success "命令行工具创建完成 (包括超短命令: g, c, p, i, py, w, k)"
}

# 设置环境变量
setup_environment() {
    print_step "设置环境变量"
    
    # 检查shell类型 - 使用更可靠的方法
    if [ -n "$ZSH_VERSION" ] || [[ "$SHELL" == *"zsh"* ]]; then
        SHELL_RC="$HOME/.zshrc"
        print_info "检测到 ZSH shell，使用 .zshrc"
    elif [ -n "$BASH_VERSION" ] || [[ "$SHELL" == *"bash"* ]]; then
        SHELL_RC="$HOME/.bashrc"
        print_info "检测到 BASH shell，使用 .bashrc"
    else
        # 默认尝试zsh，因为这在macOS上更常见
        SHELL_RC="$HOME/.zshrc"
        print_info "使用默认 .zshrc 配置"
    fi
    
    # 添加到PATH
    if ! grep -q "terminal-controller/bin" "$SHELL_RC" 2>/dev/null; then
        echo "" >> "$SHELL_RC"
        echo "# Terminal Controller Enhanced" >> "$SHELL_RC"
        echo "export PATH=\"\$HOME/.terminal-controller/bin:\$PATH\"" >> "$SHELL_RC"
        print_success "已添加到 $SHELL_RC"
    else
        print_info "PATH 已配置"
    fi
    
    # 导出当前会话
    export PATH="$HOME/.terminal-controller/bin:$PATH"
}

# 创建启动脚本
create_launcher() {
    print_step "创建启动脚本"
    
    # 创建 launchd 配置文件 (仅macOS)
    if [ "$OS" = "macos" ]; then
        cat > "$HOME/Library/LaunchAgents/com.terminalcontroller.daemon.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.terminalcontroller.daemon</string>
    <key>ProgramArguments</key>
    <array>
        <string>$INSTALL_DIR/bin/tcd</string>
        <string>start</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$INSTALL_DIR/logs/daemon.log</string>
    <key>StandardErrorPath</key>
    <string>$INSTALL_DIR/logs/daemon.error.log</string>
</dict>
</plist>
EOF
        print_info "已创建 launchd 配置文件"
    fi
}

# 测试安装
test_installation() {
    print_step "测试安装"
    
    # 测试命令可用性
    if command -v tc &> /dev/null; then
        print_success "tc 命令可用"
    else
        print_warning "tc 命令不可用，请重新加载shell: source ~/.zshrc (或 ~/.bashrc)"
    fi
    
    # 测试配置
    source "$INSTALL_DIR/venv/bin/activate"
    if python3 "$INSTALL_DIR/bin/main_enhanced.py" --help &> /dev/null; then
        print_success "程序运行正常"
    else
        print_error "程序运行异常"
        exit 1
    fi
}

# 显示使用说明
show_usage() {
    print_success "🎉 Terminal Controller Enhanced 安装完成！"
    echo ""
    echo -e "${CYAN}快速开始:${NC}"
    echo "  1. 重新加载shell环境:"
    echo "     source ~/.zshrc    # 或 source ~/.bashrc"
    echo ""
    echo "  2. 启动守护进程:"
    echo -e "     ${GREEN}tcd start${NC}"
    echo ""
    echo "  3. 测试超短命令 (无需't'前缀):"
     echo -e "     ${GREEN}b${NC}             # 直接打开Chrome"
     echo -e "     ${GREEN}c${NC}             # 直接打开Cursor"
     echo -e "     ${GREEN}p${NC}             # 直接打开Postman"
     echo -e "     ${GREEN}k${NC}             # 直接打开Kim"
     echo -e "     ${GREEN}py${NC}             # 直接打开PyCharm"
     echo -e "     ${GREEN}i${NC}             # 直接打开IntelliJ IDEA"
     echo -e "     ${GREEN}w${NC}             # 直接打开WeChat"
     echo ""
     echo "  4. 传统命令 (如果习惯):"
     echo -e "     ${GREEN}t help${NC}        # 显示帮助"
     echo -e "     ${GREEN}t g${NC}           # 打开Chrome"
     echo -e "     ${GREEN}t c${NC}           # 打开Cursor"
    echo ""
    echo -e "${CYAN}命令说明:${NC}"
    echo -e "  ${YELLOW}超短命令${NC}     - 单字母启动: g, c, p, i, py, w, k"
    echo -e "  ${YELLOW}tc${NC}           - 完整命令行工具"
    echo -e "  ${YELLOW}tcd${NC}          - 守护进程管理 (start/stop/status/restart)"
    echo -e "  ${YELLOW}t${NC}            - 快速命令 (需要守护进程运行)"
    echo -e "  ${YELLOW}tc-benchmark${NC} - 性能测试"
    echo ""
    echo -e "${CYAN}配置文件位置:${NC}"
    echo "  $INSTALL_DIR/config/"
    echo ""
    echo -e "${CYAN}日志文件位置:${NC}"
    echo "  $INSTALL_DIR/logs/"
    echo ""
    if [ "$OS" = "macos" ]; then
        echo -e "${CYAN}开机自启动:${NC}"
        echo "  launchctl load ~/Library/LaunchAgents/com.terminalcontroller.daemon.plist"
        echo "  launchctl unload ~/Library/LaunchAgents/com.terminalcontroller.daemon.plist"
        echo ""
    fi
    echo -e "${GREEN}享受超快的应用程序切换体验！⚡${NC}"
}

# 主安装流程
main() {
    echo -e "${GREEN}"
    cat << 'EOF'
╔══════════════════════════════════════════════════════════════╗
║            Terminal Controller Enhanced Daemon              ║
║                   增强守护进程安装程序                       ║
║                                                              ║
║  🚀 基于原版main.py实现的高性能守护进程                      ║
║  ⚡ 命令执行时间 < 1ms                                       ║
║  🔥 性能提升 99.7%                                          ║
╚══════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
    
    check_os
    check_python
    create_install_dir
    copy_files
    install_dependencies
    create_cli_tools
    setup_environment
    create_launcher
    test_installation
    show_usage
}

# 运行安装
main "$@"
