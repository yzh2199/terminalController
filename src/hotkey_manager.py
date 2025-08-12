"""Hotkey management module for Terminal Controller."""
import logging
import threading
import time
from typing import Dict, Callable, Optional, List
from dataclasses import dataclass

from .platform import get_platform_adapter, PlatformAdapter
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


@dataclass
class HotkeyBinding:
    """Represents a hotkey binding."""
    hotkey: str
    callback: Callable
    description: str
    enabled: bool = True


class HotkeyManager:
    """Manages global hotkey registration and handling."""
    
    def __init__(self, config_manager: ConfigManager):
        """Initialize the hotkey manager.
        
        Args:
            config_manager: Configuration manager instance
        """
        self.config_manager = config_manager
        self.platform_adapter: PlatformAdapter = get_platform_adapter()()
        import sys
        # 避免命名冲突，直接使用sys.platform
        p = sys.platform.lower()
        if p.startswith("darwin") or p in ("mac", "macos"):
            self.current_platform = "darwin"
        elif p.startswith("linux"):
            self.current_platform = "linux"
        elif p.startswith("win"):
            self.current_platform = "windows"
        else:
            self.current_platform = p
        
        self._bindings: Dict[str, HotkeyBinding] = {}
        self._active = False
        self._lock = threading.RLock()  # Use RLock to allow re-entrance
        
        logger.info(f"Initialized HotkeyManager for platform: {self.current_platform}")
    
    def start(self) -> bool:
        """Start the hotkey manager and register configured hotkeys.
        
        Returns:
            True if started successfully, False otherwise
        """
        try:
            with self._lock:
                if self._active:
                    logger.warning("HotkeyManager is already active")
                    return True
                
                logger.info("Starting HotkeyManager and registering configured hotkeys")
                
                # Load and register hotkeys from configuration
                success = self._register_configured_hotkeys()
                logger.info(f"Configured hotkeys registration result: {success}")
                
                if success:
                    self._active = True
                    logger.info("HotkeyManager started successfully")
                else:
                    logger.error("Failed to register configured hotkeys")
                
                return success
                
        except Exception as e:
            logger.error(f"Error starting HotkeyManager: {e}", exc_info=True)
            return False
    
    def stop(self) -> bool:
        """Stop the hotkey manager and unregister all hotkeys.
        
        Returns:
            True if stopped successfully, False otherwise
        """
        try:
            with self._lock:
                if not self._active:
                    logger.warning("HotkeyManager is not active")
                    return True
                
                # Unregister all hotkeys
                success = True
                for binding_id in list(self._bindings.keys()):
                    if not self.unregister_hotkey(binding_id):
                        success = False
                
                self._active = False
                logger.info("HotkeyManager stopped")
                
                return success
                
        except Exception as e:
            logger.error(f"Error stopping HotkeyManager: {e}")
            return False
    
    def register_hotkey(self, binding_id: str, hotkey: str, 
                       callback: Callable, description: str = "") -> bool:
        """Register a new hotkey binding.
        
        Args:
            binding_id: Unique identifier for the binding
            hotkey: Hotkey string (e.g., "cmd+shift+t")
            callback: Function to call when hotkey is pressed
            description: Description of what the hotkey does
            
        Returns:
            True if registration was successful, False otherwise
        """
        try:
            with self._lock:
                if binding_id in self._bindings:
                    logger.warning(f"Hotkey binding {binding_id} already exists, replacing")
                    self.unregister_hotkey(binding_id)
                
                # Create wrapper callback for error handling
                def safe_callback():
                    try:
                        callback()
                    except Exception as e:
                        logger.error(f"Error in hotkey callback for {binding_id}: {e}")
                
                logger.info(f"Registering hotkey binding: id={binding_id}, hotkey={hotkey}, desc='{description}'")

                # Register with platform adapter
                success = self.platform_adapter.register_hotkey(hotkey, safe_callback)
                logger.info(f"Platform adapter register_hotkey result for {binding_id}: {success}")
                
                if success:
                    self._bindings[binding_id] = HotkeyBinding(
                        hotkey=hotkey,
                        callback=callback,
                        description=description
                    )
                    logger.info(f"Registered hotkey {hotkey} for {binding_id}")
                else:
                    logger.error(f"Failed to register hotkey {hotkey} for {binding_id}")
                
                return success
                
        except Exception as e:
            logger.error(f"Error registering hotkey {binding_id}: {e}")
            return False
    
    def unregister_hotkey(self, binding_id: str) -> bool:
        """Unregister a hotkey binding.
        
        Args:
            binding_id: Identifier of the binding to unregister
            
        Returns:
            True if unregistration was successful, False otherwise
        """
        try:
            with self._lock:
                if binding_id not in self._bindings:
                    logger.warning(f"Hotkey binding {binding_id} not found")
                    return False
                
                binding = self._bindings[binding_id]
                success = self.platform_adapter.unregister_hotkey(binding.hotkey)
                
                if success:
                    del self._bindings[binding_id]
                    logger.info(f"Unregistered hotkey {binding.hotkey} for {binding_id}")
                else:
                    logger.error(f"Failed to unregister hotkey {binding.hotkey} for {binding_id}")
                
                return success
                
        except Exception as e:
            logger.error(f"Error unregistering hotkey {binding_id}: {e}")
            return False
    
    def enable_hotkey(self, binding_id: str) -> bool:
        """Enable a disabled hotkey binding.
        
        Args:
            binding_id: Identifier of the binding to enable
            
        Returns:
            True if enabled successfully, False otherwise
        """
        try:
            with self._lock:
                if binding_id not in self._bindings:
                    logger.error(f"Hotkey binding {binding_id} not found")
                    return False
                
                binding = self._bindings[binding_id]
                if binding.enabled:
                    logger.warning(f"Hotkey binding {binding_id} is already enabled")
                    return True
                
                # Re-register the hotkey
                success = self.platform_adapter.register_hotkey(
                    binding.hotkey, 
                    binding.callback
                )
                
                if success:
                    binding.enabled = True
                    logger.info(f"Enabled hotkey binding {binding_id}")
                
                return success
                
        except Exception as e:
            logger.error(f"Error enabling hotkey {binding_id}: {e}")
            return False
    
    def disable_hotkey(self, binding_id: str) -> bool:
        """Disable a hotkey binding without removing it.
        
        Args:
            binding_id: Identifier of the binding to disable
            
        Returns:
            True if disabled successfully, False otherwise
        """
        try:
            with self._lock:
                if binding_id not in self._bindings:
                    logger.error(f"Hotkey binding {binding_id} not found")
                    return False
                
                binding = self._bindings[binding_id]
                if not binding.enabled:
                    logger.warning(f"Hotkey binding {binding_id} is already disabled")
                    return True
                
                # Unregister from platform
                success = self.platform_adapter.unregister_hotkey(binding.hotkey)
                
                if success:
                    binding.enabled = False
                    logger.info(f"Disabled hotkey binding {binding_id}")
                
                return success
                
        except Exception as e:
            logger.error(f"Error disabling hotkey {binding_id}: {e}")
            return False
    
    def get_bindings(self) -> Dict[str, HotkeyBinding]:
        """Get all hotkey bindings.
        
        Returns:
            Dictionary of all hotkey bindings
        """
        with self._lock:
            return self._bindings.copy()
    
    def get_binding(self, binding_id: str) -> Optional[HotkeyBinding]:
        """Get a specific hotkey binding.
        
        Args:
            binding_id: Identifier of the binding
            
        Returns:
            HotkeyBinding object or None if not found
        """
        with self._lock:
            return self._bindings.get(binding_id)
    
    def is_active(self) -> bool:
        """Check if the hotkey manager is active.
        
        Returns:
            True if active, False otherwise
        """
        with self._lock:
            return self._active
    
    def reload_configuration(self) -> bool:
        """Reload hotkey configuration from config manager.
        
        Returns:
            True if reload was successful, False otherwise
        """
        try:
            logger.info("Reloading hotkey configuration")
            
            # Unregister existing configured hotkeys
            configured_bindings = [bid for bid in self._bindings.keys() 
                                 if bid.startswith('config_')]
            
            for binding_id in configured_bindings:
                self.unregister_hotkey(binding_id)
            
            # Re-register configured hotkeys
            return self._register_configured_hotkeys()
            
        except Exception as e:
            logger.error(f"Error reloading hotkey configuration: {e}")
            return False
    
    def format_bindings_list(self) -> str:
        """Format all bindings for display.
        
        Returns:
            Formatted string of all hotkey bindings
        """
        with self._lock:
            if not self._bindings:
                return "No hotkey bindings registered."
            
            lines = ["Registered Hotkey Bindings:"]
            for binding_id, binding in self._bindings.items():
                status = "enabled" if binding.enabled else "disabled"
                description = binding.description or "No description"
                lines.append(f"  {binding_id}: {binding.hotkey} ({status}) - {description}")
            
            return "\n".join(lines)
    
    def get_platform_hotkey(self, hotkey_type: str) -> str:
        """Get platform-specific hotkey string.
        
        Args:
            hotkey_type: Type of hotkey (e.g., 'terminal')
            
        Returns:
            Platform-specific hotkey string
        """
        settings = self.config_manager.get_settings()
        
        if hotkey_type == "terminal":
            if self.current_platform == "darwin":
                return settings.hotkeys.terminal
            elif self.current_platform == "linux":
                return settings.hotkeys.terminal_linux
            elif self.current_platform == "windows":
                return settings.hotkeys.terminal_windows
        
        # Fallback to default
        return getattr(settings.hotkeys, hotkey_type, "")
    
    def _register_configured_hotkeys(self) -> bool:
        """Register hotkeys from configuration.
        
        Returns:
            True if all configured hotkeys were registered successfully
        """
        try:
            settings = self.config_manager.get_settings()
            success = True
            
            # Register terminal hotkey
            terminal_hotkey = self.get_platform_hotkey("terminal")
            logger.info(f"Configured terminal hotkey resolved to: '{terminal_hotkey}' for platform {self.current_platform}")
            if terminal_hotkey:
                logger.info(f"Creating terminal callback and registering hotkey...")
                terminal_callback = self._create_terminal_callback()
                register_result = self.register_hotkey(
                    "config_terminal", 
                    terminal_hotkey, 
                    terminal_callback,
                    "Launch terminal application"
                )
                logger.info(f"Terminal hotkey registration result: {register_result}")
                if not register_result:
                    success = False
            else:
                logger.warning("No terminal hotkey configured")
            
            # TODO: Add more configured hotkeys here
            # For example, hotkeys for specific applications or actions
            
            logger.info(f"Configured hotkeys registration completed. Overall success: {success}")
            return success
            
        except Exception as e:
            logger.error(f"Error registering configured hotkeys: {e}", exc_info=True)
            return False
    
    def _create_terminal_callback(self) -> Callable:
        """Create callback function for terminal hotkey.
        
        Returns:
            Callback function that toggles terminal visibility
        """
        logger.info("Creating terminal callback function")
        def terminal_callback():
            try:
                import time
                callback_start_time = time.time()
                logger.info("【hotkey】Terminal hotkey callback triggered")  # 热键回调触发的日志
                
                # Import here to avoid circular imports
                from .terminal_manager import TerminalManager
                from .window_manager import WindowManager
                
                init_start_time = time.time()
                terminal_manager = TerminalManager(self.config_manager)
                window_manager = WindowManager(self.config_manager)
                init_time = (time.time() - init_start_time) * 1000
                logger.info(f"【hotkey】Manager initialization completed - {init_time:.2f}ms")  # 管理器初始化耗时
                
                # Get current active window
                window_start_time = time.time()
                current_window = window_manager.get_active_window()
                window_time = (time.time() - window_start_time) * 1000
                logger.info(f"【hotkey】Get active window completed - {window_time:.2f}ms")  # 获取活动窗口耗时
                
                # Check if current window is a terminal
                if current_window:
                    check_start_time = time.time()
                    is_terminal = self._is_terminal_window(current_window, terminal_manager)
                    check_time = (time.time() - check_start_time) * 1000
                    logger.info(f"【hotkey】Terminal window check completed - {check_time:.2f}ms, is_terminal: {is_terminal}")  # 终端窗口检查耗时
                else:
                    is_terminal = False
                    logger.info("【hotkey】No current window found, treating as non-terminal")  # 无当前窗口
                
                if current_window and is_terminal:
                    # Current window is terminal, use smart return logic
                    action_start_time = time.time()
                    success = self._smart_return_from_terminal(window_manager, terminal_manager)
                    action_time = (time.time() - action_start_time) * 1000
                    logger.info(f"【hotkey】Smart return from terminal completed - {action_time:.2f}ms, success: {success}")  # 智能返回耗时
                    if success:
                        logger.info("Smart return completed via hotkey")
                    else:
                        logger.warning("Could not complete smart return, no suitable window found")
                else:
                    # Current window is not terminal, use smart terminal focus
                    # First save current window as previous window
                    if current_window:
                        save_start_time = time.time()
                        self._save_previous_window(current_window)
                        save_time = (time.time() - save_start_time) * 1000
                        logger.info(f"【hotkey】Save previous window completed - {save_time:.2f}ms")  # 保存前一个窗口耗时
                    
                    action_start_time = time.time()
                    success = self._smart_focus_terminal(window_manager, terminal_manager)
                    action_time = (time.time() - action_start_time) * 1000
                    logger.info(f"【hotkey】Smart focus terminal completed - {action_time:.2f}ms, success: {success}")  # 智能聚焦终端耗时
                    if success:
                        logger.info("Smart terminal focus completed via hotkey")
                    else:
                        logger.error("Failed to focus/launch terminal via hotkey")
                
                total_time = (time.time() - callback_start_time) * 1000
                logger.info(f"【hotkey】Total hotkey callback execution time - {total_time:.2f}ms")  # 总回调执行时间
                    
            except Exception as e:
                logger.error(f"Error in terminal hotkey callback: {e}")
        
        logger.info("Terminal callback function created successfully")
        return terminal_callback
    
    def _create_app_callback(self, app_id: str) -> Callable:
        """Create callback function for application launch hotkey.
        
        Args:
            app_id: Application identifier
            
        Returns:
            Callback function that launches the application
        """
        def app_callback():
            try:
                # Import here to avoid circular imports
                from .app_manager import AppManager
                
                app_manager = AppManager(self.config_manager)
                success = app_manager.launch_app(app_id)
                
                if success:
                    logger.info(f"Application {app_id} launched via hotkey")
                else:
                    logger.error(f"Failed to launch application {app_id} via hotkey")
                    
            except Exception as e:
                logger.error(f"Error in app hotkey callback for {app_id}: {e}")
        
        return app_callback
    
    def register_app_hotkey(self, app_id: str, hotkey: str) -> bool:
        """Register a hotkey for launching a specific application.
        
        Args:
            app_id: Application identifier
            hotkey: Hotkey string
            
        Returns:
            True if registration was successful, False otherwise
        """
        try:
            app_config = self.config_manager.get_app_config(app_id)
            if not app_config:
                logger.error(f"Unknown application: {app_id}")
                return False
            
            callback = self._create_app_callback(app_id)
            description = f"Launch {app_config.name}"
            
            return self.register_hotkey(f"app_{app_id}", hotkey, callback, description)
            
        except Exception as e:
            logger.error(f"Error registering app hotkey for {app_id}: {e}")
            return False
    
    def unregister_app_hotkey(self, app_id: str) -> bool:
        """Unregister a hotkey for an application.
        
        Args:
            app_id: Application identifier
            
        Returns:
            True if unregistration was successful, False otherwise
        """
        return self.unregister_hotkey(f"app_{app_id}")
    
    def _is_terminal_window(self, window_info, terminal_manager) -> bool:
        """Check if a window belongs to a terminal application.
        
        Args:
            window_info: WindowInfo object
            terminal_manager: TerminalManager instance
            
        Returns:
            True if window is a terminal, False otherwise
        """
        try:
            # Get list of available terminal applications
            available_terminals = terminal_manager.get_available_terminals()
            
            for terminal_id in available_terminals:
                terminal_config = self.config_manager.get_app_config(terminal_id)
                if terminal_config and terminal_config.name.lower() in window_info.app_name.lower():
                    return True
            
            # Also check common terminal application names
            terminal_names = [
                'terminal', 'iterm', 'konsole', 'gnome-terminal', 
                'xfce4-terminal', 'cmd', 'powershell', 'windows terminal'
            ]
            
            for term_name in terminal_names:
                if term_name in window_info.app_name.lower():
                    return True
                    
            return False
            
        except Exception as e:
            logger.error(f"Error checking if window is terminal: {e}")
            return False
    
    def _save_previous_window(self, window_info) -> None:
        """Save the current window as the previous window.
        
        Args:
            window_info: WindowInfo object of current window
        """
        try:
            # Store the previous window info in a simple way
            # We'll use a special key to store non-terminal window info
            self.config_manager.set_last_used_window("_previous_window", window_info.window_id)
            # Also store the app name for easier retrieval
            self.config_manager.set_last_used_window("_previous_app", window_info.app_name)
            logger.debug(f"Saved previous window: {window_info.app_name} ({window_info.window_id})")
            
        except Exception as e:
            logger.error(f"Error saving previous window: {e}")
    
    def _smart_return_from_terminal(self, window_manager, terminal_manager) -> bool:
        """Smart return logic when current window is a terminal.
        
        Args:
            window_manager: WindowManager instance
            terminal_manager: TerminalManager instance
            
        Returns:
            True if successfully returned to a suitable window, False otherwise
        """
        try:
            # Priority 1: Return to previous non-terminal window
            success = self._return_to_previous_window(window_manager)
            if success:
                logger.debug("Returned to previous non-terminal window")
                return True
            
            # Priority 2: If no previous window, try to find a good alternative
            logger.debug("No previous window found, looking for alternatives")
            return self._find_best_non_terminal_window(window_manager, terminal_manager)
            
        except Exception as e:
            logger.error(f"Error in smart return from terminal: {e}")
            return False
    
    def _smart_focus_terminal(self, window_manager, terminal_manager) -> bool:
        """Smart terminal focus logic when current window is not a terminal.
        
        Args:
            window_manager: WindowManager instance
            terminal_manager: TerminalManager instance
            
        Returns:
            True if successfully focused/launched terminal, False otherwise
        """
        try:
            import time
            
            # Priority 0: 【hotkey】优先查找活跃的交互会话 - 精确识别运行TC的终端
            sessions_start_time = time.time()
            active_sessions = self.config_manager.get_active_interactive_sessions()
            sessions_time = (time.time() - sessions_start_time) * 1000
            logger.info(f"【hotkey】Get active interactive sessions - {sessions_time:.2f}ms, count: {len(active_sessions)}")  # 获取活跃交互会话耗时
            
            # 如果找到活跃的交互会话，优先切换到这些终端
            if active_sessions:
                # 选择最近启动的会话（通常是用户最后使用的）
                latest_session = max(active_sessions, key=lambda s: s.get('started_at', 0))
                session_window_id = latest_session.get('window_id')
                
                if session_window_id:
                    activate_start_time = time.time()
                    success = window_manager.activate_window_by_id(session_window_id)
                    activate_time = (time.time() - activate_start_time) * 1000
                    logger.info(f"【hotkey】Activate interactive session window - {activate_time:.2f}ms, success: {success}")  # 激活交互会话窗口耗时
                    
                    if success:
                        logger.debug(f"Focused active interactive session: {session_window_id}")
                        return True
            
            # Priority 1: Try to focus TC context terminal (where TC is/was running)
            context_start_time = time.time()
            tc_context_window_id = self.config_manager.get_tc_context_window()
            context_get_time = (time.time() - context_start_time) * 1000
            logger.info(f"【hotkey】Get TC context window - {context_get_time:.2f}ms, window_id: {tc_context_window_id}")  # 获取TC上下文窗口耗时
            
            if tc_context_window_id:
                find_start_time = time.time()
                window = window_manager.find_window_by_id(tc_context_window_id)
                find_time = (time.time() - find_start_time) * 1000
                logger.info(f"【hotkey】Find window by ID - {find_time:.2f}ms, found: {window is not None}")  # 根据ID查找窗口耗时
                
                if window and self._is_terminal_window(window, terminal_manager):
                    activate_start_time = time.time()
                    success = window_manager.activate_window_by_id(tc_context_window_id)
                    activate_time = (time.time() - activate_start_time) * 1000
                    logger.info(f"【hotkey】Activate TC context window - {activate_time:.2f}ms, success: {success}")  # 激活TC上下文窗口耗时
                    if success:
                        logger.debug(f"Focused TC context terminal: {tc_context_window_id}")
                        return True
                else:
                    # TC context window no longer exists, clear it
                    clear_start_time = time.time()
                    self.config_manager.clear_tc_context_window()
                    clear_time = (time.time() - clear_start_time) * 1000
                    logger.info(f"【hotkey】Clear TC context window - {clear_time:.2f}ms")  # 清除TC上下文窗口耗时
                    logger.debug("TC context window no longer exists, clearing")
            
            # Priority 2: Try to focus existing terminal using original logic
            settings_start_time = time.time()
            settings = self.config_manager.get_settings()
            default_terminal_id = settings.terminal.default
            settings_time = (time.time() - settings_start_time) * 1000
            logger.info(f"【hotkey】Get settings and default terminal - {settings_time:.2f}ms, terminal: {default_terminal_id}")  # 获取设置和默认终端耗时
            
            running_check_start_time = time.time()
            is_running = terminal_manager.is_terminal_running(default_terminal_id)
            running_check_time = (time.time() - running_check_start_time) * 1000
            logger.info(f"【hotkey】Check terminal running status - {running_check_time:.2f}ms, is_running: {is_running}")  # 检查终端运行状态耗时
            
            if is_running:
                focus_start_time = time.time()
                success = window_manager.focus_most_recent_window(default_terminal_id)
                focus_time = (time.time() - focus_start_time) * 1000
                logger.info(f"【hotkey】Focus most recent window - {focus_time:.2f}ms, success: {success}")  # 聚焦最近窗口耗时
                if success:
                    logger.debug("Focused existing terminal using original logic")
                    return True
            
            # Priority 3: Launch new terminal if no existing one or focus failed
            launch_start_time = time.time()
            success = terminal_manager.launch_terminal()
            launch_time = (time.time() - launch_start_time) * 1000
            logger.info(f"【hotkey】Launch new terminal - {launch_time:.2f}ms, success: {success}")  # 启动新终端耗时
            if success:
                logger.debug("Launched new terminal")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error in smart focus terminal: {e}")
            return False
    
    def _find_best_non_terminal_window(self, window_manager, terminal_manager) -> bool:
        """Find the best non-terminal window to focus on.
        
        Args:
            window_manager: WindowManager instance
            terminal_manager: TerminalManager instance
            
        Returns:
            True if found and focused a good window, False otherwise
        """
        try:
            all_windows = window_manager.list_all_windows()
            
            # Filter out terminal windows and find the best candidate
            non_terminal_windows = []
            for window in all_windows:
                if not self._is_terminal_window(window, terminal_manager) and not window.is_minimized:
                    non_terminal_windows.append(window)
            
            if not non_terminal_windows:
                logger.debug("No suitable non-terminal windows found")
                return False
            
            # Prefer active windows first, then recent ones
            for window in non_terminal_windows:
                if window.is_active:
                    success = window_manager.activate_window_by_id(window.window_id)
                    if success:
                        self._save_previous_window(window)
                        logger.debug(f"Focused active non-terminal window: {window.app_name}")
                        return True
            
            # If no active window, use the first available
            window = non_terminal_windows[0]
            success = window_manager.activate_window_by_id(window.window_id)
            if success:
                self._save_previous_window(window)
                logger.debug(f"Focused first available non-terminal window: {window.app_name}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error finding best non-terminal window: {e}")
            return False
    
    def _return_to_previous_window(self, window_manager) -> bool:
        """Return to the previously active non-terminal window.
        
        Args:
            window_manager: WindowManager instance
            
        Returns:
            True if successfully returned to previous window, False otherwise
        """
        try:
            # Get stored previous window ID
            previous_window_id = self.config_manager.get_last_used_window("_previous_window")
            previous_app_name = self.config_manager.get_last_used_window("_previous_app")
            
            if not previous_window_id:
                logger.debug("No previous window stored")
                return False
            
            # Try to activate the previous window
            window = window_manager.find_window_by_id(previous_window_id)
            if window and window.app_name == previous_app_name:
                success = window_manager.activate_window_by_id(previous_window_id)
                if success:
                    logger.debug(f"Successfully returned to previous window: {previous_app_name}")
                    return True
            
            # If exact window not found, try to find any window of the same app
            if previous_app_name:
                all_windows = window_manager.list_all_windows()
                for window in all_windows:
                    if window.app_name == previous_app_name and not window.is_minimized:
                        success = window_manager.activate_window_by_id(window.window_id)
                        if success:
                            # Update the stored window ID to the new one
                            self.config_manager.set_last_used_window("_previous_window", window.window_id)
                            logger.debug(f"Returned to alternative window of same app: {previous_app_name}")
                            return True
            
            logger.debug("Could not find previous window to return to")
            return False
            
        except Exception as e:
            logger.error(f"Error returning to previous window: {e}")
            return False

    def cleanup(self):
        """Clean up resources used by the hotkey manager."""
        try:
            self.stop()
            logger.info("HotkeyManager cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during HotkeyManager cleanup: {e}")
