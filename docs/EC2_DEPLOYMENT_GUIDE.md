# EC2 部署指南

本指南详细介绍如何在 AWS EC2 实例上部署层级多智能体系统的 HTTP 服务器。

## 目录

- [快速开始](#快速开始)
- [EC2 实例准备](#ec2-实例准备)
- [部署方式](#部署方式)
- [配置说明](#配置说明)
- [监控和日志](#监控和日志)
- [生产环境优化](#生产环境优化)
- [故障排除](#故障排除)

## 快速开始

### 前置条件

- AWS 账户
- EC2 实例（推荐：t3.medium 或更高配置）
- IAM 角色配置了 Bedrock 访问权限
- 安全组开放端口 8080（或自定义端口）

### 5 分钟快速部署

```bash
# 1. SSH 连接到 EC2 实例
ssh -i your-key.pem ec2-user@your-ec2-ip

# 2. 安装 Docker
sudo yum update -y
sudo yum install -y docker git
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -a -G docker ec2-user

# 3. 重新登录以应用 docker 组权限
exit
ssh -i your-key.pem ec2-user@your-ec2-ip

# 4. 克隆代码
git clone https://github.com/catface996/hierarchical-agents.git
cd hierarchical-agents

# 5. 配置环境（使用 IAM Role）
cat > .env << EOF
USE_IAM_ROLE=true
AWS_REGION=us-east-1
AWS_BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-20250514-v1:0
PORT=8080
DEBUG=false
EOF

# 6. 构建并启动
docker build -t hierarchical-agents:latest .
docker run -d \
  --name hierarchical-agents-api \
  -p 8080:8080 \
  --restart unless-stopped \
  -e USE_IAM_ROLE=true \
  -e AWS_REGION=us-east-1 \
  -e AWS_BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-20250514-v1:0 \
  hierarchical-agents:latest

# 7. 验证部署
curl http://localhost:8080/health
```

## EC2 实例准备

### 1. 创建 EC2 实例

推荐配置：

| 配置项 | 推荐值 | 说明 |
|--------|--------|------|
| **AMI** | Amazon Linux 2023 或 Ubuntu 22.04 | 最新的长期支持版本 |
| **实例类型** | t3.medium | 2 vCPU, 4 GB RAM（最低配置） |
| **实例类型** | t3.large | 2 vCPU, 8 GB RAM（推荐用于生产） |
| **实例类型** | c5.xlarge | 4 vCPU, 8 GB RAM（高负载场景） |
| **存储** | 20 GB gp3 | 根据需求调整 |
| **安全组** | 开放 22（SSH）和 8080（API） | 根据需求调整 |

### 2. 配置 IAM 角色

创建 IAM 角色并附加到 EC2 实例：

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

**步骤**：
1. 在 IAM 控制台创建角色
2. 选择 "AWS service" → "EC2"
3. 创建并附加上述策略
4. 将角色附加到 EC2 实例

### 3. 配置安全组

| 类型 | 协议 | 端口范围 | 来源 | 说明 |
|------|------|---------|------|------|
| SSH | TCP | 22 | 你的 IP | 管理访问 |
| 自定义 TCP | TCP | 8080 | 0.0.0.0/0 | API 访问（根据需求限制） |
| HTTPS | TCP | 443 | 0.0.0.0/0 | （如果使用 Nginx + SSL） |

## 部署方式

### 方式 1: 使用 Docker（推荐）

#### 优点
- 环境隔离
- 易于更新和回滚
- 一致的运行环境

#### 部署步骤

```bash
# 1. 安装 Docker
# Amazon Linux 2023
sudo yum update -y
sudo yum install -y docker
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -a -G docker ec2-user

# Ubuntu
sudo apt-get update
sudo apt-get install -y docker.io
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -a -G docker ubuntu

# 2. 克隆代码
git clone https://github.com/catface996/hierarchical-agents.git
cd hierarchical-agents

# 3. 构建镜像
docker build -t hierarchical-agents:latest .

# 4. 运行容器
docker run -d \
  --name hierarchical-agents-api \
  -p 8080:8080 \
  --restart unless-stopped \
  -e USE_IAM_ROLE=true \
  -e AWS_REGION=us-east-1 \
  -e AWS_BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-20250514-v1:0 \
  hierarchical-agents:latest

# 5. 查看日志
docker logs -f hierarchical-agents-api

# 6. 停止/启动/重启
docker stop hierarchical-agents-api
docker start hierarchical-agents-api
docker restart hierarchical-agents-api
```

### 方式 2: 使用 Docker Compose

#### 优点
- 配置管理更简单
- 支持多容器编排
- 易于版本控制

#### 部署步骤

```bash
# 1. 安装 Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 2. 克隆代码
git clone https://github.com/catface996/hierarchical-agents.git
cd hierarchical-agents

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env 文件

# 4. 启动服务
docker-compose up -d

# 5. 查看日志
docker-compose logs -f

# 6. 管理服务
docker-compose stop
docker-compose start
docker-compose restart
docker-compose down  # 停止并删除容器
```

### 方式 3: 直接运行 Python 脚本

#### 优点
- 直接控制 Python 环境
- 便于调试
- 无需 Docker

#### 部署步骤

```bash
# 1. 安装 Python 3.12
# Amazon Linux 2023
sudo yum install -y python3.12 python3.12-pip

# Ubuntu
sudo apt-get update
sudo apt-get install -y python3.12 python3.12-venv python3-pip

# 2. 克隆代码
git clone https://github.com/catface996/hierarchical-agents.git
cd hierarchical-agents

# 3. 创建虚拟环境
python3.12 -m venv venv
source venv/bin/activate

# 4. 安装依赖
pip install -r requirements.txt
pip install flask flask-cors gunicorn

# 5. 配置环境变量
export USE_IAM_ROLE=true
export AWS_REGION=us-east-1
export AWS_BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-20250514-v1:0
export PORT=8080

# 6. 使用 gunicorn 运行（生产环境）
gunicorn --bind 0.0.0.0:8080 \
         --workers 4 \
         --threads 2 \
         --timeout 300 \
         --access-logfile - \
         --error-logfile - \
         http_server:app

# 或使用 Flask 开发服务器（仅开发环境）
python http_server.py
```

### 方式 4: 使用 Systemd 服务（推荐用于生产）

#### 创建 systemd 服务文件

```bash
sudo cat > /etc/systemd/system/hierarchical-agents.service << 'EOF'
[Unit]
Description=Hierarchical Multi-Agent System HTTP Server
After=network.target

[Service]
Type=simple
User=ec2-user
WorkingDirectory=/home/ec2-user/hierarchical-agents
Environment="USE_IAM_ROLE=true"
Environment="AWS_REGION=us-east-1"
Environment="AWS_BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-20250514-v1:0"
Environment="PORT=8080"
ExecStart=/home/ec2-user/hierarchical-agents/venv/bin/gunicorn --bind 0.0.0.0:8080 --workers 4 --threads 2 --timeout 300 http_server:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 启用并启动服务
sudo systemctl daemon-reload
sudo systemctl enable hierarchical-agents
sudo systemctl start hierarchical-agents

# 查看状态
sudo systemctl status hierarchical-agents

# 查看日志
sudo journalctl -u hierarchical-agents -f
```

## 配置说明

### 环境变量详解

#### 必需的环境变量

```bash
# AWS 区域
AWS_REGION=us-east-1

# Bedrock 模型 ID
AWS_BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-20250514-v1:0

# 使用 IAM Role 认证（EC2 部署推荐）
USE_IAM_ROLE=true
```

#### 可选的环境变量

```bash
# HTTP 服务器端口（默认：8080）
PORT=8080

# HTTP 服务器监听地址（默认：0.0.0.0）
HOST=0.0.0.0

# 调试模式（默认：false）
DEBUG=false

# API Key 认证（可选，如果不使用 IAM Role）
AWS_BEDROCK_API_KEY=your-api-key
```

### 性能调优

#### Gunicorn 配置

```bash
# 基本配置
gunicorn --bind 0.0.0.0:8080 \
         --workers 4 \              # Worker 进程数 = (2 × CPU核心数) + 1
         --threads 2 \              # 每个 Worker 的线程数
         --timeout 300 \            # 请求超时时间（秒）
         --worker-class sync \      # Worker 类型
         --access-logfile - \       # 访问日志
         --error-logfile - \        # 错误日志
         http_server:app

# 高性能配置（适用于高负载）
gunicorn --bind 0.0.0.0:8080 \
         --workers 8 \
         --threads 4 \
         --timeout 600 \
         --worker-class gthread \
         --worker-connections 1000 \
         --max-requests 1000 \
         --max-requests-jitter 50 \
         --access-logfile - \
         --error-logfile - \
         http_server:app
```

#### Docker 资源限制

```bash
docker run -d \
  --name hierarchical-agents-api \
  -p 8080:8080 \
  --restart unless-stopped \
  --memory="4g" \                # 内存限制
  --cpus="2" \                   # CPU 限制
  -e USE_IAM_ROLE=true \
  -e AWS_REGION=us-east-1 \
  hierarchical-agents:latest
```

## 监控和日志

### 查看日志

```bash
# Docker 日志
docker logs -f hierarchical-agents-api
docker logs --tail 100 hierarchical-agents-api

# Docker Compose 日志
docker-compose logs -f
docker-compose logs --tail 100

# Systemd 日志
sudo journalctl -u hierarchical-agents -f
sudo journalctl -u hierarchical-agents --since "1 hour ago"
```

### 健康检查

```bash
# 本地健康检查
curl http://localhost:8080/health

# 远程健康检查
curl http://your-ec2-ip:8080/health

# 监控脚本
cat > health_check.sh << 'EOF'
#!/bin/bash
while true; do
  if curl -f http://localhost:8080/health > /dev/null 2>&1; then
    echo "$(date): Service is healthy"
  else
    echo "$(date): Service is DOWN!"
    # 可以添加重启逻辑或告警
  fi
  sleep 60
done
EOF

chmod +x health_check.sh
./health_check.sh &
```

### 监控指标

建议监控以下指标：

- CPU 使用率
- 内存使用率
- 磁盘使用率
- 网络流量
- HTTP 响应时间
- 错误率

可以使用 CloudWatch、Prometheus、Grafana 等工具。

## 生产环境优化

### 1. 使用 Nginx 反向代理

```bash
# 安装 Nginx
sudo yum install -y nginx  # Amazon Linux
# 或
sudo apt-get install -y nginx  # Ubuntu

# 配置 Nginx
sudo cat > /etc/nginx/conf.d/hierarchical-agents.conf << 'EOF'
upstream hierarchical_agents {
    server 127.0.0.1:8080;
}

server {
    listen 80;
    server_name your-domain.com;

    # 访问日志
    access_log /var/log/nginx/hierarchical-agents-access.log;
    error_log /var/log/nginx/hierarchical-agents-error.log;

    # 客户端最大请求体大小
    client_max_body_size 10M;

    location / {
        proxy_pass http://hierarchical_agents;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # 超时设置
        proxy_connect_timeout 75s;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
        
        # 缓冲设置
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
    }

    # 健康检查端点不记录日志
    location /health {
        proxy_pass http://hierarchical_agents;
        access_log off;
    }
}
EOF

# 测试配置
sudo nginx -t

# 启动 Nginx
sudo systemctl start nginx
sudo systemctl enable nginx
```

### 2. 配置 HTTPS（使用 Let's Encrypt）

```bash
# 安装 Certbot
sudo yum install -y certbot python3-certbot-nginx  # Amazon Linux
# 或
sudo apt-get install -y certbot python3-certbot-nginx  # Ubuntu

# 获取 SSL 证书
sudo certbot --nginx -d your-domain.com

# 自动续期
sudo systemctl enable certbot-renew.timer
```

### 3. 配置防火墙

```bash
# 使用 firewalld (Amazon Linux)
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload

# 使用 ufw (Ubuntu)
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### 4. 设置日志轮转

```bash
sudo cat > /etc/logrotate.d/hierarchical-agents << 'EOF'
/var/log/nginx/hierarchical-agents*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 nginx nginx
    sharedscripts
    postrotate
        /bin/kill -USR1 `cat /run/nginx.pid 2>/dev/null` 2>/dev/null || true
    endscript
}
EOF
```

## 故障排除

### 问题 1: 容器无法启动

```bash
# 查看容器日志
docker logs hierarchical-agents-api

# 常见原因：
# - 端口已被占用：lsof -i :8080
# - 环境变量配置错误
# - IAM 角色权限不足
```

### 问题 2: 无法访问 API

```bash
# 检查容器是否运行
docker ps

# 检查端口监听
sudo netstat -tlnp | grep 8080

# 检查防火墙
sudo iptables -L -n

# 检查安全组配置（在 AWS 控制台）
```

### 问题 3: AWS Bedrock 调用失败

```bash
# 检查 IAM 角色是否正确附加
aws sts get-caller-identity

# 检查 IAM 角色权限
aws iam get-role --role-name YourRoleName

# 测试 Bedrock 访问
aws bedrock list-foundation-models --region us-east-1
```

### 问题 4: 内存不足

```bash
# 监控内存使用
free -h
docker stats

# 解决方案：
# 1. 升级 EC2 实例类型
# 2. 减少 Gunicorn workers 数量
# 3. 限制 Docker 容器内存使用
```

### 问题 5: 响应超时

```bash
# 增加超时时间
# 在 Gunicorn 配置中：
--timeout 600

# 在 Nginx 配置中：
proxy_read_timeout 600s;

# 在 Docker 中：
--health-timeout=30s
```

## 更新部署

### Docker 部署更新

```bash
# 1. 拉取最新代码
cd hierarchical-agents
git pull

# 2. 重新构建镜像
docker build -t hierarchical-agents:latest .

# 3. 停止并删除旧容器
docker stop hierarchical-agents-api
docker rm hierarchical-agents-api

# 4. 启动新容器
docker run -d \
  --name hierarchical-agents-api \
  -p 8080:8080 \
  --restart unless-stopped \
  -e USE_IAM_ROLE=true \
  -e AWS_REGION=us-east-1 \
  hierarchical-agents:latest
```

### 零停机更新（使用 Nginx）

```bash
# 1. 启动新版本容器（使用不同端口）
docker run -d \
  --name hierarchical-agents-api-new \
  -p 8081:8080 \
  --restart unless-stopped \
  -e USE_IAM_ROLE=true \
  -e AWS_REGION=us-east-1 \
  hierarchical-agents:latest

# 2. 测试新版本
curl http://localhost:8081/health

# 3. 更新 Nginx 配置指向新端口
# 编辑 /etc/nginx/conf.d/hierarchical-agents.conf
sudo nginx -t
sudo nginx -s reload

# 4. 停止旧容器
docker stop hierarchical-agents-api
docker rm hierarchical-agents-api

# 5. 重命名新容器
docker rename hierarchical-agents-api-new hierarchical-agents-api
```

## 备份和恢复

### 备份配置

```bash
# 备份环境变量
cp .env .env.backup

# 备份 Docker 镜像
docker save hierarchical-agents:latest | gzip > hierarchical-agents-backup.tar.gz

# 备份日志
tar -czf logs-backup.tar.gz /var/log/nginx /var/log/hierarchical-agents
```

### 恢复

```bash
# 恢复 Docker 镜像
docker load < hierarchical-agents-backup.tar.gz

# 恢复配置
cp .env.backup .env
```

## 成本优化

### 1. 使用 Spot 实例

对于非关键工作负载，可以使用 EC2 Spot 实例节省成本。

### 2. 自动缩放

在流量低谷时停止实例：

```bash
# 使用 CloudWatch Events + Lambda 实现自动缩放
# 或使用 EC2 Auto Scaling
```

### 3. 使用预留实例

对于长期运行的生产环境，考虑购买预留实例节省成本。

## 安全最佳实践

1. **最小权限原则**：IAM 角色只授予必需的权限
2. **网络隔离**：使用 VPC 和安全组限制访问
3. **数据加密**：使用 HTTPS 加密传输
4. **定期更新**：保持系统和依赖库更新
5. **日志审计**：启用 CloudTrail 和访问日志
6. **密钥管理**：使用 AWS Secrets Manager 管理敏感信息

## 参考资源

- [Docker 官方文档](https://docs.docker.com/)
- [AWS EC2 用户指南](https://docs.aws.amazon.com/ec2/)
- [AWS Bedrock 开发者指南](https://docs.aws.amazon.com/bedrock/)
- [Gunicorn 文档](https://docs.gunicorn.org/)
- [Nginx 文档](https://nginx.org/en/docs/)
