# 动态层级多智能体系统 (Dynamic Hierarchical Multi-Agent System)

基于 Strands Agent SDK 构建的动态层级团队协作系统，支持配置驱动的多智能体拓扑结构。

## 核心特性

- ✅ **动态层级架构**：Global Supervisor → Team Supervisor → Worker Agent
- ✅ **配置驱动**：通过配置文件动态构建团队拓扑
- ✅ **执行模式控制**：支持顺序执行和并行执行两种模式
- ✅ **执行控制**：代码级别的防重复调用机制
- ✅ **调用追踪**：完整的调用历史和统计信息
- ✅ **流式输出**：实时显示所有层级的工作过程
- ✅ **上下文流动**：自动的层级间上下文传递
- ✅ **跨团队上下文共享**：可配置的团队间上下文传递机制

## 系统架构

```
┌─────────────────────────────────────────────────────────┐
│ Global Supervisor (首席科学家)                           │
│ - 协调所有团队                                           │
│ - 整合研究成果                                           │
└─────────────────────────────────────────────────────────┘
                    ↓ 并发调用
┌──────────────────┬──────────────────┬──────────────────┐
│ Team Supervisor  │ Team Supervisor  │ Team Supervisor  │
│ (理论物理学团队)  │ (实验物理学团队)  │ (专家评审团队)    │
└──────────────────┴──────────────────┴──────────────────┘
        ↓                  ↓                  ↓
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ Worker Agent │  │ Worker Agent │  │ Worker Agent │
│ (量子理论专家)│  │ (实验设计师)  │  │ (方法论专家)  │
└──────────────┘  └──────────────┘  └──────────────┘
```

## 快速开始

### 安装依赖

```bash
pip install strands strands-tools
```

### 配置 AWS 认证

系统支持两种灵活的认证方式，可根据部署场景自动切换：

#### 认证方式 1: API Key 认证（本地开发和调试）

**适用场景**：本地开发、测试、调试

API Key 认证有三种配置方式：

**方式 1-1: 使用 .env 文件（推荐）**

```bash
# 复制示例文件
cp .env.example .env

# 编辑 .env 文件，填入你的配置
# AWS_BEDROCK_API_KEY=your-api-key-here
# AWS_BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-20250514-v1:0
# AWS_REGION=us-east-1
```

**方式 1-2: 使用环境变量**

```bash
export AWS_BEDROCK_API_KEY='your-api-key'
export AWS_BEDROCK_MODEL_ID='us.anthropic.claude-sonnet-4-20250514-v1:0'
export AWS_REGION='us-east-1'
```

**方式 1-3: 在代码中设置**

```python
from config import setup_config

setup_config(
    api_key='your-api-key',
    model_id='us.anthropic.claude-sonnet-4-20250514-v1:0',
    aws_region='us-east-1'
)
```

#### 认证方式 2: IAM Role 认证（AWS 部署）

**适用场景**：AWS Lambda、EC2、ECS 等 AWS 环境部署

IAM Role 认证使用 AWS 服务的执行角色，无需管理 API Key，更加安全。

**方式 2-1: 使用 .env 文件**

```bash
# 编辑 .env 文件
# USE_IAM_ROLE=true
# AWS_REGION=us-east-1
# AWS_BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-20250514-v1:0
```

**方式 2-2: 使用环境变量**

```bash
export USE_IAM_ROLE=true
export AWS_REGION='us-east-1'
export AWS_BEDROCK_MODEL_ID='us.anthropic.claude-sonnet-4-20250514-v1:0'
```

**方式 2-3: 在代码中设置**

```python
from config import setup_config

setup_config(
    use_iam_role=True,
    model_id='us.anthropic.claude-sonnet-4-20250514-v1:0',
    aws_region='us-east-1'
)
```

**IAM Role 权限要求**：

确保您的 Lambda 函数或 EC2 实例的 IAM 角色具有以下权限：

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

#### 认证模式自动检测

系统会根据配置自动选择合适的认证方式：

1. **优先级 1**：如果设置了 `AWS_BEDROCK_API_KEY`，使用 API Key 认证
2. **优先级 2**：如果设置了 `USE_IAM_ROLE=true`，使用 IAM Role 认证
3. **自动检测**：如果在 AWS Lambda 环境中运行且未配置 API Key，自动切换到 IAM Role 认证

**查看当前认证模式**：

```python
from config import get_config

config = get_config()
print(f"认证模式: {config.authentication_mode}")  # 输出: 'api_key' 或 'iam_role'
```

### 运行示例

