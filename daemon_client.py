'''
Author: yangzhi05 && <yangzhi05@kuaishou.com>
Date: 2025-08-12 09:07:43
'''
#!/usr/bin/env python3
"""
守护进程客户端工具
用于向守护进程发送命令
"""
import os
import sys
import socket
import json
import time
import argparse
from typing import Dict, Optional


class DaemonClient:
    """守护进程客户端"""
    
    def __init__(self, socket_path: str = "/tmp/terminal_controller.sock"):
        """
        初始化客户端
        
        Args:
            socket_path: Unix Socket路径
        """
        self.socket_path = socket_path
    
    def send_command(self, command: str, timeout: float = 10.0) -> Dict:
        """
        发送命令到守护进程
        
        Args:
            command: 要执行的命令
            timeout: 超时时间（秒）
            
        Returns:
            包含执行结果的字典
        """
        try:
            # 检查socket文件是否存在
            if not os.path.exists(self.socket_path):
                return {
                    'success': False,
                    'error': f'守护进程未运行，socket文件不存在: {self.socket_path}',
                    'execution_time_ms': 0,
                    'output': ''
                }
            
            # 连接到守护进程
            client_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            client_socket.settimeout(timeout)
            
            try:
                client_socket.connect(self.socket_path)
                
                # 发送命令
                request = {'command': command}
                request_data = json.dumps(request, ensure_ascii=False).encode('utf-8')
                client_socket.send(request_data)
                
                # 接收响应
                response_data = client_socket.recv(8192).decode('utf-8')
                response = json.loads(response_data)
                
                return response
                
            finally:
                client_socket.close()
                
        except socket.timeout:
            return {
                'success': False,
                'error': f'命令执行超时 (>{timeout}s)',
                'execution_time_ms': timeout * 1000,
                'output': ''
            }
        except ConnectionRefusedError:
            return {
                'success': False,
                'error': '无法连接到守护进程，请确保守护进程正在运行',
                'execution_time_ms': 0,
                'output': ''
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'客户端错误: {e}',
                'execution_time_ms': 0,
                'output': ''
            }
    
    def is_daemon_running(self) -> bool:
        """检查守护进程是否运行"""
        try:
            response = self.send_command("help", timeout=2.0)
            return response['success']
        except:
            return False
    
    def benchmark(self, commands: list = None, iterations: int = 5) -> Dict:
        """
        性能基准测试
        
        Args:
            commands: 要测试的命令列表
            iterations: 每个命令的测试次数
            
        Returns:
            基准测试结果
        """
        if commands is None:
            commands = ["help", "config", "config list apps"]
        
        print(f"🚀 开始性能基准测试 ({iterations}次迭代)")
        print("-" * 50)
        
        results = {}
        total_time = 0
        total_requests = 0
        
        for command in commands:
            print(f"\n📋 测试命令: '{command}'")
            times = []
            
            for i in range(iterations):
                print(f"  迭代 {i+1}/{iterations}", end="\r", flush=True)
                
                start = time.perf_counter()
                response = self.send_command(command)
                end = time.perf_counter()
                
                client_total_time = (end - start) * 1000
                daemon_time = response.get('execution_time_ms', 0)
                
                times.append({
                    'client_total': client_total_time,
                    'daemon_execution': daemon_time,
                    'ipc_overhead': client_total_time - daemon_time,
                    'success': response.get('success', False)
                })
                
                time.sleep(0.1)  # 避免过于频繁的请求
            
            print()  # 换行
            
            # 计算统计信息
            successful_times = [t for t in times if t['success']]
            if successful_times:
                avg_total = sum(t['client_total'] for t in successful_times) / len(successful_times)
                avg_daemon = sum(t['daemon_execution'] for t in successful_times) / len(successful_times)
                avg_ipc = sum(t['ipc_overhead'] for t in successful_times) / len(successful_times)
                
                results[command] = {
                    'avg_total_time': avg_total,
                    'avg_daemon_time': avg_daemon,
                    'avg_ipc_overhead': avg_ipc,
                    'success_rate': len(successful_times) / len(times) * 100,
                    'iterations': len(times)
                }
                
                total_time += avg_total * len(successful_times)
                total_requests += len(successful_times)
                
                print(f"  📊 平均总耗时: {avg_total:.2f}ms")
                print(f"  ⚡ 平均守护进程执行: {avg_daemon:.2f}ms")
                print(f"  📡 平均IPC开销: {avg_ipc:.2f}ms")
                print(f"  ✅ 成功率: {len(successful_times)}/{len(times)} ({results[command]['success_rate']:.1f}%)")
            else:
                print(f"  ❌ 所有请求都失败了")
                results[command] = {
                    'avg_total_time': 0,
                    'avg_daemon_time': 0,
                    'avg_ipc_overhead': 0,
                    'success_rate': 0,
                    'iterations': len(times)
                }
        
        # 总体统计
        if total_requests > 0:
            overall_avg = total_time / total_requests
            print(f"\n🎯 总体性能:")
            print(f"  平均响应时间: {overall_avg:.2f}ms")
            print(f"  总请求数: {total_requests}")
            print(f"  性能评级: {'优秀' if overall_avg < 20 else '良好' if overall_avg < 50 else '一般'}")
        
        return {
            'results': results,
            'overall_avg_time': total_time / total_requests if total_requests > 0 else 0,
            'total_requests': total_requests
        }


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='Terminal Controller 守护进程客户端')
    parser.add_argument('command', nargs='*', help='要执行的命令')
    parser.add_argument('--socket', '-s', default='/tmp/terminal_controller.sock',
                       help='Unix Socket路径')
    parser.add_argument('--timeout', '-t', type=float, default=10.0,
                       help='命令超时时间（秒）')
    parser.add_argument('--benchmark', '-b', action='store_true',
                       help='运行性能基准测试')
    parser.add_argument('--status', action='store_true',
                       help='检查守护进程状态')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='显示详细输出')
    
    args = parser.parse_args()
    
    client = DaemonClient(args.socket)
    
    # 检查状态
    if args.status:
        print("🔍 检查守护进程状态...")
        is_running = client.is_daemon_running()
        print(f"守护进程状态: {'🟢 运行中' if is_running else '🔴 未运行'}")
        print(f"Socket路径: {args.socket}")
        print(f"Socket文件存在: {'是' if os.path.exists(args.socket) else '否'}")
        sys.exit(0 if is_running else 1)
    
    # 基准测试
    if args.benchmark:
        if not client.is_daemon_running():
            print("❌ 守护进程未运行，无法进行基准测试")
            print("请先启动守护进程: python3 main.py daemon")
            sys.exit(1)
        
        results = client.benchmark()
        sys.exit(0)
    
    # 执行命令
    if not args.command:
        print("❌ 请提供要执行的命令")
        print("示例:")
        print("  python3 daemon_client.py help")
        print("  python3 daemon_client.py c")
        print("  python3 daemon_client.py 'config list apps'")
        print("  python3 daemon_client.py --benchmark")
        print("  python3 daemon_client.py --status")
        sys.exit(1)
    
    command_str = ' '.join(args.command)
    
    print(f"📤 发送命令: '{command_str}'")
    
    start_time = time.perf_counter()
    response = client.send_command(command_str, args.timeout)
    total_time = (time.perf_counter() - start_time) * 1000
    
    if response['success']:
        print(f"✅ 命令执行成功")
        if response.get('output'):
            print(f"\n📋 输出内容:")
            print(response['output'])
        
        if args.verbose:
            daemon_time = response.get('execution_time_ms', 0)
            ipc_overhead = total_time - daemon_time
            print(f"\n📊 性能统计:")
            print(f"  总耗时: {total_time:.2f}ms")
            print(f"  守护进程执行: {daemon_time:.2f}ms")
            print(f"  IPC通信开销: {ipc_overhead:.2f}ms")
            print(f"  请求ID: {response.get('request_id', 'N/A')}")
    else:
        print(f"❌ 命令执行失败")
        print(f"错误信息: {response.get('error', '未知错误')}")
        
        if args.verbose:
            print(f"总耗时: {total_time:.2f}ms")
        
        sys.exit(1)


if __name__ == "__main__":
    main()
