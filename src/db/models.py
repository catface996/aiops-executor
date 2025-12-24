"""
Database Models - SQLAlchemy 数据库模型定义
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import List, Optional

from sqlalchemy import (
    Column, String, Float, Integer, BigInteger, Boolean, DateTime,
    Text, JSON, ForeignKey, Enum as SQLEnum
)
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


def generate_uuid() -> str:
    """生成 UUID 字符串"""
    return str(uuid.uuid4())


class RunStatus(str, Enum):
    """运行状态枚举"""
    PENDING = 'pending'
    RUNNING = 'running'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'


class AIModel(Base):
    """AI 模型配置"""
    __tablename__ = 'ai_models'

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(100), nullable=False, unique=True, comment='模型显示名称')
    model_id = Column(String(200), nullable=False, comment='AWS Bedrock 模型 ID')
    region = Column(String(50), default='us-east-1', comment='AWS 区域')

    # 模型参数
    temperature = Column(Float, default=0.7, comment='温度参数')
    max_tokens = Column(Integer, default=2048, comment='最大 token 数')
    top_p = Column(Float, default=0.9, comment='Top-P 参数')

    # 元数据
    description = Column(Text, nullable=True, comment='模型描述')
    is_active = Column(Boolean, default=True, comment='是否激活')

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'id': self.id,
            'name': self.name,
            'model_id': self.model_id,
            'region': self.region,
            'temperature': self.temperature,
            'max_tokens': self.max_tokens,
            'top_p': self.top_p,
            'description': self.description,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class HierarchyTeam(Base):
    """层级团队配置 - 主表"""
    __tablename__ = 'hierarchy_teams'

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(100), nullable=False, unique=True, comment='层级团队名称')
    description = Column(Text, nullable=True, comment='描述')

    # 全局配置
    global_prompt = Column(Text, nullable=False, comment='全局 Supervisor 提示词')
    execution_mode = Column(String(20), default='sequential', comment='执行模式: sequential/parallel')
    enable_context_sharing = Column(Boolean, default=False, comment='是否启用上下文共享')

    # Global Supervisor LLM 配置
    global_model_id = Column(String(36), ForeignKey('ai_models.id'), nullable=True)
    global_temperature = Column(Float, default=0.7, comment='Global Supervisor 温度参数')
    global_max_tokens = Column(Integer, default=2048, comment='Global Supervisor 最大 token 数')
    global_top_p = Column(Float, default=0.9, comment='Global Supervisor Top-P 参数')

    # 元数据
    is_active = Column(Boolean, default=True)
    version = Column(Integer, default=1)

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    global_model = relationship("AIModel", foreign_keys=[global_model_id])
    teams = relationship("Team", back_populates="hierarchy", cascade="all, delete-orphan",
                        order_by="Team.order_index")

    def to_dict(self, include_teams: bool = True) -> dict:
        """转换为字典"""
        result = {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'global_prompt': self.global_prompt,
            'execution_mode': self.execution_mode,
            'enable_context_sharing': self.enable_context_sharing,
            'llm_config': {
                'model_id': self.global_model_id,
                'temperature': self.global_temperature,
                'max_tokens': self.global_max_tokens,
                'top_p': self.global_top_p,
            },
            'is_active': self.is_active,
            'version': self.version,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_teams:
            result['teams'] = [team.to_dict() for team in self.teams]
        return result

    def to_execution_config(self) -> dict:
        """转换为执行配置格式（兼容现有 execute_hierarchy）"""
        return {
            'global_prompt': self.global_prompt,
            'execution_mode': self.execution_mode,
            'enable_context_sharing': self.enable_context_sharing,
            'teams': [team.to_execution_config() for team in self.teams]
        }


class Team(Base):
    """团队配置"""
    __tablename__ = 'teams'

    id = Column(String(36), primary_key=True, default=generate_uuid)
    hierarchy_id = Column(String(36), ForeignKey('hierarchy_teams.id'), nullable=False)

    name = Column(String(100), nullable=False, comment='团队名称')
    supervisor_prompt = Column(Text, nullable=False, comment='团队 Supervisor 提示词')

    # 团队配置
    prevent_duplicate = Column(Boolean, default=True, comment='防止重复调用')
    share_context = Column(Boolean, default=False, comment='共享上下文')
    order_index = Column(Integer, default=0, comment='团队顺序')

    # Team Supervisor LLM 配置
    model_id = Column(String(36), ForeignKey('ai_models.id'), nullable=True)
    temperature = Column(Float, default=0.7, comment='Team Supervisor 温度参数')
    max_tokens = Column(Integer, default=2048, comment='Team Supervisor 最大 token 数')
    top_p = Column(Float, default=0.9, comment='Team Supervisor Top-P 参数')

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    hierarchy = relationship("HierarchyTeam", back_populates="teams")
    model = relationship("AIModel", foreign_keys=[model_id])
    workers = relationship("Worker", back_populates="team", cascade="all, delete-orphan",
                          order_by="Worker.order_index")

    def to_dict(self, include_workers: bool = True) -> dict:
        """转换为字典"""
        result = {
            'id': self.id,
            'hierarchy_id': self.hierarchy_id,
            'name': self.name,
            'supervisor_prompt': self.supervisor_prompt,
            'prevent_duplicate': self.prevent_duplicate,
            'share_context': self.share_context,
            'order_index': self.order_index,
            'llm_config': {
                'model_id': self.model_id,
                'temperature': self.temperature,
                'max_tokens': self.max_tokens,
                'top_p': self.top_p,
            },
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_workers:
            result['workers'] = [worker.to_dict() for worker in self.workers]
        return result

    def to_execution_config(self) -> dict:
        """转换为执行配置格式"""
        return {
            'name': self.name,
            'supervisor_prompt': self.supervisor_prompt,
            'prevent_duplicate': self.prevent_duplicate,
            'share_context': self.share_context,
            'workers': [worker.to_execution_config() for worker in self.workers]
        }


class Worker(Base):
    """Worker Agent 配置"""
    __tablename__ = 'workers'

    id = Column(String(36), primary_key=True, default=generate_uuid)
    team_id = Column(String(36), ForeignKey('teams.id'), nullable=False)

    name = Column(String(100), nullable=False, comment='Worker 名称')
    role = Column(String(200), nullable=False, comment='角色描述')
    system_prompt = Column(Text, nullable=False, comment='系统提示词')

    # Worker 参数
    tools = Column(JSON, default=list, comment='工具列表')
    order_index = Column(Integer, default=0, comment='Worker 顺序')

    # Worker LLM 配置
    model_id = Column(String(36), ForeignKey('ai_models.id'), nullable=True)
    temperature = Column(Float, default=0.7, comment='Worker 温度参数')
    max_tokens = Column(Integer, default=2048, comment='Worker 最大 token 数')
    top_p = Column(Float, default=0.9, comment='Worker Top-P 参数')

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    team = relationship("Team", back_populates="workers")
    model = relationship("AIModel", foreign_keys=[model_id])

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'id': self.id,
            'team_id': self.team_id,
            'name': self.name,
            'role': self.role,
            'system_prompt': self.system_prompt,
            'tools': self.tools or [],
            'order_index': self.order_index,
            'llm_config': {
                'model_id': self.model_id,
                'temperature': self.temperature,
                'max_tokens': self.max_tokens,
                'top_p': self.top_p,
            },
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def to_execution_config(self) -> dict:
        """转换为执行配置格式"""
        return {
            'name': self.name,
            'role': self.role,
            'system_prompt': self.system_prompt,
            'tools': self.tools or [],
            'temperature': self.temperature,
            'max_tokens': self.max_tokens,
        }


class ExecutionRun(Base):
    """执行运行记录"""
    __tablename__ = 'execution_runs'

    id = Column(String(36), primary_key=True, default=generate_uuid)
    hierarchy_id = Column(String(36), ForeignKey('hierarchy_teams.id'), nullable=False)

    # 任务信息
    task = Column(Text, nullable=False, comment='任务描述')
    status = Column(String(20), default=RunStatus.PENDING.value, comment='运行状态')

    # 执行结果
    result = Column(Text, nullable=True, comment='执行结果')
    error = Column(Text, nullable=True, comment='错误信息')
    statistics = Column(JSON, nullable=True, comment='执行统计')

    # 拓扑信息快照
    topology_snapshot = Column(JSON, nullable=True, comment='拓扑快照')

    # 时间戳
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    hierarchy = relationship("HierarchyTeam")
    events = relationship("ExecutionEvent", back_populates="run", cascade="all, delete-orphan",
                         order_by="ExecutionEvent.timestamp")

    def to_dict(self, include_events: bool = False) -> dict:
        """转换为字典"""
        result = {
            'id': self.id,
            'hierarchy_id': self.hierarchy_id,
            'task': self.task,
            'status': self.status,
            'result': self.result,
            'error': self.error,
            'statistics': self.statistics,
            'topology_snapshot': self.topology_snapshot,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
        if include_events:
            result['events'] = [event.to_dict() for event in self.events]
        return result


class ExecutionEvent(Base):
    """执行事件记录"""
    __tablename__ = 'execution_events'

    id = Column(String(36), primary_key=True, default=generate_uuid)
    run_id = Column(String(36), ForeignKey('execution_runs.id'), nullable=False)

    # 事件信息
    event_type = Column(String(50), nullable=False, comment='事件类型')
    timestamp = Column(DateTime, default=datetime.utcnow)
    sequence = Column(BigInteger, nullable=False, default=0, comment='序列号，用于同一秒内事件排序')
    data = Column(JSON, nullable=True, comment='事件数据')

    # 来源标识
    is_global_supervisor = Column(Boolean, default=False, comment='是否为 Global Supervisor 输出')
    team_name = Column(String(100), nullable=True, comment='团队名称')
    is_team_supervisor = Column(Boolean, default=False, comment='是否为 Team Supervisor 输出')
    worker_name = Column(String(100), nullable=True, comment='Worker 名称')

    # 关系
    run = relationship("ExecutionRun", back_populates="events")

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'id': self.id,
            'run_id': self.run_id,
            'event_type': self.event_type,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'sequence': self.sequence,
            'data': self.data,
            'is_global_supervisor': self.is_global_supervisor,
            'team_name': self.team_name,
            'is_team_supervisor': self.is_team_supervisor,
            'worker_name': self.worker_name,
        }
