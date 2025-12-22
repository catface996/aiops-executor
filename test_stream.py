#!/usr/bin/env python3
"""
流式事件测试脚本 - 实时输出运行事件

使用方法:
    python test_stream.py [options] [task]

选项:
    --hierarchy=ID    指定层级团队ID (不指定则自动获取第一个)
    --api=URL         指定API地址 (默认: http://localhost:8080)

示例:
    python test_stream.py "请用50字解释量子纠缠"
    python test_stream.py --hierarchy=abc123 "你的问题"
    python test_stream.py --api=http://ec2-ip:18080 "测试问题"

环境变量:
    API_BASE      API服务地址
    HIERARCHY_ID  层级团队ID

层级团队结构示例:
    量子力学研究团队
    ├── 理论研究组 (Team 1)
    │   ├── 量子力学专家 (Worker 1) - 理论物理学家
    │   └── 数学物理专家 (Worker 2) - 数学物理学家
    └── 应用研究组 (Team 2)
        ├── 量子计算专家 (Worker 1) - 量子计算研究员
        └── 量子通信专家 (Worker 2) - 量子通信研究员
"""

import sys
import json
import time
import requests
from datetime import datetime

# 配置 (可通过环境变量覆盖)
import os
API_BASE = os.environ.get("API_BASE", "http://localhost:8080")
HIERARCHY_ID = os.environ.get("HIERARCHY_ID", "")  # 需要通过环境变量或参数指定


def print_colored(text, color="white"):
    """打印彩色文本"""
    colors = {
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "magenta": "\033[95m",
        "cyan": "\033[96m",
        "white": "\033[97m",
        "reset": "\033[0m"
    }
    print(f"{colors.get(color, '')}{text}{colors['reset']}")


