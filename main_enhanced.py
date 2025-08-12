#!/usr/bin/env python3
"""
Terminal Controller Enhanced - A cross-platform application launcher and window manager.

This is the main entry point for the Enhanced Terminal Controller application.
Features:
- Enhanced daemon process with IPC support
- High-performance command execution
- Client-server architecture
"""

import os
import sys
import signal
import logging
import argparse
import platform
import threading
import socket
import json
import time
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
    """Enhanced Terminal Controller with daemon IPC support."""
    
    def __init__(self, config_dir: Optional[str] = None, debug: bool = False):
        """Initialize the Enhanced Terminal Controller.
        
        Args:
            config_dir: Directory containing configuration files
            debug: Enable debug logging
        """
        self.debug = debug
        # Use installed config directory by default
        if config_dir is None:
            installed_config = Path.home() / ".terminal-controller" / "config"
            if installed_config.exists():
                config_dir = str(installed_config)
            else:
                config_dir = "config"  # Fallback to local config
        self.config_dir = config_dir
        self.running = False
        
        # Enhanced daemon IPC support
        self.daemon_socket_path = "/tmp/terminal_controller.sock"
        self.daemon_server = None
        self.daemon_server_thread = None
        
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
        self.logger.info(f"Initialized Enhanced Terminal Controller on {platform.system()}")
    
    def start_daemon(self) -> bool:
        """Start the Enhanced Terminal Controller as a daemon process with IPC support.
        
        Returns:
            True if daemon started successfully, False otherwise
        """
        try:
            self.logger.info("🚀 Starting Enhanced Terminal Controller daemon")
            
            # Start hotkey manager
            if not self.hotkey_manager.start():
                self.logger.error("❌ Failed to start hotkey manager")
                return False
            self.logger.info("✅ Hotkey manager started successfully")
            
            self.running = True
            
            # Start enhanced daemon IPC server
            if not self._start_daemon_server():
                self.logger.error("❌ Failed to start daemon IPC server")
                return False
            self.logger.info("✅ Daemon IPC server started successfully")
            self.logger.info("🎯 Enhanced Terminal Controller daemon started successfully")
            print(f"{Fore.GREEN}Enhanced daemon started successfully!{Style.RESET_ALL}")
            print(f"{Fore.CYAN}Socket: {self.daemon_socket_path}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}Use 'python3 daemon_client.py <command>' to send commands{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}Use 'python3 main_enhanced.py send <command>' for quick access{Style.RESET_ALL}")
            print()
            
            # Keep the daemon running
            try:
                while self.running:
                    time.sleep(1)
            except KeyboardInterrupt:
                self.logger.info("🛑 Received interrupt signal")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error starting enhanced daemon: {e}")
            return False
        finally:
            self.stop()
    
    def stop(self):
        """Stop the Enhanced Terminal Controller daemon."""
        try:
            self.logger.info("🛑 Stopping Enhanced Terminal Controller")
            self.running = False
            
            # Stop daemon IPC server
            if self.daemon_server_thread and self.daemon_server_thread.is_alive():
                try:
                    # The daemon server will stop when self.running becomes False
                    self.daemon_server_thread.join(timeout=5)
                    self.logger.info("✅ Daemon IPC server stopped")
                except Exception as e:
                    self.logger.error(f"❌ Error stopping daemon server: {e}")
            
            # Stop managers
            if hasattr(self, 'hotkey_manager'):
                self.hotkey_manager.cleanup()
            
            if hasattr(self, 'window_manager'):
                self.window_manager.cleanup()
            
            self.logger.info("✅ Enhanced Terminal Controller stopped")
            
        except Exception as e:
            self.logger.error(f"❌ Error stopping Enhanced Terminal Controller: {e}")
    
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
        
        # Ensure terminal context is registered for interactive mode
        self._register_terminal_context()
        
        # 【hotkey】注册交互会话，支持精确的热键终端切换
        current_pid = os.getpid()
        current_window_id = self.window_manager.get_current_terminal_window_id()
        if current_window_id:
            self.config_manager.register_interactive_session(current_window_id, current_pid)
            self.logger.info(f"【hotkey】Interactive session registered: PID={current_pid}, window={current_window_id}")  # 交互会话已注册
        
        # Start hotkey manager for interactive mode
        hotkey_started = False
        try:
            if self.hotkey_manager.start():
                hotkey_started = True
                print(f"{Fore.GREEN}✅ Hotkeys enabled (Ctrl+; available){Style.RESET_ALL}")
                self.logger.info("Hotkey manager started in interactive mode")
            else:
                print(f"{Fore.YELLOW}⚠️  Hotkeys not available (may require permissions){Style.RESET_ALL}")
                self.logger.warning("Failed to start hotkey manager in interactive mode")
        except Exception as e:
            print(f"{Fore.YELLOW}⚠️  Hotkeys not available: {e}{Style.RESET_ALL}")
            self.logger.error(f"Error starting hotkey manager: {e}")
        
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
        finally:
            # Stop hotkey manager if it was started
            if hotkey_started:
                try:
                    self.hotkey_manager.stop()
                    self.logger.info("Hotkey manager stopped")
                except Exception as e:
                    self.logger.error(f"Error stopping hotkey manager: {e}")
            
            # 【hotkey】注销交互会话
            current_pid = os.getpid()
            self.config_manager.unregister_interactive_session(current_pid)
            self.logger.info(f"【hotkey】Interactive session unregistered: PID={current_pid}")  # 交互会话已注销
            
            # Clear terminal context when exiting interactive mode
            self._clear_terminal_context()
        
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
    
    def _start_daemon_server(self) -> bool:
        """Start the simplified daemon IPC server in a separate thread."""
        try:
            # Create simplified daemon server directly
            self.daemon_server_thread = threading.Thread(
                target=self._run_daemon_server,
                daemon=True
            )
            self.daemon_server_thread.start()
            
            # Wait a moment for server to start
            time.sleep(0.5)
            
            # Check if server started successfully
            if os.path.exists(self.daemon_socket_path):
                return True
            else:
                self.logger.error("❌ Daemon server failed to create socket")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Error starting daemon server: {e}")
            return False
    
    def _run_daemon_server(self):
        """Run the simplified daemon IPC server"""
        try:
            # Remove existing socket file
            if os.path.exists(self.daemon_socket_path):
                os.unlink(self.daemon_socket_path)
            
            # Create Unix domain socket
            server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            server_socket.bind(self.daemon_socket_path)
            server_socket.listen(5)
            
            # Set socket permissions
            os.chmod(self.daemon_socket_path, 0o666)
            
            self.logger.info(f"✅ Simplified daemon server listening on {self.daemon_socket_path}")
            
            # Request counters for statistics
            request_count = 0
            
            while self.running:
                try:
                    # Set timeout so we can check self.running
                    server_socket.settimeout(1.0)
                    
                    # Accept client connection
                    client_socket, _ = server_socket.accept()
                    
                    # Handle request in current thread (simplified)
                    self._handle_daemon_request(client_socket, request_count)
                    request_count += 1
                    
                except socket.timeout:
                    # Timeout - continue loop to check running status
                    continue
                except Exception as e:
                    if self.running:
                        self.logger.error(f"❌ Error in daemon server: {e}")
            
            # Cleanup
            server_socket.close()
            if os.path.exists(self.daemon_socket_path):
                os.unlink(self.daemon_socket_path)
            
            self.logger.info("✅ Simplified daemon server stopped")
            
        except Exception as e:
            self.logger.error(f"❌ Daemon server error: {e}")
    
    def _handle_daemon_request(self, client_socket: socket.socket, request_id: int):
        """Handle a single daemon request"""
        try:
            # Receive request data
            data = client_socket.recv(4096).decode('utf-8')
            if not data:
                return
            
            # Parse request
            try:
                request = json.loads(data)
                command = request.get('command', '').strip()
            except json.JSONDecodeError:
                self._send_daemon_error(client_socket, "Invalid JSON")
                return
            
            if not command:
                self._send_daemon_error(client_socket, "Empty command")
                return
            
            self.logger.info(f"📥 Processing command: '{command}' (request #{request_id})")
            
            # Execute command and measure time
            start_time = time.perf_counter()
            
            # Capture command output
            import io
            from contextlib import redirect_stdout
            
            output_buffer = io.StringIO()
            success = False
            
            try:
                with redirect_stdout(output_buffer):
                    success = self.execute_command(command)
                
                execution_time = (time.perf_counter() - start_time) * 1000
                output_content = output_buffer.getvalue()
                
                # Send success response
                response = {
                    'success': success,
                    'execution_time_ms': round(execution_time, 2),
                    'output': output_content.strip() if output_content else '',
                    'message': 'Command executed successfully' if success else 'Command execution failed',
                    'request_id': request_id
                }
                
                self._send_daemon_response(client_socket, response)
                self.logger.info(f"📤 Command completed: {execution_time:.2f}ms (request #{request_id})")
                
            except Exception as e:
                execution_time = (time.perf_counter() - start_time) * 1000
                self.logger.error(f"❌ Command execution error: {e}")
                self._send_daemon_error(client_socket, f"Command execution error: {e}", execution_time)
                
        except Exception as e:
            self.logger.error(f"❌ Error handling daemon request: {e}")
        finally:
            try:
                client_socket.close()
            except:
                pass
    
    def _send_daemon_response(self, client_socket: socket.socket, response: dict):
        """Send response to daemon client"""
        try:
            response_data = json.dumps(response, ensure_ascii=False).encode('utf-8')
            client_socket.send(response_data)
        except Exception as e:
            self.logger.error(f"❌ Error sending daemon response: {e}")
    
    def _send_daemon_error(self, client_socket: socket.socket, error_msg: str, 
                          execution_time: float = 0):
        """Send error response to daemon client"""
        response = {
            'success': False,
            'error': error_msg,
            'execution_time_ms': round(execution_time, 2),
            'output': ''
        }
        self._send_daemon_response(client_socket, response)
    
    def send_to_daemon(self, command: str, timeout: float = 10.0) -> dict:
        """Send command to running daemon process.
        
        Args:
            command: Command to send
            timeout: Timeout in seconds
            
        Returns:
            Response dictionary from daemon
        """
        try:
            # Check if daemon is running
            if not os.path.exists(self.daemon_socket_path):
                return {
                    'success': False,
                    'error': 'Daemon is not running',
                    'execution_time_ms': 0
                }
            
            # Connect to daemon
            client_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            client_socket.settimeout(timeout)
            
            try:
                client_socket.connect(self.daemon_socket_path)
                
                # Send command
                request = {'command': command}
                request_data = json.dumps(request, ensure_ascii=False).encode('utf-8')
                client_socket.send(request_data)
                
                # Receive response
                response_data = client_socket.recv(8192).decode('utf-8')
                response = json.loads(response_data)
                
                return response
                
            finally:
                client_socket.close()
                
        except socket.timeout:
            return {
                'success': False,
                'error': f'Command timeout (>{timeout}s)',
                'execution_time_ms': timeout * 1000
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Client error: {e}',
                'execution_time_ms': 0
            }
    
    def is_daemon_running(self) -> bool:
        """Check if daemon is running."""
        try:
            response = self.send_to_daemon("help", timeout=2.0)
            return response.get('success', False)
        except:
            return False
    
    def _register_terminal_context(self):
        """Register the current terminal window as TC context if applicable."""
        try:
            terminal_window_id = self.window_manager.get_current_terminal_window_id()
            if terminal_window_id:
                self.config_manager.set_tc_context_window(terminal_window_id)
                self.logger.debug(f"Registered TC context terminal: {terminal_window_id}")
            else:
                self.logger.debug("TC not running in a terminal, no context to register")
        except Exception as e:
            self.logger.error(f"Error registering terminal context: {e}")
    
    def _clear_terminal_context(self):
        """Clear the TC context when TC exits."""
        try:
            self.config_manager.clear_tc_context_window()
            self.logger.debug("Cleared TC context")
        except Exception as e:
            self.logger.error(f"Error clearing terminal context: {e}")


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
    try:
        socket_path = "/tmp/terminal_controller.sock"
        
        if not os.path.exists(socket_path):
            print(f"{Fore.YELLOW}Daemon is not running (socket file not found){Style.RESET_ALL}")
            sys.exit(0)
        
        # Try to send quit command to daemon
        controller = TerminalController()
        response = controller.send_to_daemon("quit", timeout=5.0)
        
        if response.get('success'):
            print(f"{Fore.GREEN}Daemon stopped successfully{Style.RESET_ALL}")
            
            # Wait for socket file to be removed
            for _ in range(10):
                if not os.path.exists(socket_path):
                    break
                time.sleep(0.5)
            
            if os.path.exists(socket_path):
                print(f"{Fore.YELLOW}Warning: Socket file still exists{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}Failed to stop daemon: {response.get('error', 'Unknown error')}{Style.RESET_ALL}")
            
            # Force remove socket file if needed
            try:
                os.unlink(socket_path)
                print(f"{Fore.YELLOW}Removed orphaned socket file{Style.RESET_ALL}")
            except:
                pass
                
    except Exception as e:
        print(f"{Fore.RED}Error stopping daemon: {e}{Style.RESET_ALL}")
        sys.exit(1)


