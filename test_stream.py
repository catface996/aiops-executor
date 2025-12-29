#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
流式事件测试脚本 - Chatbot 交互模式

实时显示层级多智能体系统的执行过程，类似 ChatGPT 的对话体验。

使用方法:
    python test_stream.py [options] [task]

选项:
    --api=URL         指定API地址 (默认: http://localhost:8082)
    --skip-create     跳过创建层级团队，使用已有的
    --hierarchy=ID    指定已有的层级团队ID

示例:
    python test_stream.py "请用50字解释量子纠缠"
    python test_stream.py --api=http://ec2-ip:8080 "测试问题"
"""

import sys
import json
import time
import os
import requests
from datetime import datetime

# 配置
API_BASE = os.environ.get("API_BASE", "http://localhost:8082")
HIERARCHY_ID = ""

# ANSI 颜色代码
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    # 前景色
    BLACK = "\033[30m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"

    # 背景色
    BG_BLUE = "\033[44m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_MAGENTA = "\033[45m"
    BG_CYAN = "\033[46m"


# 角色样式配置
ROLE_STYLES = {
    'global_supervisor': {
        'icon': '🎯',
        'name': 'Global Supervisor',
        'color': Colors.MAGENTA + Colors.BOLD,
        'bg': ''
    },
    'team_supervisor': {
        'icon': '👔',
        'name': 'Team Supervisor',
        'color': Colors.CYAN + Colors.BOLD,
        'bg': ''
    },
    'worker': {
        'icon': '🔬',
        'name': 'Worker',
        'color': Colors.GREEN + Colors.BOLD,
        'bg': ''
    },
    'system': {
        'icon': '⚙️',
        'name': 'System',
        'color': Colors.BLUE,
        'bg': ''
    }
}


# 默认层级团队配置
DEFAULT_HIERARCHY_CONFIG = {
    "name": "测试研究团队",
    "global_prompt": """你是测试研究团队的首席科学家，负责协调理论研究和应用研究两个小组。
你的职责是分析研究任务，将任务分配给合适的团队，并综合各团队的研究成果。""",
    "execution_mode": "sequential",
    "enable_context_sharing": True,
    "teams": [
        {
            "name": "理论研究组",
            "supervisor_prompt": """你是理论研究组的负责人，协调理论研究工作。
你需要将研究任务分配给组内的专家，并整合他们的研究成果。""",
            "workers": [
                {
                    "name": "理论专家",
                    "role": "理论研究员",
                    "system_prompt": """你是理论专家，专注于理论基础研究。
请用清晰、准确的语言回答问题。"""
                },
                {
                    "name": "分析专家",
                    "role": "分析研究员",
                    "system_prompt": """你是分析专家，专注于深度分析研究。
请从分析角度解释问题。"""
                }
            ]
        },
        {
            "name": "应用研究组",
            "supervisor_prompt": """你是应用研究组的负责人，协调应用研究工作。
你需要将应用研究任务分配给组内的专家，并整合他们的研究成果。""",
            "workers": [
                {
                    "name": "应用专家",
                    "role": "应用研究员",
                    "system_prompt": """你是应用专家，专注于应用实践研究。
请从应用角度分析问题。"""
                },
                {
                    "name": "实践专家",
                    "role": "实践研究员",
                    "system_prompt": """你是实践专家，专注于实际案例研究。
请从实践角度分析问题。"""
                }
            ]
        }
    ]
}


class ChatbotDisplay:
    """Chatbot 风格的显示器"""

    def __init__(self):
        self.current_role = None
        self.current_content = ""
        self.line_started = False

    def _get_role_info(self, event):
        """从事件中获取角色信息"""
        if event.get('is_global_supervisor'):
            return 'global_supervisor', 'Global Supervisor', None
        elif event.get('is_team_supervisor'):
            team_name = event.get('team_name', 'Unknown Team')
            return 'team_supervisor', f"{team_name} Supervisor", team_name
        elif event.get('worker_name'):
            team_name = event.get('team_name', '')
            worker_name = event.get('worker_name')
            return 'worker', f"{worker_name}", team_name
        elif event.get('team_name'):
            return 'team_supervisor', f"{event['team_name']} Supervisor", event['team_name']
        return 'system', 'System', None

    def _print_role_header(self, role_type, role_name, team_name=None):
        """打印角色头部"""
        style = ROLE_STYLES.get(role_type, ROLE_STYLES['system'])

        # 结束上一行
        if self.line_started:
            print()
            self.line_started = False

        print()  # 空行分隔

        # 打印角色标识
        header = f"{style['color']}{style['icon']} {role_name}{Colors.RESET}"
        if team_name and role_type == 'worker':
            header += f" {Colors.DIM}({team_name}){Colors.RESET}"

        print(header)
        print(f"{Colors.DIM}{'─' * 50}{Colors.RESET}")

    def _print_stream_content(self, content):
        """打印流式内容（不换行）"""
        sys.stdout.write(content)
        sys.stdout.flush()
        self.line_started = True

    def _print_content(self, content):
        """打印完整内容"""
        if self.line_started:
            print()
            self.line_started = False
        print(content)

    def process_event(self, event):
        """处理单个事件"""
        event_type = event.get('event_type', '')
        data = event.get('data', {})

        role_type, role_name, team_name = self._get_role_info(event)

        # 处理不同类型的事件
        if event_type == 'llm_stream':
            # LLM 流式输出 - 核心交互体验
            content = data.get('content', '')
            if content:
                # 检查是否需要切换角色
                if self.current_role != (role_type, role_name):
                    self._print_role_header(role_type, role_name, team_name)
                    self.current_role = (role_type, role_name)

                # 实时输出内容
                self._print_stream_content(content)

        elif event_type == 'llm_output':
            # LLM 完整输出
            content = data.get('content', '')
            if content and not self.line_started:  # 避免重复
                if self.current_role != (role_type, role_name):
                    self._print_role_header(role_type, role_name, team_name)
                    self.current_role = (role_type, role_name)
                self._print_content(content)

        elif event_type == 'llm_tool_call':
            # 工具调用
            tool_name = data.get('tool_name', '')
            if tool_name:
                if self.line_started:
                    print()
                    self.line_started = False
                print(f"\n{Colors.YELLOW}🔧 调用工具: {tool_name}{Colors.RESET}")

        elif event_type == 'global_dispatch':
            # Global Supervisor 调度
            target = data.get('name', '')
            if target:
                if self.line_started:
                    print()
                    self.line_started = False
                print(f"\n{Colors.MAGENTA}📤 调度团队: {target}{Colors.RESET}")

        elif event_type == 'team_dispatch':
            # Team Supervisor 调度
            target = data.get('name', '')
            if target:
                if self.line_started:
                    print()
                    self.line_started = False
                print(f"\n{Colors.CYAN}📤 调度成员: {target}{Colors.RESET}")

        elif event_type == 'output':
            # 一般输出
            content = data.get('content', '')
            if content:
                # 过滤装饰性消息
                if '开始协调' in content or '思考中' in content or '开始工作' in content:
                    return  # 跳过这些消息，用 llm_stream 替代
                if '完成' in content:
                    if self.line_started:
                        print()
                        self.line_started = False
                    print(f"\n{Colors.GREEN}✅ {content}{Colors.RESET}")
                    self.current_role = None

        elif event_type == 'execution_started':
            task = data.get('task', '')
            print(f"\n{Colors.BLUE}{'═' * 60}{Colors.RESET}")
            print(f"{Colors.BLUE}🚀 开始执行任务{Colors.RESET}")
            if task:
                print(f"{Colors.DIM}任务: {task[:100]}...{Colors.RESET}" if len(task) > 100 else f"{Colors.DIM}任务: {task}{Colors.RESET}")
            print(f"{Colors.BLUE}{'═' * 60}{Colors.RESET}\n")

        elif event_type == 'execution_completed':
            if self.line_started:
                print()
                self.line_started = False
            print(f"\n{Colors.GREEN}{'═' * 60}{Colors.RESET}")
            print(f"{Colors.GREEN}🎉 任务执行完成!{Colors.RESET}")
            print(f"{Colors.GREEN}{'═' * 60}{Colors.RESET}")

        elif event_type == 'execution_failed':
            if self.line_started:
                print()
                self.line_started = False
            error = data.get('error', 'Unknown error')
            print(f"\n{Colors.RED}{'═' * 60}{Colors.RESET}")
            print(f"{Colors.RED}❌ 执行失败: {error}{Colors.RESET}")
            print(f"{Colors.RED}{'═' * 60}{Colors.RESET}")


def print_hierarchy_structure():
    """打印层级团队结构"""
    config = DEFAULT_HIERARCHY_CONFIG

    print(f"\n{Colors.CYAN}{'═' * 60}{Colors.RESET}")
    print(f"{Colors.CYAN}📊 层级团队结构{Colors.RESET}")
    print(f"{Colors.CYAN}{'═' * 60}{Colors.RESET}")

    # 打印全局信息
    print(f"\n{Colors.MAGENTA}{Colors.BOLD}🎯 Global Supervisor: {config['name']}{Colors.RESET}")
    print(f"{Colors.DIM}   执行模式: {config.get('execution_mode', 'sequential')}{Colors.RESET}")
    print(f"{Colors.DIM}   上下文共享: {config.get('enable_context_sharing', False)}{Colors.RESET}")

    # 打印团队结构
    teams = config.get('teams', [])
    for i, team in enumerate(teams):
        team_name = team.get('name', f'Team {i+1}')
        is_last_team = (i == len(teams) - 1)
        team_prefix = "└──" if is_last_team else "├──"

        print(f"\n{Colors.CYAN}{Colors.BOLD}   {team_prefix} 👔 Team Supervisor: {team_name}{Colors.RESET}")

        # 打印 Worker
        workers = team.get('workers', [])
        for j, worker in enumerate(workers):
            worker_name = worker.get('name', f'Worker {j+1}')
            worker_role = worker.get('role', '')
            is_last_worker = (j == len(workers) - 1)

            if is_last_team:
                worker_prefix = "       └──" if is_last_worker else "       ├──"
            else:
                worker_prefix = "   │   └──" if is_last_worker else "   │   ├──"

            print(f"{Colors.GREEN}   {worker_prefix} 🔬 {worker_name}{Colors.RESET}", end="")
            if worker_role:
                print(f" {Colors.DIM}({worker_role}){Colors.RESET}")
            else:
                print()

    print(f"\n{Colors.CYAN}{'═' * 60}{Colors.RESET}\n")


def create_hierarchy_team():
    """创建层级团队"""
    print(f"\n{Colors.CYAN}📦 创建层级团队...{Colors.RESET}")

    try:
        response = requests.post(
            f"{API_BASE}/api/executor/v1/hierarchies/create",
            json=DEFAULT_HIERARCHY_CONFIG,
            headers={"Content-Type": "application/json"},
            timeout=30
        )

        result = response.json()
        if not result.get("success"):
            print(f"{Colors.RED}创建失败: {result.get('error')}{Colors.RESET}")
            return None

        hierarchy_id = result["data"]["id"]
        print(f"{Colors.GREEN}✅ 创建成功! ID: {hierarchy_id}{Colors.RESET}")
        return hierarchy_id

    except Exception as e:
        print(f"{Colors.RED}创建层级团队时出错: {e}{Colors.RESET}")
        return None


def get_first_hierarchy():
    """获取第一个可用的层级团队"""
    try:
        response = requests.post(
            f"{API_BASE}/api/executor/v1/hierarchies/list",
            json={"page": 1, "size": 1},
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        result = response.json()
        if result.get("success") and result.get("data", {}).get("items"):
            return result["data"]["items"][0]["id"]
    except Exception:
        pass
    return None


def start_run(task):
    """启动运行"""
    response = requests.post(
        f"{API_BASE}/api/executor/v1/runs/start",
        json={"hierarchy_id": HIERARCHY_ID, "task": task},
        headers={"Content-Type": "application/json"}
    )

    result = response.json()
    if not result.get("success"):
        print(f"{Colors.RED}启动失败: {result.get('error')}{Colors.RESET}")
        return None

    return result["data"]["id"]


def stream_events(run_id):
    """流式获取并显示事件"""
    display = ChatbotDisplay()
    seen_events = set()
    last_status = "pending"
    poll_count = 0
    max_polls = 300

    while poll_count < max_polls and last_status in ("pending", "running"):
        try:
            response = requests.post(
                f"{API_BASE}/api/executor/v1/runs/get",
                json={"id": run_id},
                headers={"Content-Type": "application/json"}
            )

            result = response.json()
            if not result.get("success"):
                print(f"{Colors.RED}获取状态失败: {result.get('error')}{Colors.RESET}")
                break

            data = result["data"]
            last_status = data["status"]

            # 处理新事件
            events = data.get("events", [])
            for event in events:
                event_id = event.get("id")
                if event_id and event_id not in seen_events:
                    seen_events.add(event_id)
                    display.process_event(event)

            # 检查是否完成
            if last_status in ("completed", "failed"):
                break

            time.sleep(0.5)  # 更快的轮询
            poll_count += 1

        except KeyboardInterrupt:
            print(f"\n\n{Colors.YELLOW}用户中断{Colors.RESET}")
            break
        except Exception as e:
            print(f"{Colors.RED}错误: {e}{Colors.RESET}")
            time.sleep(2)
            poll_count += 1

    # 确保最后换行
    if display.line_started:
        print()

    return last_status


def main():
    global HIERARCHY_ID, API_BASE

    # 解析命令行参数
    task = "请用50字解释什么是人工智能？"
    skip_create = False

    args = sys.argv[1:]
    remaining_args = []

    for arg in args:
        if arg.startswith("--hierarchy="):
            HIERARCHY_ID = arg.split("=", 1)[1]
        elif arg.startswith("--api="):
            API_BASE = arg.split("=", 1)[1]
        elif arg == "--skip-create":
            skip_create = True
        elif not arg.startswith("--"):
            remaining_args.append(arg)

    if remaining_args:
        task = " ".join(remaining_args)

    # 打印标题
    print(f"""
{Colors.CYAN}╔══════════════════════════════════════════════════════════════╗
║          层级多智能体系统 - Chatbot 交互模式                 ║
╚══════════════════════════════════════════════════════════════╝{Colors.RESET}
    """)

    # 1. 先打印层级团队结构
    print_hierarchy_structure()

    # 2. 连接服务
    print(f"{Colors.DIM}连接服务: {API_BASE}{Colors.RESET}")
    try:
        health = requests.get(f"{API_BASE}/health", timeout=5)
        if health.status_code != 200:
            print(f"{Colors.RED}❌ 服务不可用{Colors.RESET}")
            return
        print(f"{Colors.GREEN}✅ 服务连接成功{Colors.RESET}")
    except Exception as e:
        print(f"{Colors.RED}❌ 无法连接: {e}{Colors.RESET}")
        return

    # 3. 获取或创建层级团队
    if not HIERARCHY_ID:
        if not skip_create:
            existing = get_first_hierarchy()
            if existing:
                HIERARCHY_ID = existing
                print(f"{Colors.DIM}使用已有团队: {HIERARCHY_ID}{Colors.RESET}")
            else:
                HIERARCHY_ID = create_hierarchy_team()
        else:
            HIERARCHY_ID = get_first_hierarchy()

    if not HIERARCHY_ID:
        print(f"{Colors.RED}无法获取层级团队{Colors.RESET}")
        return

    # 显示任务信息
    print(f"\n{Colors.YELLOW}📋 任务: {task}{Colors.RESET}")

    # 启动运行
    run_id = start_run(task)
    if not run_id:
        return

    # 流式显示事件
    stream_events(run_id)


if __name__ == "__main__":
    main()
