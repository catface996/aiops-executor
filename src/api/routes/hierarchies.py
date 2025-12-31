"""
Hierarchies Routes - 层级团队管理路由
"""

from flask import Blueprint, request, jsonify
from flasgger import swag_from
from pydantic import ValidationError

from ..schemas.hierarchy_schemas import (
    HierarchyCreateRequest, HierarchyUpdateRequest, HierarchyListRequest
)
from ..schemas.common import IdRequest, build_page_response
from ...db.database import get_db_session
from ...db.repositories import HierarchyRepository
from ...db.repositories.hierarchy_repo import check_agent_ids_unique_in_hierarchy


hierarchies_bp = Blueprint('hierarchies', __name__)


def get_repo():
    """获取层级团队仓库"""
    return HierarchyRepository(get_db_session())


@hierarchies_bp.route('/list', methods=['POST'])
@swag_from({
    'tags': ['Hierarchies'],
    'summary': '获取层级团队列表',
    'description': '分页获取层级团队配置列表，支持按激活状态筛选',
    'parameters': [{
        'name': 'body',
        'in': 'body',
        'required': True,
        'schema': {
            'type': 'object',
            'properties': {
                'page': {'type': 'integer', 'default': 1, 'description': '页码，从 1 开始'},
                'size': {'type': 'integer', 'default': 20, 'description': '每页数量，范围 1-100'},
                'is_active': {'type': 'boolean', 'description': '筛选激活状态，true=仅激活，false=仅未激活，不传=全部'}
            }
        }
    }],
    'responses': {
        200: {
            'description': '层级团队列表',
            'schema': {
                'type': 'object',
                'properties': {
                    'code': {'type': 'integer', 'example': 0},
                    'success': {'type': 'boolean', 'example': True},
                    'data': {
                        'type': 'object',
                        'properties': {
                            'content': {
                                'type': 'array',
                                'items': {
                                    'type': 'object',
                                    'properties': {
                                        'id': {'type': 'string', 'description': '层级团队唯一标识'},
                                        'name': {'type': 'string', 'description': '层级团队名称'},
                                        'description': {'type': 'string', 'description': '描述信息'},
                                        'execution_mode': {'type': 'string', 'enum': ['sequential', 'parallel'], 'description': '执行模式'},
                                        'team_count': {'type': 'integer', 'description': '团队数量'},
                                        'is_active': {'type': 'boolean', 'description': '是否激活'},
                                        'version': {'type': 'integer', 'description': '版本号'},
                                        'created_at': {'type': 'string', 'format': 'date-time'},
                                        'updated_at': {'type': 'string', 'format': 'date-time'}
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
        }
    }
})
def list_hierarchies():
    """获取层级团队列表"""
    try:
        data = request.get_json() or {}
        req = HierarchyListRequest(**data)

        repo = get_repo()
        hierarchies, total = repo.list(
            page=req.page,
            size=req.size,
            is_active=req.is_active
        )

        # 返回简化的列表项
        content = []
        for h in hierarchies:
            config = h.config or {}
            item = {
                'id': h.id,
                'name': h.name,
                'description': h.description,
                'execution_mode': config.get('execution_mode', 'sequential'),
                'team_count': len(config.get('teams', [])),
                'is_active': h.is_active,
                'version': h.version,
                'created_at': h.created_at.isoformat() if h.created_at else None,
                'updated_at': h.updated_at.isoformat() if h.updated_at else None,
            }
            content.append(item)

        return jsonify(build_page_response(
            content=content,
            page=req.page,
            size=req.size,
            total=total
        ))
    except ValidationError as e:
        return jsonify({'code': 400, 'success': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'code': 500, 'success': False, 'error': str(e)}), 500


@hierarchies_bp.route('/get', methods=['POST'])
@swag_from({
    'tags': ['Hierarchies'],
    'summary': '获取层级团队详情',
    'description': '根据 ID 获取层级团队的完整配置信息，包括 Global Supervisor、Team Supervisors 和 Workers 的详细配置',
    'parameters': [{
        'name': 'body',
        'in': 'body',
        'required': True,
        'schema': {
            'type': 'object',
            'required': ['id'],
            'properties': {
                'id': {'type': 'string', 'description': '层级团队唯一标识 (UUID)'}
            }
        }
    }],
    'responses': {
        200: {
            'description': '层级团队详情',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'data': {
                        'type': 'object',
                        'properties': {
                            'id': {'type': 'string', 'description': '层级团队唯一标识'},
                            'name': {'type': 'string', 'description': '层级团队名称'},
                            'description': {'type': 'string', 'description': '描述信息'},
                            'config': {'type': 'object', 'description': '完整的层级配置 JSON'},
                            'is_active': {'type': 'boolean'},
                            'version': {'type': 'integer'},
                            'created_at': {'type': 'string', 'format': 'date-time'},
                            'updated_at': {'type': 'string', 'format': 'date-time'}
                        }
                    }
                }
            }
        },
        404: {'description': '层级团队不存在'}
    }
})
def get_hierarchy():
    """获取层级团队详情"""
    try:
        data = request.get_json() or {}
        req = IdRequest(**data)

        repo = get_repo()
        hierarchy = repo.get_by_id(req.id)

        if not hierarchy:
            return jsonify({'success': False, 'error': '层级团队不存在'}), 404

        return jsonify({
            'success': True,
            'data': hierarchy.to_dict()
        })
    except ValidationError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@hierarchies_bp.route('/create', methods=['POST'])
@swag_from({
    'tags': ['Hierarchies'],
    'summary': '创建层级团队',
    'description': '''创建新的层级多智能体系统配置。

## 层级结构

```
Global Supervisor (全局协调者)
├── Team 1 (团队1)
│   ├── Team Supervisor (团队主管)
│   └── Workers (工作者)
│       ├── Worker 1
│       └── Worker 2
└── Team 2 (团队2)
    ├── Team Supervisor
    └── Workers
```

## agent_id 规则

- 每个 Agent (Global Supervisor, Team Supervisor, Worker) 都可以指定 `agent_id`
- `agent_id` 在同一个 Hierarchy 内必须唯一
- 用于事件追踪和日志关联

## llm_config 结构

```json
{
  "temperature": 0.7,    // 温度参数 (0.0-2.0)
  "max_tokens": 2048,    // 最大 Token 数
  "top_p": 0.9,          // Top-P 采样参数
  "model_id": "xxx"      // 可选，关联的模型配置 ID
}
```
''',
    'parameters': [{
        'name': 'body',
        'in': 'body',
        'required': True,
        'schema': {
            'type': 'object',
            'required': ['name', 'global_supervisor_agent', 'teams'],
            'properties': {
                'name': {'type': 'string', 'description': '层级团队名称，必须唯一', 'example': 'customer-service-team'},
                'description': {'type': 'string', 'description': '层级团队描述', 'example': '客服智能体团队'},
                'execution_mode': {'type': 'string', 'enum': ['sequential', 'parallel'], 'default': 'sequential', 'description': '团队执行模式：sequential=顺序执行，parallel=并行执行'},
                'enable_context_sharing': {'type': 'boolean', 'default': False, 'description': '是否启用跨团队上下文共享'},
                'global_supervisor_agent': {
                    'type': 'object',
                    'required': ['system_prompt'],
                    'description': 'Global Supervisor 配置 - 全局协调者，负责任务分解和团队调度',
                    'properties': {
                        'agent_id': {'type': 'string', 'description': 'Agent 唯一标识，用于事件追踪', 'example': 'gs-001'},
                        'system_prompt': {'type': 'string', 'description': '系统提示词，定义 Agent 角色和行为', 'example': 'You are a global coordinator...'},
                        'user_message': {'type': 'string', 'description': '预定义的用户消息（可选）'},
                        'llm_config': {
                            'type': 'object',
                            'description': 'LLM 配置参数',
                            'properties': {
                                'temperature': {'type': 'number', 'default': 0.7, 'description': '温度参数 (0.0-2.0)，越高越随机'},
                                'max_tokens': {'type': 'integer', 'default': 2048, 'description': '最大输出 Token 数'},
                                'top_p': {'type': 'number', 'default': 0.9, 'description': 'Top-P 采样参数'},
                                'model_id': {'type': 'string', 'description': '关联的模型配置 ID（可选）'}
                            }
                        }
                    }
                },
                'teams': {
                    'type': 'array',
                    'description': '团队配置列表，至少包含一个团队',
                    'items': {
                        'type': 'object',
                        'required': ['name', 'team_supervisor_agent', 'workers'],
                        'properties': {
                            'name': {'type': 'string', 'description': '团队名称，在层级内唯一', 'example': 'analysis-team'},
                            'team_supervisor_agent': {
                                'type': 'object',
                                'required': ['system_prompt'],
                                'description': 'Team Supervisor 配置 - 团队主管，负责协调本团队的 Workers',
                                'properties': {
                                    'agent_id': {'type': 'string', 'description': 'Agent 唯一标识', 'example': 'ts-001'},
                                    'system_prompt': {'type': 'string', 'description': '系统提示词'},
                                    'user_message': {'type': 'string', 'description': '预定义的用户消息（可选）'},
                                    'llm_config': {
                                        'type': 'object',
                                        'description': 'LLM 配置参数',
                                        'properties': {
                                            'temperature': {'type': 'number', 'default': 0.7},
                                            'max_tokens': {'type': 'integer', 'default': 2048},
                                            'top_p': {'type': 'number', 'default': 0.9},
                                            'model_id': {'type': 'string'}
                                        }
                                    }
                                }
                            },
                            'prevent_duplicate': {'type': 'boolean', 'default': True, 'description': '是否防止重复调用同一任务'},
                            'share_context': {'type': 'boolean', 'default': False, 'description': '是否接收其他团队的执行上下文'},
                            'workers': {
                                'type': 'array',
                                'description': 'Worker 配置列表，至少包含一个 Worker',
                                'items': {
                                    'type': 'object',
                                    'required': ['name', 'role', 'system_prompt'],
                                    'properties': {
                                        'agent_id': {'type': 'string', 'description': 'Agent 唯一标识', 'example': 'w-001'},
                                        'name': {'type': 'string', 'description': 'Worker 名称', 'example': 'Data Analyst'},
                                        'role': {'type': 'string', 'description': 'Worker 角色描述', 'example': '数据分析专家'},
                                        'system_prompt': {'type': 'string', 'description': '系统提示词，定义 Worker 的专业能力'},
                                        'user_message': {'type': 'string', 'description': '预定义的用户消息（可选）'},
                                        'tools': {'type': 'array', 'items': {'type': 'string'}, 'description': '可用工具列表', 'example': ['calculator', 'http_request']},
                                        'llm_config': {
                                            'type': 'object',
                                            'description': 'LLM 配置参数',
                                            'properties': {
                                                'temperature': {'type': 'number', 'default': 0.7},
                                                'max_tokens': {'type': 'integer', 'default': 2048},
                                                'top_p': {'type': 'number', 'default': 0.9},
                                                'model_id': {'type': 'string'}
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
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
                    'message': {'type': 'string', 'example': '层级团队创建成功'},
                    'data': {'type': 'object', 'description': '创建的层级团队完整信息'}
                }
            }
        },
        400: {
            'description': '请求无效',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean', 'example': False},
                    'error': {'type': 'string', 'example': '层级团队名称已存在'},
                    'code': {'type': 'integer', 'example': 400001, 'description': '错误码，400001=agent_id 重复'}
                }
            }
        }
    }
})
def create_hierarchy():
    """创建层级团队"""
    try:
        data = request.get_json() or {}
        req = HierarchyCreateRequest(**data)

        repo = get_repo()

        # 检查名称是否重复
        if repo.get_by_name(req.name):
            return jsonify({'success': False, 'error': f'层级团队名称 "{req.name}" 已存在'}), 400

        # 构建 config JSON
        config = {
            'execution_mode': req.execution_mode,
            'enable_context_sharing': req.enable_context_sharing,
            'global_supervisor_agent': req.global_supervisor_agent.model_dump(),
            'teams': [team.model_dump() for team in req.teams]
        }

        # 验证 agent_id 唯一性
        is_unique, duplicate_id = check_agent_ids_unique_in_hierarchy(config)
        if not is_unique:
            return jsonify({
                'success': False,
                'error': f"agent_id '{duplicate_id}' is duplicated within this hierarchy",
                'code': 400001
            }), 400

        # 创建 Hierarchy
        hierarchy = repo.create(
            name=req.name,
            description=req.description,
            config=config
        )

        return jsonify({
            'success': True,
            'message': '层级团队创建成功',
            'data': hierarchy.to_dict()
        })
    except ValidationError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@hierarchies_bp.route('/update', methods=['POST'])
@swag_from({
    'tags': ['Hierarchies'],
    'summary': '更新层级团队',
    'description': '''更新层级团队配置。支持部分更新，只传入需要修改的字段即可。

## 更新规则

- `name`: 修改名称时会检查唯一性
- `global_supervisor_agent`: 完整替换 Global Supervisor 配置
- `teams`: 完整替换所有团队配置（不支持增量更新）
- `is_active`: 可用于停用/启用层级团队

## agent_id 验证

更新 `global_supervisor_agent` 或 `teams` 时，会重新验证所有 `agent_id` 的唯一性。
''',
    'parameters': [{
        'name': 'body',
        'in': 'body',
        'required': True,
        'schema': {
            'type': 'object',
            'required': ['id'],
            'properties': {
                'id': {'type': 'string', 'description': '层级团队唯一标识 (UUID)'},
                'name': {'type': 'string', 'description': '新的层级团队名称'},
                'description': {'type': 'string', 'description': '新的描述信息'},
                'execution_mode': {'type': 'string', 'enum': ['sequential', 'parallel'], 'description': '团队执行模式'},
                'enable_context_sharing': {'type': 'boolean', 'description': '是否启用跨团队上下文共享'},
                'global_supervisor_agent': {'type': 'object', 'description': '完整的 Global Supervisor 配置（完整替换）'},
                'teams': {'type': 'array', 'description': '完整的团队配置列表（完整替换）'},
                'is_active': {'type': 'boolean', 'description': '是否激活，false=停用'}
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
                    'message': {'type': 'string', 'example': '层级团队更新成功'},
                    'data': {'type': 'object', 'description': '更新后的层级团队完整信息'}
                }
            }
        },
        400: {'description': '请求无效（名称重复或 agent_id 重复）'},
        404: {'description': '层级团队不存在'}
    }
})
def update_hierarchy():
    """更新层级团队"""
    try:
        data = request.get_json() or {}
        req = HierarchyUpdateRequest(**data)

        repo = get_repo()

        # 检查名称是否与其他层级重复
        if req.name:
            existing = repo.get_by_name(req.name)
            if existing and existing.id != req.id:
                return jsonify({'success': False, 'error': f'层级团队名称 "{req.name}" 已存在'}), 400

        # 构建更新数据
        update_data = {}
        if req.name:
            update_data['name'] = req.name
        if req.description is not None:
            update_data['description'] = req.description
        if req.is_active is not None:
            update_data['is_active'] = req.is_active

        # 如果有配置更新，构建新的 config
        if req.global_supervisor_agent or req.teams or req.execution_mode or req.enable_context_sharing is not None:
            # 获取现有配置
            hierarchy = repo.get_by_id(req.id)
            if not hierarchy:
                return jsonify({'success': False, 'error': '层级团队不存在'}), 404

            config = hierarchy.config.copy() if hierarchy.config else {}

            if req.execution_mode:
                config['execution_mode'] = req.execution_mode
            if req.enable_context_sharing is not None:
                config['enable_context_sharing'] = req.enable_context_sharing
            if req.global_supervisor_agent:
                config['global_supervisor_agent'] = req.global_supervisor_agent.model_dump()
            if req.teams:
                config['teams'] = [team.model_dump() for team in req.teams]

            # 验证 agent_id 唯一性
            is_unique, duplicate_id = check_agent_ids_unique_in_hierarchy(config)
            if not is_unique:
                return jsonify({
                    'success': False,
                    'error': f"agent_id '{duplicate_id}' is duplicated within this hierarchy",
                    'code': 400001
                }), 400

            update_data['config'] = config

        hierarchy = repo.update(req.id, update_data)

        if not hierarchy:
            return jsonify({'success': False, 'error': '层级团队不存在'}), 404

        return jsonify({
            'success': True,
            'message': '层级团队更新成功',
            'data': hierarchy.to_dict()
        })
    except ValidationError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@hierarchies_bp.route('/delete', methods=['POST'])
@swag_from({
    'tags': ['Hierarchies'],
    'summary': '删除层级团队',
    'description': '''永久删除指定的层级团队配置。

**注意**: 此操作不可逆，删除后无法恢复。建议在删除前先将 `is_active` 设为 `false` 进行停用。
''',
    'parameters': [{
        'name': 'body',
        'in': 'body',
        'required': True,
        'schema': {
            'type': 'object',
            'required': ['id'],
            'properties': {
                'id': {'type': 'string', 'description': '层级团队唯一标识 (UUID)'}
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
                    'message': {'type': 'string', 'example': '层级团队删除成功'}
                }
            }
        },
        404: {'description': '层级团队不存在'}
    }
})
def delete_hierarchy():
    """删除层级团队"""
    try:
        data = request.get_json() or {}
        req = IdRequest(**data)

        repo = get_repo()
        success = repo.delete(req.id)

        if not success:
            return jsonify({'success': False, 'error': '层级团队不存在'}), 404

        return jsonify({
            'success': True,
            'message': '层级团队删除成功'
        })
    except ValidationError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
