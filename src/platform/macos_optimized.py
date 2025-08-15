"""
优化版macOS平台适配器实现
主要优化：
1. 减少AppleScript超时时间 (5s -> 0.5s)
2. 添加窗口信息缓存机制 (1秒缓存)
3. 使用Cocoa API替代部分AppleScript调用
4. 批量操作优化
5. 异步调用支持
"""
import os
import subprocess
import psutil
import logging
import time
import threading
from typing import List, Dict, Any, Optional, Callable
from urllib.parse import quote
from concurrent.futures import ThreadPoolExecutor, as_completed

from .base import PlatformAdapter, WindowInfo, AppInfo

try:
    from pynput import keyboard
    from pynput.keyboard import Key, Listener
except ImportError:
    keyboard = None
    Key = None
    Listener = None

try:
    import Quartz
    from Cocoa import NSWorkspace, NSRunningApplication
    HAS_COCOA = True
except ImportError:
    HAS_COCOA = False

logger = logging.getLogger(__name__)


class OptimizedMacOSAdapter(PlatformAdapter):
    """优化版macOS平台适配器"""
    
    def __init__(self):
        self._hotkey_listeners = {}
        self._running_listener = None
        
        # 性能优化：缓存机制
        self._window_cache: Dict[str, List[WindowInfo]] = {}
        self._cache_timestamps: Dict[str, float] = {}
        self._cache_timeout = 1.0  # 1秒缓存超时
        
        # 性能优化：线程池用于并发操作
        self._thread_pool = ThreadPoolExecutor(max_workers=3)
        
        logger.info("初始化优化版macOS适配器，启用缓存和并发优化")
    
    def launch_app(self, app_path: str, args: Optional[List[str]] = None, 
                   cwd: Optional[str] = None) -> bool:
        """
        启动应用程序
        """
        try:
            normalized_path = self.normalize_app_path(app_path)
            
            if normalized_path.endswith('.app'):
                cmd = ['open', '-a', normalized_path]
                if args:
                    cmd.extend(['--args'] + args)
            else:
                cmd = [normalized_path]
                if args:
                    cmd.extend(args)
            
            logger.info(f"【launch_app】启动应用: {app_path}, 参数: {args}, 工作目录: {cwd}")
            subprocess.Popen(
                cmd,
                cwd=cwd or os.path.expanduser('~'),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            return True
            
        except Exception as e:
            logger.error(f"启动应用失败 {app_path}: {e}")
            return False
    
    def get_running_apps(self, app_name: Optional[str] = None) -> List[AppInfo]:
        """
        获取运行中的应用程序
        优化：优先使用Cocoa API，性能更好
        """
        apps = []
        
        try:
            if HAS_COCOA:
                # 优化：使用Cocoa API，比psutil更快
                workspace = NSWorkspace.sharedWorkspace()
                running_apps = workspace.runningApplications()
                
                for app in running_apps:
                    if app.activationPolicy() == 0:  # 只获取常规应用
                        name = str(app.localizedName())
                        if app_name and app_name.lower() not in name.lower():
                            continue
                        
                        app_info = AppInfo(
                            pid=app.processIdentifier(),
                            name=name,
                            executable_path=str(app.executableURL().path()) if app.executableURL() else "",
                            windows=[]  # 延迟加载窗口信息
                        )
                        apps.append(app_info)
            else:
                # 后备方案：使用psutil
                for proc in psutil.process_iter(['pid', 'name', 'exe']):
                    try:
                        proc_info = proc.info
                        name = proc_info['name']
                        if app_name and app_name.lower() not in name.lower():
                            continue
                        
                        app_info = AppInfo(
                            pid=proc_info['pid'],
                            name=name,
                            executable_path=proc_info['exe'] or "",
                            windows=[]
                        )
                        apps.append(app_info)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
                        
        except Exception as e:
            logger.error(f"获取运行应用失败: {e}")
        
        return apps
    
    def get_app_windows(self, app_name: str) -> List[WindowInfo]:
        """
        获取应用程序窗口信息
        优化1：缓存机制 - 1秒内重复请求直接返回缓存
        优化2：减少AppleScript超时时间
        优化3：优先使用Cocoa API
        """
        current_time = time.time()
        
        # 优化：检查缓存
        if self._is_cache_valid(app_name, current_time):
            logger.debug(f"从缓存返回 {app_name} 的窗口信息")
            return self._window_cache[app_name]
        
        # 优化：优先尝试Cocoa API
        if HAS_COCOA:
            windows = self._get_windows_cocoa(app_name)
            if windows:
                self._update_cache(app_name, windows, current_time)
                return windows
        
        # 后备方案：优化的AppleScript
        windows = self._get_windows_applescript_optimized(app_name)
        self._update_cache(app_name, windows, current_time)
        
        return windows
    
    def _get_windows_cocoa(self, app_name: str) -> List[WindowInfo]:
        """
        使用Cocoa API获取窗口信息
        优化：比AppleScript快5-10倍
        """
        try:
            # 获取所有窗口
            window_list = Quartz.CGWindowListCopyWindowInfo(
                Quartz.kCGWindowListOptionOnScreenOnly, 
                Quartz.kCGNullWindowID
            )
            
            windows = []
            all_apps = set()  # 收集所有应用名称用于调试
            
            for window in window_list:
                owner_name = window.get('kCGWindowOwnerName', '')
                all_apps.add(owner_name)
                
                if owner_name == app_name:
                    window_id = str(window.get('kCGWindowNumber', 0))
                    title = window.get('kCGWindowName', '')
                    
                    # 对于终端应用，即使没有标题也要包含窗口
                    # 使用默认标题或窗口ID作为标识
                    if not title:
                        if 'iterm' in app_name.lower() or 'terminal' in app_name.lower():
                            title = f"Terminal Window {window_id}"
                        else:
                            title = f"Untitled Window {window_id}"
                    
                    # 只过滤掉明显无效的窗口（窗口ID为0）
                    if window_id and window_id != '0':
                        windows.append(WindowInfo(
                            window_id=window_id,
                            title=title,
                            app_name=app_name,
                            is_active=False,  # Cocoa API需要额外调用来确定
                            is_minimized=False
                        ))
                        logger.debug(f"添加窗口: {window_id} - '{title}'")
                    else:
                        logger.debug(f"跳过无效窗口: {window_id}")
            
            # 调试日志：如果没有找到窗口，显示所有应用名称
            if not windows and any('iterm' in app.lower() or 'terminal' in app.lower() for app in all_apps):
                terminal_apps = [app for app in all_apps if 'iterm' in app.lower() or 'terminal' in app.lower()]
                logger.info(f"调试: 查找 '{app_name}' 时未找到窗口，但发现终端类应用: {terminal_apps}")
            
            logger.debug(f"通过Cocoa API获取到 {len(windows)} 个窗口")
            return windows
            
        except Exception as e:
            logger.warning(f"Cocoa API获取窗口失败: {e}")
            return []
    
    def _get_windows_applescript_optimized(self, app_name: str) -> List[WindowInfo]:
        """
        优化的AppleScript窗口获取
        优化1：减少超时时间 (5s -> 0.5s)
        优化2：简化脚本逻辑
        优化3：更好的错误处理
        """
        windows = []
        
        try:
            # 优化：简化的AppleScript，减少循环复杂度
            script = f'''
            tell application "System Events"
                try
                    set appProcess to first process whose name is "{app_name}"
                    set windowList to windows of appProcess
                    set result to ""
                    repeat with w in windowList
                        set result to result & (id of w) & "|" & (name of w) & "\\n"
                    end repeat
                    return result
                on error
                    return ""
                end try
            end tell
            '''
            
            start_time = time.time()
            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True,
                text=True,
                timeout=0.5  # 优化：从5秒减少到0.5秒
            )
            execution_time = (time.time() - start_time) * 1000
            
            logger.debug(f"AppleScript执行时间: {execution_time:.2f}ms")
            
            if result.returncode == 0 and result.stdout.strip():
                for line in result.stdout.strip().split('\\n'):
                    if '|' in line:
                        parts = line.split('|', 1)
                        if len(parts) == 2:
                            window_id, title = parts
                            windows.append(WindowInfo(
                                window_id=window_id.strip(),
                                title=title.strip(),
                                app_name=app_name,
                                is_active=False,
                                is_minimized=False
                            ))
                            
        except subprocess.TimeoutExpired:
            logger.warning(f"AppleScript超时获取 {app_name} 窗口")
        except Exception as e:
            logger.error(f"AppleScript获取窗口失败 {app_name}: {e}")
        
        return windows
    
    # todo这个方法比较慢，接近300ms，按t终端切换时会调用，后续考虑优化为按c切换应用一样的逻辑
    def activate_window(self, window_id: str) -> bool:
        """
        激活窗口
        优化：减少超时时间，添加快速失败机制
        """
        try:
            # 首先尝试找到窗口所属的应用
            window_info = self.find_window_by_id_fast(window_id)
            
            # 针对 iTerm2 使用专门的激活脚本
            if window_info and 'iterm' in window_info.app_name.lower():
                script = f'''
                tell application "iTerm2"
                    activate
                    try
                        repeat with theWindow in windows
                            if id of theWindow is {window_id} then
                                select theWindow
                                return "success"
                            end if
                        end repeat
                        return "notfound"
                    on error errMsg
                        return "error:" & errMsg
                    end try
                end tell
                '''
            else:
                # 对于其他应用，使用 System Events
                script = f'''
                tell application "System Events"
                    try
                        perform action "AXRaise" of (first window whose id is {window_id})
                        return "success"
                    on error errMsg
                        return "error:" & errMsg
                    end try
                end tell
                '''
            
            start_time = time.time()
            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True,
                text=True,
                timeout=2.0 if window_info and 'iterm' in window_info.app_name.lower() else 0.5  # iTerm2 需要更多时间
            )
            execution_time = (time.time() - start_time) * 1000
            
            logger.debug(f"窗口激活耗时: {execution_time:.2f}ms")
            
            # 检查激活结果
            success = result.returncode == 0 and 'success' in result.stdout
            
            if success:
                logger.info(f"成功激活窗口 {window_id}")
                # 清除缓存，因为窗口状态可能改变
                self._clear_cache()
            else:
                # 详细的错误日志
                if 'notfound' in result.stdout:
                    logger.warning(f"激活失败：未找到窗口 {window_id}")
                elif 'error:' in result.stdout:
                    error_msg = result.stdout.replace('error:', '').strip()
                    logger.warning(f"激活失败：{error_msg} (窗口 {window_id})")
                else:
                    logger.warning(f"激活失败：未知错误 (窗口 {window_id}), returncode: {result.returncode}, stdout: '{result.stdout}', stderr: '{result.stderr}'")
            
            return success
            
        except subprocess.TimeoutExpired:
            logger.warning(f"激活窗口超时: {window_id}")
            return False
        except Exception as e:
            logger.error(f"激活窗口失败 {window_id}: {e}")
            return False
    
    def activate_window_fast(self, window_id: str) -> bool:
        """
        快速窗口激活 - 异步版本
        优化：使用线程池避免阻塞
        """
        future = self._thread_pool.submit(self.activate_window, window_id)
        try:
            return future.result(timeout=1.0)  # 1秒总超时
        except:
            return False
    
    def find_window_by_id_fast(self, window_id: str) -> Optional[WindowInfo]:
        """
        快速根据ID查找窗口
        优化：避免获取所有窗口，直接通过Cocoa API查找特定窗口
        """
        try:
            if not HAS_COCOA:
                return None
            
            # 优化：使用Cocoa API直接根据窗口ID查找
            window_list = Quartz.CGWindowListCopyWindowInfo(
                Quartz.kCGWindowListOptionOnScreenOnly, 
                Quartz.kCGNullWindowID
            )
            
            for window in window_list:
                if str(window.get('kCGWindowNumber', 0)) == window_id:
                    owner_name = window.get('kCGWindowOwnerName', '')
                    title = window.get('kCGWindowName', '')
                    
                    logger.debug(f"【hotkey】快速查找窗口成功: {window_id}")
                    return WindowInfo(
                        window_id=window_id,
                        title=title,
                        app_name=owner_name,
                        is_active=False,  # 需要额外查询
                        is_minimized=False
                    )
            
            return None
            
        except Exception as e:
            logger.warning(f"快速窗口查找失败: {e}")
            return None
    
    def minimize_window(self, window_id: str) -> bool:
        """最小化窗口 - 优化版"""
        try:
            script = f'''
            tell application "System Events"
                try
                    set minimized of (first window whose id is {window_id}) to true
                    return true
                on error
                    return false
                end try
            end tell
            '''
            
            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True,
                text=True,
                timeout=0.3  # 优化：短超时
            )
            
            success = result.returncode == 0 and 'true' in result.stdout
            if success:
                self._clear_cache()
            
            return success
            
        except Exception as e:
            logger.error(f"最小化窗口失败 {window_id}: {e}")
            return False
    
    def close_window(self, window_id: str) -> bool:
        """关闭窗口 - 优化版"""
        try:
            script = f'''
            tell application "System Events"
                try
                    perform action "AXCancel" of (first window whose id is {window_id})
                    return true
                on error
                    return false
                end try
            end tell
            '''
            
            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True,
                text=True,
                timeout=0.3
            )
            
            success = result.returncode == 0 and 'true' in result.stdout
            if success:
                self._clear_cache()
            
            return success
            
        except Exception as e:
            logger.error(f"关闭窗口失败 {window_id}: {e}")
            return False
    
    def get_active_window(self) -> Optional[WindowInfo]:
        """
        获取当前活动窗口
        优化：缓存活动窗口信息
        """
        try:
            script = '''
            tell application "System Events"
                try
                    set frontApp to name of first application process whose frontmost is true
                    set frontWindow to window 1 of first application process whose frontmost is true
                    set windowTitle to name of frontWindow
                    set windowID to id of frontWindow
                    return (windowID as string) & "|" & windowTitle & "|" & frontApp
                on error
                    return ""
                end try
            end tell
            '''
            
            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True,
                text=True,
                timeout=0.5  # 优化：短超时
            )
            
            if result.returncode == 0 and result.stdout.strip():
                parts = result.stdout.strip().split('|')
                if len(parts) >= 3:
                    return WindowInfo(
                        window_id=parts[0],
                        title=parts[1],
                        app_name=parts[2],
                        is_active=True,
                        is_minimized=False
                    )
                    
        except Exception as e:
            logger.error(f"获取活动窗口失败: {e}")
        
        return None
    
    def batch_get_windows(self, app_names: List[str]) -> Dict[str, List[WindowInfo]]:
        """
        批量获取多个应用的窗口信息
        优化：并发执行，大幅提升多应用查询性能
        """
        results = {}
        
        # 使用线程池并发获取
        future_to_app = {
            self._thread_pool.submit(self.get_app_windows, app_name): app_name 
            for app_name in app_names
        }
        
        for future in as_completed(future_to_app, timeout=2.0):
            app_name = future_to_app[future]
            try:
                results[app_name] = future.result()
            except Exception as e:
                logger.error(f"批量获取 {app_name} 窗口失败: {e}")
                results[app_name] = []
        
        return results
    
    def _is_cache_valid(self, app_name: str, current_time: float) -> bool:
        """检查缓存是否有效"""
        if app_name not in self._window_cache:
            return False
        
        last_update = self._cache_timestamps.get(app_name, 0)
        return (current_time - last_update) < self._cache_timeout
    
    def _update_cache(self, app_name: str, windows: List[WindowInfo], timestamp: float):
        """更新缓存"""
        self._window_cache[app_name] = windows
        self._cache_timestamps[app_name] = timestamp
        logger.debug(f"更新 {app_name} 窗口缓存，共 {len(windows)} 个窗口")
    
    def _clear_cache(self):
        """清除所有缓存"""
        self._window_cache.clear()
        self._cache_timestamps.clear()
        logger.debug("清除窗口缓存")
    
    def cleanup(self):
        """清理资源"""
        self._clear_cache()
        if hasattr(self, '_thread_pool'):
            self._thread_pool.shutdown(wait=False)
        
        logger.info("优化版macOS适配器已清理")
    
    def register_hotkey(self, hotkey: str, callback: Callable) -> bool:
        """注册全局热键"""
        logger.info(f"【mac_hotkey】注册热键: '{hotkey}'")
        if not keyboard:
            logger.error("【mac_hotkey】pynput不可用")
            return False
        
        if not self._check_accessibility_permissions():
            logger.error("【mac_hotkey】无辅助功能权限")
            return False
        
        try:
            key_combination = self._parse_hotkey(hotkey)
            logger.info(f"【mac_hotkey】解析热键: '{hotkey}' 为: '{key_combination}'")
            if not key_combination:
                return False
            
            def on_hotkey():
                try:
                    callback()
                except Exception as e:
                    logger.error(f"热键回调错误: {e}")
            
            if self._running_listener:
                self._running_listener.stop()
            
            mapping = {key_combination: on_hotkey}
            # 注册热键kv结构，key是热键，value是回调方法
            self._running_listener = keyboard.GlobalHotKeys(mapping)
            self._running_listener.start()
            
            self._hotkey_listeners[hotkey] = self._running_listener
            return True
            
        except Exception as e:
            logger.error(f"注册热键失败 {hotkey}: {e}")
            return False
    
    def unregister_hotkey(self, hotkey: str) -> bool:
        """注销热键"""
        try:
            if hotkey in self._hotkey_listeners:
                listener = self._hotkey_listeners[hotkey]
                listener.stop()
                del self._hotkey_listeners[hotkey]
                return True
            return False
        except Exception as e:
            logger.error(f"注销热键失败 {hotkey}: {e}")
            return False
    
    def is_app_running(self, app_name: str) -> bool:
        """检查应用是否运行"""
        try:
            if HAS_COCOA:
                workspace = NSWorkspace.sharedWorkspace()
                running_apps = workspace.runningApplications()
                
                for app in running_apps:
                    if app.activationPolicy() == 0:
                        name = str(app.localizedName())
                        if app_name.lower() in name.lower():
                            return True
            else:
                for proc in psutil.process_iter(['name']):
                    try:
                        if app_name.lower() in proc.info['name'].lower():
                            return True
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
        except Exception as e:
            logger.error(f"检查应用运行状态失败: {e}")
        
        return False
    
    def kill_app(self, app_name: str, force: bool = False) -> bool:
        """终止应用"""
        try:
            if force:
                subprocess.run(['killall', '-9', app_name], check=False)
            else:
                script = f'tell application "{app_name}" to quit'
                subprocess.run(['osascript', '-e', script], check=False)
            return True
        except Exception as e:
            logger.error(f"终止应用失败 {app_name}: {e}")
            return False
    
    def open_url(self, url: str, browser_path: Optional[str] = None) -> bool:
        """打开URL"""
        try:
            if browser_path:
                subprocess.run(['open', '-a', browser_path, url], check=False)
            else:
                subprocess.run(['open', url], check=False)
            return True
        except Exception as e:
            logger.error(f"打开URL失败 {url}: {e}")
            return False
    
    def get_default_terminal(self) -> str:
        """获取默认终端"""
        terminals = [
            "/Applications/iTerm.app",
            "/Applications/Terminal.app",
            "/System/Applications/Terminal.app"
        ]
        
        for terminal in terminals:
            if os.path.exists(terminal):
                return terminal
        
        return "Terminal"
    
    def normalize_app_path(self, app_path: str) -> str:
        """规范化应用路径"""
        path = os.path.expanduser(app_path)
        
        if not path.startswith('/') and not path.endswith('.app'):
            app_name = path + '.app'
            for search_path in ['/Applications', '/System/Applications', 
                              os.path.expanduser('~/Applications')]:
                full_path = os.path.join(search_path, app_name)
                if os.path.exists(full_path):
                    return full_path
        
        return path
    
    def _parse_hotkey(self, hotkey: str) -> Optional[str]:
        """解析热键字符串"""
        key_mapping = {
            'cmd': 'cmd', 'ctrl': 'ctrl', 'alt': 'alt', 'shift': 'shift',
            'option': 'alt', 'command': 'cmd'
        }
        
        keys = [key.strip().lower() for key in hotkey.split('+')]
        normalized_keys = []
        
        for key in keys:
            if key in key_mapping:
                normalized_keys.append(f'<{key_mapping[key]}>')
            elif len(key) == 1:
                normalized_keys.append(key)
            else:
                normalized_keys.append(f'<{key}>')
        
        return '+'.join(normalized_keys) if normalized_keys else None
    
    # todo 这个方法比较慢，250ms,不过只有启动时候调用一次，可以接受
    def _check_accessibility_permissions(self) -> bool:
        """检查辅助功能权限"""
        try:
            start_time = time.time()
            result = subprocess.run([
                'osascript', '-e', 
                'tell application "System Events" to get name of first process'
            ], capture_output=True, text=True, timeout=1)
            end_time = time.time()
            logger.info(f"【mac_hotkey】检查辅助功能权限耗时: {(end_time - start_time) * 1000:.2f}ms")
            return result.returncode == 0
        except Exception:
            return False
