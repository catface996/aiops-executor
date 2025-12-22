"""
层级执行器 - 支持事件流式输出的执行器
"""

import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from io import StringIO
import sys

from .hierarchy_system import (
    HierarchyBuilder,
    GlobalSupervisorFactory,
    ExecutionTracker,
    CallTracker
)
from .api_models import (
    HierarchyConfigRequest,
    TopologyInfo,
    StreamEvent,
    EventType,
    ExecutionResponse,
    ExecutionMode
)
from strands_tools import calculator, http_request


class EventCapture:
    """
    事件捕获器 - 捕获执行过程中的事件
    
    通过重定向标准输出来捕获打印的事件信息，并转换为结构化的事件对象。
    """
    
    def __init__(self):
        self.events: List[StreamEvent] = []
        self.original_stdout = None
        self.captured_output = StringIO()
        
    def start_capture(self):
        """开始捕获输出"""
        self.original_stdout = sys.stdout
        sys.stdout = self.captured_output
        
    def stop_capture(self):
        """停止捕获输出"""
        if self.original_stdout:
            sys.stdout = self.original_stdout
            
    def add_event(self, event_type: EventType, data: Dict[str, Any], 
                  topology_metadata: Optional[Dict[str, str]] = None):
        """
        添加事件
        
        Args:
            event_type: 事件类型
            data: 事件数据
            topology_metadata: 拓扑元数据（team_id, supervisor_id, worker_id）
        """
        event = StreamEvent(
            event_type=event_type,
            timestamp=datetime.now().isoformat(),
            data=data,
            topology_metadata=topology_metadata
        )
        self.events.append(event)
        
    def get_events(self) -> List[StreamEvent]:
        """获取所有捕获的事件"""
        return self.events


