#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
原始流式事件测试脚本 - 原封不动打印所有收到的 stream event

使用方法:
    python test_stream_raw.py [options] [task]

选项:
    --api=URL         指定API地址 (默认: http://localhost:8082)
    --hierarchy=ID    指定层级团队ID (可选，未指定时自动创建)

示例:
    python test_stream_raw.py "测试任务"
    python test_stream_raw.py --hierarchy=abc123 "测试任务"
    python test_stream_raw.py --api=http://ec2-ip:8080 "测试任务"
"""

import sys
import json
import time
import os
import requests

# 配置
API_BASE = os.environ.get("API_BASE", "http://localhost:8082")
HIERARCHY_ID = os.environ.get("HIERARCHY_ID", "")


def start_run(task):
    """启动运行"""
    print(f"\n{'='*60}")
    print(f"启动任务: {task}")
    print(f"Hierarchy ID: {HIERARCHY_ID}")
    print(f"{'='*60}\n")

    response = requests.post(
        f"{API_BASE}/api/executor/v1/runs/start",
        json={"hierarchy_id": HIERARCHY_ID, "task": task},
        headers={"Content-Type": "application/json"}
    )

    print(f"[START RESPONSE] Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))
    print()

    result = response.json()
    if not result.get("success"):
        return None

    return result["data"]["id"]


def stream_events_raw(run_id):
    """原封不动打印所有事件"""
    print(f"\n{'='*60}")
    print(f"开始监听事件流 (Run ID: {run_id})")
    print(f"{'='*60}\n")

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
                print(f"[ERROR] 获取状态失败: {result.get('error')}")
                break

            data = result["data"]
            last_status = data["status"]

            # 原封不动打印新事件
            events = data.get("events", [])
            for event in events:
                event_id = event.get("id")
                if event_id and event_id not in seen_events:
                    seen_events.add(event_id)
                    print(f"[EVENT #{len(seen_events)}]")
                    print(json.dumps(event, indent=2, ensure_ascii=False))
                    print("-" * 40)

            # 检查是否完成
            if last_status == "completed":
                print(f"\n{'='*60}")
                print("[COMPLETED] 执行完成!")
                print(f"{'='*60}")
                print("\n[FINAL RESULT]")
                print(json.dumps({
                    "status": data.get("status"),
                    "result": data.get("result"),
                    "total_events": len(seen_events)
                }, indent=2, ensure_ascii=False))
                break

            elif last_status == "failed":
                print(f"\n{'='*60}")
                print("[FAILED] 执行失败!")
                print(f"{'='*60}")
                print(json.dumps({
                    "status": data.get("status"),
                    "error": data.get("error")
                }, indent=2, ensure_ascii=False))
                break

            time.sleep(1)
            poll_count += 1

        except KeyboardInterrupt:
            print("\n[INTERRUPTED] 用户中断")
            break
        except Exception as e:
            print(f"[EXCEPTION] {e}")
            time.sleep(2)
            poll_count += 1

    if poll_count >= max_polls:
        print("[TIMEOUT] 轮询超时")

    return last_status


def list_hierarchies():
    """列出所有层级团队"""
    try:
        response = requests.post(
            f"{API_BASE}/api/executor/v1/hierarchies/list",
            json={"page": 1, "size": 10},
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        result = response.json()
        if result.get("success"):
            items = result.get("data", {}).get("items", [])
            if items:
                print("\n可用的层级团队:")
                for item in items:
                    print(f"  - {item['id']}: {item['name']}")
                return items[0]["id"]
            else:
                print("没有找到任何层级团队")
        else:
            print(f"获取层级团队失败: {result.get('error')}")
    except Exception as e:
        print(f"获取层级团队失败: {e}")
    return None


def create_default_hierarchy():
    """创建默认层级团队"""
    print("\n[INFO] 自动创建默认层级团队...")

    config = {
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

    try:
        response = requests.post(
            f"{API_BASE}/api/executor/v1/hierarchies/create",
            json=config,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        result = response.json()
        if result.get("success"):
            hierarchy_id = result["data"]["id"]
            print(f"[SUCCESS] 创建成功! ID: {hierarchy_id}")
            return hierarchy_id
        else:
            print(f"[ERROR] 创建失败: {result.get('error')}")
    except Exception as e:
        print(f"[ERROR] 创建层级团队失败: {e}")
    return None


def main():
    global HIERARCHY_ID, API_BASE

    # 解析命令行参数
    task = "请用50字解释什么是人工智能？"
    args = sys.argv[1:]
    remaining_args = []

    for arg in args:
        if arg.startswith("--hierarchy="):
            HIERARCHY_ID = arg.split("=", 1)[1]
        elif arg.startswith("--api="):
            API_BASE = arg.split("=", 1)[1]
        elif not arg.startswith("--"):
            remaining_args.append(arg)

    if remaining_args:
        task = " ".join(remaining_args)

    print("=" * 60)
    print("  原始流式事件测试脚本")
    print("  (原封不动打印所有 stream event)")
    print("=" * 60)
    print(f"\nAPI: {API_BASE}")

    # 检查服务
    try:
        health = requests.get(f"{API_BASE}/health", timeout=5)
        print(f"[HEALTH] Status: {health.status_code}")
        print(json.dumps(health.json(), indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"[ERROR] 无法连接到服务: {e}")
        return

    # 如果没有指定 hierarchy_id，列出可用的或自动创建
    if not HIERARCHY_ID:
        print("\n[WARNING] 未指定 --hierarchy=ID")
        first_id = list_hierarchies()
        if first_id:
            HIERARCHY_ID = first_id
            print(f"\n自动使用第一个: {HIERARCHY_ID}")
        else:
            # 自动创建默认层级团队
            HIERARCHY_ID = create_default_hierarchy()
            if not HIERARCHY_ID:
                print("\n[ERROR] 无法创建层级团队，退出")
                return

    # 启动运行
    run_id = start_run(task)
    if not run_id:
        print("[ERROR] 启动失败")
        return

    # 流式获取事件
    stream_events_raw(run_id)


if __name__ == "__main__":
    main()
