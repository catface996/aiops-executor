# EC2 Deployment - Standalone HTTP Server

This document summarizes the new EC2/Docker deployment capability for the Hierarchical Multi-Agent System.

## 🎯 Overview

The system now supports **standalone HTTP server deployment** in addition to AWS Lambda, enabling deployment on:

- **EC2 Instances** - Full control over resources and environment
- **Docker Containers** - Portable, isolated deployment
- **Any Server** - Run on-premises or other cloud providers
- **Local Development** - Easy local testing and debugging

## 🆕 What's New

### New Files Created

1. **`http_server.py`** - Standalone HTTP server application
   - Flask-based REST API server
   - Same endpoints as Lambda handler
   - Supports both API Key and IAM Role authentication
   - Configurable port and host

2. **`Dockerfile`** - Container configuration
   - Python 3.12 slim base image
   - Production-ready with Gunicorn
   - Health check configured
   - Non-root user for security

3. **`docker-compose.yml`** - Development environment
   - Easy local development setup
   - Environment variable management
   - Port mapping and networking

4. **`test_http_server.py`** - HTTP server testing script
   - Automated endpoint testing
   - Health check validation
   - Request validation testing

5. **`.dockerignore`** - Docker build optimization
   - Excludes unnecessary files from image
   - Reduces image size

6. **`docs/EC2_DEPLOYMENT_GUIDE.md`** - Comprehensive deployment guide
   - Detailed EC2 setup instructions
   - Multiple deployment methods
   - Production best practices
   - Troubleshooting guide

7. **`DEPLOYMENT_QUICKREF.md`** - Quick reference card
   - Fast lookup for common commands
   - Deployment method selection
   - Configuration templates

### Updated Files

1. **`README.md`** - Enhanced with:
   - EC2/Docker deployment sections
   - Comparison of Lambda vs EC2 deployment
   - Environment variables documentation
   - Deployment mode selection guide

2. **`.env.example`** - Added:
   - HTTP server configuration variables
   - Port and host settings
   - AWS credentials for local IAM testing

3. **`requirements.txt`** - Documented:
   - HTTP server dependencies (Flask, Flask-CORS, Gunicorn)
   - Installation instructions

## 📊 Deployment Comparison

| Feature | AWS Lambda | EC2/Docker |
|---------|-----------|------------|
| **Setup** | Complex (SAM/CloudFormation) | Simple (Docker) |
| **Scaling** | Automatic | Manual/Auto-Scaling |
| **Cost** | Pay per request | Pay per instance-hour |
| **Cold Start** | Yes (~1-5s) | No |
| **Time Limit** | 15 minutes max | Unlimited |
| **Resources** | Limited (10GB RAM max) | Flexible |
| **Maintenance** | Minimal | Server updates required |
| **Use Case** | Sporadic workloads | Continuous workloads |

## 🚀 Quick Start

### Using Docker Compose (Recommended for Development)

```bash
# 1. Configure environment
cp .env.example .env
# Edit .env with your AWS credentials

# 2. Start the server
docker-compose up -d

# 3. Test
curl http://localhost:8080/health
```

### Using Docker (Production)

```bash
# 1. Build
docker build -t hierarchical-agents:latest .

# 2. Run
docker run -d \
  --name hierarchical-agents-api \
  -p 8080:8080 \
  -e USE_IAM_ROLE=true \
  -e AWS_REGION=us-east-1 \
  hierarchical-agents:latest

# 3. Test
curl http://localhost:8080/health
```

### On EC2 Instance

```bash
# 1. Install Docker
sudo yum install -y docker git
sudo systemctl start docker

# 2. Deploy
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

## 🔑 Key Features

### Same API as Lambda
The HTTP server implements the **exact same API** as the Lambda handler:

- **POST /execute** - Execute hierarchy tasks
- **GET /health** - Health check endpoint
- **GET /** - API information

### Flexible Authentication
Supports both authentication methods:

- **API Key** - For local development (`AWS_BEDROCK_API_KEY`)
- **IAM Role** - For AWS deployment (`USE_IAM_ROLE=true`)

### Production Ready
Includes production features:

- **Gunicorn** WSGI server with worker processes
- **Health checks** for monitoring
- **CORS support** for web applications
- **Error handling** with detailed logging
- **Non-root user** for container security
- **Graceful shutdown** and restart support

### Easy Configuration
All configuration via environment variables:

```bash
# Required
AWS_REGION=us-east-1
AWS_BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-20250514-v1:0
USE_IAM_ROLE=true  # or AWS_BEDROCK_API_KEY=xxx

# Optional
PORT=8080
HOST=0.0.0.0
DEBUG=false
```

## 📖 Endpoints

### GET /health
Health check endpoint

**Response:**
```json
{
  "status": "healthy",
  "service": "hierarchical-agents-api",
  "version": "1.0.0",
  "deployment": "ec2"
}
```

### POST /execute
Execute hierarchy task (same as Lambda)

**Request:** See `examples/simple_request.json`

**Response:** Same format as Lambda handler

### GET /
API information

**Response:**
```json
{
  "service": "Hierarchical Multi-Agent System API",
  "version": "1.0.0",
  "deployment": "ec2",
  "endpoints": {...},
  "documentation": "https://github.com/catface996/hierarchical-agents"
}
```

## 🧪 Testing

### Automated Tests

```bash
# Run HTTP server tests
python test_http_server.py
```

### Manual Tests

```bash
# Health check
curl http://localhost:8080/health

