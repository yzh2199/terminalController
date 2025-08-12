"""Configuration management module for Terminal Controller."""
import os
import yaml
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from pathlib import Path


logger = logging.getLogger(__name__)


@dataclass
class AppConfig:
    """Configuration for an application."""
    name: str
    executable: Dict[str, str]
    type: str
    description: str = ""
    args: List[str] = field(default_factory=list)


@dataclass
class WebsiteConfig:
    """Configuration for a website."""
    name: str
    url: str
    description: str = ""


@dataclass
class HotkeyConfig:
    """Configuration for hotkeys."""
    terminal: str = "cmd+shift+t"
    terminal_linux: str = "ctrl+alt+t"
    terminal_windows: str = "ctrl+shift+t"


@dataclass
class BehaviorConfig:
    """Configuration for application behavior."""
    auto_focus: bool = True
    show_window_selection: bool = True
    remember_last_used: bool = True
    window_selection_timeout: int = 10


@dataclass
class TerminalConfig:
    """Configuration for terminal settings."""
    default: str = "t"
    startup_command: str = ""
    work_directory: str = "~"


@dataclass
class LoggingConfig:
    """Configuration for logging."""
    level: str = "INFO"
    file: str = "terminalController.log"
    max_size: str = "10MB"
    backup_count: int = 3


@dataclass
class DaemonConfig:
    """Configuration for daemon settings."""
    pid_file: str = "/tmp/terminalController.pid"
    auto_start: bool = False


