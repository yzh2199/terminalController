"""Windows platform adapter implementation."""
import os
import subprocess
import psutil
import logging
from typing import List, Dict, Any, Optional, Callable

from .base import PlatformAdapter, WindowInfo, AppInfo

try:
    from pynput import keyboard
    from pynput.keyboard import Key, Listener
except ImportError:
    keyboard = None
    Key = None
    Listener = None

try:
    import win32gui
    import win32con
    import win32process
    import win32api
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False


logger = logging.getLogger(__name__)


class WindowsAdapter(PlatformAdapter):
    """Windows-specific implementation of platform adapter."""
    
    def __init__(self):
        self._hotkey_listeners = {}
        self._running_listener = None
    
    def launch_app(self, app_path: str, args: Optional[List[str]] = None, 
                   cwd: Optional[str] = None) -> bool:
        """Launch an application on Windows."""
        try:
            normalized_path = self.normalize_app_path(app_path)
            cmd = [normalized_path]
            if args:
                cmd.extend(args)
            
            subprocess.Popen(
                cmd,
                cwd=cwd or os.path.expanduser('~'),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
            )
            return True
            
        except Exception as e:
            logger.error(f"Failed to launch app {app_path}: {e}")
            return False
    
    def get_running_apps(self, app_name: Optional[str] = None) -> List[AppInfo]:
        """Get information about running applications."""
        apps = []
        
        try:
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
                        windows=self.get_app_windows(name)
                    )
                    apps.append(app_info)
                    
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
                    
        except Exception as e:
            logger.error(f"Failed to get running apps: {e}")
        
        return apps
    
    def get_app_windows(self, app_name: str) -> List[WindowInfo]:
        """Get windows for a specific application using Win32 API."""
        windows = []
        
        if not HAS_WIN32:
            return windows
        
        try:
            def enum_windows_callback(hwnd, results):
                if win32gui.IsWindowVisible(hwnd):
                    window_title = win32gui.GetWindowText(hwnd)
                    if window_title:
                        try:
                            _, pid = win32process.GetWindowThreadProcessId(hwnd)
                            proc = psutil.Process(pid)
                            if app_name.lower() in proc.name().lower():
                                windows.append(WindowInfo(
                                    window_id=str(hwnd),
                                    title=window_title,
                                    app_name=app_name,
                                    is_active=hwnd == win32gui.GetForegroundWindow(),
                                    is_minimized=win32gui.IsIconic(hwnd)
                                ))
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
                return True
            
            win32gui.EnumWindows(enum_windows_callback, None)
            
        except Exception as e:
            logger.error(f"Failed to get windows for {app_name}: {e}")
        
        return windows
    
    def activate_window(self, window_id: str) -> bool:
        """Activate a specific window using Win32 API."""
        if not HAS_WIN32:
            return False
        
        try:
            hwnd = int(window_id)
            
            # Restore window if minimized
            if win32gui.IsIconic(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            
            # Bring window to foreground
            win32gui.SetForegroundWindow(hwnd)
            return True
            
        except Exception as e:
            logger.error(f"Failed to activate window {window_id}: {e}")
            return False
    
    def minimize_window(self, window_id: str) -> bool:
        """Minimize a specific window."""
        if not HAS_WIN32:
            return False
        
        try:
            hwnd = int(window_id)
            win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
            return True
            
        except Exception as e:
            logger.error(f"Failed to minimize window {window_id}: {e}")
            return False
    
    def close_window(self, window_id: str) -> bool:
        """Close a specific window."""
        if not HAS_WIN32:
            return False
        
        try:
            hwnd = int(window_id)
            win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
            return True
            
        except Exception as e:
            logger.error(f"Failed to close window {window_id}: {e}")
            return False
    
    def register_hotkey(self, hotkey: str, callback: Callable) -> bool:
        """Register a global hotkey using pynput."""
        if not keyboard:
            logger.error("pynput not available for hotkey registration")
            return False
        
        try:
            # Parse hotkey string (e.g., "ctrl+shift+t")
            key_combination = self._parse_hotkey(hotkey)
            if not key_combination:
                return False
            
            def on_hotkey():
                try:
                    callback()
                except Exception as e:
                    logger.error(f"Hotkey callback error: {e}")
            
            # Stop existing listener if present
            if self._running_listener:
                self._running_listener.stop()
            
            # Create new listener
            self._running_listener = keyboard.GlobalHotKeys({
                hotkey: on_hotkey
            })
            self._running_listener.start()
            
            self._hotkey_listeners[hotkey] = self._running_listener
            return True
            
        except Exception as e:
            logger.error(f"Failed to register hotkey {hotkey}: {e}")
            return False
    
    def unregister_hotkey(self, hotkey: str) -> bool:
        """Unregister a global hotkey."""
        try:
            if hotkey in self._hotkey_listeners:
                listener = self._hotkey_listeners[hotkey]
                listener.stop()
                del self._hotkey_listeners[hotkey]
                return True
            return False
            
        except Exception as e:
            logger.error(f"Failed to unregister hotkey {hotkey}: {e}")
            return False
    
    def get_active_window(self) -> Optional[WindowInfo]:
        """Get information about the currently active window."""
        if not HAS_WIN32:
            return None
        
        try:
            hwnd = win32gui.GetForegroundWindow()
            if hwnd:
                window_title = win32gui.GetWindowText(hwnd)
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                
                try:
                    proc = psutil.Process(pid)
                    app_name = proc.name()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    app_name = ""
                
                return WindowInfo(
                    window_id=str(hwnd),
                    title=window_title,
                    app_name=app_name,
                    is_active=True,
                    is_minimized=win32gui.IsIconic(hwnd)
                )
                
        except Exception as e:
            logger.error(f"Failed to get active window: {e}")
        
        return None
    
    def is_app_running(self, app_name: str) -> bool:
        """Check if an application is currently running."""
        try:
            for proc in psutil.process_iter(['name']):
                try:
                    if app_name.lower() in proc.info['name'].lower():
                        return True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
                    
        except Exception as e:
            logger.error(f"Failed to check if app is running: {e}")
        
        return False
    
    def kill_app(self, app_name: str, force: bool = False) -> bool:
        """Terminate an application."""
        try:
            if force:
                subprocess.run(['taskkill', '/f', '/im', app_name], check=False)
            else:
                subprocess.run(['taskkill', '/im', app_name], check=False)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to kill app {app_name}: {e}")
            return False
    
    def open_url(self, url: str) -> bool:
        """Open a URL."""
        try:
            # Use start command to open with default browser
            subprocess.run(['start', url], shell=True, check=False)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to open URL {url}: {e}")
            return False
    
    def get_default_terminal(self) -> str:
        """Get the default terminal application for Windows."""
        # Check for Windows Terminal first, then fallback to cmd
        terminals = [
            "wt.exe",  # Windows Terminal
            "cmd.exe",  # Command Prompt
            "powershell.exe"  # PowerShell
        ]
        
        for terminal in terminals:
            try:
                subprocess.run(['where', terminal], 
                             check=True, 
                             stdout=subprocess.DEVNULL)
                return terminal
            except subprocess.CalledProcessError:
                continue
        
        # Fallback to cmd
        return "cmd.exe"
    
    def normalize_app_path(self, app_path: str) -> str:
        """Normalize application path for Windows."""
        # Expand user home directory
        path = os.path.expanduser(app_path)
        
        # If it doesn't have an extension, try common ones
        if not os.path.splitext(path)[1]:
            for ext in ['.exe', '.com', '.bat', '.cmd']:
                test_path = path + ext
                if os.path.exists(test_path):
                    return test_path
        
        # If it's not an absolute path, try to find it in PATH
        if not os.path.isabs(path):
            try:
                result = subprocess.run(['where', path], 
                                      capture_output=True, 
                                      text=True)
                if result.returncode == 0:
                    return result.stdout.strip().split('\n')[0]
            except Exception:
                pass
        
        return path
    
    def _parse_hotkey(self, hotkey: str) -> Optional[str]:
        """Parse hotkey string and convert to pynput format."""
        # Convert common key names
        key_mapping = {
            'ctrl': 'ctrl',
            'alt': 'alt',
            'shift': 'shift',
            'win': 'cmd',  # Windows key
            'windows': 'cmd'
        }
        
        # Split and normalize keys
        keys = [key.strip().lower() for key in hotkey.split('+')]
        normalized_keys = []
        
        for key in keys:
            if key in key_mapping:
                normalized_keys.append(f'<{key_mapping[key]}>')
            elif len(key) == 1:
                normalized_keys.append(key)
            else:
                # Handle special keys
                normalized_keys.append(f'<{key}>')
        
        return '+'.join(normalized_keys) if normalized_keys else None
