"""Application management module for Terminal Controller."""
import platform as std_platform
import logging
from typing import List, Optional, Dict, Any
from pathlib import Path
import time

from .platform import get_platform_adapter, PlatformAdapter
from .platform.base import WindowInfo, AppInfo
from .config_manager import ConfigManager, AppConfig, WebsiteConfig


logger = logging.getLogger(__name__)


class AppManager:
    """Manages application launching, window control, and URL opening."""
    
    def __init__(self, config_manager: ConfigManager):
        """Initialize the application manager.
        
        Args:
            config_manager: Configuration manager instance
        """
        self.config_manager = config_manager
        self.platform_adapter: PlatformAdapter = get_platform_adapter()()
        self.current_platform = std_platform.system().lower()
        
        logger.info(f"Initialized AppManager for platform: {self.current_platform}")
    
    def launch_app(self, app_id: str, website_id: Optional[str] = None, 
                   url: Optional[str] = None, force_new: bool = False) -> bool:
        """Launch an application, optionally opening a website or URL.
        
        Args:
            app_id: Application identifier from configuration
            website_id: Website identifier to open (optional)
            url: Direct URL to open (optional)
            force_new: Force new window/instance
            
        Returns:
            True if launch was successful, False otherwise
        """
        try:
            logger.info(f"【launch_app】启动应用: app_id={app_id}, force_new={force_new}")
            app_config = self.config_manager.get_app_config(app_id)
            if not app_config:
                logger.error(f"Unknown application: {app_id}")
                return False
            
            logger.info(f"【launch_app】应用配置: name={app_config.name}, type={app_config.type}")
            
            # 对终端的特殊逻辑已经在main中处理
            # if app_config.type == "terminal" and not force_new:
                # logger.info(f"【终端切换】检测到终端应用，进入特殊处理逻辑")
                # success = self._handle_terminal_launch(app_id, app_config)
                # logger.info(f"【终端切换】_handle_terminal_launch返回结果: {success}")
                # if success is not None:  # 如果处理了终端切换逻辑，直接返回
                    # return success
                # else:
                    # logger.info(f"【终端切换】未执行切换逻辑，继续正常启动流程")
            
            # Get platform-specific executable path
            executable_path = self._get_executable_path(app_config)
            if not executable_path:
                logger.error(f"【launch_app】No executable found for {app_id} on {self.current_platform}")
                return False
            
            # Prepare arguments
            args = app_config.args.copy() if app_config.args else []
            
            # Handle URL opening for browser applications
            target_url = None
            if website_id:
                website_config = self.config_manager.get_website_config(website_id)
                if website_config:
                    target_url = website_config.url
                else:
                    logger.warning(f"【launch_app】Unknown website: {website_id}")
            elif url:
                target_url = url
            
            logger.info(f"【launch_app】args: {args}, target_url: {target_url}")
            
            # Launch application
            if app_config.type == "browser" and target_url:
                # Special handling for browsers with URLs
                # todo 这里需要修复，目前无法打开特定链接
                success = self._launch_browser_with_url(executable_path, target_url, 
                                                     args, force_new)
            else:
                # Standard application launch
                if force_new or 'new' in args:
                    if '--new-window' not in args:
                        args.append('--new-window')
                
                start_time = time.time()
                success = self.platform_adapter.launch_app(
                    executable_path, 
                    args=args,
                    cwd=Path.home()
                )
                end_time = time.time()
                logger.info(f"【launch_app】应用启动完成: {app_config.name}, 耗时: {(end_time - start_time) * 1000:.2f}ms")

            if success:
                logger.info(f"【launch_app】Successfully launched {app_config.name}")
                
                # Open URL separately if not a browser
                if target_url and app_config.type != "browser":
                    self.platform_adapter.open_url(target_url, executable_path)
                
                return True
            else:
                logger.error(f"【launch_app】Failed to launch {app_config.name}")
                return False
                
        except Exception as e:
            logger.error(f"【launch_app】Error launching app {app_id}: {e}")
            return False
    
    def get_app_windows(self, app_id: str) -> List[WindowInfo]:
        """Get all windows for a specific application.
        
        Args:
            app_id: Application identifier
            
        Returns:
            List of window information for the application
        """
        try:
            app_config = self.config_manager.get_app_config(app_id)
            if not app_config:
                logger.error(f"Unknown application: {app_id}")
                return []
            
            windows = self.platform_adapter.get_app_windows(app_config.name)
            
            # Sort windows by title for consistent ordering
            windows.sort(key=lambda w: w.title)
            
            logger.debug(f"Found {len(windows)} windows for {app_config.name}")
            return windows
            
        except Exception as e:
            logger.error(f"Error getting windows for {app_id}: {e}")
            return []
    
    def activate_window(self, app_id: str, window_id: Optional[str] = None) -> bool:
        """Activate a specific window or the most recently used window.
        
        Args:
            app_id: Application identifier
            window_id: Specific window ID to activate (optional)
            
        Returns:
            True if window was activated successfully, False otherwise
        """
        try:
            if window_id:
                # Activate specific window
                success = self.platform_adapter.activate_window(window_id)
                if success:
                    # Remember this as the last used window
                    if self.config_manager.get_settings().behavior.remember_last_used:
                        self.config_manager.set_last_used_window(app_id, window_id)
                    logger.info(f"Activated window {window_id}")
                return success
            else:
                # Get last used window or first available window
                target_window = self._get_target_window(app_id)
                if target_window:
                    success = self.platform_adapter.activate_window(target_window.window_id)
                    if success:
                        if self.config_manager.get_settings().behavior.remember_last_used:
                            self.config_manager.set_last_used_window(app_id, target_window.window_id)
                        logger.info(f"Activated window {target_window.window_id} for {app_id}")
                    return success
                else:
                    logger.warning(f"No windows found for {app_id}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error activating window for {app_id}: {e}")
            return False
    
    def minimize_window(self, app_id: str, window_id: Optional[str] = None) -> bool:
        """Minimize a specific window or all windows of an application.
        
        Args:
            app_id: Application identifier
            window_id: Specific window ID to minimize (optional)
            
        Returns:
            True if window(s) were minimized successfully, False otherwise
        """
        try:
            if window_id:
                # Minimize specific window
                success = self.platform_adapter.minimize_window(window_id)
                if success:
                    logger.info(f"Minimized window {window_id}")
                return success
            else:
                # Minimize all windows for the application
                windows = self.get_app_windows(app_id)
                if not windows:
                    logger.warning(f"No windows found for {app_id}")
                    return False
                
                success_count = 0
                for window in windows:
                    if self.platform_adapter.minimize_window(window.window_id):
                        success_count += 1
                
                logger.info(f"Minimized {success_count}/{len(windows)} windows for {app_id}")
                return success_count > 0
                
        except Exception as e:
            logger.error(f"Error minimizing window for {app_id}: {e}")
            return False
    
    def close_window(self, app_id: str, window_id: Optional[str] = None) -> bool:
        """Close a specific window or all windows of an application.
        
        Args:
            app_id: Application identifier
            window_id: Specific window ID to close (optional)
            
        Returns:
            True if window(s) were closed successfully, False otherwise
        """
        try:
            if window_id:
                # Close specific window
                success = self.platform_adapter.close_window(window_id)
                if success:
                    logger.info(f"Closed window {window_id}")
                return success
            else:
                # Close all windows for the application
                windows = self.get_app_windows(app_id)
                if not windows:
                    logger.warning(f"No windows found for {app_id}")
                    return False
                
                success_count = 0
                for window in windows:
                    if self.platform_adapter.close_window(window.window_id):
                        success_count += 1
                
                logger.info(f"Closed {success_count}/{len(windows)} windows for {app_id}")
                return success_count > 0
                
        except Exception as e:
            logger.error(f"Error closing window for {app_id}: {e}")
            return False
    
    def is_app_running(self, app_id: str) -> bool:
        """Check if an application is currently running.
        
        Args:
            app_id: Application identifier
            
        Returns:
            True if the application is running, False otherwise
        """
        try:
            app_config = self.config_manager.get_app_config(app_id)
            if not app_config:
                return False
            
            return self.platform_adapter.is_app_running(app_config.name)
            
        except Exception as e:
            logger.error(f"Error checking if app {app_id} is running: {e}")
            return False
    
    def kill_app(self, app_id: str, force: bool = False) -> bool:
        """Terminate an application.
        
        Args:
            app_id: Application identifier
            force: Whether to force termination
            
        Returns:
            True if termination was successful, False otherwise
        """
        try:
            app_config = self.config_manager.get_app_config(app_id)
            if not app_config:
                logger.error(f"Unknown application: {app_id}")
                return False
            
            success = self.platform_adapter.kill_app(app_config.name, force)
            if success:
                logger.info(f"Terminated {app_config.name}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error terminating app {app_id}: {e}")
            return False
    
    def open_url(self, url: str, app_id: Optional[str] = None) -> bool:
        """Open a URL in the default or specified browser.
        
        Args:
            url: URL to open
            app_id: Specific browser application to use (optional)
            
        Returns:
            True if URL was opened successfully, False otherwise
        """
        try:
            browser_path = None
            if app_id:
                app_config = self.config_manager.get_app_config(app_id)
                if app_config:
                    browser_path = self._get_executable_path(app_config)
            
            success = self.platform_adapter.open_url(url, browser_path)
            if success:
                logger.info(f"Opened URL: {url}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error opening URL {url}: {e}")
            return False
    
    def get_running_apps(self) -> List[AppInfo]:
        """Get information about all running applications.
        
        Returns:
            List of running application information
        """
        try:
            return self.platform_adapter.get_running_apps()
        except Exception as e:
            logger.error(f"Error getting running apps: {e}")
            return []
    
    def select_window_interactive(self, windows: List[WindowInfo], 
                                 timeout: int = 10) -> Optional[WindowInfo]:
        """Interactively select a window from multiple options.
        
        Args:
            windows: List of available windows
            timeout: Selection timeout in seconds
            
        Returns:
            Selected window or None if selection failed/timed out
        """
        if not windows:
            return None
        
        if len(windows) == 1:
            return windows[0]
        
        try:
            print("\nMultiple windows found:")
            for i, window in enumerate(windows, 1):
                status = " (active)" if window.is_active else ""
                minimized = " [minimized]" if window.is_minimized else ""
                print(f"  {i}. {window.title}{status}{minimized}")
            
            print(f"\nSelect window (1-{len(windows)}, default=1, timeout={timeout}s): ", end="", flush=True)
            
            # TODO: Implement proper timeout input handling
            # For now, use simple input without timeout
            try:
                choice = input().strip()
                if not choice:
                    choice = "1"
                
                index = int(choice) - 1
                if 0 <= index < len(windows):
                    return windows[index]
                else:
                    logger.warning(f"Invalid selection: {choice}")
                    return windows[0]  # Default to first window
                    
            except ValueError:
                logger.warning(f"Invalid input, using first window")
                return windows[0]
            
        except Exception as e:
            logger.error(f"Error in window selection: {e}")
            return windows[0] if windows else None
    
    def _get_executable_path(self, app_config: AppConfig) -> Optional[str]:
        """Get the platform-specific executable path for an application.
        
        Args:
            app_config: Application configuration
            
        Returns:
            Executable path for the current platform or None if not found
        """
        executables = app_config.executable
        
        # Try current platform first
        if self.current_platform in executables:
            path = executables[self.current_platform]
            normalized_path = self.platform_adapter.normalize_app_path(path)
            return normalized_path
        
        # Fallback to generic paths
        fallback_keys = ['default', 'generic', 'all']
        for key in fallback_keys:
            if key in executables:
                path = executables[key]
                normalized_path = self.platform_adapter.normalize_app_path(path)
                return normalized_path
        
        return None
    
    def _get_target_window(self, app_id: str) -> Optional[WindowInfo]:
        """Get the target window for an application (last used or first available).
        
        Args:
            app_id: Application identifier
            
        Returns:
            Target window or None if no windows found
        """
        windows = self.get_app_windows(app_id)
        if not windows:
            return None
        
        # Try to get last used window if remember_last_used is enabled
        settings = self.config_manager.get_settings()
        if settings.behavior.remember_last_used:
            last_used_id = self.config_manager.get_last_used_window(app_id)
            if last_used_id:
                for window in windows:
                    if window.window_id == last_used_id:
                        return window
        
        # Find active window first
        for window in windows:
            if window.is_active:
                return window
        
        # Find non-minimized window
        for window in windows:
            if not window.is_minimized:
                return window
        
        # Return first window as fallback
        return windows[0]
    
    def _launch_browser_with_url(self, browser_path: str, url: str, 
                                args: List[str], force_new: bool) -> bool:
        """Launch a browser application with a specific URL.
        
        Args:
            browser_path: Path to browser executable
            url: URL to open
            args: Additional arguments
            force_new: Force new window
            
        Returns:
            True if launch was successful, False otherwise
        """
        try:
            # Prepare browser-specific arguments
            browser_args = args.copy()
            
            # Add URL to arguments
            browser_args.append(url)
            
            # Force new window if requested
            if force_new:
                if '--new-window' not in browser_args:
                    browser_args.insert(0, '--new-window')
            
            return self.platform_adapter.launch_app(
                browser_path,
                args=browser_args,
                cwd=Path.home()
            )
            
        except Exception as e:
            logger.error(f"Error launching browser with URL: {e}")
            return False
    
    # def _handle_terminal_launch(self, app_id: str, app_config: AppConfig) -> Optional[bool]:
        # """Handle terminal application launch with special logic for switching windows.
        # 
        # 当在交互模式下启动终端应用时，如果当前正在终端中运行脚本，
        # 应该切换到其他已存在的终端窗口，而不是启动新的。
        # 
        # Args:
            # app_id: Terminal application identifier
            # app_config: Terminal application configuration
            # 
        # Returns:
            # True if window switching was successful, False if failed, 
            # None if should proceed with normal launch
        # """
        # try:
            # logger.info(f"【终端切换】开始处理终端启动逻辑: app_id={app_id}")
            # 
            # # Check if we're currently running in a terminal context
            # tc_context_window = self.config_manager.get_tc_context_window()
            # logger.info(f"【终端切换】TC上下文窗口ID: {tc_context_window}")
            # if not tc_context_window:
                # logger.info(f"【终端切换】未在终端上下文中运行，使用正常启动")
                # return None
            # 
            # # Get all windows for this terminal application
            # terminal_windows = self.get_app_windows(app_id)
            # logger.info(f"【终端切换】找到终端窗口数量: {len(terminal_windows)}")
            # for i, win in enumerate(terminal_windows):
                # logger.info(f"【终端切换】窗口{i}: id={win.window_id}, title='{win.title}', minimized={win.is_minimized}")
                # 
            # if not terminal_windows:
                # logger.info(f"【终端切换】无终端窗口存在，使用正常启动")
                # return None
            # 
            # # Filter out the current terminal window (the one running the script)
            # other_windows = [w for w in terminal_windows if w.window_id != tc_context_window]
            # logger.info(f"【终端切换】过滤当前窗口后剩余窗口数: {len(other_windows)}")
            # 
            # if not other_windows:
                # logger.info(f"【终端切换】只有当前终端窗口，使用正常启动")
                # return None
            # 
            # # Find the best window to switch to
            # target_window = self._select_terminal_window_to_switch(other_windows, app_id)
            # logger.info(f"【终端切换】选择的目标窗口: {target_window.window_id if target_window else None}")
            # if target_window:
                # logger.info(f"【终端切换】目标窗口详情: title='{target_window.title}', minimized={target_window.is_minimized}")
                # # Switch to the selected terminal window
                # logger.info(f"【终端切换】尝试激活窗口: {target_window.window_id}")
                # success = self.platform_adapter.activate_window(target_window.window_id)
                # logger.info(f"【终端切换】窗口激活结果: {success}")
                # if success:
                    # logger.info(f"Switched to existing {app_config.name} window: {target_window.title}")
                    # # Remember this as the last used window
                    # settings = self.config_manager.get_settings()
                    # if settings.behavior.remember_last_used:
                        # self.config_manager.set_last_used_window(app_id, target_window.window_id)
                    # return True
                # else:
                    # logger.warning(f"Failed to switch to terminal window {target_window.window_id}")
                    # return False
            # 
            # # No suitable window found, proceed with normal launch
            # logger.info(f"【终端切换】未找到合适窗口，使用正常启动")
            # return None
            # 
        # except Exception as e:
            # logger.error(f"Error in terminal launch handling: {e}")
            # return None
    
    def _select_terminal_window_to_switch(self, windows: List[WindowInfo], app_id: str) -> Optional[WindowInfo]:
        """Select the best terminal window to switch to.
        
        Args:
            windows: List of available terminal windows (excluding current)
            app_id: Terminal application identifier
            
        Returns:
            Best window to switch to, or None if none suitable
        """
        if not windows:
            return None
        
        # Try to get last used window if remember_last_used is enabled
        settings = self.config_manager.get_settings()
        if settings.behavior.remember_last_used:
            last_used_id = self.config_manager.get_last_used_window(app_id)
            if last_used_id:
                for window in windows:
                    if window.window_id == last_used_id:
                        return window
        
        # Prefer non-minimized windows
        non_minimized = [w for w in windows if not w.is_minimized]
        if non_minimized:
            # Return the first non-minimized window (could be made smarter)
            return non_minimized[0]
        
        # If all windows are minimized, return the first one
        return windows[0]