@dataclass
class SettingsConfig:
    """Main settings configuration."""
    hotkeys: HotkeyConfig = field(default_factory=HotkeyConfig)
    behavior: BehaviorConfig = field(default_factory=BehaviorConfig)
    terminal: TerminalConfig = field(default_factory=TerminalConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    daemon: DaemonConfig = field(default_factory=DaemonConfig)


class ConfigManager:
    """Manages configuration loading and saving for Terminal Controller."""
    
    def __init__(self, config_dir: Optional[str] = None):
        """Initialize configuration manager.
        
        Args:
            config_dir: Directory containing configuration files. 
                       Defaults to 'config' in current directory.
        """
        self.config_dir = Path(config_dir or 'config')
        self.apps_file = self.config_dir / 'apps.yaml'
        self.websites_file = self.config_dir / 'websites.yaml'
        self.settings_file = self.config_dir / 'settings.yaml'
        
        self._apps: Dict[str, AppConfig] = {}
        self._websites: Dict[str, WebsiteConfig] = {}
        self._settings: SettingsConfig = SettingsConfig()
        self._last_used: Dict[str, str] = {}
        
        # Create config directory if it doesn't exist
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Load configurations
        self.reload()
    
    def reload(self) -> bool:
        """Reload all configuration files.
        
        Returns:
            True if all configurations loaded successfully, False otherwise.
        """
        success = True
        
        try:
            success &= self._load_apps()
            success &= self._load_websites()
            success &= self._load_settings()
            success &= self._load_last_used()
            
            logger.info("Configuration reloaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to reload configuration: {e}")
            success = False
        
        return success
    
    def get_app_config(self, app_id: str) -> Optional[AppConfig]:
        """Get configuration for a specific application.
        
        Args:
            app_id: Application identifier
            
        Returns:
            Application configuration or None if not found
        """
        return self._apps.get(app_id)
    
    def get_website_config(self, website_id: str) -> Optional[WebsiteConfig]:
        """Get configuration for a specific website.
        
        Args:
            website_id: Website identifier
            
        Returns:
            Website configuration or None if not found
        """
        return self._websites.get(website_id)
    
    def get_settings(self) -> SettingsConfig:
        """Get general settings configuration.
        
        Returns:
            Settings configuration
        """
        return self._settings
    
    def get_all_apps(self) -> Dict[str, AppConfig]:
        """Get all application configurations.
        
        Returns:
            Dictionary of all application configurations
        """
        return self._apps.copy()
    
    def get_all_websites(self) -> Dict[str, WebsiteConfig]:
        """Get all website configurations.
        
        Returns:
            Dictionary of all website configurations
        """
        return self._websites.copy()
    
    def get_last_used_window(self, app_id: str) -> Optional[str]:
        """Get the last used window ID for an application.
        
        Args:
            app_id: Application identifier
            
        Returns:
            Window ID or None if not found
        """
        return self._last_used.get(app_id)
    
    def set_last_used_window(self, app_id: str, window_id: str) -> None:
        """Set the last used window ID for an application.
        
        Args:
            app_id: Application identifier
            window_id: Window identifier
        """
        self._last_used[app_id] = window_id
        self._save_last_used()
    
    def get_tc_context_window(self) -> Optional[str]:
        """Get the terminal window ID where TC was launched or is running.
        
        Returns:
            Window ID of TC context terminal or None if not set
        """
        return self._last_used.get("_tc_context_window")
    
    def set_tc_context_window(self, window_id: str) -> None:
        """Set the terminal window ID where TC was launched or is running.
        
        Args:
            window_id: Terminal window identifier
        """
        self._last_used["_tc_context_window"] = window_id
        self._save_last_used()
        logger.debug(f"Set TC context window: {window_id}")
    
    def clear_tc_context_window(self) -> None:
        """Clear the TC context window (when TC exits)."""
        if "_tc_context_window" in self._last_used:
            del self._last_used["_tc_context_window"]
            self._save_last_used()
            logger.debug("Cleared TC context window")
    
    def register_interactive_session(self, window_id: str, pid: int) -> bool:
        """Register an interactive TC session with PID file.
        
        Args:
            window_id: Terminal window ID where TC is running
            pid: Process ID of the TC interactive session
            
        Returns:
            True if registration successful, False otherwise
        """
        try:
            import os
            import json
            import tempfile
            import time
            from pathlib import Path
            
            # Create TC runtime directory
            runtime_dir = Path(tempfile.gettempdir()) / "terminal_controller"
            runtime_dir.mkdir(exist_ok=True)
            
            # Create PID file with session info
            pid_file = runtime_dir / f"tc_interactive_{pid}.pid"
            session_info = {
                "pid": pid,
                "window_id": window_id,
                "started_at": time.time(),
                "app_name": "terminal_controller_interactive"
            }
            
            with open(pid_file, 'w') as f:
                json.dump(session_info, f)
            
            logger.info(f"【hotkey】Registered interactive session: PID={pid}, window={window_id}")  # 注册交互会话
            return True
            
        except Exception as e:
            logger.error(f"Failed to register interactive session: {e}")
            return False
    
    def unregister_interactive_session(self, pid: int) -> bool:
        """Unregister an interactive TC session.
        
        Args:
            pid: Process ID to unregister
            
        Returns:
            True if unregistration successful, False otherwise
        """
        try:
            import tempfile
            from pathlib import Path
            
            runtime_dir = Path(tempfile.gettempdir()) / "terminal_controller"
            pid_file = runtime_dir / f"tc_interactive_{pid}.pid"
            
            if pid_file.exists():
                pid_file.unlink()
                logger.info(f"【hotkey】Unregistered interactive session: PID={pid}")  # 注销交互会话
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to unregister interactive session: {e}")
            return False
    
    def get_active_interactive_sessions(self) -> List[Dict[str, Any]]:
        """Get all active interactive TC sessions.
        
        Returns:
            List of active session information
        """
        try:
            import os
            import json
            import psutil
            import tempfile
            import time
            from pathlib import Path
            
            runtime_dir = Path(tempfile.gettempdir()) / "terminal_controller"
            if not runtime_dir.exists():
                return []
            
            active_sessions = []
            current_time = time.time()
            
            # Check all PID files
            for pid_file in runtime_dir.glob("tc_interactive_*.pid"):
                try:
                    with open(pid_file, 'r') as f:
                        session_info = json.load(f)
                    
                    pid = session_info.get("pid")
                    
                    # Verify process is still running
                    if pid and psutil.pid_exists(pid):
                        try:
                            proc = psutil.Process(pid)
                            # Verify it's actually a Python process running TC
                            if any("main_enhanced.py" in arg for arg in proc.cmdline()):
                                active_sessions.append(session_info)
                                continue
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
                    
                    # Process not running, clean up PID file
                    pid_file.unlink()
                    logger.debug(f"Cleaned up stale PID file: {pid_file}")
                    
                except Exception as e:
                    logger.warning(f"Error processing PID file {pid_file}: {e}")
                    # Try to remove corrupted PID file
                    try:
                        pid_file.unlink()
                    except:
                        pass
            
            logger.info(f"【hotkey】Found {len(active_sessions)} active interactive sessions")  # 找到的活跃交互会话数量
            return active_sessions
            
        except Exception as e:
            logger.error(f"Failed to get active interactive sessions: {e}")
            return []
    
    def add_app(self, app_id: str, config: AppConfig) -> bool:
        """Add or update an application configuration.
        
        Args:
            app_id: Application identifier
            config: Application configuration
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self._apps[app_id] = config
            return self._save_apps()
        except Exception as e:
            logger.error(f"Failed to add app {app_id}: {e}")
            return False
    
    def remove_app(self, app_id: str) -> bool:
        """Remove an application configuration.
        
        Args:
            app_id: Application identifier
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if app_id in self._apps:
                del self._apps[app_id]
                return self._save_apps()
            return True
        except Exception as e:
            logger.error(f"Failed to remove app {app_id}: {e}")
            return False
    
    def add_website(self, website_id: str, config: WebsiteConfig) -> bool:
        """Add or update a website configuration.
        
        Args:
            website_id: Website identifier
            config: Website configuration
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self._websites[website_id] = config
            return self._save_websites()
        except Exception as e:
            logger.error(f"Failed to add website {website_id}: {e}")
            return False
    
    def remove_website(self, website_id: str) -> bool:
        """Remove a website configuration.
        
        Args:
            website_id: Website identifier
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if website_id in self._websites:
                del self._websites[website_id]
                return self._save_websites()
            return True
        except Exception as e:
            logger.error(f"Failed to remove website {website_id}: {e}")
            return False
    
    def update_settings(self, settings: SettingsConfig) -> bool:
        """Update general settings.
        
        Args:
            settings: New settings configuration
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self._settings = settings
            return self._save_settings()
        except Exception as e:
            logger.error(f"Failed to update settings: {e}")
            return False
    
    def _load_apps(self) -> bool:
        """Load application configurations from file."""
        try:
            if self.apps_file.exists():
                with open(self.apps_file, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f) or {}
                
                apps_data = data.get('apps', {})
                for app_id, app_config in apps_data.items():
                    self._apps[app_id] = AppConfig(
                        name=app_config.get('name', ''),
                        executable=app_config.get('executable', {}),
                        type=app_config.get('type', ''),
                        description=app_config.get('description', ''),
                        args=app_config.get('args', [])
                    )
                
                logger.debug(f"Loaded {len(self._apps)} applications")
                return True
            else:
                logger.warning(f"Apps configuration file not found: {self.apps_file}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to load apps configuration: {e}")
            return False
    
    def _load_websites(self) -> bool:
        """Load website configurations from file."""
        try:
            if self.websites_file.exists():
                with open(self.websites_file, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f) or {}
                
                websites_data = data.get('websites', {})
                for website_id, website_config in websites_data.items():
                    self._websites[website_id] = WebsiteConfig(
                        name=website_config.get('name', ''),
                        url=website_config.get('url', ''),
                        description=website_config.get('description', '')
                    )
                
                logger.debug(f"Loaded {len(self._websites)} websites")
                return True
            else:
                logger.warning(f"Websites configuration file not found: {self.websites_file}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to load websites configuration: {e}")
            return False
    
    def _load_settings(self) -> bool:
        """Load general settings from file."""
        try:
            if self.settings_file.exists():
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f) or {}
                
                # Load hotkeys
                hotkeys_data = data.get('hotkeys', {})
                hotkeys = HotkeyConfig(
                    terminal=hotkeys_data.get('terminal', 'cmd+shift+t'),
                    terminal_linux=hotkeys_data.get('terminal_linux', 'ctrl+alt+t'),
                    terminal_windows=hotkeys_data.get('terminal_windows', 'ctrl+shift+t')
                )
                
                # Load behavior
                behavior_data = data.get('behavior', {})
                behavior = BehaviorConfig(
                    auto_focus=behavior_data.get('auto_focus', True),
                    show_window_selection=behavior_data.get('show_window_selection', True),
                    remember_last_used=behavior_data.get('remember_last_used', True),
                    window_selection_timeout=behavior_data.get('window_selection_timeout', 10)
                )
                
                # Load terminal
                terminal_data = data.get('terminal', {})
                terminal = TerminalConfig(
                    default=terminal_data.get('default', 't'),
                    startup_command=terminal_data.get('startup_command', ''),
                    work_directory=terminal_data.get('work_directory', '~')
                )
                
                # Load logging
                logging_data = data.get('logging', {})
                logging_config = LoggingConfig(
                    level=logging_data.get('level', 'INFO'),
                    file=logging_data.get('file', 'terminalController.log'),
                    max_size=logging_data.get('max_size', '10MB'),
                    backup_count=logging_data.get('backup_count', 3)
                )
                
                # Load daemon
                daemon_data = data.get('daemon', {})
                daemon = DaemonConfig(
                    pid_file=daemon_data.get('pid_file', '/tmp/terminalController.pid'),
                    auto_start=daemon_data.get('auto_start', False)
                )
                
                self._settings = SettingsConfig(
                    hotkeys=hotkeys,
                    behavior=behavior,
                    terminal=terminal,
                    logging=logging_config,
                    daemon=daemon
                )
                
                logger.debug("Loaded settings configuration")
                return True
            else:
                logger.warning(f"Settings configuration file not found: {self.settings_file}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to load settings configuration: {e}")
            return False
    
    def _load_last_used(self) -> bool:
        """Load last used window information."""
        try:
            last_used_file = self.config_dir / 'last_used.yaml'
            if last_used_file.exists():
                with open(last_used_file, 'r', encoding='utf-8') as f:
                    self._last_used = yaml.safe_load(f) or {}
                
                logger.debug(f"Loaded {len(self._last_used)} last used entries")
            
            return True
                
        except Exception as e:
            logger.error(f"Failed to load last used configuration: {e}")
            return False
    
    def _save_apps(self) -> bool:
        """Save application configurations to file."""
        try:
            apps_data = {}
            for app_id, app_config in self._apps.items():
                apps_data[app_id] = {
                    'name': app_config.name,
                    'executable': app_config.executable,
                    'type': app_config.type,
                    'description': app_config.description,
                    'args': app_config.args
                }
            
            data = {'apps': apps_data}
            with open(self.apps_file, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to save apps configuration: {e}")
            return False
    
    def _save_websites(self) -> bool:
        """Save website configurations to file."""
        try:
            websites_data = {}
            for website_id, website_config in self._websites.items():
                websites_data[website_id] = {
                    'name': website_config.name,
                    'url': website_config.url,
                    'description': website_config.description
                }
            
            data = {'websites': websites_data}
            with open(self.websites_file, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to save websites configuration: {e}")
            return False
    
    def _save_settings(self) -> bool:
        """Save general settings to file."""
        try:
            data = {
                'hotkeys': {
                    'terminal': self._settings.hotkeys.terminal,
                    'terminal_linux': self._settings.hotkeys.terminal_linux,
                    'terminal_windows': self._settings.hotkeys.terminal_windows
                },
                'behavior': {
                    'auto_focus': self._settings.behavior.auto_focus,
                    'show_window_selection': self._settings.behavior.show_window_selection,
                    'remember_last_used': self._settings.behavior.remember_last_used,
                    'window_selection_timeout': self._settings.behavior.window_selection_timeout
                },
                'terminal': {
                    'default': self._settings.terminal.default,
                    'startup_command': self._settings.terminal.startup_command,
                    'work_directory': self._settings.terminal.work_directory
                },
                'logging': {
                    'level': self._settings.logging.level,
                    'file': self._settings.logging.file,
                    'max_size': self._settings.logging.max_size,
                    'backup_count': self._settings.logging.backup_count
                },
                'daemon': {
                    'pid_file': self._settings.daemon.pid_file,
                    'auto_start': self._settings.daemon.auto_start
                }
            }
            
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to save settings configuration: {e}")
            return False
    
    def _save_last_used(self) -> bool:
        """Save last used window information."""
        try:
            last_used_file = self.config_dir / 'last_used.yaml'
            with open(last_used_file, 'w', encoding='utf-8') as f:
                yaml.dump(self._last_used, f, default_flow_style=False, allow_unicode=True)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to save last used configuration: {e}")
            return False
