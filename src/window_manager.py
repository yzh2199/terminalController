"""Window management module for Terminal Controller."""
import logging
import time
from typing import List, Optional, Dict, Any, Callable
from threading import Timer

from .platform import get_platform_adapter, PlatformAdapter
from .platform.base import WindowInfo
from .config_manager import ConfigManager


logger = logging.getLogger(__name__)

# 统一的性能日志前缀
PERF_LOG_PREFIX = "[PERF]"

def log_perf(msg: str, duration_ms: Optional[float] = None):
    """统一的性能日志记录函数"""
    if duration_ms is not None:
        logger.info(f"{PERF_LOG_PREFIX} {msg} - {duration_ms:.2f}ms")
    else:
        logger.info(f"{PERF_LOG_PREFIX} {msg}")


class WindowManager:
    """Manages window operations and interactions."""
    
    def __init__(self, config_manager: ConfigManager):
        """Initialize the window manager.
        
        Args:
            config_manager: Configuration manager instance
        """
        self.config_manager = config_manager
        self.platform_adapter: PlatformAdapter = get_platform_adapter()()
        self._selection_timers: Dict[str, Timer] = {}
        
        logger.info("Initialized WindowManager")
    
    def list_all_windows(self, filter_app: Optional[str] = None) -> List[WindowInfo]:
        """List all windows or windows for a specific application.
        
        Args:
            filter_app: Application name to filter by (optional)
            
        Returns:
            List of window information
        """
        try:
            if filter_app:
                app_config = self.config_manager.get_app_config(filter_app)
                if app_config:
                    return self.platform_adapter.get_app_windows(app_config.name)
                else:
                    logger.warning(f"Unknown application: {filter_app}")
                    return []
            else:
                # Get all running apps and their windows
                all_windows = []
                running_apps = self.platform_adapter.get_running_apps()
                
                for app in running_apps:
                    windows = self.platform_adapter.get_app_windows(app.name)
                    all_windows.extend(windows)
                
                # Sort by application name, then by window title
                all_windows.sort(key=lambda w: (w.app_name, w.title))
                return all_windows
                
        except Exception as e:
            logger.error(f"Error listing windows: {e}")
            return []
    
    def format_window_list(self, windows: List[WindowInfo], 
                          include_app_name: bool = True) -> str:
        """Format a list of windows for display.
        
        Args:
            windows: List of windows to format
            include_app_name: Whether to include application name in output
            
        Returns:
            Formatted string representation of windows
        """
        if not windows:
            return "No windows found."
        
        lines = []
        current_app = None
        
        for window in windows:
            # Group by application if including app name
            if include_app_name and window.app_name != current_app:
                if current_app is not None:
                    lines.append("")  # Add spacing between apps
                lines.append(f"{window.app_name}:")
                current_app = window.app_name
            
            # Format window information
            prefix = "  " if include_app_name else ""
            status_indicators = []
            
            if window.is_active:
                status_indicators.append("active")
            if window.is_minimized:
                status_indicators.append("minimized")
            
            status = f" [{', '.join(status_indicators)}]" if status_indicators else ""
            title = window.title[:50] + "..." if len(window.title) > 50 else window.title
            
            lines.append(f"{prefix}{window.window_id}: {title}{status}")
        
        return "\n".join(lines)
    
    # todo 目前没在使用，后续看看能不能选具体窗口
    def select_window_with_timeout(self, windows: List[WindowInfo], 
                                  timeout: int = 10, 
                                  callback: Optional[Callable[[Optional[WindowInfo]], None]] = None) -> Optional[WindowInfo]:
        """Select a window with timeout support.
        
        Args:
            windows: List of available windows
            timeout: Selection timeout in seconds
            callback: Callback function to call with selected window
            
        Returns:
            Selected window or None if selection failed/timed out
        """
        if not windows:
            if callback:
                callback(None)
            return None
        
        if len(windows) == 1:
            selected = windows[0]
            if callback:
                callback(selected)
            return selected
        
        try:
            # Show window selection
            print("\nMultiple windows found:")
            for i, window in enumerate(windows, 1):
                status_parts = []
                if window.is_active:
                    status_parts.append("active")
                if window.is_minimized:
                    status_parts.append("minimized")
                
                status = f" [{', '.join(status_parts)}]" if status_parts else ""
                title = window.title[:40] + "..." if len(window.title) > 40 else window.title
                print(f"  {i}. {title}{status}")
            
            print(f"\nSelect window (1-{len(windows)}, default=1): ", end="", flush=True)
            
            # Set up timeout
            selection_result = {'window': None, 'timed_out': False}
            
            def timeout_handler():
                selection_result['timed_out'] = True
                print(f"\nSelection timed out after {timeout}s, using first window.")
                selection_result['window'] = windows[0]
                if callback:
                    callback(windows[0])
            
            timer = Timer(timeout, timeout_handler)
            timer.start()
            
            try:
                choice = input().strip()
                timer.cancel()  # Cancel timeout
                
                if selection_result['timed_out']:
                    return selection_result['window']
                
                if not choice:
                    choice = "1"
                
                index = int(choice) - 1
                if 0 <= index < len(windows):
                    selected = windows[index]
                else:
                    logger.warning(f"Invalid selection: {choice}, using first window")
                    selected = windows[0]
                
                if callback:
                    callback(selected)
                return selected
                
            except ValueError:
                timer.cancel()
                logger.warning("Invalid input, using first window")
                selected = windows[0]
                if callback:
                    callback(selected)
                return selected
            except KeyboardInterrupt:
                timer.cancel()
                print("\nSelection cancelled.")
                if callback:
                    callback(None)
                return None
            
        except Exception as e:
            logger.error(f"Error in window selection: {e}")
            selected = windows[0] if windows else None
            if callback:
                callback(selected)
            return selected
    
    # todo这里面调的activate_window方法很慢，考虑优化
    def activate_window_by_id(self, window_id: str) -> bool:
        """Activate a window by its ID.
        
        Args:
            window_id: Window identifier
            
        Returns:
            True if activation was successful, False otherwise
        """
        try:
            import time
            start_time = time.time()
            success = self.platform_adapter.activate_window(window_id)
            duration = (time.time() - start_time) * 1000
            logger.info(f"【hotkey】Platform adapter activate_window - {duration:.2f}ms, success: {success}")  # 平台适配器激活窗口耗时
            if success:
                logger.info(f"Activated window {window_id}")
            else:
                logger.warning(f"Failed to activate window {window_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error activating window {window_id}: {e}")
            return False
    
    def minimize_window_by_id(self, window_id: str) -> bool:
        """Minimize a window by its ID.
        
        Args:
            window_id: Window identifier
            
        Returns:
            True if minimization was successful, False otherwise
        """
        try:
            success = self.platform_adapter.minimize_window(window_id)
            if success:
                logger.info(f"Minimized window {window_id}")
            else:
                logger.warning(f"Failed to minimize window {window_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error minimizing window {window_id}: {e}")
            return False
    
    def close_window_by_id(self, window_id: str) -> bool:
        """Close a window by its ID.
        
        Args:
            window_id: Window identifier
            
        Returns:
            True if closing was successful, False otherwise
        """
        try:
            success = self.platform_adapter.close_window(window_id)
            if success:
                logger.info(f"Closed window {window_id}")
            else:
                logger.warning(f"Failed to close window {window_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error closing window {window_id}: {e}")
            return False
    
    def _perform_window_action(self, window_id: str, action: str, 
                             app_id: Optional[str] = None) -> bool:
        """Perform a specific action on a window.
        
        Args:
            window_id: Window identifier
            action: Action to perform (activate, minimize, close)
            app_id: Application identifier for remembering last used
            
        Returns:
            True if action was successful, False otherwise
        """
        try:
            if action == "activate":
                success = self.activate_window_by_id(window_id)
                if success and app_id:
                    settings = self.config_manager.get_settings()
                    if settings.behavior.remember_last_used:
                        self.config_manager.set_last_used_window(app_id, window_id)
                return success
            elif action == "minimize":
                return self.minimize_window_by_id(window_id)
            elif action == "close":
                return self.close_window_by_id(window_id)
            else:
                logger.error(f"Unknown window action: {action}")
                return False
                
        except Exception as e:
            logger.error(f"Error performing window action {action} on {window_id}: {e}")
            return False
    
    def get_current_terminal_window_id(self) -> Optional[str]:
        """Get the window ID of the current terminal window (if any).
        
        This is typically called when TC starts to register the terminal context.
        
        Returns:
            Window ID of current terminal or None if current window is not a terminal
        """
        try:
            import os
            logger.info(f"【终端切换】获取当前终端窗口ID")
            
            # 修复：首先检查环境变量以确定是否在终端中运行
            term_program = os.environ.get('TERM_PROGRAM', '').lower()
            term_session_id = os.environ.get('TERM_SESSION_ID')
            iterm_session_id = os.environ.get('ITERM_SESSION_ID')
            
            logger.info(f"【终端切换】环境变量检查: TERM_PROGRAM={term_program}, TERM_SESSION_ID={term_session_id}, ITERM_SESSION_ID={iterm_session_id}")
            
            # 如果有明确的终端环境变量，说明我们在终端中运行
            is_in_terminal = term_program or term_session_id or iterm_session_id
            
            if not is_in_terminal:
                logger.info(f"【终端切换】环境变量检查显示未在终端中运行")
                return None
            
            # current_window = self.get_active_window()
            # if not current_window:
            return self._find_terminal_window_by_env()
            
            
            # # Import here to avoid circular imports
            # from .terminal_manager import TerminalManager
            # terminal_manager = TerminalManager(self.config_manager)
            # 
            # # Check if current window is a terminal
            # available_terminals = terminal_manager.get_available_terminals()
            # logger.info(f"【终端切换】可用终端应用: {available_terminals}")
            # 
            # for terminal_id in available_terminals:
                # terminal_config = self.config_manager.get_app_config(terminal_id)
                # if terminal_config:
                    # logger.info(f"【终端切换】检查终端应用: {terminal_id} -> {terminal_config.name}")
                    # if terminal_config.name.lower() in current_window.app_name.lower():
                        # logger.info(f"【终端切换】匹配成功，检测到当前终端窗口: {current_window.window_id} ({current_window.app_name})")
                        # return current_window.window_id
            # 
            # # Also check common terminal application names
            # terminal_names = [
                # 'terminal', 'iterm', 'konsole', 'gnome-terminal', 
                # 'xfce4-terminal', 'cmd', 'powershell', 'windows terminal'
            # ]
            # 
            # logger.info(f"【终端切换】通过通用名称检查终端")
            # for term_name in terminal_names:
                # if term_name in current_window.app_name.lower():
                    # logger.info(f"【终端切换】通过名称匹配成功: {current_window.window_id} ({current_window.app_name})")
                    # return current_window.window_id
            # 
            # # 如果通过环境变量确定在终端中运行，但无法匹配窗口，尝试其他方法
            # if is_in_terminal:
                # logger.info(f"【终端切换】环境变量确认在终端中运行，但窗口匹配失败，尝试其他方法")
                # return self._find_terminal_window_by_env()
            # 
            # logger.info(f"【终端切换】当前窗口不是终端应用")
            # return None
            
        except Exception as e:
            logger.error(f"Error getting current terminal window ID: {e}")
            return None
    
    def _find_terminal_window_by_env(self) -> Optional[str]:
        """通过环境变量和进程信息查找终端窗口ID"""
        try:
            import os
            term_program = os.environ.get('TERM_PROGRAM', '').lower()
            logger.info(f"【终端切换】通过环境变量查找终端窗口: TERM_PROGRAM={term_program}")
            
            # if 'iterm' in term_program:
            # 对于iTerm，尝试获取所有iTerm窗口 - 支持不同的应用名称变体
            possible_names = ["iTerm2"] #后续可以改成可配置的
            iterm_windows = []
            
            for app_name in possible_names:
                windows = self.platform_adapter.get_app_windows(app_name)
                if windows:
                    iterm_windows.extend(windows)
                    logger.info(f"【终端切换】通过应用名称 '{app_name}' 找到 {len(windows)} 个窗口")
                    break
            
            logger.info(f"【终端切换】找到 {len(iterm_windows)} 个iTerm窗口")
            if iterm_windows:
                # 返回第一个窗口（可以进一步优化选择逻辑）
                return iterm_windows[0].window_id
            # elif 'terminal' in term_program:
                # # 对于Terminal.app
                # terminal_windows = self.platform_adapter.get_app_windows("Terminal")
                # logger.info(f"【终端切换】找到 {len(terminal_windows)} 个Terminal窗口")
                # if terminal_windows:
                    # return terminal_windows[0].window_id
            
            return None
        except Exception as e:
            logger.error(f"通过环境变量查找终端窗口失败: {e}")
            return None
    
    def cleanup(self):
        """Clean up resources used by the window manager."""
        try:
            # Cancel any running selection timers
            for timer in self._selection_timers.values():
                if timer.is_alive():
                    timer.cancel()
            self._selection_timers.clear()
            
            logger.info("WindowManager cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during WindowManager cleanup: {e}")
