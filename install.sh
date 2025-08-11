#!/bin/bash

# Terminal Controller Installation Script
# Supports macOS, Linux, and Windows (via WSL/Git Bash)

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Global variables
INSTALL_DIR="$HOME/.terminal-controller"
VENV_DIR="$INSTALL_DIR/venv"
PYTHON_CMD=""
OS_TYPE=""

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
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

# Function to detect operating system
detect_os() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        OS_TYPE="macos"
        print_status "Detected macOS"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OS_TYPE="linux"
        print_status "Detected Linux"
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
        OS_TYPE="windows"
        print_status "Detected Windows (via Git Bash/MSYS)"
    else
        print_warning "Unknown OS type: $OSTYPE, assuming Linux"
        OS_TYPE="linux"
    fi
}

# Function to find Python command
find_python() {
    print_status "Looking for Python 3.8+ installation..."
    
    for cmd in python3.12 python3.11 python3.10 python3.9 python3.8 python3 python; do
        if command -v "$cmd" >/dev/null 2>&1; then
            version=$($cmd --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
            major=$(echo $version | cut -d. -f1)
            minor=$(echo $version | cut -d. -f2)
            
            if [[ $major -eq 3 ]] && [[ $minor -ge 8 ]]; then
                PYTHON_CMD="$cmd"
                print_success "Found Python $version at $(command -v $cmd)"
                return 0
            fi
        fi
    done
    
    print_error "Python 3.8+ not found. Please install Python 3.8 or later."
    print_status "Visit https://www.python.org/downloads/ to download Python"
    exit 1
}

# Function to install system dependencies
install_system_deps() {
    print_status "Installing system dependencies..."
    
    case $OS_TYPE in
        "macos")
            if command -v brew >/dev/null 2>&1; then
                print_status "Installing macOS dependencies via Homebrew..."
                # Install Python if not available
                if ! command -v python3 >/dev/null 2>&1; then
                    brew install python
                fi
            else
                print_warning "Homebrew not found. Some features may not work correctly."
                print_status "Install Homebrew from https://brew.sh/ for better compatibility"
            fi
            ;;
        "linux")
            if command -v apt-get >/dev/null 2>&1; then
                print_status "Installing Linux dependencies via apt..."
                sudo apt-get update
                sudo apt-get install -y python3 python3-pip python3-venv \
                    python3-dev build-essential \
                    wmctrl xdotool \
                    libx11-dev libxtst6 libxss1 libgconf-2-4
            elif command -v yum >/dev/null 2>&1; then
                print_status "Installing Linux dependencies via yum..."
                sudo yum install -y python3 python3-pip python3-devel gcc \
                    wmctrl xdotool \
                    libX11-devel libXtst
            elif command -v pacman >/dev/null 2>&1; then
                print_status "Installing Linux dependencies via pacman..."
                sudo pacman -S --noconfirm python python-pip \
                    wmctrl xdotool \
                    libx11 libxtst
            else
                print_warning "Package manager not found. Please install dependencies manually:"
                print_status "- Python 3.8+"
                print_status "- wmctrl (for window management)"
                print_status "- xdotool (for window control)"
                print_status "- Development tools (gcc, etc.)"
            fi
            ;;
        "windows")
            print_status "Windows detected. Some features may require additional setup:"
            print_status "- Ensure Python 3.8+ is installed"
            print_status "- pywin32 will be installed automatically"
            ;;
    esac
}

# Function to create installation directory
create_install_dir() {
    print_status "Creating installation directory at $INSTALL_DIR..."
    
    if [[ -d "$INSTALL_DIR" ]]; then
        print_warning "Installation directory already exists. Backing up..."
        mv "$INSTALL_DIR" "${INSTALL_DIR}.backup.$(date +%s)"
    fi
    
    mkdir -p "$INSTALL_DIR"
    print_success "Installation directory created"
}

# Function to copy files
copy_files() {
    print_status "Copying Terminal Controller files..."
    
    # Copy main files
    cp -r . "$INSTALL_DIR/"
    
    # Remove backup directory if it was copied
    [[ -d "$INSTALL_DIR/${INSTALL_DIR}.backup."* ]] && rm -rf "$INSTALL_DIR/${INSTALL_DIR}.backup."*
    
    # Make main script executable
    chmod +x "$INSTALL_DIR/main.py"
    
    print_success "Files copied successfully"
}

