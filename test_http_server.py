#!/usr/bin/env python3
"""
HTTP Server Test Script
测试 HTTP 服务器的基本功能
"""

import json
import requests
import sys
import time

# 服务器配置
BASE_URL = "http://localhost:8080"

def test_health_check():
    """测试健康检查端点"""
    print("\n" + "=" * 80)
    print("测试 1: 健康检查端点")
    print("=" * 80)
    
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        print(f"状态码: {response.status_code}")
        print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        
        if response.status_code == 200:
            print("✓ 健康检查测试通过")
            return True
        else:
            print("✗ 健康检查测试失败")
            return False
    except Exception as e:
        print(f"✗ 健康检查测试失败: {e}")
        return False


def test_root_endpoint():
    """测试根路径端点"""
    print("\n" + "=" * 80)
    print("测试 2: 根路径端点")
    print("=" * 80)
    
    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        print(f"状态码: {response.status_code}")
        print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        
        if response.status_code == 200:
            print("✓ 根路径测试通过")
            return True
        else:
            print("✗ 根路径测试失败")
            return False
    except Exception as e:
        print(f"✗ 根路径测试失败: {e}")
        return False


def test_execute_endpoint():
    """测试执行端点（简单验证）"""
    print("\n" + "=" * 80)
    print("测试 3: 执行端点（基本验证）")
    print("=" * 80)
    
    # 简单的测试请求
    test_request = {
        "global_prompt": "你是全局协调者",
        "teams": [
            {
                "name": "测试团队",
                "supervisor_prompt": "你是团队负责人",
                "workers": [
                    {
                        "name": "测试工作者",
                        "role": "测试",
                        "system_prompt": "你是测试专家"
                    }
                ]
            }
        ],
        "task": "执行一个简单的测试任务",
        "execution_mode": "sequential"
    }
    
    try:
        print("发送测试请求...")
        response = requests.post(
            f"{BASE_URL}/execute",
            json=test_request,
            headers={"Content-Type": "application/json"},
            timeout=120
        )
        
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"响应成功: {result.get('success', False)}")
            if result.get('topology'):
                print(f"拓扑创建成功")
            print("✓ 执行端点测试通过")
            return True
        else:
            print(f"响应: {response.text}")
            print("⚠ 执行端点返回错误（可能是配置问题）")
            return False
    except requests.exceptions.Timeout:
        print("⚠ 请求超时（这可能是正常的，如果实际执行时间较长）")
        return False
    except Exception as e:
        print(f"✗ 执行端点测试失败: {e}")
        return False


def test_validation():
    """测试请求验证"""
    print("\n" + "=" * 80)
    print("测试 4: 请求验证")
    print("=" * 80)
    
    # 无效的请求（缺少必需字段）
    invalid_request = {
        "global_prompt": "测试"
        # 缺少 teams 和 task
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/execute",
            json=invalid_request,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        print(f"状态码: {response.status_code}")
        print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        
        if response.status_code == 400:
            print("✓ 请求验证测试通过（正确拒绝了无效请求）")
            return True
        else:
            print("✗ 请求验证测试失败（应该返回 400 错误）")
            return False
    except Exception as e:
        print(f"✗ 请求验证测试失败: {e}")
        return False


def main():
    """主测试函数"""
    print("=" * 80)
    print("HTTP Server 测试套件")
    print("=" * 80)
    print(f"目标服务器: {BASE_URL}")
    print("\n确保服务器正在运行:")
    print("  python http_server.py")
    print("  或")
    print("  docker-compose up -d")
    
    # 等待用户确认
    input("\n按 Enter 继续测试...")
    
    # 运行所有测试
    results = []
    
    # 测试 1: 健康检查
    results.append(("健康检查", test_health_check()))
    
    # 测试 2: 根路径
    results.append(("根路径", test_root_endpoint()))
    
    # 测试 3: 请求验证
    results.append(("请求验证", test_validation()))
    
    # 测试 4: 执行端点（可选，需要有效的 AWS 配置）
    print("\n" + "=" * 80)
    print("注意: 下一个测试需要有效的 AWS Bedrock 配置")
    choice = input("是否运行执行端点测试? (y/N): ").strip().lower()
    if choice == 'y':
        results.append(("执行端点", test_execute_endpoint()))
    else:
        print("跳过执行端点测试")
    
    # 打印总结
    print("\n" + "=" * 80)
    print("测试总结")
    print("=" * 80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{name}: {status}")
    
    print(f"\n总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("\n✓ 所有测试通过！服务器运行正常。")
        return 0
    else:
        print(f"\n⚠ {total - passed} 个测试失败")
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
        sys.exit(1)
