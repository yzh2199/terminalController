"""macOS platform adapter implementation."""
import os
import subprocess
import psutil
import logging
from typing import List, Dict, Any, Optional, Callable
from urllib.parse import quote

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


class MacOSAdapter(PlatformAdapter):
    """macOS-specific implementation of platform adapter."""
    
    def __init__(self):
        self._hotkey_listeners = {}
        self._running_listener = None
    
    def launch_app(self, app_path: str, args: Optional[List[str]] = None, 
                   cwd: Optional[str] = None) -> bool:
        """Launch an application on macOS."""
        try:
            normalized_path = self.normalize_app_path(app_path)
            
            if normalized_path.endswith('.app'):
                # Use 'open' command for .app bundles
                cmd = ['open', '-a', normalized_path]
                if args:
                    cmd.extend(['--args'] + args)
            else:
                # Direct executable
                cmd = [normalized_path]
                if args:
                    cmd.extend(args)
            
            subprocess.Popen(
                cmd,
                cwd=cwd or os.path.expanduser('~'),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            return True
            
        except Exception as e:
            logger.error(f"Failed to launch app {app_path}: {e}")
            return False
    
    def get_running_apps(self, app_name: Optional[str] = None) -> List[AppInfo]:
        """Get information about running applications."""
        apps = []
        
        try:
            if HAS_COCOA:
                # Use Cocoa API for better accuracy
                workspace = NSWorkspace.sharedWorkspace()
                running_apps = workspace.runningApplications()
                
                for app in running_apps:
                    if app.activationPolicy() == 0:  # Regular applications only
                        name = str(app.localizedName())
                        if app_name and app_name.lower() not in name.lower():
                            continue
                        
                        app_info = AppInfo(
                            pid=app.processIdentifier(),
                            name=name,
                            executable_path=str(app.executableURL().path()) if app.executableURL() else "",
                            windows=self.get_app_windows(name)
                        )
                        apps.append(app_info)
            else:
                # Fallback to psutil
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
            logger.error(f"Failed to get running apps: {e}")
        
        return apps
    
    def get_app_windows(self, app_name: str) -> List[WindowInfo]:
        """Get windows for a specific application using AppleScript."""
        windows = []
        
        try:
            # Use AppleScript to get window information
            script = f'''
            tell application "System Events"
                try
                    set appProcess to first process whose name is "{app_name}"
                    set windowList to windows of appProcess
                    set windowInfo to {{}}
                    repeat with w in windowList
                        set windowTitle to name of w
                        set windowID to id of w
                        set end of windowInfo to (windowID as string) & "|" & windowTitle
                    end repeat
                    return windowInfo
                on error
                    return {{}}
                end try
            end tell
            '''
            
            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True,
                text=True,
                timeout=1.0  # 【hotkey】优化：减少超时时间提升响应速度
            )
            
            if result.returncode == 0 and result.stdout.strip():
                window_data = result.stdout.strip().split(', ')
                for item in window_data:
                    if '|' in item:
                        window_id, title = item.split('|', 1)
                        windows.append(WindowInfo(
                            window_id=window_id.strip(),
                            title=title.strip(),
                            app_name=app_name,
                            is_active=False,
                            is_minimized=False
                        ))
                        
        except Exception as e:
            logger.error(f"Failed to get windows for {app_name}: {e}")
        
        return windows
    
    def activate_window(self, window_id: str) -> bool:
        """Activate a specific window using AppleScript."""
        try:
            script = f'''
            tell application "System Events"
                try
                    set targetWindow to first window whose id is {window_id}
                    set frontmost of (first process whose windows contains targetWindow) to true
                    perform action "AXRaise" of targetWindow
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
                timeout=1.0  # 【hotkey】优化：减少超时时间提升响应速度
            )
            
            return result.returncode == 0 and 'true' in result.stdout
            
        except Exception as e:
            logger.error(f"Failed to activate window {window_id}: {e}")
            return False
    
    def minimize_window(self, window_id: str) -> bool:
        """Minimize a specific window."""
        try:
            script = f'''
            tell application "System Events"
                try
                    set targetWindow to first window whose id is {window_id}
                    set minimized of targetWindow to true
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
                timeout=1.0  # 【hotkey】优化：减少超时时间提升响应速度
            )
            
            return result.returncode == 0 and 'true' in result.stdout
            
        except Exception as e:
            logger.error(f"Failed to minimize window {window_id}: {e}")
            return False
    
    def close_window(self, window_id: str) -> bool:
        """Close a specific window."""
        try:
            script = f'''
            tell application "System Events"
                try
                    set targetWindow to first window whose id is {window_id}
                    perform action "AXCancel" of targetWindow
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
                timeout=1.0  # 【hotkey】优化：减少超时时间提升响应速度
            )
            
            return result.returncode == 0 and 'true' in result.stdout
            
        except Exception as e:
            logger.error(f"Failed to close window {window_id}: {e}")
            return False
    
    def register_hotkey(self, hotkey: str, callback: Callable) -> bool:
        """Register a global hotkey using pynput."""
        logger.info(f"Starting hotkey registration for: '{hotkey}'")
        if not keyboard:
            logger.error("pynput not available for hotkey registration")
            return False
        
        # Check for accessibility permissions on macOS
        if not self._check_accessibility_permissions():
            logger.error("Accessibility permissions not granted. Please enable accessibility permissions for this application in System Preferences > Security & Privacy > Privacy > Accessibility")
            return False
        
        try:
            # Parse hotkey string (e.g., "cmd+shift+t")
            logger.info(f"Parsing hotkey: '{hotkey}'")
            key_combination = self._parse_hotkey(hotkey)
            logger.info(f"Parsed hotkey '{hotkey}' -> '{key_combination}'")
            if not key_combination:
                logger.error(f"Failed to parse hotkey: '{hotkey}'")
                return False
            
            def on_hotkey():
                try:
                    logger.info(f"Hotkey fired: '{key_combination}'")
                    callback()
                except Exception as e:
                    logger.error(f"Hotkey callback error: {e}", exc_info=True)
            
            # Stop existing listener if present
            if self._running_listener:
                logger.info("Stopping existing hotkey listener before starting a new one")
                try:
                    self._running_listener.stop()
                    logger.info("Existing listener stopped successfully")
                except Exception as e:
                    logger.error(f"Error stopping existing listener: {e}")
            
            # Create new listener using parsed key combination
            mapping = { key_combination: on_hotkey }
            logger.info(f"Creating GlobalHotKeys with mapping: {mapping}")
            
            try:
                import threading
                import time
                
                success = False
                exception_occurred = None
                
                def register_with_timeout():
                    nonlocal success, exception_occurred
                    try:
                        self._running_listener = keyboard.GlobalHotKeys(mapping)
                        logger.info("GlobalHotKeys object created successfully")
                        self._running_listener.start()
                        logger.info("GlobalHotKeys listener started successfully")
                        success = True
                    except Exception as e:
                        exception_occurred = e
                
                # Start registration in a separate thread with timeout
                thread = threading.Thread(target=register_with_timeout)
                thread.daemon = True
                thread.start()
                thread.join(timeout=2.0)  # 【hotkey】优化：减少热键注册超时时间
                
                if thread.is_alive():
                    logger.error("Hotkey registration timed out after 5 seconds")
                    return False
                elif exception_occurred:
                    logger.error(f"Error creating or starting GlobalHotKeys: {exception_occurred}", exc_info=True)
                    return False
                elif success:
                    self._hotkey_listeners[hotkey] = self._running_listener
                    logger.info(f"Hotkey registration completed for: '{hotkey}'")
                    return True
                else:
                    logger.error("Hotkey registration failed for unknown reason")
                    return False
            except Exception as e:
                logger.error(f"Error in hotkey registration timeout handler: {e}", exc_info=True)
                return False
            
        except Exception as e:
            logger.error(f"Failed to register hotkey {hotkey}: {e}", exc_info=True)
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
                timeout=1.0  # 【hotkey】优化：减少超时时间提升响应速度
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
            logger.error(f"Failed to get active window: {e}")
        
        return None
    
    def is_app_running(self, app_name: str) -> bool:
        """Check if an application is currently running."""
        try:
            if HAS_COCOA:
                workspace = NSWorkspace.sharedWorkspace()
                running_apps = workspace.runningApplications()
                
                for app in running_apps:
                    if app.activationPolicy() == 0:  # Regular applications only
                        name = str(app.localizedName())
                        if app_name.lower() in name.lower():
                            return True
            else:
                # Fallback to psutil
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
                # Force kill using killall
                subprocess.run(['killall', '-9', app_name], check=False)
            else:
                # Graceful termination using AppleScript
                script = f'tell application "{app_name}" to quit'
                subprocess.run(['osascript', '-e', script], check=False)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to kill app {app_name}: {e}")
            return False
    
    def open_url(self, url: str, browser_path: Optional[str] = None) -> bool:
        """Open a URL in the default or specified browser."""
        try:
            if browser_path:
                # Open with specific browser
                subprocess.run(['open', '-a', browser_path, url], check=False)
            else:
                # Open with default browser
                subprocess.run(['open', url], check=False)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to open URL {url}: {e}")
            return False
    
    def get_default_terminal(self) -> str:
        """Get the default terminal application for macOS."""
        # Check for common terminal applications in order of preference
        terminals = [
            "/Applications/iTerm.app",
            "/Applications/Terminal.app",
            "/System/Applications/Terminal.app"
        ]
        
        for terminal in terminals:
            if os.path.exists(terminal):
                return terminal
        
        # Fallback to system Terminal
        return "Terminal"
    
    def normalize_app_path(self, app_path: str) -> str:
        """Normalize application path for macOS."""
        # Expand user home directory
        path = os.path.expanduser(app_path)
        
        # If it's just an app name, try to find it in Applications
        if not path.startswith('/') and not path.endswith('.app'):
            app_name = path + '.app'
            for search_path in ['/Applications', '/System/Applications', 
                              os.path.expanduser('~/Applications')]:
                full_path = os.path.join(search_path, app_name)
                if os.path.exists(full_path):
                    return full_path
        
        return path
    
    def _parse_hotkey(self, hotkey: str) -> Optional[str]:
        """Parse hotkey string and convert to pynput format."""
        logger.info(f"Parsing hotkey string: '{hotkey}'")
        
        # Convert common key names
        key_mapping = {
            'cmd': 'cmd',
            'ctrl': 'ctrl',
            'alt': 'alt',
            'shift': 'shift',
            'option': 'alt',
            'command': 'cmd'
        }
        
        # Split and normalize keys
        keys = [key.strip().lower() for key in hotkey.split('+')]
        logger.info(f"Split keys: {keys}")
        normalized_keys = []
        
        for key in keys:
            logger.info(f"Processing key: '{key}'")
            if key in key_mapping:
                mapped_key = f'<{key_mapping[key]}>'
                normalized_keys.append(mapped_key)
                logger.info(f"Mapped '{key}' to '{mapped_key}'")
            elif len(key) == 1:
                normalized_keys.append(key)
                logger.info(f"Added single character key: '{key}'")
            else:
                # Handle special keys
                special_key = f'<{key}>'
                normalized_keys.append(special_key)
                logger.info(f"Added special key: '{special_key}'")
        
        result = '+'.join(normalized_keys) if normalized_keys else None
        logger.info(f"Final parsed hotkey result: '{result}'")
        return result
    
    def _check_accessibility_permissions(self) -> bool:
        """Check if accessibility permissions are granted on macOS."""
        try:
            # Try a simple test to see if we can access accessibility features
            import subprocess
            result = subprocess.run([
                'osascript', '-e', 
                'tell application "System Events" to get name of first process'
            ], capture_output=True, text=True, timeout=3)
            
            if result.returncode == 0:
                logger.info("Accessibility permissions check passed")
                return True
            else:
                logger.warning(f"Accessibility permissions check failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error checking accessibility permissions: {e}")
            return False