```bash
# 运行完整测试
python test/test_quantum_research_full.py

# 或使用快速入口
python test/test_quantum_research.py
```

## 核心组件

### 1. ExecutionTracker（执行追踪器）

跟踪所有已执行的 Team 和 Worker，防止重复调用：

```python
tracker = ExecutionTracker()
tracker.mark_team_executed("理论物理学团队", result)
tracker.is_team_executed("理论物理学团队")  # True
```

### 2. WorkerAgentFactory（Worker 工厂）

动态创建 Worker Agent：

```python
worker_config = WorkerConfig(
    name="量子理论专家",
    role="量子力学理论研究",
    system_prompt="你是量子理论专家...",
    tools=[calculator]
)
worker = WorkerAgentFactory.create_worker(worker_config)
```

### 3. TeamSupervisorFactory（Team 工厂）

动态创建 Team Supervisor：

```python
team_config = TeamConfig(
    name="理论物理学团队",
    supervisor_prompt="你是理论物理学团队的负责人...",
    workers=[worker_config1, worker_config2]
)
supervisor = TeamSupervisorFactory.create_supervisor(team_config, tracker)
```

### 4. HierarchyBuilder（层级构建器）

流式 API 构建完整系统：

```python
agent, tracker, team_names = (
    HierarchyBuilder()
    .set_global_prompt("你是首席科学家...")
    .set_parallel_execution(False)  # 设置执行模式：False=顺序，True=并行
    .add_team(
        name="理论物理学团队",
        supervisor_prompt="...",
        workers=[...]
    )
    .add_team(
        name="实验物理学团队",
        supervisor_prompt="...",
        workers=[...]
    )
    .build()
)
```

## 执行模式

系统支持两种团队执行模式：

### 顺序执行（默认）

适合有依赖关系的任务，团队按顺序依次执行：

```python
agent, tracker, teams = (
    HierarchyBuilder(parallel_execution=False)  # 顺序执行
    .set_global_prompt("按顺序完成：1.数据收集 2.数据分析 3.报告撰写")
    .add_team("数据收集团队", ..., workers=[...])
    .add_team("数据分析团队", ..., workers=[...])
    .add_team("报告撰写团队", ..., workers=[...])
    .build()
)
```

### 并行执行

适合独立任务，团队可以同时执行，提高效率：

```python
agent, tracker, teams = (
    HierarchyBuilder(parallel_execution=True)  # 并行执行
    .set_global_prompt("以下团队可以同时工作：前端、后端、测试")
    .add_team("前端开发团队", ..., workers=[...])
    .add_team("后端开发团队", ..., workers=[...])
    .add_team("测试团队", ..., workers=[...])
    .build()
)
```

详细说明请参考：[执行模式文档](docs/EXECUTION_MODES.md)

## 防重复机制

系统提供三层防重复保护：

### 1. Worker 层面
- 基于任务内容的哈希值检测
- 相同 Worker 处理相同任务时返回简短提示，避免上下文重复

### 2. Team 层面
- 基于团队名称的执行状态检测
- 防止同一团队被重复调用

### 3. 执行状态反馈
- 每次决策时显示执行状态（✅已执行 / ⭕未执行）
- Supervisor 可以看到哪些 Agent 已执行

## 跨团队上下文共享

系统支持可配置的跨团队上下文共享机制。

### 默认行为

**默认情况下，team 之间不共享上下文**，每个团队独立工作。

### 启用上下文共享

如果需要团队间共享上下文，需要显式配置：

```python
agent, tracker, team_names = (
    HierarchyBuilder(enable_context_sharing=True)  # 1. 启用全局上下文共享开关
    .set_global_prompt("...")
    .add_team(
        name="理论物理学团队",
        supervisor_prompt="...",
        workers=[...],
        share_context=False  # 此团队不接收其他团队的上下文（默认）
    )
    .add_team(
        name="实验物理学团队",
        supervisor_prompt="...",
        workers=[...],
        share_context=True  # 2. 此团队接收已执行团队的上下文
    )
    .build()
)
```

**两个条件都需要满足**：
1. 全局开关 `enable_context_sharing=True`
2. 团队配置 `share_context=True`

### 工作机制

1. **全局开关**：`enable_context_sharing=True` 启用上下文共享功能
2. **团队级配置**：每个团队通过 `share_context` 参数控制是否接收其他团队的上下文
3. **自动传递**：当 Team 被调用时，如果 `share_context=True`，系统会自动将已执行团队的结果附加到任务描述中
4. **顺序依赖**：后执行的团队可以看到先执行团队的结果