# Function to create virtual environment
create_venv() {
    print_status "Creating Python virtual environment..."
    
    "$PYTHON_CMD" -m venv "$VENV_DIR"
    
    # Activate virtual environment
    if [[ -f "$VENV_DIR/bin/activate" ]]; then
        source "$VENV_DIR/bin/activate"
    elif [[ -f "$VENV_DIR/Scripts/activate" ]]; then
        source "$VENV_DIR/Scripts/activate"
    else
        print_error "Failed to find virtual environment activation script"
        exit 1
    fi
    
    # Upgrade pip
    pip install --upgrade pip
    
    print_success "Virtual environment created"
}

# Function to install Python dependencies
install_python_deps() {
    print_status "Installing Python dependencies..."
    
    # Activate virtual environment
    if [[ -f "$VENV_DIR/bin/activate" ]]; then
        source "$VENV_DIR/bin/activate"
    elif [[ -f "$VENV_DIR/Scripts/activate" ]]; then
        source "$VENV_DIR/Scripts/activate"
    fi
    
    # Install dependencies
    pip install -r "$INSTALL_DIR/requirements.txt"
    
    print_success "Python dependencies installed"
}

# Function to create symlink
create_symlink() {
    print_status "Creating command-line symlink..."
    
    # Create wrapper script
    WRAPPER_SCRIPT="$INSTALL_DIR/tc"
    cat > "$WRAPPER_SCRIPT" << EOF
#!/bin/bash
# Terminal Controller wrapper script

# Activate virtual environment
if [[ -f "$VENV_DIR/bin/activate" ]]; then
    source "$VENV_DIR/bin/activate"
elif [[ -f "$VENV_DIR/Scripts/activate" ]]; then
    source "$VENV_DIR/Scripts/activate"
fi

# Run Terminal Controller
exec "$VENV_DIR/bin/python" "$INSTALL_DIR/main.py" "\$@"
EOF
    
    chmod +x "$WRAPPER_SCRIPT"
    
    # Create symlink in user's local bin
    LOCAL_BIN="$HOME/.local/bin"
    mkdir -p "$LOCAL_BIN"
    
    if [[ -L "$LOCAL_BIN/tc" ]] || [[ -f "$LOCAL_BIN/tc" ]]; then
        rm -f "$LOCAL_BIN/tc"
    fi
    
    ln -s "$WRAPPER_SCRIPT" "$LOCAL_BIN/tc"
    
    print_success "Command-line tool 'tc' created"
    
    # Create single-letter shortcuts
    create_shortcuts
    
    print_status "Make sure $LOCAL_BIN is in your PATH"
}

# Function to create single-letter shortcuts
create_shortcuts() {
    print_status "Creating single-letter shortcuts..."
    
    # Create Chrome shortcut (b)
    cat > "$LOCAL_BIN/b" << 'EOF'
#!/bin/bash
# Quick Chrome launcher
exec "$HOME/.local/bin/tc" run c "$@"
EOF
    chmod +x "$LOCAL_BIN/b"
    
    # Create Cursor shortcut (c for cursor)
    cat > "$LOCAL_BIN/c" << 'EOF'
#!/bin/bash
# Quick Cursor launcher
exec "$HOME/.local/bin/tc" run cur "$@"
EOF
    chmod +x "$LOCAL_BIN/c"
    
    # Create terminal shortcut (t)
    cat > "$LOCAL_BIN/t" << 'EOF'
#!/bin/bash
# Quick terminal launcher
exec "$HOME/.local/bin/tc" run t "$@"
EOF
    chmod +x "$LOCAL_BIN/t"
    
    # Create Postman shortcut (p)
    cat > "$LOCAL_BIN/p" << 'EOF'
#!/bin/bash
# Quick Postman launcher
exec "$HOME/.local/bin/tc" run postman "$@"
EOF
    chmod +x "$LOCAL_BIN/p"
    
    # Create Kim shortcut (k)
    cat > "$LOCAL_BIN/k" << 'EOF'
#!/bin/bash
# Quick Kim launcher
exec "$HOME/.local/bin/tc" run kim "$@"
EOF
    chmod +x "$LOCAL_BIN/k"

    # Create PyCharm shortcut (py)
    cat > "$LOCAL_BIN/py" << 'EOF'
#!/bin/bash
# Quick PyCharm launcher
exec "$HOME/.local/bin/tc" run py "$@"
EOF
    chmod +x "$LOCAL_BIN/py"

    # Create IntelliJ IDEA shortcut (i)
    cat > "$LOCAL_BIN/i" << 'EOF'
#!/bin/bash
# Quick IntelliJ IDEA launcher
exec "$HOME/.local/bin/tc" run idea "$@"
EOF
    chmod +x "$LOCAL_BIN/i"

    # Create WeChat shortcut (w)
    cat > "$LOCAL_BIN/w" << 'EOF'
#!/bin/bash
# Quick WeChat launcher
exec "$HOME/.local/bin/tc" run wechat "$@"
EOF
    chmod +x "$LOCAL_BIN/w"
    
    print_success "Single-letter shortcuts created: b, c, t, p, k, py, i, w"
}

