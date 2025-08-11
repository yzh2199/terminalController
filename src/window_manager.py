"""Window management module for Terminal Controller."""
import logging
import time
from typing import List, Optional, Dict, Any, Callable
from threading import Timer

from .platform import get_platform_adapter, PlatformAdapter
from .platform.base import WindowInfo
from .config_manager import ConfigManager


logger = logging.getLogger(__name__)


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
    
    def activate_window_by_id(self, window_id: str) -> bool:
        """Activate a window by its ID.
        
        Args:
            window_id: Window identifier
            
        Returns:
            True if activation was successful, False otherwise
        """
        try:
            success = self.platform_adapter.activate_window(window_id)
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
    
    def get_active_window(self) -> Optional[WindowInfo]:
        """Get information about the currently active window.
        
        Returns:
            Current active window information or None if not available
        """
        try:
            return self.platform_adapter.get_active_window()
        except Exception as e:
            logger.error(f"Error getting active window: {e}")
            return None
    
    def find_windows_by_title(self, title_pattern: str, 
                             app_name: Optional[str] = None) -> List[WindowInfo]:
        """Find windows by title pattern.
        
        Args:
            title_pattern: Pattern to match in window titles
            app_name: Optional application name to filter by
            
        Returns:
            List of matching windows
        """
        try:
            all_windows = self.list_all_windows(app_name)
            matching_windows = []
            
            title_lower = title_pattern.lower()
            for window in all_windows:
                if title_lower in window.title.lower():
                    matching_windows.append(window)
            
            return matching_windows
            
        except Exception as e:
            logger.error(f"Error finding windows by title: {e}")
            return []
    
    def find_window_by_id(self, window_id: str) -> Optional[WindowInfo]:
        """Find a window by its ID.
        
        Args:
            window_id: Window identifier to search for
            
        Returns:
            Window information if found, None otherwise
        """
        try:
            all_windows = self.list_all_windows()
            for window in all_windows:
                if window.window_id == window_id:
                    return window
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding window by ID: {e}")
            return None
    
    def focus_most_recent_window(self, app_id: str) -> bool:
        """Focus the most recently used window for an application.
        
        Args:
            app_id: Application identifier
            
        Returns:
            True if successful, False otherwise
        """
        try:
            settings = self.config_manager.get_settings()
            
            # Try to get last used window
            if settings.behavior.remember_last_used:
                last_used_id = self.config_manager.get_last_used_window(app_id)
                if last_used_id:
                    window = self.find_window_by_id(last_used_id)
                    if window:
                        success = self.activate_window_by_id(last_used_id)
                        if success:
                            return True
            
            # Fallback to application windows
            app_config = self.config_manager.get_app_config(app_id)
            if not app_config:
                return False
            
            windows = self.platform_adapter.get_app_windows(app_config.name)
            if not windows:
                return False
            
            # Find active window first
            for window in windows:
                if window.is_active:
                    return self.activate_window_by_id(window.window_id)
            
            # Find non-minimized window
            for window in windows:
                if not window.is_minimized:
                    success = self.activate_window_by_id(window.window_id)
                    if success and settings.behavior.remember_last_used:
                        self.config_manager.set_last_used_window(app_id, window.window_id)
                    return success
            
            # Use first window as last resort
            window = windows[0]
            success = self.activate_window_by_id(window.window_id)
            if success and settings.behavior.remember_last_used:
                self.config_manager.set_last_used_window(app_id, window.window_id)
            
            return success
            
        except Exception as e:
            logger.error(f"Error focusing most recent window for {app_id}: {e}")
            return False
    
    def handle_multi_window_selection(self, app_id: str, 
                                    action: str = "activate") -> bool:
        """Handle window selection when multiple windows exist for an application.
        
        Args:
            app_id: Application identifier
            action: Action to perform on selected window (activate, minimize, close)
            
        Returns:
            True if action was successful, False otherwise
        """
        try:
            app_config = self.config_manager.get_app_config(app_id)
            if not app_config:
                logger.error(f"Unknown application: {app_id}")
                return False
            
            windows = self.platform_adapter.get_app_windows(app_config.name)
            if not windows:
                logger.warning(f"No windows found for {app_config.name}")
                return False
            
            if len(windows) == 1:
                # Single window, perform action directly
                window = windows[0]
                return self._perform_window_action(window.window_id, action, app_id)
            
            # Multiple windows, check if we should show selection
            settings = self.config_manager.get_settings()
            if not settings.behavior.show_window_selection:
                # Use most recent window without showing selection
                return self.focus_most_recent_window(app_id)
            
            # Show selection interface
            selected_window = self.select_window_with_timeout(
                windows, 
                settings.behavior.window_selection_timeout
            )
            
            if selected_window:
                success = self._perform_window_action(
                    selected_window.window_id, 
                    action, 
                    app_id
                )
                return success
            else:
                logger.warning("No window selected")
                return False
                
        except Exception as e:
            logger.error(f"Error handling multi-window selection for {app_id}: {e}")
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
