# AWS 认证配置指南

本文档详细介绍如何配置层级多智能体系统的 AWS 认证机制。

## 概述

系统支持两种灵活的认证方式，可根据部署场景自动切换：

1. **API Key 认证** - 适用于本地开发和调试
2. **IAM Role 认证** - 适用于 AWS 环境部署

系统会根据配置自动检测并选择合适的认证方式，无需手动切换。

## 认证方式对比

| 特性 | API Key 认证 | IAM Role 认证 |
|------|-------------|--------------|
| **适用场景** | 本地开发、测试、调试 | AWS Lambda、EC2、ECS 部署 |
| **安全性** | 需要安全存储 API Key | 使用 AWS IAM 角色，更安全 |
| **配置复杂度** | 简单，只需配置 API Key | 需要配置 IAM 角色和权限 |
| **成本** | 按 API Key 使用计费 | 按 AWS 服务使用计费 |
| **推荐用途** | 快速原型开发、本地调试 | 生产环境部署 |

## 认证方式 1: API Key 认证

### 适用场景

- 本地开发环境
- 快速原型验证
- 调试和测试
- 非 AWS 环境部署

### 配置方法

#### 方法 1-1: 使用 .env 文件（推荐）

1. 复制示例配置文件：
```bash
cp .env.example .env
```

2. 编辑 `.env` 文件，取消注释并填入您的配置：
```bash
# API Key 认证配置
AWS_BEDROCK_API_KEY=your-api-key-here
AWS_REGION=us-east-1
AWS_BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-20250514-v1:0
```

3. 运行您的应用：
```bash
python test/test_quantum_research_full.py
```

#### 方法 1-2: 使用环境变量

```bash
# 设置环境变量
export AWS_BEDROCK_API_KEY='your-api-key-here'
export AWS_REGION='us-east-1'
export AWS_BEDROCK_MODEL_ID='us.anthropic.claude-sonnet-4-20250514-v1:0'

# 运行应用
python test/test_quantum_research_full.py
```

#### 方法 1-3: 在代码中配置

```python
from config import setup_config

# 配置 API Key 认证
config = setup_config(
    api_key='your-api-key-here',
    model_id='us.anthropic.claude-sonnet-4-20250514-v1:0',
    aws_region='us-east-1'
)

# 验证配置
print(f"认证模式: {config.authentication_mode}")  # 输出: api_key
print(f"API Key 已配置: {config.is_configured()}")  # 输出: True
```

### 获取 API Key

1. 登录 AWS 控制台
2. 导航到 AWS Bedrock 服务
3. 在左侧菜单中选择 "API Keys"
4. 点击 "Create API Key"
5. 复制生成的 API Key（注意：API Key 只显示一次）
6. 安全存储您的 API Key

### 安全最佳实践

- ✅ 使用 `.env` 文件存储 API Key，并将 `.env` 添加到 `.gitignore`
- ✅ 定期轮换 API Key
- ✅ 为不同环境使用不同的 API Key
- ✅ 限制 API Key 的权限范围
- ❌ 不要将 API Key 提交到版本控制系统
- ❌ 不要在代码中硬编码 API Key

## 认证方式 2: IAM Role 认证

### 适用场景

- AWS Lambda 函数
- Amazon EC2 实例
- Amazon ECS 容器
- 其他 AWS 服务
- 生产环境部署

### 为什么选择 IAM Role 认证？

1. **更高的安全性**：不需要管理和存储 API Key
2. **自动轮换**：AWS 自动管理临时凭证
3. **精细的权限控制**：通过 IAM 策略精确控制访问权限
4. **审计和合规**：完整的 CloudTrail 审计日志
5. **最佳实践**：AWS 推荐的认证方式

### 配置方法

#### 方法 2-1: 使用 .env 文件

1. 编辑 `.env` 文件：
```bash
# IAM Role 认证配置
USE_IAM_ROLE=true
AWS_REGION=us-east-1
AWS_BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-20250514-v1:0

# 注意：不需要设置 AWS_BEDROCK_API_KEY
```

2. 运行应用（确保在具有适当 IAM 角色的 AWS 环境中）：
```bash
python test/test_quantum_research_full.py
```

#### 方法 2-2: 使用环境变量

```bash
# 设置环境变量
export USE_IAM_ROLE=true
export AWS_REGION='us-east-1'
export AWS_BEDROCK_MODEL_ID='us.anthropic.claude-sonnet-4-20250514-v1:0'

# 运行应用
python test/test_quantum_research_full.py
```

