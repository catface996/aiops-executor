# 部署快速参考

快速查找不同部署场景的命令和配置。

## 📋 部署方式选择

| 场景 | 推荐方式 | 优势 |
|------|---------|------|
| 开发测试 | 本地 Python | 快速迭代 |
| 开发测试 | Docker Compose | 环境一致性 |
| 生产环境（低负载） | AWS Lambda | 无需管理服务器 |
| 生产环境（中高负载） | EC2 + Docker | 性能和控制 |
| 生产环境（企业级） | EC2 + Docker + Nginx | 完整的生产解决方案 |

## 🚀 快速启动命令

### 本地开发（Python）

```bash
# 1. 安装依赖
pip install -r requirements.txt flask flask-cors gunicorn

# 2. 配置环境
export AWS_BEDROCK_API_KEY='your-api-key'
export AWS_REGION='us-east-1'

# 3. 运行
python http_server.py
```

### Docker Compose（推荐用于本地测试）

```bash
# 1. 配置
cp .env.example .env
# 编辑 .env 文件

# 2. 启动
docker-compose up -d

# 3. 测试
curl http://localhost:8080/health
```

### Docker（单容器）

```bash
# 1. 构建
docker build -t hierarchical-agents:latest .

# 2. 运行
docker run -d \
  --name hierarchical-agents-api \
  -p 8080:8080 \
  -e AWS_BEDROCK_API_KEY='your-api-key' \
  -e AWS_REGION='us-east-1' \
  hierarchical-agents:latest
```

### EC2 快速部署

```bash
# 1. 安装 Docker
sudo yum install -y docker git
sudo systemctl start docker
sudo usermod -a -G docker $USER

# 2. 部署
git clone https://github.com/catface996/hierarchical-agents.git
cd hierarchical-agents
docker build -t hierarchical-agents:latest .
docker run -d \
  --name hierarchical-agents-api \
  -p 8080:8080 \
  --restart unless-stopped \
  -e USE_IAM_ROLE=true \
  -e AWS_REGION=us-east-1 \
  hierarchical-agents:latest
```

### AWS Lambda

```bash
# 1. 部署
sam deploy --guided

# 2. 配置
# - Stack Name: hierarchical-agents
# - UseIAMRole: true
# - AWS Region: us-east-1
```

## 🔑 认证配置

### API Key 认证（本地开发）

```bash
# 环境变量
export AWS_BEDROCK_API_KEY='your-api-key'
export AWS_REGION='us-east-1'
export AWS_BEDROCK_MODEL_ID='us.anthropic.claude-sonnet-4-20250514-v1:0'

# .env 文件
AWS_BEDROCK_API_KEY=your-api-key
AWS_REGION=us-east-1
AWS_BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-20250514-v1:0
```

### IAM Role 认证（AWS 部署）

```bash
# 环境变量
export USE_IAM_ROLE=true
export AWS_REGION='us-east-1'
export AWS_BEDROCK_MODEL_ID='us.anthropic.claude-sonnet-4-20250514-v1:0'

# .env 文件
USE_IAM_ROLE=true
AWS_REGION=us-east-1
AWS_BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-20250514-v1:0
```

## 🧪 测试命令

### 健康检查

```bash
curl http://localhost:8080/health
```

### API 信息

```bash
curl http://localhost:8080/
```

### 执行测试

```bash
curl -X POST http://localhost:8080/execute \
  -H "Content-Type: application/json" \
  -d @examples/simple_request.json
```

### 运行测试脚本

```bash
python test_http_server.py
```

## 📊 监控命令

### Docker 日志

```bash
# 查看日志
docker logs -f hierarchical-agents-api

# 最近 100 行
docker logs --tail 100 hierarchical-agents-api

# 带时间戳
docker logs -f --timestamps hierarchical-agents-api
```

### Docker Compose 日志

```bash
docker-compose logs -f
docker-compose logs --tail 100
```

### Docker 状态

```bash
# 容器状态
docker ps
docker stats hierarchical-agents-api

# 资源使用
docker container inspect hierarchical-agents-api
```

## 🔧 管理命令

### Docker 容器管理

```bash
# 启动/停止/重启
docker start hierarchical-agents-api
docker stop hierarchical-agents-api
docker restart hierarchical-agents-api

# 删除
docker stop hierarchical-agents-api
docker rm hierarchical-agents-api

# 进入容器
docker exec -it hierarchical-agents-api /bin/bash
```

### Docker Compose 管理

```bash
# 启动/停止
docker-compose up -d
docker-compose stop
docker-compose start

# 重启
docker-compose restart

# 完全清理
docker-compose down
docker-compose down -v  # 同时删除 volumes
```

### 更新部署