# API info
curl http://localhost:8080/

# Execute task
curl -X POST http://localhost:8080/execute \
  -H "Content-Type: application/json" \
  -d @examples/simple_request.json
```

## 📦 Docker Image

### Build Options

```bash
# Standard build
docker build -t hierarchical-agents:latest .

# With build args
docker build \
  --build-arg PYTHON_VERSION=3.12 \
  -t hierarchical-agents:latest .

# Multi-platform build
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t hierarchical-agents:latest .
```

### Image Details

- **Base Image:** python:3.12-slim
- **Size:** ~400-500 MB (optimized)
- **User:** Non-root (appuser, UID 1000)
- **Port:** 8080
- **Entrypoint:** Gunicorn with 4 workers

## 🔧 Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `AWS_REGION` | Yes | - | AWS region for Bedrock |
| `AWS_BEDROCK_MODEL_ID` | Yes | - | Bedrock model ID |
| `AWS_BEDROCK_API_KEY` | No* | - | API key (if not using IAM) |
| `USE_IAM_ROLE` | No* | false | Use IAM role authentication |
| `PORT` | No | 8080 | HTTP server port |
| `HOST` | No | 0.0.0.0 | HTTP server host |
| `DEBUG` | No | false | Enable debug mode |

*One of `AWS_BEDROCK_API_KEY` or `USE_IAM_ROLE=true` is required

### Gunicorn Configuration

Default settings in Dockerfile:
- Workers: 4
- Threads per worker: 2
- Timeout: 300 seconds
- Bind: 0.0.0.0:8080

Can be customized by overriding the CMD in docker run.

## 📚 Documentation

### Main Documentation
- **[README.md](README.md)** - Main project documentation
- **[docs/EC2_DEPLOYMENT_GUIDE.md](docs/EC2_DEPLOYMENT_GUIDE.md)** - Detailed EC2 deployment
- **[DEPLOYMENT_QUICKREF.md](DEPLOYMENT_QUICKREF.md)** - Quick reference

### API Documentation
- **[docs/API_REFERENCE.md](docs/API_REFERENCE.md)** - API specification
- **[docs/AUTHENTICATION_GUIDE.md](docs/AUTHENTICATION_GUIDE.md)** - Authentication setup
- **[README_API.md](README_API.md)** - API quick start

## 🛠️ Troubleshooting

### Common Issues

1. **Port already in use**
   ```bash
   # Check what's using the port
   sudo lsof -i :8080
   # Use different port
   docker run -e PORT=8081 -p 8081:8081 ...
   ```

2. **IAM Role not working**
   ```bash
   # Verify IAM role
   aws sts get-caller-identity
   # Check Bedrock permissions
   aws bedrock list-foundation-models --region us-east-1
   ```

3. **Container fails to start**
   ```bash
   # Check logs
   docker logs hierarchical-agents-api
   # Run interactively for debugging
   docker run -it hierarchical-agents:latest /bin/bash
   ```

See [EC2 Deployment Guide](docs/EC2_DEPLOYMENT_GUIDE.md) for more troubleshooting.

## 🚦 When to Use Each Deployment

### Choose Lambda When:
- ✅ Variable/unpredictable traffic
- ✅ Tasks complete in < 15 minutes
- ✅ Want minimal ops overhead
- ✅ Cost optimization for low/medium use

### Choose EC2/Docker When:
- ✅ Consistent high traffic
- ✅ Long-running tasks (> 15 min)
- ✅ Need specific resources/environment
- ✅ Already have EC2 infrastructure
- ✅ Want full control

## 🎓 Next Steps

1. **Local Testing**
   - Start with Docker Compose
   - Test with your own requests
   - Verify authentication works

2. **EC2 Deployment**
   - Follow [EC2 Deployment Guide](docs/EC2_DEPLOYMENT_GUIDE.md)
   - Configure IAM roles
   - Set up monitoring

3. **Production Hardening**
   - Add Nginx reverse proxy
   - Configure HTTPS with Let's Encrypt
   - Set up log aggregation
   - Configure auto-scaling

4. **Monitoring**
   - CloudWatch metrics
   - Application logs
   - Health check monitoring
   - Performance tuning

## 💡 Best Practices

1. **Use IAM Roles** in production (not API keys)
2. **Set resource limits** on Docker containers
3. **Enable health checks** for monitoring
4. **Use reverse proxy** (Nginx) for SSL/load balancing
5. **Configure log rotation** to prevent disk fill
6. **Regular updates** of base images and dependencies
7. **Backup configuration** files
8. **Monitor resource usage** (CPU, memory, network)

## 📞 Support

For issues or questions:
1. Check the [troubleshooting guide](docs/EC2_DEPLOYMENT_GUIDE.md#故障排除)
2. Review the [quick reference](DEPLOYMENT_QUICKREF.md)
3. Submit an issue on GitHub

---

**Quick Links:**
- [Main README](README.md)
- [EC2 Deployment Guide](docs/EC2_DEPLOYMENT_GUIDE.md)
- [Deployment Quick Reference](DEPLOYMENT_QUICKREF.md)
- [API Reference](docs/API_REFERENCE.md)

Built with ❤️ using Strands Agent SDK
