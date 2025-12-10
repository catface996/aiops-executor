"""
配置管理模块 - 统一管理系统配置和敏感信息

支持多种配置方式:
1. 环境变量
2. .env 文件
3. 配置文件 (config.json)

支持灵活的 AWS 认证机制:
1. API Key 认证（优先）- 适用于本地开发和调试
2. IAM Role 认证（回退）- 适用于 AWS 部署场景
"""

import os
from typing import Optional
from pathlib import Path


class Config:
    """配置管理类 - 单例模式"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self._aws_bedrock_api_key: Optional[str] = None
            self._model_id: str = "us.anthropic.claude-sonnet-4-20250514-v1:0"
            self._aws_region: str = "us-east-1"
            self._use_iam_role: bool = False  # 是否使用 IAM Role 认证
            self._initialized = True
    
    def load_from_env(self) -> 'Config':
        """从环境变量加载配置"""
        self._aws_bedrock_api_key = os.environ.get('AWS_BEDROCK_API_KEY')
        model_id = os.environ.get('AWS_BEDROCK_MODEL_ID')
        if model_id:
            self._model_id = model_id
        
        # 加载 AWS Region 配置
        aws_region = os.environ.get('AWS_REGION') or os.environ.get('AWS_DEFAULT_REGION')
        if aws_region:
            self._aws_region = aws_region
        
        # 检查是否应使用 IAM Role 认证
        use_iam = os.environ.get('USE_IAM_ROLE', '').lower() in ('true', '1', 'yes')
        if use_iam:
            self._use_iam_role = True
        
        return self
    
    def load_from_dotenv(self, dotenv_path: str = '.env') -> 'Config':
        """从 .env 文件加载配置"""
        env_file = Path(dotenv_path)
        if not env_file.exists():
            return self
        
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    
                    if key == 'AWS_BEDROCK_API_KEY':
                        self._aws_bedrock_api_key = value
                    elif key == 'AWS_BEDROCK_MODEL_ID':
                        self._model_id = value
                    elif key in ('AWS_REGION', 'AWS_DEFAULT_REGION'):
                        self._aws_region = value
                    elif key == 'USE_IAM_ROLE':
                        self._use_iam_role = value.lower() in ('true', '1', 'yes')
        
        return self
    
    def set_api_key(self, api_key: str) -> 'Config':
        """手动设置 API Key"""
        self._aws_bedrock_api_key = api_key
        return self
    
    def set_model_id(self, model_id: str) -> 'Config':
        """手动设置模型 ID"""
        self._model_id = model_id
        return self
    
    def set_aws_region(self, region: str) -> 'Config':
        """手动设置 AWS Region"""
        self._aws_region = region
        return self
    
    def set_use_iam_role(self, use_iam: bool) -> 'Config':
        """手动设置是否使用 IAM Role 认证"""
        self._use_iam_role = use_iam
        return self
    
    @property
    def aws_bedrock_api_key(self) -> Optional[str]:
        """获取 AWS Bedrock API Key"""
        return self._aws_bedrock_api_key
    
    @property
    def model_id(self) -> str:
        """获取模型 ID"""
        return self._model_id
    
    @property
    def aws_region(self) -> str:
        """获取 AWS Region"""
        return self._aws_region
    
    @property
    def use_iam_role(self) -> bool:
        """是否使用 IAM Role 认证"""
        return self._use_iam_role
    
    @property
    def authentication_mode(self) -> str:
        """
        获取当前认证模式
        
        Returns:
            'api_key': 使用 API Key 认证
            'iam_role': 使用 IAM Role 认证
        """
        if self._aws_bedrock_api_key and not self._use_iam_role:
            return 'api_key'
        else:
            return 'iam_role'
    
    def setup_environment(self) -> None:
        """
        将配置设置到环境变量中（供 Strands SDK 使用）
        
        根据认证模式设置不同的环境变量：
        - API Key 模式：设置 AWS_BEDROCK_API_KEY
        - IAM Role 模式：确保 AWS_REGION 已设置，不设置 API Key
        """
        # 设置模型 ID
        if self._model_id:
            os.environ['AWS_BEDROCK_MODEL_ID'] = self._model_id
        
        # 设置 AWS Region
        if self._aws_region:
            os.environ['AWS_REGION'] = self._aws_region
            if 'AWS_DEFAULT_REGION' not in os.environ:
                os.environ['AWS_DEFAULT_REGION'] = self._aws_region
        
        # 根据认证模式设置相应的环境变量
        if self.authentication_mode == 'api_key':
            # API Key 模式
            if self._aws_bedrock_api_key:
                os.environ['AWS_BEDROCK_API_KEY'] = self._aws_bedrock_api_key
                print(f"✓ 认证模式: API Key 认证（本地开发模式）")
        else:
            # IAM Role 模式
            # 清除 API Key（如果存在），以确保使用 IAM Role
            if 'AWS_BEDROCK_API_KEY' in os.environ:
                del os.environ['AWS_BEDROCK_API_KEY']
            print(f"✓ 认证模式: IAM Role 认证（AWS 部署模式）")
            print(f"  AWS Region: {self._aws_region}")
    
    def is_configured(self) -> bool:
        """
        检查是否已配置认证信息
        
        Returns:
            True 如果配置了 API Key 或启用了 IAM Role 模式
        """
        return self._aws_bedrock_api_key is not None or self._use_iam_role
    
    def validate(self) -> None:
        """
        验证配置是否完整
        
        根据认证模式验证不同的配置项：
        - API Key 模式：需要 API Key
        - IAM Role 模式：需要 AWS Region
        """
        if self.authentication_mode == 'api_key':
            if not self._aws_bedrock_api_key:
                raise ValueError(
                    "AWS Bedrock API Key 未配置。请通过以下方式之一配置:\n"
                    "1. 环境变量: export AWS_BEDROCK_API_KEY='your-key'\n"
                    "2. .env 文件: 创建 .env 文件并添加 AWS_BEDROCK_API_KEY=your-key\n"
                    "3. 代码设置: config.set_api_key('your-key')\n\n"
                    "或者使用 IAM Role 认证:\n"
                    "1. 环境变量: export USE_IAM_ROLE=true\n"
                    "2. .env 文件: 创建 .env 文件并添加 USE_IAM_ROLE=true"
                )
        else:
            # IAM Role 模式，确保 AWS Region 已配置
            if not self._aws_region:
                raise ValueError(
                    "AWS Region 未配置。IAM Role 认证模式需要配置 AWS Region。\n"
                    "请通过以下方式之一配置:\n"
                    "1. 环境变量: export AWS_REGION='us-east-1'\n"
                    "2. .env 文件: 创建 .env 文件并添加 AWS_REGION=us-east-1\n"
                    "3. 代码设置: config.set_aws_region('us-east-1')"
                )


# ============================================================================
# 便捷函数
# ============================================================================

def get_config() -> Config:
    """获取配置实例（单例）"""
    return Config()


def setup_config(
    api_key: Optional[str] = None,
    model_id: Optional[str] = None,
    aws_region: Optional[str] = None,
    use_iam_role: Optional[bool] = None,
    use_dotenv: bool = True,
    use_env: bool = True
) -> Config:
    """
    设置配置并返回配置实例
    
    Args:
        api_key: 直接提供的 API Key（优先级最高）
        model_id: 模型 ID
        aws_region: AWS Region
        use_iam_role: 是否使用 IAM Role 认证
        use_dotenv: 是否从 .env 文件加载
        use_env: 是否从环境变量加载
    
    Returns:
        Config 实例
    
    优先级顺序:
    1. 直接提供的参数（api_key, model_id, aws_region, use_iam_role）
    2. 环境变量
    3. .env 文件
    
    认证模式自动检测逻辑:
    - 如果提供了 api_key 或环境变量中有 AWS_BEDROCK_API_KEY，使用 API Key 认证
    - 如果设置了 use_iam_role=True 或环境变量 USE_IAM_ROLE=true，使用 IAM Role 认证
    - 如果都没有设置，默认尝试从环境变量/配置文件加载
    """
    config = get_config()
    
    # 从 .env 文件加载（优先级最低）
    if use_dotenv:
        config.load_from_dotenv()
    
    # 从环境变量加载（优先级中等）
    if use_env:
        config.load_from_env()
    
    # 直接设置（优先级最高）
    if api_key:
        config.set_api_key(api_key)
    if model_id:
        config.set_model_id(model_id)
    if aws_region:
        config.set_aws_region(aws_region)
    if use_iam_role is not None:
        config.set_use_iam_role(use_iam_role)
    
    # 自动检测认证模式：如果在 AWS Lambda 环境且没有 API Key，自动切换到 IAM Role 模式
    if not config._aws_bedrock_api_key and not config._use_iam_role:
        # 检测是否在 AWS Lambda 环境
        if os.environ.get('AWS_EXECUTION_ENV') or os.environ.get('AWS_LAMBDA_FUNCTION_NAME'):
            config.set_use_iam_role(True)
    
    # 设置到环境变量
    config.setup_environment()
    
    return config


def ensure_configured() -> Config:
    """
    确保配置已设置，如果未设置则尝试自动加载
    
    Returns:
        Config 实例
    
    Raises:
        ValueError: 如果配置未设置且无法自动加载
    
    自动检测逻辑：
    1. 尝试从 .env 文件和环境变量加载配置
    2. 如果在 AWS Lambda 环境且没有 API Key，自动切换到 IAM Role 模式
    3. 验证配置完整性
    """
    config = get_config()
    
    if not config.is_configured():
        # 尝试自动加载
        config.load_from_dotenv().load_from_env()
        
        # 如果仍未配置且在 AWS Lambda 环境，自动启用 IAM Role 模式
        if not config.is_configured():
            if os.environ.get('AWS_EXECUTION_ENV') or os.environ.get('AWS_LAMBDA_FUNCTION_NAME'):
                config.set_use_iam_role(True)
        
        config.setup_environment()
    
    # 验证配置
    config.validate()
    
    return config


# ============================================================================
# 示例用法
# ============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("配置管理模块示例")
    print("=" * 80)
    
    # 方式 1: 自动加载（从环境变量或 .env 文件）
    print("\n【方式 1: 自动加载】")
    config = setup_config()
    print(f"认证模式: {config.authentication_mode}")
    print(f"API Key 已配置: {config.aws_bedrock_api_key is not None}")
    print(f"使用 IAM Role: {config.use_iam_role}")
    print(f"模型 ID: {config.model_id}")
    print(f"AWS Region: {config.aws_region}")
    
    # 方式 2: 手动设置 API Key 认证（本地开发）
    print("\n【方式 2: API Key 认证（本地开发）】")
    config = setup_config(
        api_key="your-api-key-here",
        model_id="us.anthropic.claude-sonnet-4-20250514-v1:0",
        aws_region="us-east-1"
    )
    print(f"认证模式: {config.authentication_mode}")
    print(f"API Key 已配置: {config.is_configured()}")
    print(f"模型 ID: {config.model_id}")
    print(f"AWS Region: {config.aws_region}")
    
    # 方式 3: 手动设置 IAM Role 认证（AWS 部署）
    print("\n【方式 3: IAM Role 认证（AWS 部署）】")
    config = setup_config(
        use_iam_role=True,
        model_id="us.anthropic.claude-sonnet-4-20250514-v1:0",
        aws_region="us-east-1"
    )
    print(f"认证模式: {config.authentication_mode}")
    print(f"使用 IAM Role: {config.use_iam_role}")
    print(f"模型 ID: {config.model_id}")
    print(f"AWS Region: {config.aws_region}")
    
    # 方式 4: 确保已配置（推荐在应用启动时使用）
    print("\n【方式 4: 确保已配置】")
    try:
        config = ensure_configured()
        print("✓ 配置验证通过")
        print(f"  认证模式: {config.authentication_mode}")
    except ValueError as e:
        print(f"✗ 配置验证失败: {e}")
    
    print("\n" + "=" * 80)
