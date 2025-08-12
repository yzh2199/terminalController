"""Terminal management module for Terminal Controller."""
import os
import sys
import subprocess
import logging
from typing import Optional, List, Dict, Any
from pathlib import Path

from .platform import get_platform_adapter, PlatformAdapter
from .config_manager import ConfigManager


logger = logging.getLogger(__name__)


class TerminalManager:
    """Manages terminal operations and interactions."""
    
    def __init__(self, config_manager: ConfigManager):
        """Initialize the terminal manager.
        
        Args:
            config_manager: Configuration manager instance
        """
        self.config_manager = config_manager
        self.platform_adapter: PlatformAdapter = get_platform_adapter()()
        p = sys.platform.lower()
        if p.startswith("darwin") or p in ("mac", "macos"):
            self.current_platform = "darwin"
        elif p.startswith("linux"):
            self.current_platform = "linux"
        elif p.startswith("win"):
            self.current_platform = "windows"
        else:
            self.current_platform = p
        
        logger.info(f"Initialized TerminalManager for platform: {self.current_platform}")
    
    def launch_terminal(self, startup_command: Optional[str] = None, 
                       work_directory: Optional[str] = None,
                       app_id: Optional[str] = None) -> bool:
        """Launch a terminal application.
        
        Args:
            startup_command: Command to run in the terminal after launch
            work_directory: Working directory for the terminal
            app_id: Specific terminal application ID to use
            
        Returns:
            True if terminal was launched successfully, False otherwise
        """
        try:
            settings = self.config_manager.get_settings()
            
            # Determine which terminal to use
            if app_id:
                terminal_config = self.config_manager.get_app_config(app_id)
                if not terminal_config:
                    logger.error(f"Unknown terminal application: {app_id}")
                    return False
                
                if terminal_config.type != "terminal":
                    logger.warning(f"Application {app_id} is not a terminal")
                
                terminal_path = self._get_terminal_executable(terminal_config.executable)
            else:
                # Use default terminal
                default_terminal_id = settings.terminal.default
                terminal_config = self.config_manager.get_app_config(default_terminal_id)
                
                if terminal_config:
                    terminal_path = self._get_terminal_executable(terminal_config.executable)
                else:
                    # Fallback to system default
                    terminal_path = self.platform_adapter.get_default_terminal()
            
            if not terminal_path:
                logger.error("No suitable terminal found")
                return False
            
            # Prepare working directory
            if not work_directory:
                work_directory = settings.terminal.work_directory
            
            if work_directory == "~":
                work_directory = str(Path.home())
            else:
                work_directory = os.path.expanduser(work_directory)
            
            # Prepare startup command
            if not startup_command:
                startup_command = settings.terminal.startup_command
            
            # Launch terminal with platform-specific handling
            return self._launch_platform_terminal(
                terminal_path, 
                startup_command, 
                work_directory,
                terminal_config if 'terminal_config' in locals() else None
            )
            
        except Exception as e:
            logger.error(f"Error launching terminal: {e}")
            return False
    
    def is_terminal_running(self, app_id: Optional[str] = None) -> bool:
        """Check if a terminal application is currently running.
        
        Args:
            app_id: Specific terminal application ID to check
            
        Returns:
            True if terminal is running, False otherwise
        """
        try:
            if app_id:
                terminal_config = self.config_manager.get_app_config(app_id)
                if terminal_config:
                    return self.platform_adapter.is_app_running(terminal_config.name)
            else:
                # Check default terminal
                settings = self.config_manager.get_settings()
                default_terminal_id = settings.terminal.default
                return self.is_terminal_running(default_terminal_id)
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking if terminal is running: {e}")
            return False
    
    def get_terminal_windows(self, app_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get information about terminal windows.
        
        Args:
            app_id: Specific terminal application ID
            
        Returns:
            List of terminal window information
        """
        try:
            if app_id:
                terminal_config = self.config_manager.get_app_config(app_id)
                if terminal_config:
                    windows = self.platform_adapter.get_app_windows(terminal_config.name)
                    return [self._window_info_to_dict(w) for w in windows]
            else:
                # Get windows for default terminal
                settings = self.config_manager.get_settings()
                default_terminal_id = settings.terminal.default
                return self.get_terminal_windows(default_terminal_id)
            
            return []
            
        except Exception as e:
            logger.error(f"Error getting terminal windows: {e}")
            return []
    
    def execute_command_in_terminal(self, command: str, 
                                  app_id: Optional[str] = None,
                                  work_directory: Optional[str] = None) -> bool:
        """Execute a command in a new terminal window.
        
        Args:
            command: Command to execute
            app_id: Specific terminal application ID to use
            work_directory: Working directory for command execution
            
        Returns:
            True if command was executed successfully, False otherwise
        """
        try:
            # Launch terminal with the command
            return self.launch_terminal(
                startup_command=command,
                work_directory=work_directory,
                app_id=app_id
            )
            
        except Exception as e:
            logger.error(f"Error executing command in terminal: {e}")
            return False
    
    def create_terminal_session(self, session_name: str, 
                              commands: List[str],
                              app_id: Optional[str] = None) -> bool:
        """Create a terminal session with multiple commands.
        
        Args:
            session_name: Name for the terminal session
            commands: List of commands to execute
            app_id: Specific terminal application ID to use
            
        Returns:
            True if session was created successfully, False otherwise
        """
        try:
            # For now, just launch terminal with first command
            # TODO: Implement proper session management
            if commands:
                startup_command = "; ".join(commands)
                return self.launch_terminal(
                    startup_command=startup_command,
                    app_id=app_id
                )
            else:
                return self.launch_terminal(app_id=app_id)
            
        except Exception as e:
            logger.error(f"Error creating terminal session: {e}")
            return False
    
    def get_available_terminals(self) -> List[str]:
        """Get a list of available terminal applications.
        
        Returns:
            List of terminal application IDs
        """
        try:
            available_terminals = []
            all_apps = self.config_manager.get_all_apps()
            
            for app_id, app_config in all_apps.items():
                if app_config.type == "terminal":
                    # Check if the terminal is actually available on this platform
                    executable_path = self._get_terminal_executable(app_config.executable)
                    if executable_path and self._is_executable_available(executable_path):
                        available_terminals.append(app_id)
            
            return available_terminals
            
        except Exception as e:
            logger.error(f"Error getting available terminals: {e}")
            return []
    
    def set_default_terminal(self, app_id: str) -> bool:
        """Set the default terminal application.
        
        Args:
            app_id: Terminal application ID to set as default
            
        Returns:
            True if default was set successfully, False otherwise
        """
        try:
            terminal_config = self.config_manager.get_app_config(app_id)
            if not terminal_config:
                logger.error(f"Unknown terminal application: {app_id}")
                return False
            
            if terminal_config.type != "terminal":
                logger.error(f"Application {app_id} is not a terminal")
                return False
            
            # Update settings
            settings = self.config_manager.get_settings()
            settings.terminal.default = app_id
            
            return self.config_manager.update_settings(settings)
            
        except Exception as e:
            logger.error(f"Error setting default terminal: {e}")
            return False
    
    def _get_terminal_executable(self, executables: Dict[str, str]) -> Optional[str]:
        """Get the platform-specific terminal executable path.
        
        Args:
            executables: Dictionary of platform-specific executables
            
        Returns:
            Terminal executable path for current platform or None
        """
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
    
    def _launch_platform_terminal(self, terminal_path: str, 
                                 startup_command: Optional[str],
                                 work_directory: str,
                                 terminal_config: Optional[Any] = None) -> bool:
        """Launch terminal with platform-specific handling.
        
        Args:
            terminal_path: Path to terminal executable
            startup_command: Command to run after launch
            work_directory: Working directory
            terminal_config: Terminal configuration object
            
        Returns:
            True if launch was successful, False otherwise
        """
        try:
            args = []
            
            # Platform-specific argument handling
            if self.current_platform == "darwin":
                return self._launch_macos_terminal(
                    terminal_path, startup_command, work_directory, args
                )
            elif self.current_platform == "linux":
                return self._launch_linux_terminal(
                    terminal_path, startup_command, work_directory, args
                )
            elif self.current_platform == "windows":
                return self._launch_windows_terminal(
                    terminal_path, startup_command, work_directory, args
                )
            else:
                # Generic launch
                return self.platform_adapter.launch_app(
                    terminal_path, args=args, cwd=work_directory
                )
                
        except Exception as e:
            logger.error(f"Error in platform-specific terminal launch: {e}")
            return False
    
    def _launch_macos_terminal(self, terminal_path: str, 
                             startup_command: Optional[str],
                             work_directory: str, 
                             base_args: List[str]) -> bool:
        """Launch terminal on macOS with proper handling.
        
        Args:
            terminal_path: Path to terminal application
            startup_command: Command to execute
            work_directory: Working directory
            base_args: Base arguments
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if "iterm" in terminal_path.lower():
                # iTerm2 specific handling
                args = base_args.copy()
                if startup_command:
                    # Use AppleScript to run command in iTerm
                    script = f'''
                    tell application "iTerm"
                        create window with default profile
                        tell current session of current window
                            write text "cd {work_directory}"
                            write text "{startup_command}"
                        end tell
                    end tell
                    '''
                    subprocess.run(['osascript', '-e', script], check=False)
                    return True
                else:
                    return self.platform_adapter.launch_app(
                        terminal_path, args=args, cwd=work_directory
                    )
            else:
                # Standard Terminal.app
                args = base_args.copy()
                if startup_command:
                    # Use AppleScript for Terminal.app
                    script = f'''
                    tell application "Terminal"
                        do script "cd {work_directory} && {startup_command}"
                    end tell
                    '''
                    subprocess.run(['osascript', '-e', script], check=False)
                    return True
                else:
                    return self.platform_adapter.launch_app(
                        terminal_path, args=args, cwd=work_directory
                    )
                    
        except Exception as e:
            logger.error(f"Error launching macOS terminal: {e}")
            return False
    
    def _launch_linux_terminal(self, terminal_path: str, 
                             startup_command: Optional[str],
                             work_directory: str, 
                             base_args: List[str]) -> bool:
        """Launch terminal on Linux with proper handling.
        
        Args:
            terminal_path: Path to terminal executable
            startup_command: Command to execute
            work_directory: Working directory
            base_args: Base arguments
            
        Returns:
            True if successful, False otherwise
        """
        try:
            args = base_args.copy()
            
            # Add working directory
            if "gnome-terminal" in terminal_path:
                args.extend(["--working-directory", work_directory])
                if startup_command:
                    args.extend(["--", "bash", "-c", f"{startup_command}; exec bash"])
            elif "konsole" in terminal_path:
                args.extend(["--workdir", work_directory])
                if startup_command:
                    args.extend(["-e", "bash", "-c", f"{startup_command}; exec bash"])
            elif "xfce4-terminal" in terminal_path:
                args.extend(["--working-directory", work_directory])
                if startup_command:
                    args.extend(["--command", f"bash -c '{startup_command}; exec bash'"])
            else:
                # Generic terminal
                if startup_command:
                    args.extend(["-e", "bash", "-c", f"cd {work_directory} && {startup_command}; exec bash"])
            
            return self.platform_adapter.launch_app(
                terminal_path, args=args, cwd=work_directory
            )
            
        except Exception as e:
            logger.error(f"Error launching Linux terminal: {e}")
            return False
    
    def _launch_windows_terminal(self, terminal_path: str, 
                               startup_command: Optional[str],
                               work_directory: str, 
                               base_args: List[str]) -> bool:
        """Launch terminal on Windows with proper handling.
        
        Args:
            terminal_path: Path to terminal executable
            startup_command: Command to execute
            work_directory: Working directory
            base_args: Base arguments
            
        Returns:
            True if successful, False otherwise
        """
        try:
            args = base_args.copy()
            
            if "wt.exe" in terminal_path or "WindowsTerminal" in terminal_path:
                # Windows Terminal
                args.extend(["--startingDirectory", work_directory])
                if startup_command:
                    # Windows Terminal doesn't have direct command execution
                    # Launch and send command via other means
                    pass
            elif "cmd.exe" in terminal_path:
                # Command Prompt
                args.extend(["/k", f"cd /d {work_directory}"])
                if startup_command:
                    args.extend(["&&", startup_command])
            elif "powershell.exe" in terminal_path:
                # PowerShell
                args.extend(["-NoExit", "-Command", f"Set-Location '{work_directory}'"])
                if startup_command:
                    args.extend([";", startup_command])
            
            return self.platform_adapter.launch_app(
                terminal_path, args=args, cwd=work_directory
            )
            
        except Exception as e:
            logger.error(f"Error launching Windows terminal: {e}")
            return False
    
    def _is_executable_available(self, executable_path: str) -> bool:
        """Check if an executable is available on the system.
        
        Args:
            executable_path: Path to executable
            
        Returns:
            True if executable is available, False otherwise
        """
        try:
            if os.path.isabs(executable_path):
                return os.path.exists(executable_path)
            else:
                # Check if it's in PATH
                try:
                    subprocess.run(['which', executable_path], 
                                 check=True, 
                                 stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL)
                    return True
                except subprocess.CalledProcessError:
                    return False
                    
        except Exception:
            return False
    
    def _window_info_to_dict(self, window_info) -> Dict[str, Any]:
        """Convert WindowInfo object to dictionary.
        
        Args:
            window_info: WindowInfo object
            
        Returns:
            Dictionary representation of window info
        """
        return {
            'window_id': window_info.window_id,
            'title': window_info.title,
            'app_name': window_info.app_name,
            'is_active': window_info.is_active,
            'is_minimized': window_info.is_minimized,
            'position': window_info.position,
            'size': window_info.size
        }
