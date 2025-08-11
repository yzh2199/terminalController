#!/usr/bin/env python3
"""
增强守护进程服务器
基于原版main.py实现高性能的进程间通信
"""
import os
import sys
import socket
import json
import threading
import time
import signal
import logging
from pathlib import Path
from typing import Optional
import io
from contextlib import redirect_stdout, redirect_stderr

# 确保能导入所需模块
import sys
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# 导入必要的模块
import config_manager
import app_manager  
import window_manager
import terminal_manager
import hotkey_manager
import command_parser

logger = logging.getLogger(__name__)


class DaemonTerminalController:
    """守护进程内部的Terminal Controller实现"""
    
    def __init__(self, config_dir: Optional[str] = None, debug: bool = False):
        """初始化Terminal Controller for daemon"""
        self.debug = debug
        
        # Use installed config directory by default
        if config_dir is None:
            installed_config = Path.home() / ".terminal-controller" / "config"
            if installed_config.exists():
                config_dir = str(installed_config)
            else:
                config_dir = "config"  # Fallback to local config
        self.config_dir = config_dir
        
        # Initialize managers
        self.config_manager = config_manager.ConfigManager(self.config_dir)
        self.app_manager = app_manager.AppManager(self.config_manager)
        self.window_manager = window_manager.WindowManager(self.config_manager)
        self.terminal_manager = terminal_manager.TerminalManager(self.config_manager)
        self.hotkey_manager = hotkey_manager.HotkeyManager(self.config_manager)
        self.command_parser = command_parser.CommandParser()
        
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Initialized Daemon Terminal Controller")
    
    def execute_command(self, command: str) -> bool:
        """Execute a user command in daemon context"""
        try:
            from colorama import Fore, Style
            
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
            
            # Execute the command based on type - simplified for daemon
            if parsed_cmd.command_type == command_parser.CommandType.LAUNCH_APP:
                return self._handle_launch_app(parsed_cmd)
            elif parsed_cmd.command_type == command_parser.CommandType.OPEN_URL:
                return self._handle_open_url(parsed_cmd)
            elif parsed_cmd.command_type == command_parser.CommandType.WINDOW_CONTROL:
                return self._handle_window_control(parsed_cmd)
            elif parsed_cmd.command_type == command_parser.CommandType.HELP:
                return self._handle_help(parsed_cmd)
            elif parsed_cmd.command_type == command_parser.CommandType.CONFIG:
                return self._handle_config(parsed_cmd)
            elif parsed_cmd.command_type == command_parser.CommandType.QUIT:
                return self._handle_quit(parsed_cmd)
            else:
                print(f"{Fore.RED}Unknown command type: {parsed_cmd.command_type}{Style.RESET_ALL}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error executing command '{command}': {e}")
            print(f"Error executing command: {e}")
            return False
    
    def _handle_launch_app(self, parsed_cmd) -> bool:
        """Handle application launch command."""
        from colorama import Fore, Style
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
        from colorama import Fore, Style
        if parsed_cmd.website_id:
            website_config = self.config_manager.get_website_config(parsed_cmd.website_id)
            url = website_config.url
            print(f"{Fore.CYAN}Opening {website_config.name}: {url}{Style.RESET_ALL}")
        else:
            url = parsed_cmd.url
            print(f"{Fore.CYAN}Opening URL: {url}{Style.RESET_ALL}")
        
        if parsed_cmd.app_id:
            success = self.app_manager.launch_app(
                parsed_cmd.app_id,
                website_id=parsed_cmd.website_id,
                url=parsed_cmd.url,
                force_new=parsed_cmd.options.get('new', False)
            )
        else:
            success = self.app_manager.open_url(url)
        
        if not success:
            print(f"{Fore.RED}Failed to open URL{Style.RESET_ALL}")
        
        return success
    
    def _handle_window_control(self, parsed_cmd) -> bool:
        """Handle window control command."""
        from colorama import Fore, Style
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
        from colorama import Fore, Style
        action = parsed_cmd.options.get('action', 'show')
        
        if action == "show":
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
            
        elif action == "reload":
            success = self.config_manager.reload()
            if success:
                print(f"{Fore.GREEN}Configuration reloaded successfully{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}Failed to reload configuration{Style.RESET_ALL}")
            return success
        
        elif action == "list":
            args = parsed_cmd.options.get('args', [])
            if args and args[0] == "apps":
                apps = self.config_manager.get_all_apps()
                print(f"{Fore.CYAN}Available Applications:{Style.RESET_ALL}")
                for app_id, app_config in apps.items():
                    running = self.app_manager.is_app_running(app_id)
                    status = f" {Fore.GREEN}[running]{Style.RESET_ALL}" if running else ""
                    print(f"  {Fore.YELLOW}{app_id}{Style.RESET_ALL}: {app_config.name} ({app_config.type}){status}")
            elif args and args[0] == "websites":
                websites = self.config_manager.get_all_websites()
                print(f"{Fore.CYAN}Available Websites:{Style.RESET_ALL}")
                for website_id, website_config in websites.items():
                    print(f"  {Fore.YELLOW}{website_id}{Style.RESET_ALL}: {website_config.name}")
                    print(f"    {website_config.url}")
            else:
                print(f"{Fore.RED}Usage: config list [apps|websites]{Style.RESET_ALL}")
                return False
        else:
            print(f"{Fore.RED}Unknown config action: {action}{Style.RESET_ALL}")
            return False
        
        return True
    
    def _handle_quit(self, parsed_cmd) -> bool:
        """Handle quit command in daemon - just return success"""
        from colorama import Fore, Style
        print(f"{Fore.YELLOW}Daemon quit command received{Style.RESET_ALL}")
        return True