class HierarchyExecutor:
    """
    层级执行器 - 动态创建和执行层级多智能体系统
    
    负责：
    1. 根据配置创建层级拓扑
    2. 执行任务
    3. 捕获和返回执行事件流
    4. 提供拓扑信息
    """
    
    # 工具映射表
    TOOL_MAP = {
        'calculator': calculator,
        'http_request': http_request
    }
    
    def __init__(self):
        self.event_capture = EventCapture()
        self.topology_info: Optional[TopologyInfo] = None
        self.builder: Optional[HierarchyBuilder] = None
        self.tracker: Optional[CallTracker] = None
        
    def _resolve_tools(self, tool_names: List[str]) -> List[Any]:
        """
        解析工具名称为实际工具对象
        
        Args:
            tool_names: 工具名称列表
            
        Returns:
            工具对象列表
        """
        tools = []
        for name in tool_names:
            if name in self.TOOL_MAP:
                tools.append(self.TOOL_MAP[name])
        return tools
    
    def _build_topology(self, config: HierarchyConfigRequest) -> tuple:
        """
        构建层级拓扑
        
        Args:
            config: 层级配置请求
            
        Returns:
            (agent, tracker, team_names)
        """
        # 确定是否并行执行
        parallel_execution = config.execution_mode == ExecutionMode.PARALLEL
        
        # 创建构建器
        self.builder = HierarchyBuilder(
            enable_tracking=True,
            enable_context_sharing=config.enable_context_sharing,
            parallel_execution=parallel_execution
        )
        
        # 设置全局提示词
        self.builder.set_global_prompt(config.global_prompt)
        
        # 添加所有团队
        for team_config in config.teams:
            # 转换 Worker 配置
            workers = []
            for worker in team_config.workers:
                worker_dict = {
                    'name': worker.name,
                    'role': worker.role,
                    'system_prompt': worker.system_prompt,
                    'id': worker.id or str(uuid.uuid4()),
                    'tools': self._resolve_tools(worker.tools),
                    'temperature': worker.temperature,
                    'max_tokens': worker.max_tokens
                }
                workers.append(worker_dict)
            
            # 添加团队
            self.builder.add_team(
                name=team_config.name,
                supervisor_prompt=team_config.supervisor_prompt,
                workers=workers,
                prevent_duplicate=team_config.prevent_duplicate,
                share_context=team_config.share_context
            )
        
        # 构建系统
        agent, tracker, team_names = self.builder.build()
        self.tracker = tracker
        
        return agent, tracker, team_names
    
    def _create_topology_info(self, team_names: List[str]) -> TopologyInfo:
        """
        创建拓扑信息
        
        Args:
            team_names: 团队名称列表
            
        Returns:
            TopologyInfo 对象
        """
        global_id = self.builder.teams[0].id if self.builder.teams else str(uuid.uuid4())
        
        teams_info = []
        for team_config in self.builder.teams:
            workers_info = [
                {
                    'worker_id': w.id,
                    'worker_name': w.name,
                    'role': w.role
                }
                for w in team_config.workers
            ]
            
            team_info = {
                'team_id': team_config.id,
                'team_name': team_config.name,
                'supervisor_id': f"supervisor_{team_config.id}",
                'workers': workers_info
            }
            teams_info.append(team_info)
        
        return TopologyInfo(
            global_supervisor_id=f"global_{global_id}",
            teams=teams_info
        )
    
    def _create_execution_events(self, tracker: CallTracker) -> List[StreamEvent]:
        """
        从调用追踪器创建执行事件
        
        Args:
            tracker: 调用追踪器
            
        Returns:
            事件列表
        """
        events = []
        
        # 添加拓扑创建事件
        events.append(StreamEvent(
            event_type=EventType.TOPOLOGY_CREATED,
            timestamp=datetime.now().isoformat(),
            data={'topology': self.topology_info.to_dict()},
            topology_metadata=None
        ))
        
        # 从调用历史创建事件
        for call in tracker.call_history:
            team_id = None
            supervisor_id = None
            
            # 查找团队 ID
            for team_info in self.topology_info.teams:
                if team_info['team_name'] == call['team_name']:
                    team_id = team_info['team_id']
                    supervisor_id = team_info['supervisor_id']
                    break
            
            # 添加团队开始事件
            events.append(StreamEvent(
                event_type=EventType.TEAM_STARTED,
                timestamp=call['start_time'],
                data={
                    'team_name': call['team_name'],
                    'task': call['task']
                },
                topology_metadata={
                    'team_id': team_id,
                    'supervisor_id': supervisor_id
                }
            ))
            
            # 如果已完成，添加完成事件
            if call['status'] == 'completed':
                events.append(StreamEvent(
                    event_type=EventType.TEAM_COMPLETED,
                    timestamp=call.get('end_time', datetime.now().isoformat()),
                    data={
                        'team_name': call['team_name'],
                        'result_preview': call.get('result', '')[:200]
                    },
                    topology_metadata={
                        'team_id': team_id,
                        'supervisor_id': supervisor_id
                    }
                ))
        
        # 添加 Worker 执行事件
        for worker_name, result in tracker.execution_tracker.worker_results.items():
            # 查找 Worker 的团队和 ID
            worker_id = None
            team_id = None
            supervisor_id = None
            
            for team_info in self.topology_info.teams:
                for worker_info in team_info['workers']:
                    if worker_info['worker_name'] == worker_name:
                        worker_id = worker_info['worker_id']
                        team_id = team_info['team_id']
                        supervisor_id = team_info['supervisor_id']
                        break
                if worker_id:
                    break
            
            events.append(StreamEvent(
                event_type=EventType.WORKER_COMPLETED,
                timestamp=datetime.now().isoformat(),
                data={
                    'worker_name': worker_name,
                    'result_preview': result[:200] if result else ''
                },
                topology_metadata={
                    'team_id': team_id,
                    'supervisor_id': supervisor_id,
                    'worker_id': worker_id
                }
            ))
        
        return events
    
    def execute(self, config: HierarchyConfigRequest) -> ExecutionResponse:
        """
        执行层级多智能体系统
        
        Args:
            config: 层级配置请求
            
        Returns:
            ExecutionResponse 包含拓扑信息、事件流和执行结果
        """
        try:
            # 1. 构建拓扑
            agent, tracker, team_names = self._build_topology(config)
            
            # 2. 创建拓扑信息
            self.topology_info = self._create_topology_info(team_names)
            
            # 3. 添加拓扑创建事件
            self.event_capture.add_event(
                EventType.TOPOLOGY_CREATED,
                {'topology': self.topology_info.to_dict()}
            )
            
            # 4. 添加执行开始事件
            self.event_capture.add_event(
                EventType.EXECUTION_STARTED,
                {'task': config.task}
            )
            
            # 5. 执行任务
            result = GlobalSupervisorFactory.stream_global_supervisor(
                agent, 
                config.task, 
                tracker, 
                team_names
            )
            
            # 6. 从追踪器创建执行事件
            execution_events = self._create_execution_events(tracker)
            
            # 7. 添加执行完成事件
            self.event_capture.add_event(
                EventType.EXECUTION_COMPLETED,
                {'result_preview': result[:500] if result else ''}
            )
            
            # 8. 获取统计信息
            statistics = tracker.get_statistics() if tracker else None
            
            # 9. 合并所有事件
            all_events = execution_events + self.event_capture.get_events()
            
            # 10. 返回响应
            return ExecutionResponse(
                success=True,
                topology=self.topology_info,
                events=all_events,
                result=result,
                error=None,
                statistics=statistics
            )
            
        except Exception as e:
            # 错误处理
            error_msg = str(e)
            self.event_capture.add_event(
                EventType.ERROR,
                {'error': error_msg}
            )
            
            return ExecutionResponse(
                success=False,
                topology=self.topology_info or TopologyInfo(
                    global_supervisor_id='error',
                    teams=[]
                ),
                events=self.event_capture.get_events(),
                result=None,
                error=error_msg,
                statistics=None
            )


# ============================================================================
# 便捷函数
# ============================================================================

def execute_hierarchy(config_dict: Dict[str, Any]) -> ExecutionResponse:
    """
    从字典配置执行层级系统
    
    Args:
        config_dict: 配置字典
        
    Returns:
        ExecutionResponse
    """
    from .api_models import parse_hierarchy_config
    
    config = parse_hierarchy_config(config_dict)
    executor = HierarchyExecutor()
    return executor.execute(config)
