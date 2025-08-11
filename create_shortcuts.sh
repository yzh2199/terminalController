#!/bin/bash
# Create single-letter shortcuts for Terminal Controller

# Function to print colored messages
print_success() {
    echo -e "\033[32m✓\033[0m $1"
}

print_status() {
    echo -e "\033[34m→\033[0m $1"
}

print_error() {
    echo -e "\033[31m✗\033[0m $1"
}

# Detect Terminal Controller installation
INSTALL_DIR="$HOME/.terminal-controller"
if [[ ! -d "$INSTALL_DIR" ]]; then
    print_error "Terminal Controller not found. Please run install.sh first."
    exit 1
fi

LOCAL_BIN="$HOME/.local/bin"
mkdir -p "$LOCAL_BIN"

# Create Chrome shortcut (c)
print_status "Creating Chrome shortcut 'c'..."
cat > "$LOCAL_BIN/c" << 'EOF'
#!/bin/bash
# Quick Chrome launcher
exec "$HOME/.local/bin/tc" run c "$@"
EOF
chmod +x "$LOCAL_BIN/c"

# Create Cursor shortcut (cur -> e for editor)
print_status "Creating Cursor shortcut 'e'..."
cat > "$LOCAL_BIN/e" << 'EOF'
#!/bin/bash
# Quick Cursor launcher
exec "$HOME/.local/bin/tc" run cur "$@"
EOF
chmod +x "$LOCAL_BIN/e"

# Create terminal shortcut (t)
print_status "Creating terminal shortcut 't'..."
cat > "$LOCAL_BIN/t" << 'EOF'
#!/bin/bash
# Quick terminal launcher
exec "$HOME/.local/bin/tc" run t "$@"
EOF
chmod +x "$LOCAL_BIN/t"

# Create Postman shortcut (p)
print_status "Creating Postman shortcut 'p'..."
cat > "$LOCAL_BIN/p" << 'EOF'
#!/bin/bash
# Quick Postman launcher
exec "$HOME/.local/bin/tc" run p "$@"
EOF
chmod +x "$LOCAL_BIN/p"

# Create VS Code shortcut (v)
print_status "Creating VS Code shortcut 'v'..."
cat > "$LOCAL_BIN/v" << 'EOF'
#!/bin/bash
# Quick VS Code launcher
exec "$HOME/.local/bin/tc" run vs "$@"
EOF
chmod +x "$LOCAL_BIN/v"

print_success "Single-letter shortcuts created!"
echo ""
echo "Available shortcuts:"
echo "  c   - Google Chrome"
echo "  e   - Cursor"
echo "  t   - Terminal"
echo "  p   - Postman"
echo "  v   - VS Code"
echo ""
echo "Usage examples:"
echo "  c              # Open Chrome"
echo "  c g            # Open Chrome with Google"
echo "  c --new        # Open Chrome in new window"
echo "  e              # Open Cursor"
echo ""
echo "Make sure $LOCAL_BIN is in your PATH"

# Check if LOCAL_BIN is in PATH
if [[ ":$PATH:" != *":$LOCAL_BIN:"* ]]; then
    echo ""
    print_status "Adding $LOCAL_BIN to PATH..."
    
    # Add to shell profile
    SHELL_NAME=$(basename "$SHELL")
    case "$SHELL_NAME" in
        "bash")
            PROFILE_FILE="$HOME/.bashrc"
            if [[ -f "$HOME/.bash_profile" ]]; then
                PROFILE_FILE="$HOME/.bash_profile"
            fi
            ;;
        "zsh")
            PROFILE_FILE="$HOME/.zshrc"
            ;;
        *)
            PROFILE_FILE="$HOME/.profile"
            ;;
    esac
    
    if [[ -f "$PROFILE_FILE" ]]; then
        if ! grep -q "export PATH.*$LOCAL_BIN" "$PROFILE_FILE"; then
            echo "" >> "$PROFILE_FILE"
            echo "# Terminal Controller shortcuts" >> "$PROFILE_FILE"
            echo "export PATH=\"\$HOME/.local/bin:\$PATH\"" >> "$PROFILE_FILE"
            print_success "Added $LOCAL_BIN to PATH in $PROFILE_FILE"
            echo "Please run: source $PROFILE_FILE"
        else
            print_success "$LOCAL_BIN already in PATH"
        fi
    else
        print_status "Please add this to your shell profile:"
        echo "export PATH=\"\$HOME/.local/bin:\$PATH\""
    fi
fi