@cli.command()
@click.argument('command', nargs=-1, required=True)
@click.option('--timeout', '-t', type=float, default=10.0,
              help='Command timeout in seconds')
@click.option('--verbose', '-v', is_flag=True,
              help='Show detailed execution information')
@click.pass_context
def send(ctx, command, timeout, verbose):
    """Send command to running daemon process."""
    try:
        command_str = ' '.join(command)
        
        # Create controller instance for client operations
        controller = TerminalController()
        
        # Check if daemon is running
        if not controller.is_daemon_running():
            print(f"{Fore.RED}❌ Daemon is not running{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}Start daemon with: python3 main_enhanced.py daemon{Style.RESET_ALL}")
            sys.exit(1)
        
        print(f"{Fore.CYAN}📤 Sending command: '{command_str}'{Style.RESET_ALL}")
        
        # Send command and measure total time
        start_time = time.perf_counter()
        response = controller.send_to_daemon(command_str, timeout)
        total_time = (time.perf_counter() - start_time) * 1000
        
        if response['success']:
            print(f"{Fore.GREEN}✅ Command executed successfully{Style.RESET_ALL}")
            
            # Show command output if available
            if response.get('output'):
                print(f"\n{Fore.CYAN}📋 Output:{Style.RESET_ALL}")
                print(response['output'])
            
            # Show performance info
            if verbose:
                daemon_time = response.get('execution_time_ms', 0)
                ipc_overhead = total_time - daemon_time
                print(f"\n{Fore.BLUE}📊 Performance:{Style.RESET_ALL}")
                print(f"  Total time: {total_time:.2f}ms")
                print(f"  Daemon execution: {daemon_time:.2f}ms")
                print(f"  IPC overhead: {ipc_overhead:.2f}ms")
                print(f"  Request ID: {response.get('request_id', 'N/A')}")
            else:
                print(f"{Fore.BLUE}⚡ Execution time: {response.get('execution_time_ms', 0):.2f}ms{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}❌ Command failed{Style.RESET_ALL}")
            print(f"Error: {response.get('error', 'Unknown error')}")
            
            if verbose:
                print(f"Total time: {total_time:.2f}ms")
            
            sys.exit(1)
            
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Command interrupted{Style.RESET_ALL}")
        sys.exit(130)
    except Exception as e:
        print(f"{Fore.RED}Client error: {e}{Style.RESET_ALL}")
        sys.exit(1)