# Function to test installation
test_installation() {
    print_status "Testing installation..."
    
    # Test basic functionality
    if "$INSTALL_DIR/tc" --help >/dev/null 2>&1; then
        print_success "Installation test passed"
    else
        print_error "Installation test failed"
        exit 1
    fi
}

# Function to show post-installation instructions
show_instructions() {
    print_success "Terminal Controller installed successfully!"
    echo
    print_status "Post-installation steps:"
    echo
    echo "1. Add ~/.local/bin to your PATH if not already present:"
    echo "   export PATH=\"\$HOME/.local/bin:\$PATH\""
    echo "   (Add this to your ~/.bashrc, ~/.zshrc, or equivalent)"
    echo
    echo "2. Reload your shell or run:"
    echo "   source ~/.bashrc  # or ~/.zshrc"
    echo
    echo "3. Configure your applications by editing:"
    echo "   $INSTALL_DIR/config/apps.yaml"
    echo "   $INSTALL_DIR/config/websites.yaml"
    echo "   $INSTALL_DIR/config/settings.yaml"
    echo
    echo "4. Start using Terminal Controller:"
    echo "   tc                    # Interactive mode"
    echo "   tc daemon            # Start as daemon"
    echo "   tc run b g           # Launch Chrome with Google"
    echo "   tc status            # Show status"
    echo
    echo "5. Use single-letter shortcuts (faster!):"
    echo "   b                     # Launch Chrome"
    echo "   b g                   # Open Chrome with Google"
    echo "   b -n                  # Chrome in new window"
    echo "   c                     # Launch Cursor"
    echo "   t                     # Launch Terminal"
    echo "   p                     # Launch Postman"
    echo "   w                     # Launch WeChat"
    echo "   k                     # Launch Kim"
    echo "   py                    # Launch PyCharm"
    echo "   i                     # Launch IntelliJ IDEA"
    echo
    echo "6. For hotkey support, start the daemon:"
    echo "   tc daemon &"
    echo
    print_status "For help and documentation, run: tc help"
}

# Function to handle cleanup on error
cleanup_on_error() {
    print_error "Installation failed. Cleaning up..."
    [[ -d "$INSTALL_DIR" ]] && rm -rf "$INSTALL_DIR"
    exit 1
}

# Main installation function
main() {
    echo "==============================================="
    echo "    Terminal Controller Installation Script"
    echo "==============================================="
    echo
    
    # Set up error handling
    trap cleanup_on_error ERR
    
    # Check if we're in the project directory
    if [[ ! -f "main.py" ]] || [[ ! -f "requirements.txt" ]]; then
        print_error "Please run this script from the Terminal Controller project directory"
        exit 1
    fi
    
    # Run installation steps
    detect_os
    find_python
    install_system_deps
    create_install_dir
    copy_files
    create_venv
    install_python_deps
    create_symlink
    test_installation
    show_instructions
    
    print_success "Installation completed successfully!"
}

# Check if running as source or executed
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
