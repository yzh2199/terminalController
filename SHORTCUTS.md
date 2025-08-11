# Terminal Controller 单字母快捷命令

## 概述

为了让命令更简洁，Terminal Controller 现在支持单字母快捷命令，你再也不需要输入冗长的 `tc run c` 了！

## 可用的快捷命令

| 快捷命令 | 应用 | 原始命令 |
|---------|------|---------|
| `c` | Google Chrome | `tc run c` |
| `e` | Cursor | `tc run cur` |
| `t` | Terminal (iTerm) | `tc run t` |
| `p` | Postman | `tc run p` |
| `v` | VS Code | `tc run vs` |

## 使用示例

### Chrome 快捷命令
```bash
c                    # 启动Chrome
c g                  # 用Chrome打开Google
c gh                 # 用Chrome打开GitHub
c https://example.com # 用Chrome打开任意网址
c --new             # 强制新窗口启动Chrome
c --new g           # 新窗口打开Google
```

### 其他应用快捷命令
```bash
e                    # 启动Cursor编辑器
t                    # 启动Terminal
p                    # 启动Postman
v                    # 启动VS Code
```

## 安装快捷命令

### 自动安装（推荐）
运行安装脚本时会自动创建这些快捷命令：
```bash
./install.sh
```

### 手动安装
如果你已经安装了Terminal Controller，可以单独创建快捷命令：
```bash
./create_shortcuts.sh
```

## 工作原理

每个快捷命令实际上是一个小的bash脚本，它会调用完整的 `tc run` 命令。例如：

```bash
#!/bin/bash
# Quick Chrome launcher
exec "$HOME/.local/bin/tc" run c "$@"
```

这些脚本位于 `~/.local/bin/` 目录下，确保这个目录在你的 PATH 中。

## 兼容性

- ✅ 支持所有原始命令的参数和选项
- ✅ 支持网站快捷键（如 `c g` 打开Google）
- ✅ 支持 `--new` 等选项
- ✅ 支持直接URL（如 `c https://example.com`）
- ✅ 保持与原始 `tc run` 命令的完全兼容

## 故障排除

### 命令不工作
1. 确保 `~/.local/bin` 在你的 PATH 中：
   ```bash
   echo $PATH | grep .local/bin
   ```

2. 如果不在PATH中，添加到你的shell配置文件：
   ```bash
   echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
   source ~/.zshrc
   ```

### 重新创建快捷命令
如果快捷命令损坏或缺失，可以重新运行：
```bash
./create_shortcuts.sh
```

## 注意事项

- 这些快捷命令与系统中可能存在的同名命令（如系统的 `c` 命令）会产生冲突
- 如果遇到冲突，你可以：
  1. 使用完整的 `tc run c` 命令
  2. 修改快捷命令名称
  3. 调整PATH顺序

快享受更快速的应用启动体验吧！🚀
