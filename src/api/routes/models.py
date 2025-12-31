"""
Models Routes - AI 模型管理路由
"""

from flask import Blueprint, request, jsonify
from flasgger import swag_from
from pydantic import ValidationError

from ..schemas.model_schemas import (
    ModelCreateRequest, ModelUpdateRequest, ModelListRequest
)
from ..schemas.common import IdRequest, build_page_response
from ...db.database import get_db_session
from ...db.repositories import ModelRepository

models_bp = Blueprint('models', __name__)


def get_repo():
    """获取模型仓库"""
    return ModelRepository(get_db_session())


@models_bp.route('/list', methods=['POST'])
@swag_from({
    'tags': ['Models'],
    'summary': '获取模型列表',
    'description': '''分页获取 AI 模型配置列表。

模型配置用于定义 Agent 使用的底层 LLM 参数，包括 AWS Bedrock 模型 ID、区域、温度、最大 Token 数等。
''',
    'parameters': [{
        'name': 'body',
        'in': 'body',
        'required': True,
        'schema': {
            'type': 'object',
            'properties': {
                'page': {'type': 'integer', 'default': 1, 'description': '页码，从 1 开始'},
                'size': {'type': 'integer', 'default': 20, 'description': '每页数量，范围 1-100'},
                'is_active': {'type': 'boolean', 'description': '按激活状态筛选，true=已激活，false=已禁用，不传=全部'}
            }
        }
    }],
    'responses': {
        200: {
            'description': '模型列表',
            'schema': {
                'type': 'object',
                'properties': {
                    'code': {'type': 'integer', 'example': 0},
                    'success': {'type': 'boolean'},
                    'data': {
                        'type': 'object',
                        'properties': {
                            'content': {
                                'type': 'array',
                                'items': {
                                    'type': 'object',
                                    'properties': {
                                        'id': {'type': 'string', 'description': '模型唯一标识'},
                                        'name': {'type': 'string', 'description': '模型名称'},
                                        'model_id': {'type': 'string', 'description': 'AWS Bedrock 模型 ID'},
                                        'region': {'type': 'string', 'description': 'AWS 区域'},
                                        'temperature': {'type': 'number', 'description': '温度参数 (0-1)'},
                                        'max_tokens': {'type': 'integer', 'description': '最大 Token 数'},
                                        'top_p': {'type': 'number', 'description': 'Top-P 参数'},
                                        'is_active': {'type': 'boolean', 'description': '是否激活'}
                                    }
                                }
                            },
                            'page': {'type': 'integer'},
                            'size': {'type': 'integer'},
                            'totalElements': {'type': 'integer'},
                            'totalPages': {'type': 'integer'}
                        }
                    }
                }
            }
        },
        500: {'description': '服务器错误'}
    }
})
def list_models():
    """获取模型列表"""
    try:
        data = request.get_json() or {}
        req = ModelListRequest(**data)

        repo = get_repo()
        models, total = repo.list(
            page=req.page,
            size=req.size,
            is_active=req.is_active
        )

        return jsonify(build_page_response(
            content=[m.to_dict() for m in models],
            page=req.page,
            size=req.size,
            total=total
        ))
    except ValidationError as e:
        return jsonify({'code': 400, 'success': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'code': 500, 'success': False, 'error': str(e)}), 500


