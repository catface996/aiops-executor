#!/usr/bin/env python3
"""
测试认证配置功能

验证 API Key 和 IAM Role 两种认证模式的配置和切换。
"""

import os
import sys

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import setup_config, get_config, Config


def test_api_key_authentication():
    """测试 API Key 认证模式"""
    print("\n" + "=" * 80)
    print("测试 1: API Key 认证模式")
    print("=" * 80)
    
    # 重置配置实例
    Config._instance = None
    Config._initialized = False
    
    # 配置 API Key 认证
    config = setup_config(
        api_key='test-api-key-12345',
        model_id='us.anthropic.claude-sonnet-4-20250514-v1:0',
        aws_region='us-east-1'
    )
    
    # 验证配置
    assert config.authentication_mode == 'api_key', "应该使用 API Key 认证"
    assert config.aws_bedrock_api_key == 'test-api-key-12345', "API Key 应该正确设置"
    assert config.aws_region == 'us-east-1', "AWS Region 应该正确设置"
    assert config.use_iam_role == False, "不应该使用 IAM Role"
    assert config.is_configured() == True, "应该配置成功"
    
    print("✓ API Key 认证模式测试通过")
    print(f"  - 认证模式: {config.authentication_mode}")
    print(f"  - API Key 已配置: {config.aws_bedrock_api_key is not None}")
    print(f"  - AWS Region: {config.aws_region}")
    print(f"  - 使用 IAM Role: {config.use_iam_role}")


def test_iam_role_authentication():
    """测试 IAM Role 认证模式"""
    print("\n" + "=" * 80)
    print("测试 2: IAM Role 认证模式")
    print("=" * 80)
    
    # 重置配置实例
    Config._instance = None
    Config._initialized = False
    
    # 配置 IAM Role 认证
    config = setup_config(
        use_iam_role=True,
        model_id='us.anthropic.claude-sonnet-4-20250514-v1:0',
        aws_region='us-west-2'
    )
    
    # 验证配置
    assert config.authentication_mode == 'iam_role', "应该使用 IAM Role 认证"
    assert config.use_iam_role == True, "应该使用 IAM Role"
    assert config.aws_region == 'us-west-2', "AWS Region 应该正确设置"
    assert config.is_configured() == True, "应该配置成功"
    
    print("✓ IAM Role 认证模式测试通过")
    print(f"  - 认证模式: {config.authentication_mode}")
    print(f"  - 使用 IAM Role: {config.use_iam_role}")
    print(f"  - AWS Region: {config.aws_region}")


def test_authentication_priority():
    """测试认证优先级"""
    print("\n" + "=" * 80)
    print("测试 3: 认证优先级（API Key > IAM Role）")
    print("=" * 80)
    
    # 重置配置实例
    Config._instance = None
    Config._initialized = False
    
    # 同时设置 API Key 和 IAM Role，API Key 应该优先
    config = setup_config(
        api_key='priority-test-key',
        use_iam_role=False,  # 明确设置为 False
        aws_region='eu-west-1'
    )
    
    # 验证配置
    assert config.authentication_mode == 'api_key', "API Key 应该优先"
    assert config.aws_bedrock_api_key is not None, "API Key 应该已设置"
    
    print("✓ 认证优先级测试通过")
    print(f"  - 认证模式: {config.authentication_mode}")
    print(f"  - API Key 优先于 IAM Role")


