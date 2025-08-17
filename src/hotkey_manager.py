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
                    logger.warning("【hotkey】HotkeyManager is already active")
                    return True
                
                logger.info("【hotkey】Starting HotkeyManager and registering configured hotkeys")
                
                # Load and register hotkeys from configuration
                success = self._register_configured_hotkeys()
                logger.info(f"【hotkey】Configured hotkeys registration result: {success}")
                
                if success:
                    self._active = True
                    logger.info("【hotkey】HotkeyManager started successfully")
                else:
                    logger.error("【hotkey】Failed to register configured hotkeys")
                
                return success
                
        except Exception as e:
            logger.error(f"【hotkey】Error starting HotkeyManager: {e}", exc_info=True)
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
                        logger.error(f"【hotkey】Error in hotkey callback for {binding_id}: {e}")
                
                logger.info(f"【hotkey】Registering hotkey binding: id={binding_id}, hotkey={hotkey}, desc='{description}'")

                # Register with platform adapter
                success = self.platform_adapter.register_hotkey(hotkey, safe_callback)
                logger.info(f"【hotkey】Platform adapter register_hotkey result for {binding_id}: {success}")
                
                if success:
                    self._bindings[binding_id] = HotkeyBinding(
                        hotkey=hotkey,
                        callback=callback,
                        description=description
                    )
                    logger.info(f"【hotkey】Registered hotkey {hotkey} for {binding_id}")
                else:
                    logger.error(f"【hotkey】Failed to register hotkey {hotkey} for {binding_id}")
                
                return success
                
        except Exception as e:
            logger.error(f"【hotkey】Error registering hotkey {binding_id}: {e}")
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
    
    def get_platform_hotkey(self) -> str:
        """Get platform-specific hotkey string.
            
        Returns:
            Platform-specific hotkey string
        """
        settings = self.config_manager.get_settings()
        
        if self.current_platform == "darwin":
            return settings.hotkeys.terminal
        elif self.current_platform == "linux":
            return settings.hotkeys.terminal_linux
        elif self.current_platform == "windows":
            return settings.hotkeys.terminal_windows
    
    def _register_configured_hotkeys(self) -> bool:
        """Register hotkeys from configuration.
        
        Returns:
            True if all configured hotkeys were registered successfully
        """
        try:
            settings = self.config_manager.get_settings()
            success = True
            
            # Register terminal hotkey
            terminal_hotkey = self.get_platform_hotkey()
            logger.info(f"【hotkey】Configured terminal hotkey resolved to: '{terminal_hotkey}' for platform {self.current_platform}")
            if terminal_hotkey:
                logger.info(f"【hotkey】Creating terminal callback and registering hotkey...")
                terminal_callback = self._create_terminal_callback()
                register_result = self.register_hotkey(
                    "config_terminal", 
                    terminal_hotkey, 
                    terminal_callback,
                    "Launch terminal application"
                )
                logger.info(f"【hotkey】Terminal hotkey registration result: {register_result}")
                if not register_result:
                    success = False
            else:
                logger.warning("【hotkey】No terminal hotkey configured")
            
            # TODO: Add more configured hotkeys here

            
            logger.info(f"Configured hotkeys registration completed. Overall success: {success}")
            return success
            
        except Exception as e:
            logger.error(f"Error registering configured hotkeys: {e}", exc_info=True)
            return False
    
    # 热键回调的关键方法，作为回调方法注册到pynuput库的GlobalHotKeys，当热键被触发时，会调用这个方法里创建的terminal_callback方法
    def _create_terminal_callback(self) -> Callable:
        """Create callback function for terminal hotkey.
        
        Returns:
            Callback function that toggles terminal visibility
        """
        logger.info("Creating terminal callback function")
        def terminal_callback():
            try:
                import time
                logger.info("【hotkey_triggered】Terminal hotkey callback triggered")  # 热键回调触发的日志
                
                # Import here to avoid circular imports
                from .terminal_manager import TerminalManager
                from .window_manager import WindowManager
                
                terminal_manager = TerminalManager(self.config_manager)
                window_manager = WindowManager(self.config_manager)
                
                action_start_time = time.time()
                success = self._smart_focus_terminal(window_manager, terminal_manager)
                action_time = (time.time() - action_start_time) * 1000
                logger.info(f"【hotkey_triggered】Smart focus terminal completed - {action_time:.2f}ms, success: {success}")  # 智能聚焦终端耗时
                if success:
                    logger.info("【hotkey_triggered】Smart terminal focus completed via hotkey")
                else:
                    logger.error("【hotkey_triggered】Failed to focus/launch terminal via hotkey")
                    
            except Exception as e:
                logger.error(f"【hotkey_triggered】Error in terminal hotkey callback: {e}")
        
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
    
    # todo 阅读这段逻辑，寻找回到tc终端流程的优化点，考虑复用这个找到终端的逻辑到找到其他程序的特定窗口
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
            
            # 【hotkey】查找活跃的交互会话 - 精确识别运行TC的终端
            sessions_start_time = time.time()
            active_sessions = self.config_manager.get_active_interactive_sessions()
            sessions_time = (time.time() - sessions_start_time) * 1000
            logger.info(f"【hotkey_triggered】Get active interactive sessions - {sessions_time:.2f}ms, count: {len(active_sessions)}")  # 获取活跃交互会话耗时
            
            # 如果找到活跃的交互会话，优先切换到这些终端
            if active_sessions:
                # 选择最近启动的会话（通常是用户最后使用的）
                latest_session = max(active_sessions, key=lambda s: s.get('started_at', 0))
                session_window_id = latest_session.get('window_id')
                
                if session_window_id:
                    activate_start_time = time.time()
                    success = window_manager.activate_window_by_id(session_window_id)
                    activate_time = (time.time() - activate_start_time) * 1000
                    logger.info(f"【hotkey_triggered】Activate interactive session window - {activate_time:.2f}ms, success: {success}")  # 激活交互会话窗口耗时
                    
                    if success:
                        logger.debug(f"Focused active interactive session: {session_window_id}")
                        return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error in smart focus terminal: {e}")
            return False
    
    def cleanup(self):
        """Clean up resources used by the hotkey manager."""
        try:
            self.stop()
            logger.info("HotkeyManager cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during HotkeyManager cleanup: {e}")
