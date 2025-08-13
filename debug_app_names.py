#!/usr/bin/env python3
"""
调试脚本：查看实际的应用名称
"""

import os
import sys

# 添加 src 目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.config_manager import ConfigManager
from src.window_manager import WindowManager

def debug_app_names():
    """调试应用名称"""
    print("=== 调试应用名称 ===")
    
    try:
        config_manager = ConfigManager("config")
        window_manager = WindowManager(config_manager)
        
        # 测试不同的应用名称变体
        possible_names = ["iTerm", "iTerm2", "Terminal", "iterm", "iterm2"]
        
        for app_name in possible_names:
            windows = window_manager.platform_adapter.get_app_windows(app_name)
            print(f"应用名称 '{app_name}': 找到 {len(windows)} 个窗口")
            for i, window in enumerate(windows, 1):
                print(f"  {i}. {window.window_id}: {window.title}")
        
        # 获取所有运行中的应用
        print("\n=== 所有运行中的应用 ===")
        try:
            running_apps = window_manager.platform_adapter.get_running_apps()
            print(f"找到 {len(running_apps)} 个运行中的应用:")
            
            terminal_like_apps = []
            for app in running_apps:
                app_name_lower = app.name.lower()
                if any(term in app_name_lower for term in ['iterm', 'terminal', 'term']):
                    terminal_like_apps.append(app)
                    print(f"  🖥️  {app.name} (PID: {app.pid})")
                else:
                    print(f"  📱 {app.name} (PID: {app.pid})")
            
            print(f"\n=== 类似终端的应用 ({len(terminal_like_apps)} 个) ===")
            for app in terminal_like_apps:
                print(f"应用名称: '{app.name}'")
                windows = window_manager.platform_adapter.get_app_windows(app.name)
                print(f"  窗口数量: {len(windows)}")
                for window in windows:
                    print(f"    - {window.window_id}: {window.title}")
                    
        except Exception as e:
            print(f"获取运行应用失败: {e}")
        
        # 使用 Cocoa API 直接查看窗口信息
        print("\n=== 使用 Cocoa API 查看所有窗口 ===")
        try:
            import Quartz
            window_list = Quartz.CGWindowListCopyWindowInfo(
                Quartz.kCGWindowListOptionOnScreenOnly, 
                Quartz.kCGNullWindowID
            )
            
            terminal_windows = []
            for window in window_list:
                owner_name = window.get('kCGWindowOwnerName', '')
                window_name = window.get('kCGWindowName', '')
                
                if any(term in owner_name.lower() for term in ['iterm', 'terminal']):
                    terminal_windows.append((owner_name, window_name, window.get('kCGWindowNumber', 0)))
            
            print(f"找到 {len(terminal_windows)} 个终端类型窗口:")
            for owner, title, window_id in terminal_windows:
                print(f"  应用: '{owner}', 窗口: '{title}', ID: {window_id}")
                
        except Exception as e:
            print(f"使用 Cocoa API 失败: {e}")
            
    except Exception as e:
        print(f"调试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_app_names()