@models_bp.route('/get', methods=['POST'])
@swag_from({
    'tags': ['Models'],
    'summary': '获取模型详情',
    'description': '根据模型 ID 获取模型的详细配置信息，包括 AWS Bedrock 参数和激活状态。',
    'parameters': [{
        'name': 'body',
        'in': 'body',
        'required': True,
        'schema': {
            'type': 'object',
            'required': ['id'],
            'properties': {
                'id': {'type': 'string', 'description': '模型唯一标识 (UUID)'}
            }
        }
    }],
    'responses': {
        200: {
            'description': '模型详情',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'data': {
                        'type': 'object',
                        'properties': {
                            'id': {'type': 'string'},
                            'name': {'type': 'string'},
                            'model_id': {'type': 'string', 'description': 'AWS Bedrock 模型 ID，如 anthropic.claude-3-sonnet-20240229-v1:0'},
                            'region': {'type': 'string', 'description': 'AWS 区域'},
                            'temperature': {'type': 'number'},
                            'max_tokens': {'type': 'integer'},
                            'top_p': {'type': 'number'},
                            'description': {'type': 'string'},
                            'is_active': {'type': 'boolean'},
                            'created_at': {'type': 'string', 'format': 'date-time'},
                            'updated_at': {'type': 'string', 'format': 'date-time'}
                        }
                    }
                }
            }
        },
        404: {
            'description': '模型不存在',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean', 'example': False},
                    'error': {'type': 'string', 'example': '模型不存在'}
                }
            }
        }
    }
})
def get_model():
    """获取模型详情"""
    try:
        data = request.get_json() or {}
        req = IdRequest(**data)

        repo = get_repo()
        model = repo.get_by_id(req.id)

        if not model:
            return jsonify({'success': False, 'error': '模型不存在'}), 404

        return jsonify({
            'success': True,
            'data': model.to_dict()
        })
    except ValidationError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@models_bp.route('/create', methods=['POST'])
@swag_from({
    'tags': ['Models'],
    'summary': '创建模型',
    'description': '''创建新的 AI 模型配置。

## 参数说明

| 参数 | 说明 |
|------|------|
| model_id | AWS Bedrock 模型 ID，如 `anthropic.claude-3-sonnet-20240229-v1:0` |
| temperature | 控制输出随机性，0=确定性，1=高随机性，默认 0.7 |
| max_tokens | 单次生成的最大 Token 数，默认 2048 |
| top_p | 核采样参数，控制输出多样性，默认 0.9 |

## 常用模型 ID

- Claude 3.5 Sonnet: `anthropic.claude-3-5-sonnet-20241022-v2:0`
- Claude 3 Sonnet: `anthropic.claude-3-sonnet-20240229-v1:0`
- Claude 3 Haiku: `anthropic.claude-3-haiku-20240307-v1:0`
''',
    'parameters': [{
        'name': 'body',
        'in': 'body',
        'required': True,
        'schema': {
            'type': 'object',
            'required': ['name', 'model_id'],
            'properties': {
                'name': {'type': 'string', 'description': '模型名称，用于在层级配置中引用，必须唯一'},
                'model_id': {'type': 'string', 'description': 'AWS Bedrock 模型 ID'},
                'region': {'type': 'string', 'default': 'us-east-1', 'description': 'AWS 区域，默认 us-east-1'},
                'temperature': {'type': 'number', 'default': 0.7, 'description': '温度参数 (0-1)，默认 0.7'},
                'max_tokens': {'type': 'integer', 'default': 2048, 'description': '最大 Token 数，默认 2048'},
                'top_p': {'type': 'number', 'default': 0.9, 'description': 'Top-P 参数 (0-1)，默认 0.9'},
                'description': {'type': 'string', 'description': '模型描述（可选）'},
                'is_active': {'type': 'boolean', 'default': True, 'description': '是否激活，默认 true'}
            }
        }
    }],
    'responses': {
        200: {
            'description': '创建成功',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean', 'example': True},
                    'message': {'type': 'string', 'example': '模型创建成功'},
                    'data': {
                        'type': 'object',
                        'properties': {
                            'id': {'type': 'string'},
                            'name': {'type': 'string'},
                            'model_id': {'type': 'string'},
                            'region': {'type': 'string'},
                            'temperature': {'type': 'number'},
                            'max_tokens': {'type': 'integer'},
                            'top_p': {'type': 'number'},
                            'is_active': {'type': 'boolean'}
                        }
                    }
                }
            }
        },
        400: {
            'description': '参数无效或模型名称已存在',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean', 'example': False},
                    'error': {'type': 'string'}
                }
            }
        }
    }
})
def create_model():
    """创建模型"""
    try:
        data = request.get_json() or {}
        req = ModelCreateRequest(**data)

        repo = get_repo()

        # 检查名称是否重复
        if repo.get_by_name(req.name):
            return jsonify({'success': False, 'error': f'模型名称 "{req.name}" 已存在'}), 400

        model = repo.create(req.model_dump())

        return jsonify({
            'success': True,
            'message': '模型创建成功',
            'data': model.to_dict()
        })
    except ValidationError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@models_bp.route('/update', methods=['POST'])