```bash
# Docker
git pull
docker build -t hierarchical-agents:latest .
docker stop hierarchical-agents-api
docker rm hierarchical-agents-api
docker run -d --name hierarchical-agents-api -p 8080:8080 ... hierarchical-agents:latest

# Docker Compose
git pull
docker-compose down
docker-compose build
docker-compose up -d
```

## 🛠️ 故障排除

### 检查服务状态

```bash
# 端口监听
sudo netstat -tlnp | grep 8080
sudo lsof -i :8080

# 进程状态
ps aux | grep http_server
ps aux | grep gunicorn
```

### 检查 AWS 配置

```bash
# 验证 IAM 角色
aws sts get-caller-identity

# 测试 Bedrock 访问
aws bedrock list-foundation-models --region us-east-1

# 检查环境变量
env | grep AWS
```

### 容器调试

```bash
# 查看容器日志
docker logs hierarchical-agents-api 2>&1 | tail -50

# 进入容器检查
docker exec -it hierarchical-agents-api /bin/bash
ps aux
env | grep AWS
curl http://localhost:8080/health
```

### 网络问题

```bash
# 检查防火墙
sudo iptables -L -n
sudo firewall-cmd --list-all

# 检查安全组（EC2）
# 在 AWS Console 检查

# 测试连接
telnet localhost 8080
curl -v http://localhost:8080/health
```

## 📝 配置文件模板

### .env 模板（API Key）

```bash
AWS_BEDROCK_API_KEY=your-api-key-here
AWS_REGION=us-east-1
AWS_BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-20250514-v1:0
PORT=8080
DEBUG=false
```

### .env 模板（IAM Role）

```bash
USE_IAM_ROLE=true
AWS_REGION=us-east-1
AWS_BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-20250514-v1:0
PORT=8080
DEBUG=false
```

## 🔗 相关文档

- [完整 README](README.md) - 系统概述和特性
- [EC2 部署指南](docs/EC2_DEPLOYMENT_GUIDE.md) - 详细的 EC2 部署步骤
- [认证配置指南](docs/AUTHENTICATION_GUIDE.md) - 认证配置详解
- [API 参考文档](docs/API_REFERENCE.md) - API 接口文档

## 💡 常用场景

### 场景 1：本地快速测试

```bash
pip install flask flask-cors
export AWS_BEDROCK_API_KEY='your-api-key'
export AWS_REGION='us-east-1'
python http_server.py
```

### 场景 2：Docker 本地测试

```bash
cp .env.example .env
# 编辑 .env
docker-compose up -d
docker-compose logs -f
```

### 场景 3：EC2 生产部署

```bash
# 在 EC2 上
sudo yum install -y docker git
sudo systemctl start docker
git clone https://github.com/catface996/hierarchical-agents.git
cd hierarchical-agents
docker build -t hierarchical-agents:latest .
docker run -d --name hierarchical-agents-api -p 8080:8080 --restart unless-stopped \
  -e USE_IAM_ROLE=true -e AWS_REGION=us-east-1 hierarchical-agents:latest
```

### 场景 4：Lambda 部署

```bash
sam build
sam deploy --guided
# 测试
curl -X POST https://your-api-endpoint/prod/execute \
  -H "Content-Type: application/json" \
  -d @examples/simple_request.json
```

## ⚡ 性能优化

### Gunicorn 配置

```bash
# 开发环境
gunicorn --bind 0.0.0.0:8080 --workers 2 --threads 2 --timeout 300 http_server:app

# 生产环境
gunicorn --bind 0.0.0.0:8080 --workers 4 --threads 4 --timeout 600 \
  --worker-class gthread --max-requests 1000 http_server:app
```

### Docker 资源限制

```bash
docker run -d \
  --name hierarchical-agents-api \
  -p 8080:8080 \
  --memory="4g" \
  --cpus="2" \
  hierarchical-agents:latest
```

## 🔒 安全检查清单

- [ ] 使用 IAM Role 而非 API Key（生产环境）
- [ ] 限制安全组入站规则
- [ ] 启用 HTTPS（通过 Nginx + Let's Encrypt）
- [ ] 定期更新 Docker 镜像和依赖
- [ ] 启用日志记录和监控
- [ ] 使用非 root 用户运行容器
- [ ] 配置防火墙规则
- [ ] 定期备份配置

## 📞 获取帮助

如果遇到问题：

1. 检查日志：`docker logs hierarchical-agents-api`
2. 查看 [故障排除](#故障排除) 部分
3. 阅读 [EC2 部署指南](docs/EC2_DEPLOYMENT_GUIDE.md)
4. 提交 Issue 到 GitHub

---

**快速链接**：
- [GitHub 仓库](https://github.com/catface996/hierarchical-agents)
- [API 文档](docs/API_REFERENCE.md)
- [EC2 部署指南](docs/EC2_DEPLOYMENT_GUIDE.md)