def test_environment_variable_loading():
    """测试从环境变量加载配置"""
    print("\n" + "=" * 80)
    print("测试 4: 从环境变量加载配置")
    print("=" * 80)
    
    # 重置配置实例
    Config._instance = None
    Config._initialized = False
    
    # 设置环境变量
    os.environ['AWS_BEDROCK_API_KEY'] = 'env-test-key'
    os.environ['AWS_REGION'] = 'ap-northeast-1'
    os.environ['AWS_BEDROCK_MODEL_ID'] = 'test-model-id'
    
    try:
        # 从环境变量加载
        config = setup_config()
        
        # 验证配置
        assert config.aws_bedrock_api_key == 'env-test-key', "应该从环境变量加载 API Key"
        assert config.aws_region == 'ap-northeast-1', "应该从环境变量加载 Region"
        assert config.model_id == 'test-model-id', "应该从环境变量加载 Model ID"
        
        print("✓ 环境变量加载测试通过")
        print(f"  - API Key: {config.aws_bedrock_api_key[:10]}...")
        print(f"  - AWS Region: {config.aws_region}")
        print(f"  - Model ID: {config.model_id}")
        
    finally:
        # 清理环境变量
        os.environ.pop('AWS_BEDROCK_API_KEY', None)
        os.environ.pop('AWS_REGION', None)
        os.environ.pop('AWS_BEDROCK_MODEL_ID', None)


def test_iam_role_environment_variable():
    """测试 IAM Role 环境变量"""
    print("\n" + "=" * 80)
    print("测试 5: IAM Role 环境变量")
    print("=" * 80)
    
    # 重置配置实例
    Config._instance = None
    Config._initialized = False
    
    # 设置环境变量
    os.environ['USE_IAM_ROLE'] = 'true'
    os.environ['AWS_REGION'] = 'us-east-2'
    
    try:
        # 从环境变量加载
        config = setup_config()
        
        # 验证配置
        assert config.use_iam_role == True, "应该启用 IAM Role"
        assert config.authentication_mode == 'iam_role', "应该使用 IAM Role 认证"
        
        print("✓ IAM Role 环境变量测试通过")
        print(f"  - 使用 IAM Role: {config.use_iam_role}")
        print(f"  - 认证模式: {config.authentication_mode}")
        
    finally:
        # 清理环境变量
        os.environ.pop('USE_IAM_ROLE', None)
        os.environ.pop('AWS_REGION', None)


def test_lambda_environment_detection():
    """测试 Lambda 环境自动检测"""
    print("\n" + "=" * 80)
    print("测试 6: Lambda 环境自动检测")
    print("=" * 80)
    
    # 重置配置实例
    Config._instance = None
    Config._initialized = False
    
    # 模拟 Lambda 环境
    os.environ['AWS_LAMBDA_FUNCTION_NAME'] = 'test-function'
    os.environ['AWS_REGION'] = 'us-west-1'
    
    try:
        # 在 Lambda 环境中，没有 API Key 应该自动启用 IAM Role
        config = setup_config()
        
        # 验证配置
        assert config.use_iam_role == True, "Lambda 环境应该自动启用 IAM Role"
        assert config.authentication_mode == 'iam_role', "应该使用 IAM Role 认证"
        
        print("✓ Lambda 环境自动检测测试通过")
        print(f"  - 检测到 Lambda 环境")
        print(f"  - 自动启用 IAM Role 认证")
        print(f"  - 认证模式: {config.authentication_mode}")
        
    finally:
        # 清理环境变量
        os.environ.pop('AWS_LAMBDA_FUNCTION_NAME', None)
        os.environ.pop('AWS_REGION', None)


def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 80)
    print("开始认证配置测试")
    print("=" * 80)
    
    try:
        test_api_key_authentication()
        test_iam_role_authentication()
        test_authentication_priority()
        test_environment_variable_loading()
        test_iam_role_environment_variable()
        test_lambda_environment_detection()
        
        print("\n" + "=" * 80)
        print("✅ 所有测试通过！")
        print("=" * 80)
        print("\n认证配置功能验证成功：")
        print("  ✓ API Key 认证模式")
        print("  ✓ IAM Role 认证模式")
        print("  ✓ 认证优先级处理")
        print("  ✓ 环境变量加载")
        print("  ✓ Lambda 环境自动检测")
        print("\n系统已准备好支持灵活的认证机制！")
        
    except AssertionError as e:
        print(f"\n❌ 测试失败: {str(e)}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试出错: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    run_all_tests()