def show_hierarchy_structure():
    """显示层级团队结构"""
    try:
        response = requests.post(
            f"{API_BASE}/api/v1/hierarchies/get",
            json={"id": HIERARCHY_ID},
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        result = response.json()
        if not result.get("success"):
            print_colored(f"获取层级结构失败: {result.get('error')}", "red")
            return

        data = result["data"]
        print_colored("\n📊 层级团队结构:", "cyan")
        print_colored(f"{'─'*60}", "cyan")
        print_colored(f"🏢 {data['name']} (Global Supervisor)", "yellow")

        teams = data.get("teams", [])
        for i, team in enumerate(teams):
            is_last_team = (i == len(teams) - 1)
            team_prefix = "└──" if is_last_team else "├──"
            print_colored(f"   {team_prefix} 👔 {team['name']} (Team Supervisor)", "green")

            workers = team.get("workers", [])
            for j, worker in enumerate(workers):
                is_last_worker = (j == len(workers) - 1)
                worker_prefix = "└──" if is_last_worker else "├──"
                branch = "    " if is_last_team else "│   "
                print_colored(f"   {branch}   {worker_prefix} 🔬 {worker['name']} ({worker['role']})", "white")

        print_colored(f"{'─'*60}\n", "cyan")
        print_colored(f"📋 共 {len(teams)} 个团队, {sum(len(t.get('workers', [])) for t in teams)} 个成员\n", "cyan")

    except Exception as e:
        print_colored(f"获取层级结构时出错: {e}", "red")


def print_event(event):
    """格式化打印事件"""
    event_type = event.get("event_type", "unknown")
    timestamp = event.get("timestamp", "")
    data = event.get("data", {})

    # 根据事件类型选择颜色
    color_map = {
        "output": "white",
        "team_thinking": "cyan",
        "team_complete": "green",
        "worker_thinking": "yellow",
        "worker_complete": "green",
        "execution_started": "blue",
        "execution_completed": "green",
        "error": "red"
    }
    color = color_map.get(event_type, "white")

    # 提取内容
    content = data.get("content") or data.get("raw_text") or ""

    if content:
        # 跳过纯分隔线
        if content.strip() in ["=" * 70, "-" * 70, "*" * 70, "#" * 70]:
            return
        print_colored(f"[{event_type}] {content}", color)


def start_run(task):
    """启动运行"""
    print_colored(f"\n{'='*60}", "blue")
    print_colored(f"启动任务: {task}", "blue")
    print_colored(f"{'='*60}\n", "blue")

    response = requests.post(
        f"{API_BASE}/api/v1/runs/start",
        json={"hierarchy_id": HIERARCHY_ID, "task": task},
        headers={"Content-Type": "application/json"}
    )

    result = response.json()
    if not result.get("success"):
        print_colored(f"启动失败: {result.get('error')}", "red")
        return None

    run_id = result["data"]["id"]
    print_colored(f"运行 ID: {run_id}", "cyan")
    print_colored(f"状态: {result['data']['status']}", "cyan")
    print_colored(f"\n{'='*60}\n", "blue")

    return run_id


def stream_events(run_id):
    """流式获取事件（轮询方式）"""
    print_colored("开始监听事件流...\n", "magenta")

    seen_events = set()
    last_status = "pending"
    poll_count = 0
    max_polls = 300  # 最多轮询 300 次（5分钟）

    while poll_count < max_polls and last_status in ("pending", "running"):
        try:
            response = requests.post(
                f"{API_BASE}/api/v1/runs/get",
                json={"id": run_id},
                headers={"Content-Type": "application/json"}
            )

            result = response.json()
            if not result.get("success"):
                print_colored(f"获取状态失败: {result.get('error')}", "red")
                break

            data = result["data"]
            last_status = data["status"]

            # 处理新事件
            events = data.get("events", [])
            for event in events:
                event_id = event.get("id")
                if event_id and event_id not in seen_events:
                    seen_events.add(event_id)
                    print_event(event)

            # 检查是否完成
            if last_status == "completed":
                print_colored(f"\n{'='*60}", "green")
                print_colored("✅ 执行完成!", "green")
                print_colored(f"{'='*60}\n", "green")

                # 打印结果
                if data.get("result"):
                    print_colored("【最终结果】", "green")
                    print(data["result"])
                break

            elif last_status == "failed":
                print_colored(f"\n{'='*60}", "red")
                print_colored("❌ 执行失败!", "red")
                print_colored(f"错误: {data.get('error')}", "red")
                print_colored(f"{'='*60}\n", "red")
                break

            # 等待后继续轮询
            time.sleep(1)
            poll_count += 1

        except KeyboardInterrupt:
            print_colored("\n\n用户中断", "yellow")
            break
        except Exception as e:
            print_colored(f"错误: {e}", "red")
            time.sleep(2)
            poll_count += 1

    if poll_count >= max_polls:
        print_colored("轮询超时", "yellow")

    return last_status


def stream_sse(run_id):
    """使用 SSE 流式获取事件"""
    print_colored("开始 SSE 流式监听...\n", "magenta")

    try:
        response = requests.post(
            f"{API_BASE}/api/v1/runs/stream",
            json={"id": run_id},
            headers={
                "Content-Type": "application/json",
                "Accept": "text/event-stream"
            },
            stream=True
        )

        # 检查是否是 SSE 响应
        content_type = response.headers.get("Content-Type", "")
        if "text/event-stream" not in content_type:
            # 不是 SSE，可能是错误响应
            result = response.json()
            if not result.get("success"):
                print_colored(f"流式获取失败: {result.get('error')}", "red")
                return False
            return True

        # 处理 SSE 流
        for line in response.iter_lines():
            if line:
                line = line.decode("utf-8")
                if line.startswith("data:"):
                    data = line[5:].strip()
                    if data:
                        try:
                            event = json.loads(data)
                            print_event(event)
                        except json.JSONDecodeError:
                            print(data)

        return True

    except KeyboardInterrupt:
        print_colored("\n\n用户中断", "yellow")
        return False
    except Exception as e:
        print_colored(f"SSE 错误: {e}", "red")
        return False


def get_first_hierarchy():
    """获取第一个可用的层级团队"""
    try:
        response = requests.post(
            f"{API_BASE}/api/v1/hierarchies/list",
            json={"page": 1, "size": 1},
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        result = response.json()
        if result.get("success") and result.get("data", {}).get("items"):
            return result["data"]["items"][0]["id"]
    except Exception as e:
        print_colored(f"获取层级团队失败: {e}", "red")
    return None


def main():
    global HIERARCHY_ID

    # 解析命令行参数
    task = "请用50字简单解释什么是量子纠缠？"

    for i, arg in enumerate(sys.argv[1:], 1):
        if arg.startswith("--hierarchy="):
            HIERARCHY_ID = arg.split("=", 1)[1]
        elif arg.startswith("--api="):
            global API_BASE
            API_BASE = arg.split("=", 1)[1]
        elif not arg.startswith("--"):
            task = " ".join(sys.argv[i:])
            break

    # 如果没有指定 HIERARCHY_ID，尝试获取第一个
    if not HIERARCHY_ID:
        print_colored("未指定 HIERARCHY_ID，尝试获取第一个层级团队...", "yellow")
        HIERARCHY_ID = get_first_hierarchy()
        if not HIERARCHY_ID:
            print_colored("错误: 没有可用的层级团队，请先创建一个", "red")
            print_colored("用法: python test_stream.py [--hierarchy=ID] [--api=URL] [task]", "yellow")
            return

    print_colored("""
╔══════════════════════════════════════════════════════════════╗
║       层级多智能体系统 - 流式事件测试                        ║
╚══════════════════════════════════════════════════════════════╝
    """, "cyan")

    # 检查服务是否可用
    try:
        health = requests.get(f"{API_BASE}/health", timeout=5)
        if health.status_code != 200:
            print_colored("服务不可用，请先启动服务", "red")
            return
    except:
        print_colored("无法连接到服务，请确保服务已启动", "red")
        print_colored(f"服务地址: {API_BASE}", "yellow")
        return

    # 显示层级团队结构
    show_hierarchy_structure()

    # 启动运行
    run_id = start_run(task)
    if not run_id:
        return

    # 轮询获取事件（更可靠）
    stream_events(run_id)


if __name__ == "__main__":
    main()
