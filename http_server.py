"""
Standalone HTTP Server - 独立的 HTTP 服务器应用
支持在 EC2 实例上独立运行的 HTTP 服务器，提供与 Lambda Handler 相同的 API 接口
"""

import json
import os
import traceback
from typing import Dict, Any
from flask import Flask, request, jsonify, Response
from flask_cors import CORS

# 导入配置管理
from config import setup_config

# 导入执行器
from hierarchy_executor import execute_hierarchy
from api_models import ErrorResponse


# 创建 Flask 应用
app = Flask(__name__)

# 配置 CORS - 与 Lambda 实现保持一致
CORS(app, 
     origins='*',
     methods=['GET', 'POST', 'OPTIONS'],
     allow_headers=['Content-Type'])


def _validate_request(body: Dict[str, Any]) -> Any:
    """
    验证请求
    
    Args:
        body: 请求体
        
    Returns:
        错误消息（如果有），否则返回 None
    """
    # 检查必需字段
    required_fields = ['global_prompt', 'teams', 'task']
    for field in required_fields:
        if field not in body:
            return f"Missing required field: {field}"
    
    # 检查 teams 是否为列表
    if not isinstance(body['teams'], list):
        return "Field 'teams' must be a list"
    
    # 检查至少有一个团队
    if len(body['teams']) == 0:
        return "At least one team is required"
    
    # 验证每个团队
    for i, team in enumerate(body['teams']):
        # 检查团队必需字段
        team_required = ['name', 'supervisor_prompt', 'workers']
        for field in team_required:
            if field not in team:
                return f"Team {i}: Missing required field '{field}'"
        
        # 检查 workers 是否为列表
        if not isinstance(team['workers'], list):
            return f"Team {i}: Field 'workers' must be a list"
        
        # 检查至少有一个 worker
        if len(team['workers']) == 0:
            return f"Team {i}: At least one worker is required"
        
        # 验证每个 worker
        for j, worker in enumerate(team['workers']):
            worker_required = ['name', 'role', 'system_prompt']
            for field in worker_required:
                if field not in worker:
                    return f"Team {i}, Worker {j}: Missing required field '{field}'"
    
    return None


@app.route('/health', methods=['GET'])
def health_check():
    """
    健康检查端点
    
    Returns:
        健康状态响应
    """
    return jsonify({
        'status': 'healthy',
        'service': 'hierarchical-agents-api',
        'version': '1.0.0',
        'deployment': 'ec2'
    }), 200


@app.route('/execute', methods=['POST'])
def execute():
    """
    执行层级多智能体系统
    
    接收 JSON 请求，执行层级系统，返回结果
    
    Returns:
        执行结果的 JSON 响应
    """
    try:
        # 1. 解析请求体
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 400
        
        body = request.get_json()
        
        # 2. 验证请求
        validation_error = _validate_request(body)
        if validation_error:
            return jsonify({'error': validation_error}), 400
        
        # 3. 执行层级系统
        response = execute_hierarchy(body)
        
        # 4. 返回响应
        return jsonify(response.to_dict()), 200
        
    except Exception as e:
        # 错误处理
        error_msg = str(e)
        error_details = traceback.format_exc()
        
        print(f"Error: {error_msg}")
        print(f"Details: {error_details}")
        
        error_response = ErrorResponse(
            error=error_msg,
            details=error_details if os.environ.get('DEBUG') == 'true' else None
        )
        
        return jsonify(error_response.to_dict()), 500


@app.route('/', methods=['GET'])
def root():
    """
    根路径，提供 API 信息
    
    Returns:
        API 信息
    """
    return jsonify({
        'service': 'Hierarchical Multi-Agent System API',
        'version': '1.0.0',
        'deployment': 'ec2',
        'endpoints': {
            'health': 'GET /health - Health check endpoint',
            'execute': 'POST /execute - Execute hierarchy task',
            'info': 'GET / - API information (this endpoint)'
        },
        'authentication': {
            'mode': os.environ.get('USE_IAM_ROLE', 'false'),
            'description': 'Configured via environment variables'
        },
        'documentation': 'https://github.com/catface996/hierarchical-agents'
    }), 200


@app.errorhandler(404)
def not_found(error):
    """404 错误处理"""
    return jsonify({
        'error': 'Endpoint not found',
        'available_endpoints': ['/health', '/execute', '/']
    }), 404


@app.errorhandler(405)
def method_not_allowed(error):
    """405 错误处理"""
    return jsonify({
        'error': 'Method not allowed',
        'hint': 'Check the HTTP method (GET/POST) for this endpoint'
    }), 405


@app.errorhandler(500)
def internal_error(error):
    """500 错误处理"""
    return jsonify({
        'error': 'Internal server error',
        'details': str(error) if os.environ.get('DEBUG') == 'true' else None
    }), 500


def initialize_server():
    """
    初始化服务器配置
    
    设置 AWS 认证等配置
    """
    print("=" * 80)
    print("Hierarchical Multi-Agent System HTTP Server")
    print("=" * 80)
    
    # 设置配置（从环境变量加载）
    try:
        setup_config()
        print("✓ Configuration loaded successfully")
    except Exception as e:
        print(f"⚠ Warning: Configuration error: {e}")
        print("  Server will start but may fail on actual requests")
    
    print("=" * 80)


def main():
    """
    主函数 - 启动 HTTP 服务器
    """
    # 初始化配置
    initialize_server()
    
    # 从环境变量获取端口配置
    port = int(os.environ.get('PORT', 8080))
    host = os.environ.get('HOST', '0.0.0.0')
    debug = os.environ.get('DEBUG', 'false').lower() == 'true'
    
    print(f"\nStarting server on {host}:{port}")
    print(f"Debug mode: {debug}")
    print(f"\nEndpoints:")
    print(f"  - GET  {host}:{port}/health")
    print(f"  - POST {host}:{port}/execute")
    print(f"  - GET  {host}:{port}/")
    print(f"\nPress Ctrl+C to stop the server\n")
    
    # 启动服务器
    app.run(
        host=host,
        port=port,
        debug=debug,
        threaded=True  # 支持并发请求
    )


if __name__ == '__main__':
    main()