#### 方法 2-3: 在代码中配置

```python
from config import setup_config

# 配置 IAM Role 认证
config = setup_config(
    use_iam_role=True,
    model_id='us.anthropic.claude-sonnet-4-20250514-v1:0',
    aws_region='us-east-1'
)

# 验证配置
print(f"认证模式: {config.authentication_mode}")  # 输出: iam_role
print(f"使用 IAM Role: {config.use_iam_role}")  # 输出: True
```

### IAM 角色配置

#### 步骤 1: 创建 IAM 策略

创建一个 IAM 策略，授予访问 AWS Bedrock 的权限：

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": "*"
    }
  ]
}
```

您可以通过 AWS CLI 创建策略：

```bash
aws iam create-policy \
  --policy-name HierarchicalAgentsBedrockAccess \
  --policy-document file://bedrock-policy.json
```

#### 步骤 2: 为 Lambda 函数配置 IAM 角色

如果使用 AWS SAM 部署，`template.yaml` 已经包含了必要的 IAM 权限配置：

```yaml
Policies:
  - AWSLambdaBasicExecutionRole
  - Statement:
    - Effect: Allow
      Action:
        - bedrock:InvokeModel
        - bedrock:InvokeModelWithResponseStream
      Resource: "*"
```

#### 步骤 3: 为 EC2 实例配置 IAM 角色

1. 在 AWS 控制台中创建 IAM 角色
2. 选择 "AWS Service" → "EC2"
3. 附加上面创建的策略
4. 为 EC2 实例关联该 IAM 角色

### AWS Lambda 部署

使用 SAM 部署时配置 IAM Role 认证：

```bash
# 部署应用
sam deploy --guided

# 部署参数设置：
# Stack Name: hierarchical-agents-api
# AWS Region: us-east-1
# Parameter BedrockApiKey: (留空或按回车)
# Parameter BedrockModelId: us.anthropic.claude-sonnet-4-20250514-v1:0
# Parameter UseIAMRole: true
# Parameter DebugMode: false
# Confirm changes before deploy: Y
# Allow SAM CLI IAM role creation: Y
```

部署后，Lambda 函数会自动使用 IAM Role 认证访问 Bedrock。

## 认证模式自动检测

系统会根据以下优先级自动选择认证方式：

### 优先级规则

1. **最高优先级**：如果设置了 `AWS_BEDROCK_API_KEY` 且 `USE_IAM_ROLE` 不为 true，使用 **API Key 认证**
2. **次高优先级**：如果设置了 `USE_IAM_ROLE=true`，使用 **IAM Role 认证**
3. **自动检测**：如果在 AWS Lambda 环境中运行且未配置 API Key，自动切换到 **IAM Role 认证**

### Lambda 环境自动检测

系统会检测以下环境变量来判断是否在 Lambda 环境中：
- `AWS_EXECUTION_ENV`
- `AWS_LAMBDA_FUNCTION_NAME`

如果检测到 Lambda 环境且未配置 API Key，系统会自动启用 IAM Role 认证。

### 查看当前认证模式

您可以在代码中查看当前使用的认证模式：

```python
from config import get_config, setup_config

# 设置配置
config = setup_config()

# 查看认证模式
print(f"认证模式: {config.authentication_mode}")
print(f"API Key 已配置: {config.aws_bedrock_api_key is not None}")
print(f"使用 IAM Role: {config.use_iam_role}")
print(f"AWS Region: {config.aws_region}")
```

## 开发工作流示例

### 场景 1: 本地开发

```bash
# 1. 创建 .env 文件（API Key 认证）
cat > .env << EOF
AWS_BEDROCK_API_KEY=your-api-key-here
AWS_REGION=us-east-1
AWS_BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-20250514-v1:0
EOF

# 2. 运行测试
python test/test_quantum_research_full.py

# 输出:
# ✓ 认证模式: API Key 认证（本地开发模式）
```

### 场景 2: 部署到 AWS Lambda

```bash
# 1. 修改 .env 文件（IAM Role 认证）
cat > .env << EOF
USE_IAM_ROLE=true
AWS_REGION=us-east-1
AWS_BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-20250514-v1:0
EOF

# 2. 部署到 AWS
sam build
sam deploy --guided

