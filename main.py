#!/usr/bin/env python3
"""
Terminal Controller - A cross-platform application launcher and window manager.

This is the main entry point for the Terminal Controller application.
"""

import os
import sys
import signal
import logging
import argparse
import platform
from pathlib import Path
from typing import Optional

import click
from colorama import init as colorama_init, Fore, Style

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.config_manager import ConfigManager
from src.app_manager import AppManager
from src.window_manager import WindowManager
from src.terminal_manager import TerminalManager
from src.hotkey_manager import HotkeyManager
from src.command_parser import CommandParser, CommandType


# Initialize colorama for cross-platform colored output
colorama_init()

# Global variable for main controller instance
main_controller = None


class TerminalController:
    """Main controller for the Terminal Controller application."""
    
    def __init__(self, config_dir: Optional[str] = None, debug: bool = False):
        """Initialize the Terminal Controller.
        
        Args:
            config_dir: Directory containing configuration files
            debug: Enable debug logging
        """
        self.debug = debug
        # Use installed config directory by default,yz这一行很关键，能够保证读取的是安装目录的文件，原因待学习
        if config_dir is None:
            installed_config = Path.home() / ".terminal-controller" / "config"
            if installed_config.exists():
                config_dir = str(installed_config)
            else:
                config_dir = "config"  # Fallback to local config
        self.config_dir = config_dir
        self.running = False
        
        # Initialize logging
        self._setup_logging()
        
        # Initialize managers
        self.config_manager = ConfigManager(self.config_dir)
        self.app_manager = AppManager(self.config_manager)
        self.window_manager = WindowManager(self.config_manager)
        self.terminal_manager = TerminalManager(self.config_manager)
        self.hotkey_manager = HotkeyManager(self.config_manager)
        self.command_parser = CommandParser()
        
        # Register signal handlers
        self._setup_signal_handlers()
        
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Initialized Terminal Controller on {platform.system()}")
    
    def start_daemon(self) -> bool:
        """Start the Terminal Controller as a daemon process.
        
        Returns:
            True if daemon started successfully, False otherwise
        """
        try:
            self.logger.info("Starting Terminal Controller daemon")
            
            # Start hotkey manager
            if not self.hotkey_manager.start():
                self.logger.error("Failed to start hotkey manager")
                return False
            
            self.running = True
            self.logger.info("Terminal Controller daemon started successfully")
            
            # Keep the daemon running
            try:
                while self.running:
                    import time
                    time.sleep(1)
            except KeyboardInterrupt:
                self.logger.info("Received interrupt signal")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error starting daemon: {e}")
            return False
        finally:
            self.stop()
    
    def stop(self):
        """Stop the Terminal Controller daemon."""
        try:
            self.logger.info("Stopping Terminal Controller")
            self.running = False
            
            # Stop managers
            if hasattr(self, 'hotkey_manager'):
                self.hotkey_manager.cleanup()
            
            if hasattr(self, 'window_manager'):
                self.window_manager.cleanup()
            
            self.logger.info("Terminal Controller stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping Terminal Controller: {e}")
    
    def execute_command(self, command: str) -> bool:
        """Execute a user command.
        
        Args:
            command: Command string to execute
            
        Returns:
            True if command was executed successfully, False otherwise
        """
        try:
            # Parse the command
            parsed_cmd = self.command_parser.parse(command)
            if not parsed_cmd:
                print(f"{Fore.RED}Invalid command: {command}{Style.RESET_ALL}")
                return False
            
            # Validate the command
            available_apps = list(self.config_manager.get_all_apps().keys())
            available_websites = list(self.config_manager.get_all_websites().keys())
            
            is_valid, error_msg = self.command_parser.validate_command(
                parsed_cmd, available_apps, available_websites
            )
            
            if not is_valid:
                print(f"{Fore.RED}Error: {error_msg}{Style.RESET_ALL}")
                return False
            
            # Execute the command based on type
            if parsed_cmd.command_type == CommandType.LAUNCH_APP:
                return self._handle_launch_app(parsed_cmd)
            
            elif parsed_cmd.command_type == CommandType.OPEN_URL:
                return self._handle_open_url(parsed_cmd)
            
            elif parsed_cmd.command_type == CommandType.WINDOW_CONTROL:
                return self._handle_window_control(parsed_cmd)
            
            elif parsed_cmd.command_type == CommandType.HELP:
                return self._handle_help(parsed_cmd)
            
            elif parsed_cmd.command_type == CommandType.CONFIG:
                return self._handle_config(parsed_cmd)
            
            elif parsed_cmd.command_type == CommandType.QUIT:
                return self._handle_quit(parsed_cmd)
            
            else:
                print(f"{Fore.RED}Unknown command type: {parsed_cmd.command_type}{Style.RESET_ALL}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error executing command '{command}': {e}")
            print(f"{Fore.RED}Error executing command: {e}{Style.RESET_ALL}")
            return False
    
    def interactive_mode(self):
        """Run the Terminal Controller in interactive mode."""
        print(f"{Fore.GREEN}Terminal Controller - Interactive Mode{Style.RESET_ALL}")
        print(f"Type '{Fore.CYAN}help{Style.RESET_ALL}' for available commands, '{Fore.CYAN}quit{Style.RESET_ALL}' to exit")
        print()
        
        try:
            while True:
                try:
                    command = input(f"{Fore.YELLOW}tc> {Style.RESET_ALL}").strip()
                    
                    if not command:
                        continue
                    
                    if command.lower() in ['quit', 'exit', 'q']:
                        break
                    
                    self.execute_command(command)
                    print()  # Add spacing after command execution
                    
                except KeyboardInterrupt:
                    print(f"\n{Fore.YELLOW}Use 'quit' to exit{Style.RESET_ALL}")
                except EOFError:
                    break
                    
        except Exception as e:
            self.logger.error(f"Error in interactive mode: {e}")
            print(f"{Fore.RED}Error in interactive mode: {e}{Style.RESET_ALL}")
        
        print(f"{Fore.GREEN}Goodbye!{Style.RESET_ALL}")
    
    def _handle_launch_app(self, parsed_cmd) -> bool:
        """Handle application launch command."""
        force_new = parsed_cmd.options.get('new', False)
        
        success = self.app_manager.launch_app(
            parsed_cmd.app_id,
            force_new=force_new
        )
        
        if success:
            app_config = self.config_manager.get_app_config(parsed_cmd.app_id)
            print(f"{Fore.GREEN}Launched {app_config.name}{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}Failed to launch application{Style.RESET_ALL}")
        
        return success
    
    def _handle_open_url(self, parsed_cmd) -> bool:
        """Handle URL opening command."""
        if parsed_cmd.website_id:
            # Open configured website
            website_config = self.config_manager.get_website_config(parsed_cmd.website_id)
            url = website_config.url
            print(f"{Fore.CYAN}Opening {website_config.name}: {url}{Style.RESET_ALL}")
        else:
            # Open direct URL
            url = parsed_cmd.url
            print(f"{Fore.CYAN}Opening URL: {url}{Style.RESET_ALL}")
        
        if parsed_cmd.app_id:
            # Use specific browser
            success = self.app_manager.launch_app(
                parsed_cmd.app_id,
                website_id=parsed_cmd.website_id,
                url=parsed_cmd.url,
                force_new=parsed_cmd.options.get('new', False)
            )
        else:
            # Use default browser
            success = self.app_manager.open_url(url)
        
        if not success:
            print(f"{Fore.RED}Failed to open URL{Style.RESET_ALL}")
        
        return success
    
    def _handle_window_control(self, parsed_cmd) -> bool:
        """Handle window control command."""
        action = parsed_cmd.window_action
        app_id = parsed_cmd.app_id
        window_id = parsed_cmd.window_id
        
        if action == "list":
            if app_id:
                windows = self.app_manager.get_app_windows(app_id)
                if windows:
                    print(f"{Fore.CYAN}Windows for {app_id}:{Style.RESET_ALL}")
                    for i, window in enumerate(windows, 1):
                        status = " (active)" if window.is_active else ""
                        minimized = " [minimized]" if window.is_minimized else ""
                        print(f"  {i}. {window.window_id}: {window.title}{status}{minimized}")
                else:
                    print(f"{Fore.YELLOW}No windows found for {app_id}{Style.RESET_ALL}")
            else:
                windows = self.window_manager.list_all_windows()
                if windows:
                    print(f"{Fore.CYAN}All windows:{Style.RESET_ALL}")
                    formatted = self.window_manager.format_window_list(windows)
                    print(formatted)
                else:
                    print(f"{Fore.YELLOW}No windows found{Style.RESET_ALL}")
            return True
        
        elif action == "activate":
            if window_id:
                success = self.window_manager.activate_window_by_id(window_id)
            elif app_id:
                success = self.app_manager.activate_window(app_id)
            else:
                print(f"{Fore.RED}Window ID or application required for activate{Style.RESET_ALL}")
                return False
                
            if success:
                print(f"{Fore.GREEN}Window activated{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}Failed to activate window{Style.RESET_ALL}")
            
            return success
        
        elif action == "minimize":
            if window_id:
                success = self.window_manager.minimize_window_by_id(window_id)
            elif app_id:
                success = self.app_manager.minimize_window(app_id)
            else:
                print(f"{Fore.RED}Window ID or application required for minimize{Style.RESET_ALL}")
                return False
                
            if success:
                print(f"{Fore.GREEN}Window minimized{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}Failed to minimize window{Style.RESET_ALL}")
            
            return success
        
        elif action == "close":
            if window_id:
                success = self.window_manager.close_window_by_id(window_id)
            elif app_id:
                success = self.app_manager.close_window(app_id)
            else:
                print(f"{Fore.RED}Window ID or application required for close{Style.RESET_ALL}")
                return False
                
            if success:
                print(f"{Fore.GREEN}Window closed{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}Failed to close window{Style.RESET_ALL}")
            
            return success
        
        else:
            print(f"{Fore.RED}Unknown window action: {action}{Style.RESET_ALL}")
            return False
    
    def _handle_help(self, parsed_cmd) -> bool:
        """Handle help command."""
        topic = parsed_cmd.options.get('topic')
        help_text = self.command_parser.get_help_text(topic)
        print(help_text)
        return True
    
    def _handle_config(self, parsed_cmd) -> bool:
        """Handle configuration command."""
        action = parsed_cmd.options.get('action', 'show')
        
        if action == "show":
            self._show_configuration()
        elif action == "reload":
            success = self.config_manager.reload()
            if success:
                print(f"{Fore.GREEN}Configuration reloaded successfully{Style.RESET_ALL}")
                # Reload hotkeys
                self.hotkey_manager.reload_configuration()
            else:
                print(f"{Fore.RED}Failed to reload configuration{Style.RESET_ALL}")
            return success
        elif action == "list":
            args = parsed_cmd.options.get('args', [])
            if args and args[0] == "apps":
                self._list_apps()
            elif args and args[0] == "websites":
                self._list_websites()
            else:
                print(f"{Fore.RED}Usage: config list [apps|websites]{Style.RESET_ALL}")
                return False
        else:
            print(f"{Fore.RED}Unknown config action: {action}{Style.RESET_ALL}")
            return False
        
        return True
    
    def _handle_quit(self, parsed_cmd) -> bool:
        """Handle quit command."""
        force = parsed_cmd.options.get('force', False)
        
        if force:
            print(f"{Fore.YELLOW}Force quitting...{Style.RESET_ALL}")
            self.stop()
            sys.exit(0)
        else:
            print(f"{Fore.YELLOW}Quitting Terminal Controller...{Style.RESET_ALL}")
            self.stop()
            sys.exit(0)
    
    def _show_configuration(self):
        """Show current configuration."""
        print(f"{Fore.CYAN}Terminal Controller Configuration:{Style.RESET_ALL}")
        print()
        
        # Show apps
        apps = self.config_manager.get_all_apps()
        print(f"{Fore.GREEN}Applications ({len(apps)}):{Style.RESET_ALL}")
        for app_id, app_config in apps.items():
            print(f"  {app_id}: {app_config.name} ({app_config.type})")
        print()
        
        # Show websites
        websites = self.config_manager.get_all_websites()
        print(f"{Fore.GREEN}Websites ({len(websites)}):{Style.RESET_ALL}")
        for website_id, website_config in websites.items():
            print(f"  {website_id}: {website_config.name}")
        print()
        
        # Show hotkeys
        if self.hotkey_manager.is_active():
            print(f"{Fore.GREEN}Hotkey Bindings:{Style.RESET_ALL}")
            bindings_text = self.hotkey_manager.format_bindings_list()
            print(bindings_text)
        else:
            print(f"{Fore.YELLOW}Hotkey manager is not active{Style.RESET_ALL}")
    
    def _list_apps(self):
        """List all available applications."""
        apps = self.config_manager.get_all_apps()
        print(f"{Fore.CYAN}Available Applications:{Style.RESET_ALL}")
        
        for app_id, app_config in apps.items():
            running = self.app_manager.is_app_running(app_id)
            status = f" {Fore.GREEN}[running]{Style.RESET_ALL}" if running else ""
            print(f"  {Fore.YELLOW}{app_id}{Style.RESET_ALL}: {app_config.name} ({app_config.type}){status}")
            if app_config.description:
                print(f"    {app_config.description}")
    
    def _list_websites(self):
        """List all available websites."""
        websites = self.config_manager.get_all_websites()
        print(f"{Fore.CYAN}Available Websites:{Style.RESET_ALL}")
        
        for website_id, website_config in websites.items():
            print(f"  {Fore.YELLOW}{website_id}{Style.RESET_ALL}: {website_config.name}")
            print(f"    {website_config.url}")
            if website_config.description:
                print(f"    {website_config.description}")
    
    def _setup_logging(self):
        """Set up logging configuration."""
        log_level = logging.DEBUG if self.debug else logging.INFO
        
        # Create logs directory if it doesn't exist
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)
        
        # Configure logging
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(logs_dir / "terminalController.log"),
                logging.StreamHandler() if self.debug else logging.NullHandler()
            ]
        )
    
    def _setup_signal_handlers(self):
        """Set up signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, shutting down gracefully")
            self.stop()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Platform-specific signals
        if hasattr(signal, 'SIGHUP'):
            signal.signal(signal.SIGHUP, signal_handler)


# CLI Interface using Click，yz这一行很关键，能够保证读取的是安装目录的文件，原因待学习
@click.group(invoke_without_command=True)
@click.option('--config-dir', '-c', default=None, 
              help='Configuration directory path')
@click.option('--debug', '-d', is_flag=True, 
              help='Enable debug logging')
@click.pass_context
def cli(ctx, config_dir, debug):
    """Terminal Controller - Cross-platform application launcher and window manager."""
    global main_controller
    
    # Ensure context object exists
    ctx.ensure_object(dict)
    ctx.obj['config_dir'] = config_dir
    ctx.obj['debug'] = debug
    
    # If no subcommand is provided, run interactive mode
    if ctx.invoked_subcommand is None:
        main_controller = TerminalController(config_dir, debug)
        main_controller.interactive_mode()


@cli.command()
@click.pass_context
def daemon(ctx):
    """Start Terminal Controller as a daemon process."""
    config_dir = ctx.obj['config_dir']
    debug = ctx.obj['debug']
    
    global main_controller
    main_controller = TerminalController(config_dir, debug)
    
    success = main_controller.start_daemon()
    sys.exit(0 if success else 1)


@cli.command()
@click.argument('command', nargs=-1, required=True)
@click.pass_context
def run(ctx, command):
    """Execute a single command."""
    config_dir = ctx.obj['config_dir']
    debug = ctx.obj['debug']
    
    global main_controller
    main_controller = TerminalController(config_dir, debug)
    
    command_str = ' '.join(command)
    success = main_controller.execute_command(command_str)
    sys.exit(0 if success else 1)


@cli.command()
@click.pass_context
def status(ctx):
    """Show Terminal Controller status."""
    config_dir = ctx.obj['config_dir']
    debug = ctx.obj['debug']
    
    main_controller = TerminalController(config_dir, debug)
    main_controller._show_configuration()


@cli.command()
@click.pass_context
def stop(ctx):
    """Stop Terminal Controller daemon."""
    # TODO: Implement daemon PID file checking and stopping
    print("Daemon stop functionality not yet implemented")


if __name__ == "__main__":
    try:
        cli()
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Interrupted by user{Style.RESET_ALL}")
        if main_controller:
            main_controller.stop()
        sys.exit(130)
    except Exception as e:
        print(f"{Fore.RED}Fatal error: {e}{Style.RESET_ALL}")
        if main_controller:
            main_controller.stop()
        sys.exit(1)