class DaemonServer:
    """增强守护进程服务器"""
    
    def __init__(self, socket_path: str = "/tmp/terminal_controller.sock"):
        """
        初始化守护进程服务器
        
        Args:
            socket_path: Unix Socket路径
        """
        self.socket_path = socket_path
        self.running = False
        self.server_socket: Optional[socket.socket] = None
        self.controller: Optional[TerminalController] = None
        
        # 统计信息
        self.request_count = 0
        self.total_execution_time = 0.0
        
        logger.info(f"守护进程服务器初始化，Socket路径: {socket_path}")
    
    def start(self, config_dir: Optional[str] = None, debug: bool = False) -> bool:
        """
        启动守护进程服务器
        
        Args:
            config_dir: 配置目录
            debug: 调试模式
            
        Returns:
            启动是否成功
        """
        try:
            logger.info("🚀 启动增强守护进程服务器...")
            
            # 初始化Terminal Controller
            self.controller = DaemonTerminalController(config_dir, debug)
            logger.info("✅ Terminal Controller初始化完成")
            
            # 启动热键管理器
            if not self.controller.hotkey_manager.start():
                logger.error("❌ 热键管理器启动失败")
                return False
            logger.info("✅ 热键管理器启动成功")
            
            # 创建Unix Socket服务器
            if not self._setup_socket():
                return False
            
            # 设置信号处理
            self._setup_signal_handlers()
            
            self.running = True
            logger.info(f"🎯 增强守护进程启动成功，监听: {self.socket_path}")
            
            # 主服务循环
            self._serve_forever()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 启动守护进程失败: {e}")
            return False
        finally:
            self._cleanup()
    
    def _setup_socket(self) -> bool:
        """设置Unix Socket服务器"""
        try:
            # 删除已存在的socket文件
            if os.path.exists(self.socket_path):
                os.unlink(self.socket_path)
                logger.info(f"删除旧的socket文件: {self.socket_path}")
            
            # 创建Unix domain socket
            self.server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.server_socket.bind(self.socket_path)
            self.server_socket.listen(10)  # 支持10个并发连接
            
            # 设置socket权限
            os.chmod(self.socket_path, 0o666)
            
            logger.info(f"✅ Socket服务器创建成功: {self.socket_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Socket创建失败: {e}")
            return False
    
    def _serve_forever(self):
        """主服务循环"""
        logger.info("📡 开始监听客户端连接...")
        
        try:
            while self.running:
                try:
                    # 设置超时以便响应停止信号
                    self.server_socket.settimeout(1.0)
                    
                    # 接受客户端连接
                    client_socket, client_addr = self.server_socket.accept()
                    logger.debug(f"📥 新客户端连接")
                    
                    # 在新线程中处理请求（支持并发）
                    thread = threading.Thread(
                        target=self._handle_client,
                        args=(client_socket,),
                        daemon=True
                    )
                    thread.start()
                    
                except socket.timeout:
                    # 超时继续循环，检查running状态
                    continue
                except Exception as e:
                    if self.running:
                        logger.error(f"❌ 接受连接错误: {e}")
                        
        except KeyboardInterrupt:
            logger.info("🛑 收到键盘中断")
        except Exception as e:
            logger.error(f"❌ 服务循环错误: {e}")
    
    def _handle_client(self, client_socket: socket.socket):
        """
        处理客户端请求
        
        Args:
            client_socket: 客户端socket连接
        """
        try:
            # 接收请求数据
            data = client_socket.recv(4096).decode('utf-8')
            if not data:
                logger.warning("⚠️ 收到空数据")
                return
            
            # 解析请求
            try:
                request = json.loads(data)
            except json.JSONDecodeError as e:
                logger.error(f"❌ JSON解析错误: {e}")
                self._send_error_response(client_socket, f"Invalid JSON: {e}")
                return
            
            command = request.get('command', '').strip()
            if not command:
                self._send_error_response(client_socket, "Empty command")
                return
            
            logger.info(f"📥 收到命令: '{command}'")
            
            # 执行命令并计时
            start_time = time.perf_counter()
            
            try:
                # 捕获输出内容
                output_buffer = io.StringIO()
                success = False
                
                # 重定向stdout来捕获print输出
                with redirect_stdout(output_buffer):
                    success = self.controller.execute_command(command)
                
                execution_time = (time.perf_counter() - start_time) * 1000
                output_content = output_buffer.getvalue()
                
                # 更新统计
                self.request_count += 1
                self.total_execution_time += execution_time
                
                # 发送成功响应
                response = {
                    'success': success,
                    'execution_time_ms': round(execution_time, 2),
                    'output': output_content.strip() if output_content else '',
                    'message': '命令执行成功' if success else '命令执行失败',
                    'request_id': self.request_count
                }
                
                self._send_response(client_socket, response)
                logger.info(f"📤 命令完成: {execution_time:.2f}ms (请求#{self.request_count})")
                
            except Exception as e:
                execution_time = (time.perf_counter() - start_time) * 1000
                logger.error(f"❌ 命令执行错误: {e}")
                self._send_error_response(
                    client_socket, 
                    f"Command execution error: {e}",
                    execution_time
                )
                
        except Exception as e:
            logger.error(f"❌ 处理客户端请求错误: {e}")
            try:
                self._send_error_response(client_socket, f"Server error: {e}")
            except:
                pass
        finally:
            try:
                client_socket.close()
            except:
                pass
    
    def _send_response(self, client_socket: socket.socket, response: dict):
        """发送响应给客户端"""
        try:
            response_data = json.dumps(response, ensure_ascii=False).encode('utf-8')
            client_socket.send(response_data)
        except Exception as e:
            logger.error(f"❌ 发送响应错误: {e}")
    
    def _send_error_response(self, client_socket: socket.socket, error_msg: str, 
                           execution_time: float = 0):
        """发送错误响应"""
        response = {
            'success': False,
            'error': error_msg,
            'execution_time_ms': round(execution_time, 2),
            'output': ''
        }
        self._send_response(client_socket, response)
    
    def _setup_signal_handlers(self):
        """设置信号处理器"""
        def signal_handler(signum, frame):
            logger.info(f"📡 收到信号 {signum}，准备关闭守护进程...")
            self.stop()
        
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        
        # macOS特有信号
        if hasattr(signal, 'SIGHUP'):
            signal.signal(signal.SIGHUP, signal_handler)
    
    def stop(self):
        """停止守护进程"""
        logger.info("🛑 停止守护进程...")
        self.running = False
    
    def _cleanup(self):
        """清理资源"""
        logger.info("🧹 清理守护进程资源...")
        
        # 关闭socket
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        
        # 删除socket文件
        if os.path.exists(self.socket_path):
            try:
                os.unlink(self.socket_path)
                logger.info(f"删除socket文件: {self.socket_path}")
            except:
                pass
        
        # 停止控制器
        if self.controller:
            try:
                self.controller.stop()
            except:
                pass
        
        # 打印统计信息
        if self.request_count > 0:
            avg_time = self.total_execution_time / self.request_count
            logger.info(f"📊 服务统计: 处理了{self.request_count}个请求，平均耗时{avg_time:.2f}ms")
        
        logger.info("✅ 守护进程已完全停止")


def main():
    """主函数 - 用于直接运行守护进程"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Terminal Controller 增强守护进程服务器')
    parser.add_argument('--socket', '-s', default='/tmp/terminal_controller.sock',
                       help='Unix Socket路径 (默认: /tmp/terminal_controller.sock)')
    parser.add_argument('--config-dir', '-c', default=None,
                       help='配置目录路径')
    parser.add_argument('--debug', '-d', action='store_true',
                       help='启用调试模式')
    
    args = parser.parse_args()
    
    # 设置日志
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print(f"🚀 启动 Terminal Controller 增强守护进程")
    print(f"📡 Socket路径: {args.socket}")
    print(f"🔧 配置目录: {args.config_dir or '默认'}")
    print(f"📝 调试模式: {'开启' if args.debug else '关闭'}")
    print()
    
    # 启动守护进程
    server = DaemonServer(args.socket)
    success = server.start(args.config_dir, args.debug)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