### 使用场景

- **理论 → 实验**：实验团队基于理论团队的分析设计实验
- **研究 → 评审**：评审团队基于所有研究团队的成果进行评估
- **数据 → 分析**：分析团队基于数据采集团队的结果进行分析

## 示例场景：量子力学研究

系统预配置了量子力学研究场景，包含三个专业团队：

1. **理论物理学团队**
   - 量子理论专家
   - 数学物理学家

2. **实验物理学团队**
   - 实验设计师
   - 数据分析师

3. **专家评审团队**
   - 方法论专家
   - 同行评审专家

## 调用统计

系统自动记录和统计所有调用：

```
总调用次数: 3
完成调用数: 3
各团队调用次数:
  📊 理论物理学团队: 1 次
  📊 实验物理学团队: 1 次
  📊 专家评审团队: 1 次
```

## HTTP API 接口

系统提供 HTTP API 接口，支持通过 RESTful API 动态创建和执行层级多智能体系统。

### 快速部署

#### 本地开发部署（API Key 认证）

```bash
# 1. 配置 API Key
export AWS_BEDROCK_API_KEY='your-api-key'
export AWS_REGION='us-east-1'

# 2. 运行本地测试
python test_api.py
```

#### AWS 生产部署（IAM Role 认证）

```bash
# 1. 配置 SAM 部署参数（使用 IAM Role 认证）
sam deploy --guided

# 部署时设置:
# - UseIAMRole: true
# - BedrockApiKey: (留空)
# - AWS Region: us-east-1

# 2. 测试 API
curl -X POST https://your-api-endpoint.com/prod/execute \
  -H "Content-Type: application/json" \
  -d @examples/simple_request.json
```

#### 混合模式部署（支持两种认证）

您也可以配置为支持两种认证方式，系统会自动选择：

```bash
# SAM 部署时设置:
# - UseIAMRole: false
# - BedrockApiKey: your-api-key (可选)

# 如果提供了 API Key，使用 API Key 认证
# 如果没有提供 API Key，系统自动切换到 IAM Role 认证
```

### API 特性

- ✅ **动态拓扑创建**：通过 JSON 配置创建智能体层级结构
- ✅ **流式响应**：返回包含拓扑元数据的事件流（TeamId, SupervisorId, WorkerId）
- ✅ **AWS 原生服务**：基于 Lambda + API Gateway + Bedrock
- ✅ **Bedrock Agent Core 兼容**：完全兼容 AWS Bedrock Agent Core 部署
- ✅ **无服务器架构**：自动扩展，按使用付费
- ✅ **灵活认证机制**：支持 API Key 和 IAM Role 两种认证方式

### API 认证配置示例

**示例 1: 本地开发（API Key）**

```python
# lambda_handler.py 本地测试
import os
os.environ['AWS_BEDROCK_API_KEY'] = 'your-api-key'
os.environ['AWS_REGION'] = 'us-east-1'

from lambda_handler import test_locally
test_locally()
```

**示例 2: AWS Lambda 部署（IAM Role）**

Lambda 函数会自动检测运行环境并使用 IAM Role 认证：

```python
# Lambda 环境变量配置
USE_IAM_ROLE=true
AWS_REGION=us-east-1
AWS_BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-20250514-v1:0
```

### 详细文档

- [认证配置指南](docs/AUTHENTICATION_GUIDE.md) - 详细的认证配置说明
- [API 快速入门](README_API.md)
- [API 参考文档](docs/API_REFERENCE.md)
- [部署指南](docs/API_DEPLOYMENT.md)

## 技术栈

- **Strands Agent SDK**：Agent 框架
- **AWS Bedrock**：LLM 服务（Claude Sonnet 4）
- **AWS Lambda**：无服务器计算
- **API Gateway**：RESTful API 接口
- **Python 3.12+**：开发语言

## 项目文件

### 核心系统
- `hierarchy_system.py` - 核心系统实现
- `config.py` - 配置管理
- `output_formatter.py` - 输出格式化

### HTTP API
- `lambda_handler.py` - Lambda 函数入口
- `hierarchy_executor.py` - 层级执行器
- `api_models.py` - API 数据模型
- `template.yaml` - AWS SAM 部署模板
- `deploy.sh` - 自动化部署脚本
- `test_api.py` - API 测试脚本

### 测试和示例
- `test/` - 测试文件目录
- `examples/` - API 请求示例
- `docs/` - 详细文档

## 许可证

MIT License

## 作者

Built with ❤️ using Strands Agent SDK