# 3. Lambda 函数会自动使用 IAM Role 认证
# 输出（在 CloudWatch Logs 中）:
# ✓ 认证模式: IAM Role 认证（AWS 部署模式）
#   AWS Region: us-east-1
```

### 场景 3: 混合开发环境

在团队协作中，不同开发者可能使用不同的认证方式：

```bash
# 开发者 A（本地开发，使用 API Key）
export AWS_BEDROCK_API_KEY='dev-api-key'
python test/test_quantum_research_full.py

# 开发者 B（在 EC2 上开发，使用 IAM Role）
export USE_IAM_ROLE=true
python test/test_quantum_research_full.py

# CI/CD 流水线（在 Lambda 上运行，自动使用 IAM Role）
sam build && sam deploy
```

## 故障排查

### 问题 1: "AWS Bedrock API Key 未配置"错误

**原因**：系统检测到 API Key 认证模式但未找到 API Key。

**解决方案**：
```bash
# 方案 1: 设置 API Key
export AWS_BEDROCK_API_KEY='your-api-key'

# 方案 2: 切换到 IAM Role 认证
export USE_IAM_ROLE=true
export AWS_REGION='us-east-1'
```

### 问题 2: "AWS Region 未配置"错误

**原因**：使用 IAM Role 认证时未设置 AWS Region。

**解决方案**：
```bash
export AWS_REGION='us-east-1'
```

### 问题 3: IAM Role 权限不足

**症状**：出现 "AccessDeniedException" 或类似的权限错误。

**解决方案**：
1. 检查 IAM 角色是否附加了 Bedrock 访问权限
2. 确保策略包含 `bedrock:InvokeModel` 和 `bedrock:InvokeModelWithResponseStream` 权限
3. 查看 CloudWatch Logs 获取详细错误信息

```bash
# 检查 Lambda 函数的 IAM 角色
aws lambda get-function --function-name hierarchical-agents-api \
  --query 'Configuration.Role'

# 检查角色的策略
aws iam list-attached-role-policies --role-name <role-name>
```

### 问题 4: 本地环境无法使用 IAM Role

**原因**：IAM Role 认证需要在 AWS 环境中运行。

**解决方案**：
- 本地开发时使用 API Key 认证
- 或者配置 AWS CLI 凭证（`aws configure`）以模拟 IAM Role

## 最佳实践

### ✅ 推荐做法

1. **分离环境配置**
   - 本地开发：使用 API Key 认证
   - AWS 部署：使用 IAM Role 认证

2. **使用 .env 文件**
   - 创建 `.env.local`、`.env.dev`、`.env.prod` 等不同环境的配置文件
   - 将 `.env*` 添加到 `.gitignore`

3. **最小权限原则**
   - 只授予必要的 Bedrock 权限
   - 考虑限制特定模型的访问

4. **监控和审计**
   - 启用 CloudTrail 记录 Bedrock API 调用
   - 使用 CloudWatch 监控使用情况

### ❌ 避免的做法

1. 不要在代码中硬编码 API Key
2. 不要将 API Key 提交到版本控制系统
3. 不要在生产环境使用 API Key 认证（推荐使用 IAM Role）
4. 不要授予过于宽泛的 IAM 权限

## 配置示例总结

### API Key 认证示例 (.env)
```bash
# 本地开发配置
AWS_BEDROCK_API_KEY=your-api-key-here
AWS_REGION=us-east-1
AWS_BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-20250514-v1:0
```

### IAM Role 认证示例 (.env)
```bash
# AWS 部署配置
USE_IAM_ROLE=true
AWS_REGION=us-east-1
AWS_BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-20250514-v1:0
```

### 代码配置示例

```python
from config import setup_config

# API Key 认证
config_local = setup_config(
    api_key='your-api-key',
    aws_region='us-east-1'
)

# IAM Role 认证
config_aws = setup_config(
    use_iam_role=True,
    aws_region='us-east-1'
)

# 自动检测
config_auto = setup_config()  # 根据环境自动选择
```

## 参考资源

- [AWS Bedrock 文档](https://docs.aws.amazon.com/bedrock/)
- [AWS IAM 最佳实践](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html)
- [AWS Lambda 执行角色](https://docs.aws.amazon.com/lambda/latest/dg/lambda-intro-execution-role.html)
- [AWS SAM 部署指南](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/)

---

**更新日期**: 2024
**版本**: 1.0.0
