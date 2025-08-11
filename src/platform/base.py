"""Base platform adapter interface."""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass


@dataclass
class WindowInfo:
    """Information about an application window."""
    window_id: str
    title: str
    app_name: str
    is_active: bool
    is_minimized: bool
    position: tuple = (0, 0)
    size: tuple = (0, 0)


@dataclass
class AppInfo:
    """Information about a running application."""
    pid: int
    name: str
    executable_path: str
    windows: List[WindowInfo]


class PlatformAdapter(ABC):
    """Abstract base class for platform-specific implementations."""
    
    @abstractmethod
    def launch_app(self, app_path: str, args: Optional[List[str]] = None, 
                   cwd: Optional[str] = None) -> bool:
        """Launch an application.
        
        Args:
            app_path: Path to the application executable
            args: Command line arguments
            cwd: Working directory
            
        Returns:
            True if launch was successful, False otherwise
        """
        pass
    
    @abstractmethod
    def get_running_apps(self, app_name: Optional[str] = None) -> List[AppInfo]:
        """Get information about running applications.
        
        Args:
            app_name: Filter by application name (optional)
            
        Returns:
            List of running application information
        """
        pass
    
    @abstractmethod
    def get_app_windows(self, app_name: str) -> List[WindowInfo]:
        """Get windows for a specific application.
        
        Args:
            app_name: Name of the application
            
        Returns:
            List of window information for the application
        """
        pass
    
    @abstractmethod
    def activate_window(self, window_id: str) -> bool:
        """Activate (bring to front) a specific window.
        
        Args:
            window_id: Unique identifier for the window
            
        Returns:
            True if activation was successful, False otherwise
        """
        pass
    
    @abstractmethod
    def minimize_window(self, window_id: str) -> bool:
        """Minimize a specific window.
        
        Args:
            window_id: Unique identifier for the window
            
        Returns:
            True if minimization was successful, False otherwise
        """
        pass
    
    @abstractmethod
    def close_window(self, window_id: str) -> bool:
        """Close a specific window.
        
        Args:
            window_id: Unique identifier for the window
            
        Returns:
            True if closing was successful, False otherwise
        """
        pass
    
    @abstractmethod
    def register_hotkey(self, hotkey: str, callback: Callable) -> bool:
        """Register a global hotkey.
        
        Args:
            hotkey: Hotkey string (e.g., "cmd+shift+t")
            callback: Function to call when hotkey is pressed
            
        Returns:
            True if registration was successful, False otherwise
        """
        pass
    
    @abstractmethod
    def unregister_hotkey(self, hotkey: str) -> bool:
        """Unregister a global hotkey.
        
        Args:
            hotkey: Hotkey string to unregister
            
        Returns:
            True if unregistration was successful, False otherwise
        """
        pass
    
    @abstractmethod
    def get_active_window(self) -> Optional[WindowInfo]:
        """Get information about the currently active window.
        
        Returns:
            Window information for the active window, or None if not available
        """
        pass
    
    @abstractmethod
    def is_app_running(self, app_name: str) -> bool:
        """Check if an application is currently running.
        
        Args:
            app_name: Name of the application to check
            
        Returns:
            True if the application is running, False otherwise
        """
        pass
    
    @abstractmethod
    def kill_app(self, app_name: str, force: bool = False) -> bool:
        """Terminate an application.
        
        Args:
            app_name: Name of the application to terminate
            force: Whether to force termination
            
        Returns:
            True if termination was successful, False otherwise
        """
        pass
    
    @abstractmethod
    def open_url(self, url: str, browser_path: Optional[str] = None) -> bool:
        """Open a URL in the default or specified browser.
        
        Args:
            url: URL to open
            browser_path: Path to specific browser (optional)
            
        Returns:
            True if URL was opened successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def get_default_terminal(self) -> str:
        """Get the default terminal application for this platform.
        
        Returns:
            Path or command for the default terminal
        """
        pass
    
    @abstractmethod
    def normalize_app_path(self, app_path: str) -> str:
        """Normalize application path for the current platform.
        
        Args:
            app_path: Application path to normalize
            
        Returns:
            Normalized application path
        """
        pass
