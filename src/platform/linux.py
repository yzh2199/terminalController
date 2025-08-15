"""Linux platform adapter implementation."""
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
    import Xlib
    import Xlib.display
    HAS_XLIB = True
except ImportError:
    HAS_XLIB = False


logger = logging.getLogger(__name__)


class LinuxAdapter(PlatformAdapter):
    """Linux-specific implementation of platform adapter."""
    
    def __init__(self):
        self._hotkey_listeners = {}
        self._running_listener = None
        self._display = None
        
        if HAS_XLIB:
            try:
                self._display = Xlib.display.Display()
            except Exception as e:
                logger.warning(f"Could not connect to X display: {e}")
    
    def launch_app(self, app_path: str, args: Optional[List[str]] = None, 
                   cwd: Optional[str] = None) -> bool:
        """Launch an application on Linux."""
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
                start_new_session=True
            )
            return True
            
        except Exception as e:
            logger.error(f"Failed to launch app {app_path}: {e}")
            return False
    
    def get_running_apps(self, app_name: Optional[str] = None) -> List[AppInfo]:
        """Get information about running applications."""
        apps = []
        
        try:
            for proc in psutil.process_iter(['pid', 'name', 'exe', 'cmdline']):
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
        """Get windows for a specific application using wmctrl."""
        windows = []
        
        try:
            # Try using wmctrl first
            result = subprocess.run(
                ['wmctrl', '-l'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if line:
                        parts = line.split(None, 3)
                        if len(parts) >= 4:
                            window_id = parts[0]
                            title = parts[3]
                            
                            # Check if window belongs to the app
                            if self._is_window_for_app(window_id, app_name):
                                windows.append(WindowInfo(
                                    window_id=window_id,
                                    title=title,
                                    app_name=app_name,
                                    is_active=False,
                                    is_minimized=False
                                ))
            
            # Fallback to xwininfo if wmctrl fails
            elif HAS_XLIB and self._display:
                windows.extend(self._get_windows_xlib(app_name))
                
        except Exception as e:
            logger.error(f"Failed to get windows for {app_name}: {e}")
        
        return windows
    
    def activate_window(self, window_id: str) -> bool:
        """Activate a specific window using wmctrl."""
        try:
            # Try wmctrl first
            result = subprocess.run(
                ['wmctrl', '-i', '-a', window_id],
                capture_output=True,
                timeout=5
            )
            
            if result.returncode == 0:
                return True
            
            # Fallback to xdotool
            result = subprocess.run(
                ['xdotool', 'windowactivate', window_id],
                capture_output=True,
                timeout=5
            )
            
            return result.returncode == 0
            
        except Exception as e:
            logger.error(f"Failed to activate window {window_id}: {e}")
            return False
    
    def minimize_window(self, window_id: str) -> bool:
        """Minimize a specific window."""
        try:
            # Try xdotool
            result = subprocess.run(
                ['xdotool', 'windowminimize', window_id],
                capture_output=True,
                timeout=5
            )
            
            if result.returncode == 0:
                return True
            
            # Fallback to wmctrl
            result = subprocess.run(
                ['wmctrl', '-i', '-c', window_id],
                capture_output=True,
                timeout=5
            )
            
            return result.returncode == 0
            
        except Exception as e:
            logger.error(f"Failed to minimize window {window_id}: {e}")
            return False
    
    def close_window(self, window_id: str) -> bool:
        """Close a specific window."""
        try:
            # Try wmctrl first
            result = subprocess.run(
                ['wmctrl', '-i', '-c', window_id],
                capture_output=True,
                timeout=5
            )
            
            if result.returncode == 0:
                return True
            
            # Fallback to xdotool
            result = subprocess.run(
                ['xdotool', 'windowclose', window_id],
                capture_output=True,
                timeout=5
            )
            
            return result.returncode == 0
            
        except Exception as e:
            logger.error(f"Failed to close window {window_id}: {e}")
            return False
    
    def register_hotkey(self, hotkey: str, callback: Callable) -> bool:
        """Register a global hotkey using pynput."""
        if not keyboard:
            logger.error("pynput not available for hotkey registration")
            return False
        
        try:
            # Parse hotkey string (e.g., "ctrl+alt+t")
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
        try:
            # Try using xdotool
            result = subprocess.run(
                ['xdotool', 'getactivewindow'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                window_id = result.stdout.strip()
                
                # Get window title
                title_result = subprocess.run(
                    ['xdotool', 'getwindowname', window_id],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                title = title_result.stdout.strip() if title_result.returncode == 0 else ""
                
                return WindowInfo(
                    window_id=window_id,
                    title=title,
                    app_name="",  # Would need additional lookup
                    is_active=True,
                    is_minimized=False
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
                subprocess.run(['killall', '-9', app_name], check=False)
            else:
                subprocess.run(['killall', app_name], check=False)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to kill app {app_name}: {e}")
            return False
    
    def open_url(self, url: str) -> bool:
        """Open a URL."""
        try:
            # Try common methods to open URL
            for cmd in ['xdg-open', 'firefox', 'chromium', 'google-chrome']:
                try:
                    subprocess.run([cmd, url], check=False)
                    return True
                except FileNotFoundError:
                    continue
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to open URL {url}: {e}")
            return False
    
    def get_default_terminal(self) -> str:
        """Get the default terminal application for Linux."""
        # Check for common terminal applications
        terminals = [
            'gnome-terminal',
            'konsole',
            'xfce4-terminal',
            'terminator',
            'tilix',
            'alacritty',
            'kitty',
            'xterm'
        ]
        
        for terminal in terminals:
            try:
                subprocess.run(['which', terminal], 
                             check=True, 
                             stdout=subprocess.DEVNULL)
                return terminal
            except subprocess.CalledProcessError:
                continue
        
        # Fallback to xterm
        return 'xterm'
    
    def normalize_app_path(self, app_path: str) -> str:
        """Normalize application path for Linux."""
        # Expand user home directory
        path = os.path.expanduser(app_path)
        
        # If it's not an absolute path, try to find it in PATH
        if not path.startswith('/'):
            try:
                result = subprocess.run(['which', path], 
                                      capture_output=True, 
                                      text=True)
                if result.returncode == 0:
                    return result.stdout.strip()
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
            'super': 'cmd',  # Super key (Windows key)
            'meta': 'cmd'
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
    
    def _is_window_for_app(self, window_id: str, app_name: str) -> bool:
        """Check if a window belongs to a specific application."""
        try:
            # Get window PID
            result = subprocess.run(
                ['xdotool', 'getwindowpid', window_id],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                pid = int(result.stdout.strip())
                proc = psutil.Process(pid)
                return app_name.lower() in proc.name().lower()
                
        except Exception:
            pass
        
        return False
    
    def _get_windows_xlib(self, app_name: str) -> List[WindowInfo]:
        """Get windows using Xlib as fallback."""
        windows = []
        
        if not self._display:
            return windows
        
        try:
            root = self._display.screen().root
            window_ids = root.get_full_property(
                self._display.intern_atom('_NET_CLIENT_LIST'),
                Xlib.X.AnyPropertyType
            ).value
            
            for window_id in window_ids:
                try:
                    window = self._display.create_resource_object('window', window_id)
                    window_name = window.get_wm_name()
                    
                    if window_name and app_name.lower() in window_name.lower():
                        windows.append(WindowInfo(
                            window_id=str(window_id),
                            title=window_name,
                            app_name=app_name,
                            is_active=False,
                            is_minimized=False
                        ))
                        
                except Exception:
                    continue
                    
        except Exception as e:
            logger.error(f"Failed to get windows via Xlib: {e}")
        
        return windows
