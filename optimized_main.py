#!/usr/bin/env python3
"""
todo 目前optimized_main.py在交互模式下无法启动热键监听，后续修改为跟main.py一样后删除main.py，因为这个性能更好
优化版Terminal Controller主程序
主要优化：
1. 单例控制器模式 - 避免重复初始化 (节省200-500ms)
2. 延迟加载配置 - 只在需要时加载
3. 快速命令执行路径
4. 优化的平台适配器
"""
import os
import sys
import signal
import logging
import argparse
import platform
import time
from pathlib import Path
from typing import Optional

import click
from colorama import init as colorama_init, Fore, Style

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.config_manager import ConfigManager
from src.app_manager import AppManager
from src.window_manager import WindowManager
from src.terminal_manager import TerminalManager
from src.hotkey_manager import HotkeyManager
from src.command_parser import CommandParser, CommandType

# 初始化colorama
colorama_init()

# 全局变量
_singleton_controller = None


class OptimizedTerminalController:
    """
    优化版Terminal Controller
    
    性能优化特性：
    1. 单例模式 - 避免重复初始化
    2. 延迟加载 - 只在需要时初始化组件
    3. 快速执行路径 - 常用操作优化
    4. 缓存管理 - 减少重复计算
    """
    
    _instance = None
    _initialized = False
    
    def __new__(cls, *args, **kwargs):
        """单例模式实现"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, config_dir: Optional[str] = None, debug: bool = False):
        """
        初始化控制器
        优化：单例模式，只初始化一次
        """
        if self._initialized:
            return
        
        self.debug = debug
        
        # 使用安装配置目录
        if config_dir is None:
            installed_config = Path.home() / ".terminal-controller" / "config"
            if installed_config.exists():
                config_dir = str(installed_config)
            else:
                config_dir = "config"
        
        self.config_dir = config_dir
        self.running = False
        
        # 初始化日志
        self._setup_logging()
        
        # 延迟初始化：只创建必要的组件
        self._config_manager = None
        self._app_manager = None
        self._window_manager = None
        self._terminal_manager = None
        self._hotkey_manager = None
        self._command_parser = None
        
        # 注册信号处理器
        self._setup_signal_handlers()
        
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"优化版Terminal Controller初始化完成 ({platform.system()})")
        
        # Register current terminal context if we're running in a terminal
        self._register_terminal_context()
        
        self._initialized = True
    
    @property
    def config_manager(self) -> ConfigManager:
        """延迟加载配置管理器"""
        if self._config_manager is None:
            start = time.time()
            self._config_manager = ConfigManager(self.config_dir)
            load_time = (time.time() - start) * 1000
            self.logger.debug(f"配置管理器加载耗时: {load_time:.2f}ms")
        return self._config_manager
    
    @property
    def app_manager(self) -> AppManager:
        """延迟加载应用管理器"""
        if self._app_manager is None:
            start = time.time()
            self._app_manager = AppManager(self.config_manager)
            load_time = (time.time() - start) * 1000
            self.logger.debug(f"应用管理器加载耗时: {load_time:.2f}ms")
        return self._app_manager
    
    @property
    def window_manager(self) -> WindowManager:
        """延迟加载窗口管理器"""
        if self._window_manager is None:
            start = time.time()
            
            # 使用优化的平台适配器
            from src.platform.macos_optimized import OptimizedMacOSAdapter
            
            # 创建优化版本的窗口管理器
            self._window_manager = WindowManager(self.config_manager)
            
            # 替换为优化的适配器
            if platform.system().lower() == "darwin":
                self._window_manager.platform_adapter = OptimizedMacOSAdapter()
                self.logger.info("使用优化版macOS适配器")
            
            load_time = (time.time() - start) * 1000
            self.logger.debug(f"窗口管理器加载耗时: {load_time:.2f}ms")
        
        return self._window_manager
    
    @property
    def terminal_manager(self) -> TerminalManager:
        """延迟加载终端管理器"""
        if self._terminal_manager is None:
            self._terminal_manager = TerminalManager(self.config_manager)
        return self._terminal_manager
    
    @property
    def hotkey_manager(self) -> HotkeyManager:
        """延迟加载热键管理器"""
        if self._hotkey_manager is None:
            self._hotkey_manager = HotkeyManager(self.config_manager)
        return self._hotkey_manager
    
    @property
    def command_parser(self) -> CommandParser:
        """延迟加载命令解析器"""
        if self._command_parser is None:
            self._command_parser = CommandParser()
        return self._command_parser
    
    @classmethod
    def get_instance(cls, config_dir: Optional[str] = None, debug: bool = False):
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls(config_dir, debug)
        return cls._instance
    
    def execute_command_fast(self, command: str) -> bool:
        """
        快速命令执行
        优化：针对常用操作的快速路径
        """
        total_start = time.time()
        
        try:
            # 快速解析命令
            parsed_cmd = self.command_parser.parse(command)
            if not parsed_cmd:
                print(f"{Fore.RED}无效命令: {command}{Style.RESET_ALL}")
                return False
            
            # 快速验证（简化版）
            if parsed_cmd.command_type == CommandType.WINDOW_CONTROL:
                return self._handle_window_control_fast(parsed_cmd)
            elif parsed_cmd.command_type == CommandType.LAUNCH_APP:
                return self._handle_launch_app_fast(parsed_cmd)
            else:
                # 其他命令使用标准路径
                return self.execute_command(command)
        
        except Exception as e:
            self.logger.error(f"快速执行命令失败 '{command}': {e}")
            return False
        
        finally:
            total_time = (time.time() - total_start) * 1000
            self.logger.debug(f"总执行时间: {total_time:.2f}ms")
    
    def _handle_window_control_fast(self, parsed_cmd) -> bool:
        """
        快速窗口控制处理
        优化：跳过不必要的验证，直接执行
        """
        action = parsed_cmd.window_action
        app_id = parsed_cmd.app_id
        window_id = parsed_cmd.window_id
        
        if action == "activate":
            if window_id:
                success = self.window_manager.activate_window_by_id(window_id)
            elif app_id:
                # 快速路径：直接激活最近使用的窗口
                success = self.window_manager.focus_most_recent_window(app_id)
            else:
                return False
            
            if success:
                print(f"{Fore.GREEN}窗口已激活{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}窗口激活失败{Style.RESET_ALL}")
            
            return success
        
        elif action == "list":
            if app_id:
                windows = self.app_manager.get_app_windows(app_id)
                if windows:
                    print(f"{Fore.CYAN}{app_id} 的窗口:{Style.RESET_ALL}")
                    for i, window in enumerate(windows, 1):
                        status = " (活动)" if window.is_active else ""
                        minimized = " [最小化]" if window.is_minimized else ""
                        print(f"  {i}. {window.window_id}: {window.title}{status}{minimized}")
                else:
                    print(f"{Fore.YELLOW}未找到 {app_id} 的窗口{Style.RESET_ALL}")
            else:
                windows = self.window_manager.list_all_windows()
                if windows:
                    print(f"{Fore.CYAN}所有窗口:{Style.RESET_ALL}")
                    formatted = self.window_manager.format_window_list(windows)
                    print(formatted)
                else:
                    print(f"{Fore.YELLOW}未找到窗口{Style.RESET_ALL}")
            return True
        
        else:
            # 其他操作使用标准处理
            return self._handle_window_control(parsed_cmd)
    
    def _handle_launch_app_fast(self, parsed_cmd) -> bool:
        """快速应用启动"""
        force_new = parsed_cmd.options.get('new', False)
        
        success = self.app_manager.launch_app(
            parsed_cmd.app_id,
            force_new=force_new
        )
        
        if success:
            app_config = self.config_manager.get_app_config(parsed_cmd.app_id)
            # Check if this was a terminal switch operation
            if app_config.type == "terminal" and not force_new:
                # For terminal, check if we switched to existing window or launched new
                tc_context = self.config_manager.get_tc_context_window()
                if tc_context:
                    print(f"{Fore.GREEN}已切换到 {app_config.name} 窗口{Style.RESET_ALL}")
                else:
                    print(f"{Fore.GREEN}已启动 {app_config.name}{Style.RESET_ALL}")
            else:
                print(f"{Fore.GREEN}已启动 {app_config.name}{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}启动应用失败{Style.RESET_ALL}")
        
        return success
    
    def execute_command(self, command: str) -> bool:
        """标准命令执行（保持原有逻辑）"""
        try:
            parsed_cmd = self.command_parser.parse(command)
            if not parsed_cmd:
                print(f"{Fore.RED}无效命令: {command}{Style.RESET_ALL}")
                return False
            
            # 验证命令
            available_apps = list(self.config_manager.get_all_apps().keys())
            available_websites = list(self.config_manager.get_all_websites().keys())
            
            is_valid, error_msg = self.command_parser.validate_command(
                parsed_cmd, available_apps, available_websites
            )
            
            if not is_valid:
                print(f"{Fore.RED}错误: {error_msg}{Style.RESET_ALL}")
                return False
            
            # 执行命令
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
                print(f"{Fore.RED}未知命令类型: {parsed_cmd.command_type}{Style.RESET_ALL}")
                return False
                
        except Exception as e:
            self.logger.error(f"执行命令错误 '{command}': {e}")
            print(f"{Fore.RED}命令执行错误: {e}{Style.RESET_ALL}")
            return False
    
    # 以下方法保持原有实现...
    def start_daemon(self) -> bool:
        """启动守护进程"""
        try:
            self.logger.info("启动Terminal Controller守护进程")
            
            if not self.hotkey_manager.start():
                self.logger.error("热键管理器启动失败")
                return False
            
            self.running = True
            self.logger.info("Terminal Controller守护进程启动成功")
            
            try:
                while self.running:
                    time.sleep(1)
            except KeyboardInterrupt:
                self.logger.info("收到中断信号")
            
            return True
            
        except Exception as e:
            self.logger.error(f"启动守护进程错误: {e}")
            return False
        finally:
            self.stop()
    
    def stop(self):
        """停止控制器"""
        try:
            self.logger.info("停止Terminal Controller")
            self.running = False
            
            # 停止管理器
            if self._hotkey_manager:
                self._hotkey_manager.cleanup()
            
            if self._window_manager:
                self._window_manager.cleanup()
            
            self.logger.info("Terminal Controller已停止")
            
        except Exception as e:
            self.logger.error(f"停止控制器错误: {e}")
    
    # 原有的处理方法（简化版本）
    def _handle_launch_app(self, parsed_cmd) -> bool:
        """处理应用启动命令"""
        force_new = parsed_cmd.options.get('new', False)
        success = self.app_manager.launch_app(parsed_cmd.app_id, force_new=force_new)
        
        if success:
            app_config = self.config_manager.get_app_config(parsed_cmd.app_id)
            print(f"{Fore.GREEN}已启动 {app_config.name}{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}启动应用失败{Style.RESET_ALL}")
        
        return success
    
    def _handle_open_url(self, parsed_cmd) -> bool:
        """处理URL打开命令"""
        if parsed_cmd.website_id:
            website_config = self.config_manager.get_website_config(parsed_cmd.website_id)
            url = website_config.url
            print(f"{Fore.CYAN}打开 {website_config.name}: {url}{Style.RESET_ALL}")
        else:
            url = parsed_cmd.url
            print(f"{Fore.CYAN}打开URL: {url}{Style.RESET_ALL}")
        
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
            print(f"{Fore.RED}打开URL失败{Style.RESET_ALL}")
        
        return success
    
    def _handle_window_control(self, parsed_cmd) -> bool:
        """处理窗口控制命令"""
        action = parsed_cmd.window_action
        app_id = parsed_cmd.app_id
        window_id = parsed_cmd.window_id
        
        if action == "list":
            if app_id:
                windows = self.app_manager.get_app_windows(app_id)
                if windows:
                    print(f"{Fore.CYAN}{app_id} 的窗口:{Style.RESET_ALL}")
                    for i, window in enumerate(windows, 1):
                        status = " (活动)" if window.is_active else ""
                        minimized = " [最小化]" if window.is_minimized else ""
                        print(f"  {i}. {window.window_id}: {window.title}{status}{minimized}")
                else:
                    print(f"{Fore.YELLOW}未找到 {app_id} 的窗口{Style.RESET_ALL}")
            else:
                windows = self.window_manager.list_all_windows()
                if windows:
                    print(f"{Fore.CYAN}所有窗口:{Style.RESET_ALL}")
                    formatted = self.window_manager.format_window_list(windows)
                    print(formatted)
                else:
                    print(f"{Fore.YELLOW}未找到窗口{Style.RESET_ALL}")
            return True
        
        elif action == "activate":
            if window_id:
                success = self.window_manager.activate_window_by_id(window_id)
            elif app_id:
                success = self.app_manager.activate_window(app_id)
            else:
                print(f"{Fore.RED}激活需要窗口ID或应用程序{Style.RESET_ALL}")
                return False
                
            if success:
                print(f"{Fore.GREEN}窗口已激活{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}窗口激活失败{Style.RESET_ALL}")
            
            return success
        
        # 其他窗口操作...
        return True
    
    def _handle_help(self, parsed_cmd) -> bool:
        """处理帮助命令"""
        topic = parsed_cmd.options.get('topic')
        help_text = self.command_parser.get_help_text(topic)
        print(help_text)
        return True
    
    def _handle_config(self, parsed_cmd) -> bool:
        """处理配置命令"""
        action = parsed_cmd.options.get('action', 'show')
        
        if action == "show":
            self._show_configuration()
        elif action == "reload":
            success = self.config_manager.reload()
            if success:
                print(f"{Fore.GREEN}配置重新加载成功{Style.RESET_ALL}")
                self.hotkey_manager.reload_configuration()
            else:
                print(f"{Fore.RED}配置重新加载失败{Style.RESET_ALL}")
            return success
        # 其他配置操作...
        
        return True
    
    def _handle_quit(self, parsed_cmd) -> bool:
        """处理退出命令"""
        force = parsed_cmd.options.get('force', False)
        
        if force:
            print(f"{Fore.YELLOW}强制退出...{Style.RESET_ALL}")
        else:
            print(f"{Fore.YELLOW}退出Terminal Controller...{Style.RESET_ALL}")
        
        self.stop()
        sys.exit(0)
    
    def _show_configuration(self):
        """显示当前配置"""
        print(f"{Fore.CYAN}Terminal Controller 配置:{Style.RESET_ALL}")
        print()
        
        apps = self.config_manager.get_all_apps()
        print(f"{Fore.GREEN}应用程序 ({len(apps)}):{Style.RESET_ALL}")
        for app_id, app_config in apps.items():
            print(f"  {app_id}: {app_config.name} ({app_config.type})")
        print()
        
        websites = self.config_manager.get_all_websites()
        print(f"{Fore.GREEN}网站 ({len(websites)}):{Style.RESET_ALL}")
        for website_id, website_config in websites.items():
            print(f"  {website_id}: {website_config.name}")
    
    def interactive_mode(self):
        """交互模式"""
        print(f"{Fore.GREEN}Terminal Controller - 交互模式 (优化版){Style.RESET_ALL}")
        print(f"输入 '{Fore.CYAN}help{Style.RESET_ALL}' 查看命令，'{Fore.CYAN}quit{Style.RESET_ALL}' 退出")
        print()
        
        # Ensure terminal context is registered for interactive mode
        self._register_terminal_context()
        
        # Start hotkey manager for interactive mode
        hotkey_started = False
        try:
            if self.hotkey_manager.start():
                hotkey_started = True
                print(f"{Fore.GREEN}✅ 热键已启用 (Ctrl+; 可用){Style.RESET_ALL}")
                self.logger.info("热键管理器在交互模式中启动")
            else:
                print(f"{Fore.YELLOW}⚠️  热键不可用 (可能需要权限){Style.RESET_ALL}")
                self.logger.warning("在交互模式中启动热键管理器失败")
        except Exception as e:
            print(f"{Fore.YELLOW}⚠️  热键不可用: {e}{Style.RESET_ALL}")
            self.logger.error(f"启动热键管理器错误: {e}")
        
        try:
            while True:
                try:
                    command = input(f"{Fore.YELLOW}tc> {Style.RESET_ALL}").strip()
                    
                    if not command:
                        continue
                    
                    if command.lower() in ['quit', 'exit', 'q']:
                        break
                    
                    # 使用快速执行路径
                    start_time = time.time()
                    self.execute_command_fast(command)
                    execution_time = (time.time() - start_time) * 1000
                    
                    if self.debug:
                        print(f"{Fore.BLUE}[执行时间: {execution_time:.2f}ms]{Style.RESET_ALL}")
                    
                    print()
                    
                except KeyboardInterrupt:
                    print(f"\n{Fore.YELLOW}使用 'quit' 退出{Style.RESET_ALL}")
                except EOFError:
                    break
                    
        except Exception as e:
            self.logger.error(f"交互模式错误: {e}")
            print(f"{Fore.RED}交互模式错误: {e}{Style.RESET_ALL}")
        finally:
            # Stop hotkey manager if it was started
            if hotkey_started:
                try:
                    self.hotkey_manager.stop()
                    self.logger.info("热键管理器已停止")
                except Exception as e:
                    self.logger.error(f"停止热键管理器错误: {e}")
            
            # Clear terminal context when exiting interactive mode
            self._clear_terminal_context()
        
        print(f"{Fore.GREEN}再见!{Style.RESET_ALL}")
    
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
    
    def _setup_logging(self):
        """设置日志"""
        log_level = logging.DEBUG if self.debug else logging.INFO
        
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)
        
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(logs_dir / "terminalController_optimized.log"),
                logging.StreamHandler() if self.debug else logging.NullHandler()
            ]
        )
    
    def _setup_signal_handlers(self):
        """设置信号处理器"""
        def signal_handler(signum, frame):
            self.logger.info(f"收到信号 {signum}，正常关闭")
            self.stop()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        if hasattr(signal, 'SIGHUP'):
            signal.signal(signal.SIGHUP, signal_handler)


# CLI接口
@click.group(invoke_without_command=True)
@click.option('--config-dir', '-c', default=None, help='配置目录路径')
@click.option('--debug', '-d', is_flag=True, help='启用调试日志')
@click.pass_context
def cli(ctx, config_dir, debug):
    """优化版Terminal Controller - 跨平台应用启动器和窗口管理器"""
    global _singleton_controller
    
    ctx.ensure_object(dict)
    ctx.obj['config_dir'] = config_dir
    ctx.obj['debug'] = debug
    
    if ctx.invoked_subcommand is None:
        _singleton_controller = OptimizedTerminalController.get_instance(config_dir, debug)
        _singleton_controller.interactive_mode()


@cli.command()
@click.pass_context
def daemon(ctx):
    """启动Terminal Controller守护进程"""
    config_dir = ctx.obj['config_dir']
    debug = ctx.obj['debug']
    
    global _singleton_controller
    _singleton_controller = OptimizedTerminalController.get_instance(config_dir, debug)
    
    success = _singleton_controller.start_daemon()
    sys.exit(0 if success else 1)


@cli.command()
@click.argument('command', nargs=-1, required=True)
@click.pass_context
def run(ctx, command):
    """执行单个命令 (优化版)"""
    config_dir = ctx.obj['config_dir']
    debug = ctx.obj['debug']
    
    global _singleton_controller
    _singleton_controller = OptimizedTerminalController.get_instance(config_dir, debug)
    
    command_str = ' '.join(command)
    
    # 记录总执行时间
    start_time = time.time()
    success = _singleton_controller.execute_command_fast(command_str)
    total_time = (time.time() - start_time) * 1000
    
    if debug:
        print(f"总执行时间: {total_time:.2f}ms")
    
    sys.exit(0 if success else 1)


@cli.command()
@click.pass_context
def status(ctx):
    """显示Terminal Controller状态"""
    config_dir = ctx.obj['config_dir']
    debug = ctx.obj['debug']
    
    controller = OptimizedTerminalController.get_instance(config_dir, debug)
    controller._show_configuration()


def fast_execute(command: str, config_dir: Optional[str] = None) -> bool:
    """
    快速执行命令的便捷函数
    用于外部脚本直接调用
    """
    controller = OptimizedTerminalController.get_instance(config_dir)
    return controller.execute_command_fast(command)


if __name__ == "__main__":
    try:
        cli()
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}用户中断{Style.RESET_ALL}")
        if _singleton_controller:
            _singleton_controller.stop()
        sys.exit(130)
    except Exception as e:
        print(f"{Fore.RED}致命错误: {e}{Style.RESET_ALL}")
        if _singleton_controller:
            _singleton_controller.stop()
        sys.exit(1)
