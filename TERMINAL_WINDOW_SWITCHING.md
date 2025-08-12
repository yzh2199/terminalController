# Terminal Window Switching Feature

## 功能描述

当在运行Terminal Controller交互模式的iTerm窗口中输入命令`t`时，系统会智能地切换到另一个已存在的iTerm窗口，而不是启动新的iTerm实例。

## 实现逻辑

1. **终端上下文检测**: 系统会检测当前是否在终端环境中运行交互模式
2. **窗口过滤**: 获取所有iTerm窗口，排除当前正在运行脚本的窗口
3. **智能选择**: 优先选择最近使用的窗口，或选择非最小化的窗口
4. **窗口切换**: 激活选中的窗口并记录为最近使用的窗口

## 使用场景

### 场景1: 多个iTerm窗口存在
- 窗口A: 运行Terminal Controller交互模式
- 窗口B: 其他工作窗口
- 在窗口A中输入`t` → 切换到窗口B

### 场景2: 只有当前窗口
- 只有一个iTerm窗口运行Terminal Controller
- 输入`t` → 启动新的iTerm窗口

### 场景3: 强制启动新窗口
- 输入`t --new` → 总是启动新的iTerm窗口

## 代码修改点

### 1. AppManager (_handle_terminal_launch方法)
```python
def _handle_terminal_launch(self, app_id: str, app_config: AppConfig) -> Optional[bool]:
    # 检查是否在终端上下文中运行
    # 获取其他终端窗口
    # 智能选择目标窗口
    # 执行窗口切换
```

### 2. Main程序 (_handle_launch_app方法)
- 区分窗口切换和新窗口启动的消息显示

## 测试步骤

1. 打开第一个iTerm窗口，启动Terminal Controller交互模式
2. 打开第二个iTerm窗口
3. 在第一个窗口中输入`t`
4. 验证是否切换到第二个窗口
5. 测试`t --new`是否强制启动新窗口

## 配置选项

相关配置在`config/settings.yaml`中：
- `behavior.remember_last_used`: 是否记住最近使用的窗口
- `behavior.show_window_selection`: 多个窗口时是否显示选择界面
- `behavior.window_selection_timeout`: 窗口选择超时时间
