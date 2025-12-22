"""
Standalone HTTP Server - 独立的 HTTP 服务器应用

支持在 EC2 实例上独立运行的 HTTP 服务器
提供完整的 API 接口，包括模型管理、层级团队管理、运行管理
"""

import os
from flask import Flask, jsonify
from flask_cors import CORS
from flasgger import Swagger

# 导入配置管理
from ..core.config import setup_config

# 导入数据库
from ..db.database import init_db

# 导入路由蓝图
from ..api.routes import models_bp, hierarchies_bp, runs_bp, health_bp


def create_app(config_name: str = None) -> Flask:
    """
    应用工厂函数

    Args:
        config_name: 配置名称（可选）

    Returns:
        Flask 应用实例
    """
    app = Flask(__name__)

    # 加载配置
    app.config['DATABASE_URL'] = os.environ.get('DATABASE_URL')
    app.config['DEBUG'] = os.environ.get('DEBUG', 'false').lower() == 'true'

    # 配置 CORS
    CORS(
        app,
        origins='*',
        methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
        allow_headers=['Content-Type', 'Authorization']
    )

    # 配置 Swagger
    swagger_config = {
        "headers": [],
        "specs": [
            {
                "endpoint": 'apispec',
                "route": '/swagger.json',
                "rule_filter": lambda rule: True,
                "model_filter": lambda tag: True,
            }
        ],
        "static_url_path": "/flasgger_static",
        "swagger_ui": True,
        "specs_route": "/swagger"
    }

    swagger_template = {
        "info": {
            "title": "Hierarchical Agents API",
            "description": "层级多智能体系统 API - 支持模型管理、团队配置、运行管理",
            "version": "2.0.0",
            "contact": {
                "name": "API Support",
                "url": "https://github.com/catface996/hierarchical-agents"
            }
        },
        "tags": [
            {"name": "Health", "description": "健康检查"},
            {"name": "Models", "description": "AI 模型管理"},
            {"name": "Hierarchies", "description": "层级团队管理"},
            {"name": "Runs", "description": "运行管理"}
        ],
        "schemes": ["http", "https"],
        "securityDefinitions": {}
    }

    Swagger(app, config=swagger_config, template=swagger_template)

    # 初始化数据库
    db = init_db(app)

    # 注册请求结束时的会话清理
    @app.teardown_appcontext
    def shutdown_session(exception=None):
        """每个请求结束后清理数据库会话"""
        if db:
            db.remove()

    # 初始化配置（AWS 认证等）
    try:
        setup_config()
    except Exception as e:
        print(f"Warning: Configuration error: {e}")

    # 注册蓝图
    app.register_blueprint(health_bp)  # /health, /
    app.register_blueprint(models_bp, url_prefix='/api/v1/models')
    app.register_blueprint(hierarchies_bp, url_prefix='/api/v1/hierarchies')
    app.register_blueprint(runs_bp, url_prefix='/api/v1/runs')

    # 保留旧的 /execute 端点（向后兼容）
    register_legacy_routes(app)

    # 错误处理
    register_error_handlers(app)

    return app


def register_legacy_routes(app: Flask):
    """注册向后兼容的旧路由"""
    import traceback
    from flask import request
    from ..core.api_models import ErrorResponse
    # 注意: execute_hierarchy 延迟导入到 execute() 函数中以避免 strands 依赖检查

    def _validate_request(body):
        required_fields = ['global_prompt', 'teams', 'task']
        for field in required_fields:
            if field not in body:
                return f"Missing required field: {field}"
        if not isinstance(body['teams'], list):
            return "Field 'teams' must be a list"
        if len(body['teams']) == 0:
            return "At least one team is required"
        for i, team in enumerate(body['teams']):
            team_required = ['name', 'supervisor_prompt', 'workers']
            for field in team_required:
                if field not in team:
                    return f"Team {i}: Missing required field '{field}'"
            if not isinstance(team['workers'], list):
                return f"Team {i}: Field 'workers' must be a list"
            if len(team['workers']) == 0:
                return f"Team {i}: At least one worker is required"
            for j, worker in enumerate(team['workers']):
                worker_required = ['name', 'role', 'system_prompt']
                for field in worker_required:
                    if field not in worker:
                        return f"Team {i}, Worker {j}: Missing required field '{field}'"
        return None

    @app.route('/execute', methods=['POST'])
    def execute():
        """旧版执行端点（向后兼容）"""
        # 延迟导入 - 需要 strands 依赖
        from ..core.hierarchy_executor import execute_hierarchy

        try:
            if not request.is_json:
                return jsonify({'error': 'Content-Type must be application/json'}), 400

            body = request.get_json()
            validation_error = _validate_request(body)
            if validation_error:
                return jsonify({'error': validation_error}), 400

            response = execute_hierarchy(body)
            return jsonify(response.to_dict()), 200

        except Exception as e:
            error_msg = str(e)
            error_details = traceback.format_exc()
            print(f"Error: {error_msg}")
            print(f"Details: {error_details}")

            error_response = ErrorResponse(
                error=error_msg,
                details=error_details if os.environ.get('DEBUG') == 'true' else None
            )
            return jsonify(error_response.to_dict()), 500


def register_error_handlers(app: Flask):
    """注册错误处理器"""

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            'success': False,
            'error': 'Endpoint not found',
            'available_endpoints': {
                'swagger': '/swagger',
                'health': '/health',
                'models': '/api/v1/models/*',
                'hierarchies': '/api/v1/hierarchies/*',
                'runs': '/api/v1/runs/*',
                'legacy_execute': '/execute'
            }
        }), 404

    @app.errorhandler(405)
    def method_not_allowed(error):
        return jsonify({
            'success': False,
            'error': 'Method not allowed',
            'hint': 'All API endpoints use POST method'
        }), 405

    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'details': str(error) if os.environ.get('DEBUG') == 'true' else None
        }), 500


# 创建默认应用实例
app = create_app()


def initialize_server():
    """初始化服务器配置"""
    print("=" * 80)
    print("Hierarchical Multi-Agent System HTTP Server v2.0")
    print("=" * 80)
    print("\nAPI Endpoints:")
    print("  Swagger UI:  GET  /swagger")
    print("  Health:      GET  /health")
    print("  Models:      POST /api/v1/models/{list,get,create,update,delete}")
    print("  Hierarchies: POST /api/v1/hierarchies/{list,get,create,update,delete}")
    print("  Runs:        POST /api/v1/runs/{start,list,get,stream,cancel}")
    print("  Legacy:      POST /execute (backward compatible)")
    print("=" * 80)


def main():
    """主函数 - 启动 HTTP 服务器"""
    initialize_server()

    port = int(os.environ.get('PORT', 8080))
    host = os.environ.get('HOST', '0.0.0.0')
    debug = os.environ.get('DEBUG', 'false').lower() == 'true'

    print(f"\nStarting server on {host}:{port}")
    print(f"Debug mode: {debug}")
    print(f"Swagger UI: http://{host}:{port}/swagger")
    print(f"\nPress Ctrl+C to stop the server\n")

    app.run(
        host=host,
        port=port,
        debug=debug,
        threaded=True
    )


if __name__ == '__main__':
    main()