@swag_from({
    'tags': ['Models'],
    'summary': '更新模型',
    'description': '''更新模型配置信息。

只需传入需要更新的字段，未传入的字段保持原值不变。
''',
    'parameters': [{
        'name': 'body',
        'in': 'body',
        'required': True,
        'schema': {
            'type': 'object',
            'required': ['id'],
            'properties': {
                'id': {'type': 'string', 'description': '模型唯一标识 (UUID)，必填'},
                'name': {'type': 'string', 'description': '模型名称，必须唯一'},
                'model_id': {'type': 'string', 'description': 'AWS Bedrock 模型 ID'},
                'region': {'type': 'string', 'description': 'AWS 区域'},
                'temperature': {'type': 'number', 'description': '温度参数 (0-1)'},
                'max_tokens': {'type': 'integer', 'description': '最大 Token 数'},
                'top_p': {'type': 'number', 'description': 'Top-P 参数 (0-1)'},
                'description': {'type': 'string', 'description': '模型描述'},
                'is_active': {'type': 'boolean', 'description': '是否激活'}
            }
        }
    }],
    'responses': {
        200: {
            'description': '更新成功',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean', 'example': True},
                    'message': {'type': 'string', 'example': '模型更新成功'},
                    'data': {'type': 'object', 'description': '更新后的模型信息'}
                }
            }
        },
        400: {
            'description': '参数无效或模型名称已存在',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean', 'example': False},
                    'error': {'type': 'string'}
                }
            }
        },
        404: {
            'description': '模型不存在',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean', 'example': False},
                    'error': {'type': 'string', 'example': '模型不存在'}
                }
            }
        }
    }
})
def update_model():
    """更新模型"""
    try:
        data = request.get_json() or {}
        req = ModelUpdateRequest(**data)

        repo = get_repo()

        # 过滤掉 None 值
        update_data = {k: v for k, v in req.model_dump().items() if v is not None and k != 'id'}

        # 检查名称是否与其他模型重复
        if 'name' in update_data:
            existing = repo.get_by_name(update_data['name'])
            if existing and existing.id != req.id:
                return jsonify({'success': False, 'error': f'模型名称 "{update_data["name"]}" 已存在'}), 400

        model = repo.update(req.id, update_data)

        if not model:
            return jsonify({'success': False, 'error': '模型不存在'}), 404

        return jsonify({
            'success': True,
            'message': '模型更新成功',
            'data': model.to_dict()
        })
    except ValidationError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@models_bp.route('/delete', methods=['POST'])
@swag_from({
    'tags': ['Models'],
    'summary': '删除模型',
    'description': '''删除指定的模型配置。

**注意**: 删除模型后，引用该模型的层级配置可能无法正常执行。建议先检查模型是否被使用。
''',
    'parameters': [{
        'name': 'body',
        'in': 'body',
        'required': True,
        'schema': {
            'type': 'object',
            'required': ['id'],
            'properties': {
                'id': {'type': 'string', 'description': '模型唯一标识 (UUID)'}
            }
        }
    }],
    'responses': {
        200: {
            'description': '删除成功',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean', 'example': True},
                    'message': {'type': 'string', 'example': '模型删除成功'}
                }
            }
        },
        404: {
            'description': '模型不存在',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean', 'example': False},
                    'error': {'type': 'string', 'example': '模型不存在'}
                }
            }
        }
    }
})
def delete_model():
    """删除模型"""
    try:
        data = request.get_json() or {}
        req = IdRequest(**data)

        repo = get_repo()
        success = repo.delete(req.id)

        if not success:
            return jsonify({'success': False, 'error': '模型不存在'}), 404

        return jsonify({
            'success': True,
            'message': '模型删除成功'
        })
    except ValidationError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
