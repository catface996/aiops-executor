# HTTP API 部署指南

本文档介绍如何部署和使用层级多智能体系统的 HTTP API。

## 架构概述

系统采用 AWS 原生服务实现无服务器架构：

```
┌─────────────────┐
│  API Gateway    │  ← HTTP 请求入口
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Lambda Function│  ← 业务逻辑处理
│  - 解析配置     │
│  - 创建拓扑     │
│  - 执行任务     │
│  - 流式响应     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  AWS Bedrock    │  ← LLM 服务
│  Claude Sonnet 4│
└─────────────────┘
```

### 主要组件

1. **API Gateway**: RESTful API 入口，处理 HTTP 请求
2. **Lambda Function**: 无服务器计算，执行智能体系统
3. **AWS Bedrock**: 托管的 LLM 服务（Claude Sonnet 4）
4. **CloudWatch Logs**: 日志收集和监控

## 前置条件

### 1. 安装 AWS SAM CLI

```bash
# macOS
brew install aws-sam-cli

# Linux
pip install aws-sam-cli

# 验证安装
sam --version
```

### 2. 配置 AWS 凭证

```bash
aws configure
# 输入:
# - AWS Access Key ID
# - AWS Secret Access Key
# - Default region (例如: us-east-1)
# - Default output format (json)
```

### 3. 配置 AWS 认证

系统支持两种认证方式：

#### 方式 A: IAM Role 认证（推荐，用于生产部署）

无需配置 API Key，Lambda 函数会自动使用 IAM 角色访问 Bedrock：

- 更高的安全性
- 自动凭证轮换
- 符合 AWS 最佳实践

#### 方式 B: API Key 认证（用于本地开发和测试）

获取 AWS Bedrock API Key：

1. 登录 AWS 控制台
2. 导航到 AWS Bedrock 服务
3. 创建 API Key
4. 安全存储 API Key

详细的认证配置指南请参考：[认证配置指南](AUTHENTICATION_GUIDE.md)

## 部署步骤

### 方式 1: 使用 SAM CLI 部署（推荐）

#### 1. 构建应用

```bash
cd /projects/sandbox/hierarchical-agents
sam build
```

#### 2. 部署应用

首次部署（引导部署）：

```bash
sam deploy --guided
```

**使用 IAM Role 认证部署（推荐）**：

按照提示输入：
- Stack Name: `hierarchical-agents-api`
- AWS Region: `us-east-1`（或您的首选区域）
- Parameter BedrockApiKey: `(直接按回车，留空)`
- Parameter BedrockModelId: `us.anthropic.claude-sonnet-4-20250514-v1:0`
- Parameter UseIAMRole: `true`
- Parameter DebugMode: `false`
- Confirm changes before deploy: `Y`
- Allow SAM CLI IAM role creation: `Y`
- Save arguments to configuration file: `Y`

**使用 API Key 认证部署（本地测试）**：

按照提示输入：
- Stack Name: `hierarchical-agents-api`
- AWS Region: `us-east-1`
- Parameter BedrockApiKey: `your-bedrock-api-key`
- Parameter BedrockModelId: `us.anthropic.claude-sonnet-4-20250514-v1:0`
- Parameter UseIAMRole: `false`
- Parameter DebugMode: `false`
- Confirm changes before deploy: `Y`
- Allow SAM CLI IAM role creation: `Y`
- Save arguments to configuration file: `Y`

后续部署：

```bash
sam deploy
```

#### 3. 获取 API 端点

部署完成后，SAM 会输出 API 端点 URL：

```
Outputs:
  ApiEndpoint: https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com/prod
  ExecuteEndpoint: https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com/prod/execute
  HealthCheckEndpoint: https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com/prod/health
```

### 方式 2: 使用 CloudFormation 控制台部署

#### 1. 打包应用

```bash
sam package \
  --template-file template.yaml \
  --output-template-file packaged.yaml \
  --s3-bucket your-deployment-bucket
```

#### 2. 在 CloudFormation 控制台部署

1. 登录 AWS 控制台
2. 导航到 CloudFormation
3. 创建新堆栈
4. 上传 `packaged.yaml`
5. 填写参数
6. 创建堆栈

## 本地测试

### 使用 SAM Local

#### 1. 启动本地 API

```bash
sam local start-api
```

API 将在 `http://127.0.0.1:3000` 上运行。

#### 2. 测试请求

```bash
curl -X POST http://127.0.0.1:3000/execute \
  -H "Content-Type: application/json" \
  -d @test_request.json
```

### 使用 Python 脚本测试

```bash
# 设置环境变量
export AWS_BEDROCK_API_KEY='your-api-key'

# 运行测试
python lambda_handler.py
```

## API 使用示例

### 1. 健康检查

```bash
curl https://your-api-endpoint.com/prod/health
```

响应：
```json
{
  "status": "healthy",
  "service": "hierarchical-agents-api",
  "version": "1.0.0"
}
```

### 2. 执行智能体系统

#### 简单示例

