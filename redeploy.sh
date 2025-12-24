#!/bin/bash
#
# 重新部署脚本
# 用法: ./redeploy.sh [--no-cache] [--reset-db]
#
# 选项:
#   --no-cache    构建时不使用缓存
#   --reset-db    重置数据库（删除数据卷）
#

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置
COMPOSE_FILE="docker-compose.ec2.yml"
API_CONTAINER="hierarchical-agents-api"
MYSQL_CONTAINER="hierarchical-agents-mysql"
HEALTH_TIMEOUT=60
HEALTH_INTERVAL=2

# 加载 .env 文件（如果存在）
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# 使用环境变量或默认值（与 docker-compose.yml 保持一致，默认 8080）
API_PORT="${API_EXTERNAL_PORT:-8080}"
HEALTH_URL="http://localhost:${API_PORT}/health"

# 解析参数
NO_CACHE=""
RESET_DB=""
for arg in "$@"; do
    case $arg in
        --no-cache)
            NO_CACHE="--no-cache"
            shift
            ;;
        --reset-db)
            RESET_DB="true"
            shift
            ;;
    esac
done

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}       重新部署 AIOps Executor         ${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 1. 停止服务并删除容器
echo -e "${YELLOW}[1/6] 停止服务并删除容器...${NC}"
if docker-compose -f $COMPOSE_FILE ps -q 2>/dev/null | grep -q .; then
    if [ -n "$RESET_DB" ]; then
        # 删除容器和数据卷
        docker-compose -f $COMPOSE_FILE down -v
        echo -e "${GREEN}      服务已停止，容器和数据卷已删除${NC}"
    else
        # 只删除容器
        docker-compose -f $COMPOSE_FILE down
        echo -e "${GREEN}      服务已停止，容器已删除${NC}"
    fi
else
    echo -e "${GREEN}      服务未运行${NC}"
fi

# 强制删除数据库容器（如果存在）
if docker ps -a -q -f "name=$MYSQL_CONTAINER" | grep -q .; then
    docker rm -f $MYSQL_CONTAINER 2>/dev/null || true
    echo -e "${GREEN}      数据库容器已删除${NC}"
fi

# 强制删除 API 容器（如果存在）
if docker ps -a -q -f "name=$API_CONTAINER" | grep -q .; then
    docker rm -f $API_CONTAINER 2>/dev/null || true
    echo -e "${GREEN}      API 容器已删除${NC}"
fi
echo ""

# 2. 删除项目构建的镜像（不删除基础镜像如 mysql:8.0, python:3.12-slim）
echo -e "${YELLOW}[2/6] 删除项目镜像...${NC}"

# 获取项目构建的 API 镜像名称
PROJECT_NAME=$(basename "$(pwd)")
API_IMAGE="${PROJECT_NAME}-api"

if docker images -q "$API_IMAGE" 2>/dev/null | grep -q .; then
    docker rmi -f "$API_IMAGE" 2>/dev/null || true
    echo -e "${GREEN}      镜像 $API_IMAGE 已删除${NC}"
else
    echo -e "${GREEN}      镜像 $API_IMAGE 不存在，跳过${NC}"
fi

# 清理构建产生的悬空镜像（不影响基础镜像）
DANGLING=$(docker images -f "dangling=true" -q 2>/dev/null)
if [ -n "$DANGLING" ]; then
    echo -e "      清理悬空镜像..."
    docker rmi $DANGLING 2>/dev/null || true
fi
echo ""

# 3. 重新构建镜像
echo -e "${YELLOW}[3/6] 重新构建镜像...${NC}"
if [ -n "$NO_CACHE" ]; then
    echo -e "      使用 --no-cache 模式"
fi
docker-compose -f $COMPOSE_FILE build $NO_CACHE
echo -e "${GREEN}      镜像构建完成${NC}"
echo ""

# 4. 启动服务
echo -e "${YELLOW}[4/6] 启动服务...${NC}"
docker-compose -f $COMPOSE_FILE up -d
echo -e "${GREEN}      服务已启动${NC}"
echo ""

# 5. 等待数据库就绪
echo -e "${YELLOW}[5/6] 等待数据库就绪...${NC}"
sleep 5
echo -e "${GREEN}      数据库启动中...${NC}"
echo ""

# 6. 健康检查
echo -e "${YELLOW}[6/6] API 健康检查...${NC}"
echo -e "      等待服务就绪 (最多 ${HEALTH_TIMEOUT}s)..."

elapsed=0
while [ $elapsed -lt $HEALTH_TIMEOUT ]; do
    # 检查容器状态
    if ! docker ps -q -f "name=$API_CONTAINER" | grep -q .; then
        echo -e "${RED}      容器未运行，检查日志：${NC}"
        docker-compose -f $COMPOSE_FILE logs --tail=20 api
        exit 1
    fi

    # 检查健康接口
    response=$(curl -s -o /dev/null -w "%{http_code}" $HEALTH_URL 2>/dev/null || echo "000")

    if [ "$response" = "200" ]; then
        echo -e "${GREEN}      健康检查通过!${NC}"
        echo ""

        # 显示健康检查响应
        echo -e "${BLUE}健康检查响应:${NC}"
        curl -s $HEALTH_URL | python3 -m json.tool 2>/dev/null || curl -s $HEALTH_URL
        echo ""

        # 显示容器状态
        echo -e "${BLUE}容器状态:${NC}"
        docker-compose -f $COMPOSE_FILE ps
        echo ""

        echo -e "${GREEN}========================================${NC}"
        echo -e "${GREEN}       部署成功!                        ${NC}"
        echo -e "${GREEN}========================================${NC}"
        echo -e "API 地址: http://localhost:${API_PORT}"
        echo -e "健康检查: $HEALTH_URL"
        exit 0
    fi

    sleep $HEALTH_INTERVAL
    elapsed=$((elapsed + HEALTH_INTERVAL))
    echo -e "      等待中... (${elapsed}s)"
done

# 健康检查超时
echo -e "${RED}      健康检查超时!${NC}"
echo ""
echo -e "${RED}容器日志:${NC}"
docker-compose -f $COMPOSE_FILE logs --tail=50 api
exit 1