@cli.command()
@click.option('--socket', '-s', default='/tmp/terminal_controller.sock',
              help='Daemon socket path')
@click.pass_context  
def daemon_status(ctx, socket):
    """Check daemon status and performance."""
    try:
        controller = TerminalController()
        controller.daemon_socket_path = socket
        
        print(f"{Fore.CYAN}🔍 Checking daemon status...{Style.RESET_ALL}")
        print(f"Socket path: {socket}")
        print(f"Socket exists: {'Yes' if os.path.exists(socket) else 'No'}")
        
        if controller.is_daemon_running():
            print(f"{Fore.GREEN}Status: 🟢 Running{Style.RESET_ALL}")
            
            # Test performance
            print(f"\n{Fore.CYAN}⚡ Testing performance...{Style.RESET_ALL}")
            
            test_commands = ["help", "config"]
            for cmd in test_commands:
                start = time.perf_counter()
                response = controller.send_to_daemon(cmd, timeout=5.0)
                total_time = (time.perf_counter() - start) * 1000
                
                if response['success']:
                    daemon_time = response.get('execution_time_ms', 0)
                    print(f"  {cmd}: {daemon_time:.2f}ms (total: {total_time:.2f}ms)")
                else:
                    print(f"  {cmd}: Failed - {response.get('error', 'Unknown error')}")
        else:
            print(f"{Fore.RED}Status: 🔴 Not running{Style.RESET_ALL}")
            sys.exit(1)
            
    except Exception as e:
        print(f"{Fore.RED}Error checking daemon status: {e}{Style.RESET_ALL}")
        sys.exit(1)


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
