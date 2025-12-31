"""
Health Routes - 健康检查路由
"""

from flask import Blueprint, jsonify
from flasgger import swag_from

health_bp = Blueprint('health', __name__)


@health_bp.route('/health', methods=['GET'])
@swag_from({
    'tags': ['Health'],
    'summary': '健康检查',
    'description': '检查服务是否正常运行',
    'responses': {
        200: {
            'description': '服务正常',
            'schema': {
                'type': 'object',
                'properties': {
                    'status': {'type': 'string', 'example': 'healthy'},
                    'service': {'type': 'string', 'example': 'hierarchical-agents-api'},
                    'version': {'type': 'string', 'example': '2.0.0'}
                }
            }
        }
    }
})
def health_check():
    """健康检查"""
    return jsonify({
        'status': 'healthy',
        'service': 'op-stack-executor',
        'version': '1.0.0'
    })


@health_bp.route('/', methods=['GET'])
@swag_from({
    'tags': ['Health'],
    'summary': 'API 信息',
    'description': '获取 API 基本信息和可用端点列表',
    'responses': {
        200: {
            'description': 'API 信息',
            'schema': {
                'type': 'object',
                'properties': {
                    'name': {'type': 'string', 'example': 'Op-Stack Executor API'},
                    'version': {'type': 'string', 'example': '1.0.0'},
                    'description': {'type': 'string', 'example': '层级多智能体系统执行器 API'},
                    'endpoints': {
                        'type': 'object',
                        'description': '可用端点列表',
                        'properties': {
                            'health': {'type': 'string', 'example': '/health'},
                            'swagger_ui': {'type': 'string', 'example': '/swagger-ui.html'},
                            'openapi_json': {'type': 'string', 'example': '/v3/api-docs'},
                            'models': {'type': 'string', 'example': '/api/executor/v1/models/*'},
                            'hierarchies': {'type': 'string', 'example': '/api/executor/v1/hierarchies/*'},
                            'runs': {'type': 'string', 'example': '/api/executor/v1/runs/*'}
                        }
                    }
                }
            }
        }
    }
})
def api_info():
    """API 信息"""
    return jsonify({
        'name': 'Op-Stack Executor API',
        'version': '1.0.0',
        'description': '层级多智能体系统执行器 API',
        'endpoints': {
            'health': '/health',
            'swagger_ui': '/swagger-ui.html',
            'openapi_json': '/v3/api-docs',
            'models': '/api/executor/v1/models/*',
            'hierarchies': '/api/executor/v1/hierarchies/*',
            'runs': '/api/executor/v1/runs/*'
        }
    })