```bash
curl -X POST https://your-api-endpoint.com/prod/execute \
  -H "Content-Type: application/json" \
  -d '{
    "global_prompt": "你是研究中心的首席科学家，负责协调研究团队。",
    "teams": [
      {
        "name": "理论研究团队",
        "supervisor_prompt": "你是理论研究团队的负责人。",
        "workers": [
          {
            "name": "理论物理学家",
            "role": "量子理论研究",
            "system_prompt": "你是量子理论专家，擅长理论分析和数学推导。"
          }
        ]
      }
    ],
    "task": "分析量子纠缠的理论基础",
    "execution_mode": "sequential"
  }'
```

#### 复杂示例（多团队，并行执行）

```bash
curl -X POST https://your-api-endpoint.com/prod/execute \
  -H "Content-Type: application/json" \
  -d '{
    "global_prompt": "你是量子研究中心的首席科学家。",
    "teams": [
      {
        "name": "理论物理学团队",
        "supervisor_prompt": "你是理论物理学团队的负责人。",
        "workers": [
          {
            "name": "量子理论专家",
            "role": "量子力学理论研究",
            "system_prompt": "你精通量子力学理论。",
            "tools": ["calculator"]
          },
          {
            "name": "数学物理学家",
            "role": "数学建模",
            "system_prompt": "你擅长数学建模和方程求解。",
            "tools": ["calculator"]
          }
        ]
      },
      {
        "name": "实验物理学团队",
        "supervisor_prompt": "你是实验物理学团队的负责人。",
        "workers": [
          {
            "name": "实验设计师",
            "role": "实验设计",
            "system_prompt": "你擅长设计精密的物理实验。"
          }
        ],
        "share_context": true
      }
    ],
    "task": "研究量子纠缠现象",
    "execution_mode": "parallel",
    "enable_context_sharing": true
  }'
```

### 响应格式

```json
{
  "success": true,
  "topology": {
    "global_supervisor_id": "global_xxx-xxx-xxx",
    "teams": [
      {
        "team_id": "team_xxx-xxx-xxx",
        "team_name": "理论物理学团队",
        "supervisor_id": "supervisor_team_xxx-xxx-xxx",
        "workers": [
          {
            "worker_id": "worker_xxx-xxx-xxx",
            "worker_name": "量子理论专家",
            "role": "量子力学理论研究"
          }
        ]
      }
    ]
  },
  "events": [
    {
      "event_type": "topology_created",
      "timestamp": "2025-12-10T15:30:00.000Z",
      "data": { ... },
      "topology_metadata": null
    },
    {
      "event_type": "team_started",
      "timestamp": "2025-12-10T15:30:01.000Z",
      "data": {
        "team_name": "理论物理学团队",
        "task": "..."
      },
      "topology_metadata": {
        "team_id": "team_xxx-xxx-xxx",
        "supervisor_id": "supervisor_team_xxx-xxx-xxx"
      }
    },
    {
      "event_type": "worker_completed",
      "timestamp": "2025-12-10T15:30:05.000Z",
      "data": {
        "worker_name": "量子理论专家",
        "result_preview": "..."
      },
      "topology_metadata": {
        "team_id": "team_xxx-xxx-xxx",
        "supervisor_id": "supervisor_team_xxx-xxx-xxx",
        "worker_id": "worker_xxx-xxx-xxx"
      }
    },
    {
      "event_type": "execution_completed",
      "timestamp": "2025-12-10T15:30:10.000Z",
      "data": {
        "result_preview": "..."
      }
    }
  ],
  "result": "完整的研究结果...",
  "statistics": {
    "total_calls": 1,
    "team_calls": {
      "理论物理学团队": 1
    },
    "active_teams": [],
    "completed_calls": 1
  }
}
```

## 配置参数说明

### 全局配置

| 参数 | 类型 | 必需 | 默认值 | 说明 |
|------|------|------|--------|------|
| `global_prompt` | string | 是 | - | 全局协调者的系统提示词 |
| `teams` | array | 是 | - | 团队配置列表 |
| `task` | string | 是 | - | 要执行的任务 |
| `execution_mode` | string | 否 | "sequential" | 执行模式：sequential（顺序）或 parallel（并行） |
| `enable_context_sharing` | boolean | 否 | false | 是否启用团队间上下文共享 |

### 团队配置

| 参数 | 类型 | 必需 | 默认值 | 说明 |
|------|------|------|--------|------|
| `name` | string | 是 | - | 团队名称 |
| `supervisor_prompt` | string | 是 | - | 团队主管的系统提示词 |
| `workers` | array | 是 | - | Worker 配置列表 |
| `prevent_duplicate` | boolean | 否 | true | 是否防止重复调用 |
| `share_context` | boolean | 否 | false | 是否接收其他团队的上下文 |

### Worker 配置

| 参数 | 类型 | 必需 | 默认值 | 说明 |
|------|------|------|--------|------|
| `name` | string | 是 | - | Worker 名称 |
| `role` | string | 是 | - | Worker 角色 |
| `system_prompt` | string | 是 | - | Worker 的系统提示词 |
| `tools` | array | 否 | [] | 工具列表（"calculator", "http_request"） |
| `temperature` | number | 否 | 0.7 | 生成温度 |
| `max_tokens` | integer | 否 | 2048 | 最大 token 数 |

## 监控和日志

### CloudWatch Logs

查看 Lambda 函数日志：

```bash
# 查看最近的日志
sam logs -n HierarchicalAgentsFunction --tail

# 查看特定时间范围的日志
sam logs -n HierarchicalAgentsFunction --start-time '10min ago' --end-time 'now'
```

### CloudWatch Metrics

在 AWS 控制台查看：
- Lambda 调用次数
- 错误率
- 持续时间
- 并发执行数

## 性能优化

### 1. 调整 Lambda 配置

根据实际使用情况调整：

```yaml
# template.yaml
Globals:
  Function:
    Timeout: 900      # 增加超时时间（秒）
    MemorySize: 3008  # 增加内存（MB）
```

### 2. 预留并发

为高流量场景配置预留并发：

```bash
aws lambda put-function-concurrency \
  --function-name hierarchical-agents-api \
  --reserved-concurrent-executions 10
```

### 3. Lambda 层

将依赖打包为 Lambda 层以减少部署包大小：

```bash
# 创建层
mkdir -p layer/python
pip install -r requirements.txt -t layer/python
cd layer
zip -r ../layer.zip .
```

## 安全最佳实践

### 1. API Key 认证

在 API Gateway 中启用 API Key：

```yaml
# template.yaml
HierarchicalAgentsApi:
  Type: AWS::Serverless::Api
  Properties:
    Auth:
      ApiKeyRequired: true
```

### 2. IAM 授权

使用 IAM 角色和策略控制访问：

```yaml
Policies:
  - Statement:
    - Effect: Allow
      Action:
        - bedrock:InvokeModel
      Resource: '*'
```

### 3. VPC 配置

将 Lambda 函数部署在 VPC 中以增强安全性。

### 4. 加密

- 使用 AWS Secrets Manager 存储敏感信息
- 启用 API Gateway 的 SSL/TLS

## 故障排查

### 常见问题

#### 1. Lambda 超时

**症状**: 请求返回 504 Gateway Timeout

**解决方案**:
- 增加 Lambda 超时时间
- 优化任务复杂度
- 考虑使用异步处理

#### 2. 内存不足

**症状**: Lambda 报 "Memory exceeded" 错误

**解决方案**:
- 增加 Lambda 内存配置
- 优化代码内存使用
- 减少并发执行的团队数量

#### 3. Bedrock API 限流

**症状**: 请求返回 429 Too Many Requests

**解决方案**:
- 实现重试机制
- 增加请求配额
- 使用顺序执行模式减少并发

## 成本估算

### Lambda 成本

- 请求费用: $0.20 / 100万次请求
- 计算费用: $0.0000166667 / GB-秒

示例：每月 10,000 次请求，每次 60 秒，2048 MB 内存
- 请求费用: 10,000 × $0.20 / 1,000,000 = $0.002
- 计算费用: 10,000 × 60 × 2 × $0.0000166667 = $20
- **总计**: ~$20/月

### API Gateway 成本

- REST API: $3.50 / 100万次请求

### AWS Bedrock 成本

根据实际使用的 token 数量计费，请参考 AWS Bedrock 定价。

## 部署清单

- [ ] 安装 AWS SAM CLI
- [ ] 配置 AWS 凭证
- [ ] 获取 Bedrock API Key
- [ ] 运行 `sam build`
- [ ] 运行 `sam deploy --guided`
- [ ] 测试 health check 端点
- [ ] 测试 execute 端点
- [ ] 配置 CloudWatch 告警
- [ ] 设置 API 认证（可选）
- [ ] 配置自动扩展（可选）

## 支持

如有问题，请：
1. 查看 CloudWatch Logs
2. 检查配置参数
3. 参考示例请求
4. 联系技术支持

## 更新和维护

### 更新代码

```bash
# 修改代码后
sam build
sam deploy
```

### 回滚

```bash
# 回滚到上一个版本
aws cloudformation rollback-stack --stack-name hierarchical-agents-api
```

### 删除堆栈

```bash
# 删除所有资源
sam delete
```

## 兼容性说明

### AWS Bedrock Agent Core

该 API 设计与 AWS Bedrock Agent Core 完全兼容：

1. **标准 API 接口**: 使用 REST API 接口
2. **JSON 格式**: 请求和响应使用标准 JSON
3. **事件流式输出**: 支持拓扑信息和执行事件的流式返回
4. **AWS 原生服务**: 完全基于 AWS 服务构建

可以将此 API 集成到 Bedrock Agent Core 作为：
- Action Group
- Knowledge Base
- Custom Lambda

## 参考资源

- [AWS SAM 文档](https://docs.aws.amazon.com/serverless-application-model/)
- [AWS Lambda 最佳实践](https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html)
- [AWS API Gateway 文档](https://docs.aws.amazon.com/apigateway/)
- [AWS Bedrock 文档](https://docs.aws.amazon.com/bedrock/)
