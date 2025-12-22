"""
动态层级团队系统 (Dynamic Hierarchical Team System)

通过配置文件动态构建多智能体团队，带调用追踪和防重复机制。

核心特性:
- 通用的 Global Supervisor、Team Supervisor 和 Worker Agent
- 配置驱动的拓扑结构
- 动态指定系统提示词、工具、模型
- 调用追踪：记录每个团队的调用历史
- 防重复调用：自动检测并阻止重复调用
- 调用统计：提供详细的调用次数和状态信息
"""

import hashlib
import re
import types
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable, Set
from dataclasses import dataclass, field

from strands import Agent, tool
from strands_tools import calculator, http_request
from .output_formatter import (
    print_worker_start, print_worker_thinking, print_worker_complete,
    print_worker_warning, print_worker_error,
    print_team_start, print_team_thinking, print_team_complete, print_team_summary,
    print_team_warning, print_team_error, print_team_duplicate_warning,
    print_global_start, print_global_thinking, print_global_dispatch,
    print_global_summary, print_global_complete,
    set_current_team, OutputFormatter
)


# ============================================================================
# 调用追踪系统
# ============================================================================

class ExecutionTracker:
    """
    执行追踪器 - 跟踪已执行的 Team 和 Worker
    
    用于防止重复执行和获取执行结果。
    """
    
    def __init__(self):
        """初始化执行追踪器"""
        # 已执行的团队名称集合
        self.executed_teams: Set[str] = set()
        # 已执行的 Worker 名称集合
        self.executed_workers: Set[str] = set()
        # 团队执行结果字典
        self.team_results: Dict[str, str] = {}
        # Worker 执行结果字典
        self.worker_results: Dict[str, str] = {}
    
    def mark_team_executed(self, team_name: str, result: str):
        """
        标记团队已执行
        
        Args:
            team_name: 团队名称
            result: 执行结果
        """
        self.executed_teams.add(team_name)
        self.team_results[team_name] = result
    
    def mark_worker_executed(self, worker_name: str, result: str):
        """
        标记 Worker 已执行
        
        Args:
            worker_name: Worker 名称
            result: 执行结果
        """
        self.executed_workers.add(worker_name)
        self.worker_results[worker_name] = result
    
    def is_team_executed(self, team_name: str) -> bool:
        """
        检查团队是否已执行
        
        Args:
            team_name: 团队名称
            
        Returns:
            True 如果已执行，否则 False
        """
        return team_name in self.executed_teams
    
    def is_worker_executed(self, worker_name: str) -> bool:
        """
        检查 Worker 是否已执行
        
        Args:
            worker_name: Worker 名称
            
        Returns:
            True 如果已执行，否则 False
        """
        return worker_name in self.executed_workers
    
    def get_team_result(self, team_name: str) -> Optional[str]:
        """
        获取团队的执行结果
        
        Args:
            team_name: 团队名称
            
        Returns:
            执行结果字符串，如果未执行则返回 None
        """
        return self.team_results.get(team_name)
    
    def get_worker_result(self, worker_name: str) -> Optional[str]:
        """
        获取 Worker 的执行结果
        
        Args:
            worker_name: Worker 名称
            
        Returns:
            执行结果字符串，如果未执行则返回 None
        """
        return self.worker_results.get(worker_name)
    
    def get_execution_status(self, available_teams: List[str] = None, available_workers: List[str] = None) -> str:
        """
        获取执行状态摘要
        
        生成格式化的执行状态报告，显示哪些团队/Worker 已执行，哪些未执行。
        
        Args:
            available_teams: 可用的团队名称列表
            available_workers: 可用的 Worker 名称列表
            
        Returns:
            格式化的执行状态字符串
        """
        status_lines = []
        
        # 生成团队执行状态
        if available_teams:
            status_lines.append("【团队执行状态】")
            for team in available_teams:
                if team in self.executed_teams:
                    status_lines.append(f"  ✅ {team} - 已执行")
                else:
                    status_lines.append(f"  ⭕ {team} - 未执行")
        
        # 生成 Worker 执行状态
        if available_workers:
            status_lines.append("\n【成员执行状态】")
            for worker in available_workers:
                if worker in self.executed_workers:
                    status_lines.append(f"  ✅ {worker} - 已执行")
                else:
                    status_lines.append(f"  ⭕ {worker} - 未执行")
        
        return "\n".join(status_lines)
    
    def reset(self):
        """重置追踪器，清空所有执行记录"""
        self.executed_teams.clear()
        self.executed_workers.clear()
        self.team_results.clear()
        self.worker_results.clear()


class CallTracker:
    """
    调用追踪器 - 记录和管理 Agent 调用
    
    跟踪团队调用的历史记录、调用次数和活跃状态。
    """
    
    def __init__(self):
        """初始化调用追踪器"""
        # 调用历史记录列表
        self.call_history: List[Dict[str, Any]] = []
        # 每个团队的调用次数
        self.team_calls: Dict[str, int] = {}
        # 当前正在执行的团队集合
        self.active_teams: Set[str] = set()
        # 执行追踪器实例
        self.execution_tracker = ExecutionTracker()
    
    def start_call(self, team_name: str, task: str) -> str:
        """
        开始一次调用
        
        记录调用开始时间和状态，生成唯一的调用 ID。
        
        Args:
            team_name: 团队名称
            task: 任务描述
            
        Returns:
            调用 ID（格式：团队名_序号）
        """
        # 生成唯一的调用 ID
        call_id = f"{team_name}_{len(self.call_history)}"
        
        # 记录调用信息
        self.call_history.append({
            'call_id': call_id,
            'team_name': team_name,
            'task': task,
            'start_time': datetime.now().isoformat(),
            'status': 'in_progress'
        })
        
        # 更新调用次数
        self.team_calls[team_name] = self.team_calls.get(team_name, 0) + 1
        # 标记团队为活跃状态
        self.active_teams.add(team_name)
        
        return call_id
    
    def end_call(self, call_id: str, result: str):
        """
        结束一次调用
        
        记录调用结束时间和结果，更新状态。
        
        Args:
            call_id: 调用 ID
            result: 执行结果
        """
        # 查找对应的调用记录
        for call in self.call_history:
            if call['call_id'] == call_id:
                # 更新调用记录
                call['end_time'] = datetime.now().isoformat()
                call['result'] = result
                call['status'] = 'completed'
                
                # 从活跃团队中移除
                team_name = call['team_name']
                if team_name in self.active_teams:
                    self.active_teams.remove(team_name)
                break
    
    def is_team_active(self, team_name: str) -> bool:
        """
        检查团队是否正在处理任务
        
        Args:
            team_name: 团队名称
            
        Returns:
            True 如果团队正在执行任务，否则 False
        """
        return team_name in self.active_teams
    
    def get_team_call_count(self, team_name: str) -> int:
        """
        获取团队的调用次数
        
        Args:
            team_name: 团队名称
            
        Returns:
            调用次数
        """
        return self.team_calls.get(team_name, 0)
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取调用统计信息
        
        Returns:
            包含总调用次数、各团队调用次数、活跃团队和完成调用数的字典
        """
        return {
            'total_calls': len(self.call_history),
            'team_calls': self.team_calls.copy(),
            'active_teams': list(self.active_teams),
            'completed_calls': sum(1 for c in self.call_history if c['status'] == 'completed')
        }
    
    def get_call_log(self) -> str:
        """
        获取格式化的调用日志
        
        生成包含所有调用记录的格式化字符串。
        
        Returns:
            格式化的调用日志字符串
        """
        log_lines = ["调用日志:", "=" * 60]
        for call in self.call_history:
            log_lines.append(f"\n[{call['call_id']}]")
            log_lines.append(f"  团队: {call['team_name']}")
            log_lines.append(f"  任务: {call['task'][:50]}...")
            log_lines.append(f"  状态: {call['status']}")
            if 'result' in call:
                log_lines.append(f"  结果: {call['result'][:100]}...")
        return "\n".join(log_lines)


# ============================================================================
# 配置数据结构
# ============================================================================

@dataclass
class WorkerConfig:
    """Worker Agent 配置"""
    name: str
    role: str
    system_prompt: str
    id: str
    tools: List[Any] = field(default_factory=list)
    model: Optional[Any] = None
    temperature: float = 0.7
    max_tokens: int = 2048


@dataclass
class TeamConfig:
    """Team 配置"""
    name: str
    supervisor_prompt: str
    workers: List[WorkerConfig]
    id: str
    model: Optional[Any] = None
    prevent_duplicate: bool = True
    share_context: bool = False  # 是否接收其他团队的上下文


@dataclass
class GlobalConfig:
    """Global Supervisor 配置"""
    system_prompt: str
    teams: List[TeamConfig]
    id: str
    model: Optional[Any] = None
    enable_tracking: bool = True
    enable_context_sharing: bool = False  # 全局开关：是否启用跨团队上下文共享
    parallel_execution: bool = False  # 团队执行模式：False=顺序执行，True=并行执行


# ============================================================================
# Worker Agent 工厂
# ============================================================================

class WorkerAgentFactory:
    """
    Worker Agent 工厂 - 动态创建 Worker Agent
    
    负责创建 Worker Agent 实例，并管理 Worker 的调用追踪和防重复机制。
    """
    
    # 类级别的调用追踪器（记录任务哈希 -> 结果）
    _worker_call_tracker = {}
    # 类级别的执行追踪器引用
    _execution_tracker: Optional['ExecutionTracker'] = None
    
    @staticmethod
    def set_execution_tracker(tracker: 'ExecutionTracker'):
        """
        设置执行追踪器
        
        Args:
            tracker: ExecutionTracker 实例
        """
        WorkerAgentFactory._execution_tracker = tracker
    
    @staticmethod
    def _check_worker_executed(config: WorkerConfig) -> Optional[str]:
        """
        检查 Worker 是否已执行
        
        如果 Worker 已经执行过，返回提示消息；否则返回 None。
        
        Args:
            config: Worker 配置
            
        Returns:
            提示消息字符串或 None
        """
        if WorkerAgentFactory._execution_tracker and WorkerAgentFactory._execution_tracker.is_worker_executed(config.name):
            print_worker_warning(f"⚠️ [{config.name}] 该专家已经执行过，请直接使用之前的结果，不要重复调用")
            return OutputFormatter.format_executed_message(config.name)
        return None
    
    @staticmethod
    def _check_duplicate_task(config: WorkerConfig, task: str) -> Optional[str]:
        """
        检查是否重复任务
        
        基于任务内容的哈希值检查是否已经处理过相同任务。
        
        Args:
            config: Worker 配置
            task: 任务描述
            
        Returns:
            如果是重复任务，返回提示消息；否则返回 call_key
        """
        # 生成任务哈希值（前8位）
        task_hash = hashlib.md5(task.encode('utf-8')).hexdigest()[:8]
        call_key = f"{config.name}_{task_hash}"
        
        # 检查是否已处理过相同任务
        if call_key in WorkerAgentFactory._worker_call_tracker:
            OutputFormatter.print_worker_duplicate_task_warning(config.name)
            return OutputFormatter.format_duplicate_task_message(config.name)
        return call_key
    
    @staticmethod
    def _execute_worker(config: WorkerConfig, task: str, call_key: str) -> str:
        """
        执行 Worker 任务
        
        创建 Agent 实例并执行任务，记录执行结果。
        
        Args:
            config: Worker 配置
            task: 任务描述
            call_key: 调用标识符
            
        Returns:
            执行结果字符串
        """
        # 打印开始信息
        print_worker_start(config.name, task)
        print_worker_thinking(config.name)
        
        # 创建并执行 Agent
        agent = Agent(
            system_prompt=config.system_prompt,
            tools=config.tools,
            model=config.model,
        )
        response = agent(task)

        # 打印完成信息
        print_worker_complete(config.name)
        # 将 AgentResult 转为字符串
        response_text = str(response) if response else ""
        result = OutputFormatter.format_result_message(config.name, response_text)
        
        # 记录执行结果
        WorkerAgentFactory._worker_call_tracker[call_key] = result
        if WorkerAgentFactory._execution_tracker:
            WorkerAgentFactory._execution_tracker.mark_worker_executed(config.name, result)
        
        return result
    
    @staticmethod
    def create_worker(config: WorkerConfig) -> Callable:
        """
        创建 Worker Agent

        根据配置创建一个 Worker Agent 函数，该函数会：
        1. 检查是否已执行
        2. 检查是否重复任务
        3. 执行任务并返回结果

        Args:
            config: Worker 配置

        Returns:
            Worker Agent 函数（已应用 @tool 装饰器）
        """
        # 生成符合 AWS Bedrock 规范的函数名（使用 worker ID 确保唯一性）
        func_name = f"worker_{config.id.replace('-', '_')}"

        def worker_agent_impl(task: str) -> str:
            # 1. 检查是否已执行
            if executed_msg := WorkerAgentFactory._check_worker_executed(config):
                return executed_msg

            # 2. 检查重复任务
            call_key = WorkerAgentFactory._check_duplicate_task(config, task)
            if isinstance(call_key, str) and call_key.startswith('['):
                return call_key  # 返回重复消息

            # 3. 执行任务
            try:
                return WorkerAgentFactory._execute_worker(config, task, call_key)
            except Exception as e:
                error_msg = f"[{config.name}] 错误: {str(e)}"
                print_worker_error(error_msg)
                return error_msg

        # 创建具有正确名称的函数（在应用 @tool 装饰器之前）
        doc_string = f"调用 {config.name} ({config.role}) 来执行任务"
        worker_agent = types.FunctionType(
            worker_agent_impl.__code__,
            worker_agent_impl.__globals__,
            name=func_name,
            argdefs=worker_agent_impl.__defaults__,
            closure=worker_agent_impl.__closure__
        )
        worker_agent.__doc__ = doc_string

        # 应用 @tool 装饰器
        return tool(worker_agent)
    
    @staticmethod
    def reset_tracker():
        """重置调用追踪器，清空所有调用记录"""
        WorkerAgentFactory._worker_call_tracker.clear()


# ============================================================================
# Team Supervisor 工厂
# ============================================================================

class TeamSupervisorFactory:
    """Team Supervisor 工厂 - 动态创建 Team Supervisor"""
    
    @staticmethod
    def _build_context_sharing_content(
        config: TeamConfig,
        tracker: CallTracker,
        enable_context_sharing: bool
    ) -> List[str]:
        """
        构建跨团队上下文共享内容
        
        Args:
            config: 团队配置
            tracker: 调用追踪器
            enable_context_sharing: 是否启用上下文共享
            
        Returns:
            上下文共享内容列表（可能为空）
        """
        if not enable_context_sharing or not config.share_context:
            return []
        
        other_teams_context = []
        for team_name in tracker.execution_tracker.executed_teams:
            if team_name != config.name:  # 排除自己
                result = tracker.execution_tracker.get_team_result(team_name)
                if result:
                    other_teams_context.append(f"\n【{team_name}的研究成果】：\n{result}")
        
        if other_teams_context:
            return [
                "\n".join(other_teams_context),
                "\n【提示】：以上是其他团队已完成的工作，你可以参考这些成果来完成你的任务。"
            ]
        
        return []
    
    @staticmethod
    def _check_team_executed(config: TeamConfig, tracker: CallTracker) -> Optional[str]:
        """
        检查团队是否已执行
        
        如果团队已经执行过，返回提示消息；否则返回 None。
        
        Args:
            config: 团队配置
            tracker: 调用追踪器
            
        Returns:
            提示消息字符串或 None
        """
        if tracker.execution_tracker.is_team_executed(config.name):
            print_team_warning(f"⚠️ [{config.name}] 该团队已经执行过，请直接使用之前的结果，不要重复调用")
            return OutputFormatter.format_executed_message(config.name)
        return None
    
    @staticmethod
    def _check_team_active(config: TeamConfig, tracker: CallTracker) -> Optional[str]:
        """
        检查团队是否正在执行
        
        如果团队正在执行且启用了防重复机制，返回警告消息；否则返回 None。
        
        Args:
            config: 团队配置
            tracker: 调用追踪器
            
        Returns:
            警告消息字符串或 None
        """
        if config.prevent_duplicate and tracker.is_team_active(config.name):
            message = f"[{config.name}] 警告: 该团队正在处理任务，跳过重复调用"
            print_team_duplicate_warning(message)
            return message
        return None
    
    @staticmethod
    def _build_enhanced_task(
        task: str,
        worker_names: List[str],
        tracker: CallTracker,
        config: TeamConfig,
        enable_context_sharing: bool
    ) -> str:
        """
        构建增强任务内容
        
        将原始任务与执行状态、上下文共享内容和规则组合成增强任务。
        
        Args:
            task: 原始任务描述
            worker_names: Worker 名称列表
            tracker: 调用追踪器
            config: 团队配置
            enable_context_sharing: 是否启用上下文共享
            
        Returns:
            增强后的任务字符串
        """
        # 获取执行状态
        execution_status = tracker.execution_tracker.get_execution_status(available_workers=worker_names)
        enhanced_task_parts = [task, "", execution_status]
        
        # 添加上下文共享内容（如果启用）
        context_sharing_content = TeamSupervisorFactory._build_context_sharing_content(
            config, tracker, enable_context_sharing
        )
        if context_sharing_content:
            enhanced_task_parts.insert(1, context_sharing_content[0])
            enhanced_task_parts.append(context_sharing_content[1])
        
        # 获取团队名称用于标签
        team_name = config.name
        worker_list = ", ".join(worker_names)
        num_workers = len(worker_names)

        # 添加执行规则 - 使用严格的英文约束和循环模式
        enhanced_task_parts.append(f"""
================================================================================
CRITICAL INSTRUCTIONS FOR TEAM SUPERVISOR - NO NEGOTIATION
================================================================================

You are the TEAM SUPERVISOR of [{team_name}].
Your ONLY job is to delegate tasks to your team members (workers).

[ABSOLUTE RULES - VIOLATION IS FORBIDDEN]

1. You must NEVER answer questions directly. NO EXCEPTIONS.
2. You must ALWAYS call worker tools to handle the task.
3. Each worker can ONLY be called ONCE.
4. **CRITICAL: You MUST call EVERY worker ({num_workers} total). Calling only 1 worker is NOT acceptable.**

[YOUR TEAM MEMBERS - YOU MUST CALL ALL {num_workers} OF THEM]
{worker_list}

================================================================================
MANDATORY ITERATIVE WORKFLOW - YOU MUST ITERATE {num_workers} TIMES
================================================================================

You have {num_workers} workers. You MUST iterate {num_workers} times to call each one:

**ITERATION 1:**
  [Team: {team_name} | Supervisor] THINKING: I have {num_workers} workers. First I will call the first worker.
  [Team: {team_name} | Supervisor] SELECT: [First Worker Name]
  Subtask: [specific task for first worker]
  [Call first worker tool...]

**ITERATION 2:**
  [Team: {team_name} | Supervisor] THINKING: First worker completed. Now I must call the second worker.
  [Team: {team_name} | Supervisor] SELECT: [Second Worker Name]
  Subtask: [specific task for second worker]
  [Call second worker tool...]

**... continue until all {num_workers} workers are called ...**

**AFTER ALL {num_workers} WORKERS COMPLETE:**
  [Team: {team_name} | Supervisor] SUMMARY: All {num_workers} workers completed...
  - [First Worker] contributed: ...
  - [Second Worker] contributed: ...
  [Compile and return integrated result]

================================================================================
EXECUTION STATUS
================================================================================
- Workers marked ⭕ = NOT executed yet (you MUST call these)
- Workers marked ✅ = Already completed (do NOT call again)

================================================================================
FAILURE CONDITIONS - YOU WILL FAIL IF:
================================================================================
- You call fewer than {num_workers} workers
- You call the same worker twice
- You answer directly without calling any worker
- You skip any worker marked ⭕

**SUCCESS requires calling ALL {num_workers} workers: {worker_list}**
""")
        
        return "\n".join(enhanced_task_parts)
    
    @staticmethod
    def create_supervisor(config: TeamConfig, tracker: CallTracker, enable_context_sharing: bool = False) -> Callable:
        """
        创建 Team Supervisor
        
        根据配置创建一个 Team Supervisor 函数，该函数会：
        1. 检查团队是否已执行
        2. 检查团队是否正在执行
        3. 协调 Worker 完成任务
        
        Args:
            config: 团队配置
            tracker: 调用追踪器
            enable_context_sharing: 是否启用跨团队上下文共享
            
        Returns:
            Team Supervisor 函数（已应用 @tool 装饰器）
        """
        # 创建 Worker 工具列表
        worker_tools = [WorkerAgentFactory.create_worker(w) for w in config.workers]
        # 生成符合 AWS Bedrock 规范的函数名
        func_name = f"team_{config.id.replace('-', '_')}"
        
        def team_supervisor_impl(task: str) -> str:
            """Team Supervisor 实现函数"""
            # 1. 检查是否已执行
            if executed_msg := TeamSupervisorFactory._check_team_executed(config, tracker):
                return executed_msg
            
            # 2. 检查是否正在执行
            if active_msg := TeamSupervisorFactory._check_team_active(config, tracker):
                return active_msg
            
            # 3. 开始执行
            call_id = tracker.start_call(config.name, task)
            
            try:
                # 4. 准备执行（打印开始信息）
                worker_names = [w.name for w in config.workers]
                print_team_start(config.name, call_id, task, worker_names)
                print_team_thinking(config.name)
                
                # 5. 构建增强任务
                enhanced_task = TeamSupervisorFactory._build_enhanced_task(
                    task, worker_names, tracker, config, enable_context_sharing
                )
                
                # 6. 执行任务
                supervisor = Agent(
                    system_prompt=config.supervisor_prompt,
                    tools=worker_tools,
                    model=config.model,
                    callback_handler=None
                )
                response = supervisor(enhanced_task)

                # 7. 完成执行（记录结果）
                print_team_complete(config.name)
                # 将 AgentResult 转为字符串
                response_text = str(response) if response else ""
                result = OutputFormatter.format_result_message(config.name, response_text)
                tracker.end_call(call_id, result)
                tracker.execution_tracker.mark_team_executed(config.name, result)
                
                return result
                
            except Exception as e:
                # 处理异常
                error_msg = f"[{config.name}] 错误: {str(e)}"
                print_team_error(error_msg)
                tracker.end_call(call_id, error_msg)
                return error_msg
        
        # 创建具有正确名称的函数
        doc_string = f"调用{config.name} - 协调 {len(config.workers)} 名团队成员完成任务"
        team_supervisor = types.FunctionType(
            team_supervisor_impl.__code__,
            team_supervisor_impl.__globals__,
            name=func_name,
            argdefs=team_supervisor_impl.__defaults__,
            closure=team_supervisor_impl.__closure__
        )
        team_supervisor.__doc__ = doc_string
        
        # 应用 @tool 装饰器
        return tool(team_supervisor)


# ============================================================================
# Global Supervisor 工厂
# ============================================================================

class GlobalSupervisorFactory:
    """
    Global Supervisor 工厂 - 动态创建 Global Supervisor
    
    负责创建全局协调者，管理多个团队的协作。
    """
    
    @staticmethod
    def create_global_supervisor(config: GlobalConfig, tracker: CallTracker) -> tuple[Agent, List[str]]:
        """
        创建 Global Supervisor
        
        根据配置创建全局协调者 Agent，负责协调多个团队完成复杂任务。
        
        Args:
            config: 全局配置
            tracker: 调用追踪器
            
        Returns:
            (Global Supervisor Agent, 团队名称列表)
        """
        # 创建所有团队的 Supervisor 工具
        team_tools = [
            TeamSupervisorFactory.create_supervisor(team_config, tracker, config.enable_context_sharing)
            for team_config in config.teams
        ]
        
        # 提取团队名称列表
        team_names = [team.name for team in config.teams]
        
        # Build team list for prompt
        team_list_str = "\n".join([f"  - {team.name}" for team in config.teams])

        # Enhanced system prompt with STRICT English constraints
        execution_mode = "SEQUENTIAL" if not config.parallel_execution else "PARALLEL"

        enhanced_prompt = f"""{config.system_prompt}

================================================================================
CRITICAL INSTRUCTIONS - NO NEGOTIATION - MUST FOLLOW EXACTLY
================================================================================

You are a COORDINATOR/DISPATCHER. Your ONLY job is to delegate tasks to teams.

[ABSOLUTE RULES - VIOLATION IS FORBIDDEN]

1. You must NEVER answer questions directly. NO EXCEPTIONS.
2. You must ALWAYS call team tools to handle the task.
3. Even if the task is unclear, you MUST select the most appropriate team(s).
4. You are NOT allowed to ask clarifying questions - just delegate to teams.
5. You must call ALL available teams - not just one or two.

[EXECUTION MODE: {execution_mode}]

- Each team can ONLY be called ONCE
- Teams marked with ✅ are already completed - do NOT call them again
- Only call teams marked with ⭕ (not executed)

[AVAILABLE TEAMS]
{team_list_str}

================================================================================
MANDATORY ITERATIVE WORKFLOW - CRITICAL
================================================================================

You MUST follow this LOOP pattern until ALL teams have been called:

┌─────────────────────────────────────────────────────────────┐
│  ITERATION LOOP (repeat until all teams are ✅)             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  STEP 1: THINK                                              │
│    - Output: "[Global Supervisor] THINKING: ..."            │
│    - Review current status: which teams are ⭕ vs ✅         │
│    - Decide which ⭕ team to call next                       │
│    - Explain WHY you are selecting this team                │
│                                                             │
│  STEP 2: SELECT (Structured Output)                         │
│    - Output: "[Global Supervisor] SELECT: [Team Name]"      │
│    - State the specific subtask for this team               │
│                                                             │
│  STEP 3: DISPATCH                                           │
│    - Call the team tool with the subtask                    │
│    - Wait for the team to complete                          │
│                                                             │
│  STEP 4: CHECK                                              │
│    - After team completes, check if more ⭕ teams remain    │
│    - If YES: Go back to STEP 1                              │
│    - If NO (all teams are ✅): Proceed to SYNTHESIS          │
│                                                             │
└─────────────────────────────────────────────────────────────┘

AFTER ALL TEAMS COMPLETE:

  STEP 5: SYNTHESIS
    - Output: "[Global Supervisor] SYNTHESIS: All teams completed..."
    - Summarize the contributions from each team
    - Integrate all results into a coherent final answer
    - Present the final result to the user

================================================================================
OUTPUT FORMAT REQUIREMENTS
================================================================================

ALWAYS prefix your outputs with "[Global Supervisor]" so it's clear who is speaking.

Example iteration:
```
[Global Supervisor] THINKING: I have 2 teams available. 理论研究组 (⭕) and 应用研究组 (⭕).
For this quantum physics question, I should start with theoretical foundations.

[Global Supervisor] SELECT: 理论研究组
Subtask: Explain the theoretical concepts of quantum entanglement.

[Calls team tool...]

[Global Supervisor] THINKING: 理论研究组 (✅) completed. 应用研究组 (⭕) remains.
Now I need practical applications.

[Global Supervisor] SELECT: 应用研究组
Subtask: Explain practical applications in quantum computing.

[Calls team tool...]

[Global Supervisor] SYNTHESIS: All teams completed. Integrating results...
```

[CRITICAL REMINDER]
- You are a COORDINATOR, not an executor
- You must call ALL teams, not skip any
- If you respond without calling any team, you have FAILED your mission
"""
        
        # 创建 Global Supervisor Agent
        # 注意：并行/顺序执行主要通过系统提示词来引导 Agent 的行为
        global_supervisor = Agent(
            system_prompt=enhanced_prompt,
            tools=team_tools,
            model=config.model
        )
        
        return global_supervisor, team_names
    
    @staticmethod
    def stream_global_supervisor(agent: Agent, task: str, tracker: CallTracker, team_names: List[str]):
        """
        执行 Global Supervisor 并输出工作过程
        
        执行全局协调者的任务，并打印执行过程和状态。
        
        Args:
            agent: Global Supervisor Agent
            task: 任务描述
            tracker: 调用追踪器
            team_names: 团队名称列表
            
        Returns:
            执行结果字符串
        """
        # 1. 打印开始分析
        print_global_start(task)
        print_global_thinking()
        
        # 2. 获取团队执行状态
        execution_status = tracker.execution_tracker.get_execution_status(available_teams=team_names)
        
        # 3. 构建增强任务（添加执行状态和规则）
        enhanced_task = f"""
================================================================================
USER TASK
================================================================================
{task}

================================================================================
TEAM EXECUTION STATUS
================================================================================
{execution_status}

================================================================================
EXECUTION REMINDER
================================================================================
- Teams marked ⭕ = NOT executed yet (you MUST call these)
- Teams marked ✅ = Already completed (do NOT call again)
- You MUST call at least one team - direct answers are FORBIDDEN
- Follow the MANDATORY WORKFLOW: ANALYZE → DISPATCH → SYNTHESIZE
"""
        
        # 4. 执行任务
        response = agent(enhanced_task)

        # 5. 打印完成分析
        print_global_complete()

        # 将 AgentResult 转为字符串返回
        return str(response) if response else ""


# ============================================================================
# 配置构建器
# ============================================================================

class HierarchyBuilder:
    """
    层级团队构建器 - 提供流式 API 构建配置
    
    使用构建器模式创建层级团队系统，支持链式调用。
    
    示例:
        builder = HierarchyBuilder()
        agent, tracker, teams = (
            builder
            .set_global_prompt("全局协调者提示词")
            .add_team("团队1", "团队1提示词", workers=[...])
            .add_team("团队2", "团队2提示词", workers=[...])
            .build()
        )
    """
    
    def __init__(self, enable_tracking: bool = True, enable_context_sharing: bool = False, parallel_execution: bool = False):
        """
        初始化构建器
        
        Args:
            enable_tracking: 是否启用调用追踪
            enable_context_sharing: 是否启用跨团队上下文共享
            parallel_execution: 团队执行模式（False=顺序执行，True=并行执行）
        """
        self.teams: List[TeamConfig] = []
        self.global_prompt: str = ""
        self.global_model: Optional[Any] = None
        self.enable_tracking = enable_tracking
        self.enable_context_sharing = enable_context_sharing
        self.parallel_execution = parallel_execution
        self.tracker = CallTracker() if enable_tracking else None
    
    def set_global_prompt(self, prompt: str) -> 'HierarchyBuilder':
        """
        设置全局协调者的系统提示词
        
        Args:
            prompt: 系统提示词
            
        Returns:
            self（支持链式调用）
        """
        self.global_prompt = prompt
        return self
    
    def set_global_model(self, model: Any) -> 'HierarchyBuilder':
        """
        设置全局协调者的模型
        
        Args:
            model: 模型实例
            
        Returns:
            self（支持链式调用）
        """
        self.global_model = model
        return self
    
    def set_parallel_execution(self, parallel: bool) -> 'HierarchyBuilder':
        """
        设置团队执行模式
        
        Args:
            parallel: True=并行执行，False=顺序执行（默认）
            
        Returns:
            self（支持链式调用）
        """
        self.parallel_execution = parallel
        return self
    
    def add_team(
        self,
        name: str,
        supervisor_prompt: str,
        workers: List[Dict[str, Any]],
        model: Optional[Any] = None,
        prevent_duplicate: bool = True,
        share_context: bool = False
    ) -> 'HierarchyBuilder':
        """
        添加一个团队
        
        Args:
            name: 团队名称
            supervisor_prompt: 团队主管的系统提示词
            workers: Worker 配置列表，每个 Worker 需包含 name, role, system_prompt
            model: 团队使用的模型（可选）
            prevent_duplicate: 是否防止重复调用
            share_context: 是否接收其他团队的上下文
            
        Returns:
            self（支持链式调用）
        """
        # 创建 Worker 配置列表
        worker_configs = [
            WorkerConfig(
                name=w['name'],
                role=w['role'],
                system_prompt=w['system_prompt'],
                id=w.get('id', str(uuid.uuid4())),  # 使用提供的 id 或生成新的
                tools=w.get('tools', []),
                model=w.get('model'),
                temperature=w.get('temperature', 0.7),
                max_tokens=w.get('max_tokens', 2048)
            )
            for w in workers
        ]
        
        # 创建团队配置
        team_config = TeamConfig(
            name=name,
            supervisor_prompt=supervisor_prompt,
            workers=worker_configs,
            id=str(uuid.uuid4()),  # 生成团队 UUID
            model=model,
            prevent_duplicate=prevent_duplicate,
            share_context=share_context
        )
        
        self.teams.append(team_config)
        return self
    
    def build(self) -> tuple[Agent, Optional[CallTracker], List[str]]:
        """
        构建并返回 Global Supervisor、Tracker 和团队名称列表
        
        完成配置后调用此方法创建实际的 Agent 实例。
        
        Returns:
            (Global Supervisor Agent, CallTracker 或 None, 团队名称列表)
        """
        # 创建全局配置
        config = GlobalConfig(
            system_prompt=self.global_prompt,
            teams=self.teams,
            id=str(uuid.uuid4()),  # 生成全局配置 UUID
            model=self.global_model,
            enable_tracking=self.enable_tracking,
            enable_context_sharing=self.enable_context_sharing,
            parallel_execution=self.parallel_execution
        )
        
        # 设置执行追踪器
        if self.tracker:
            WorkerAgentFactory.set_execution_tracker(self.tracker.execution_tracker)
        
        # 创建 Global Supervisor
        agent, team_names = GlobalSupervisorFactory.create_global_supervisor(config, self.tracker)
        return agent, self.tracker, team_names


# ============================================================================
# 便捷函数
# ============================================================================

def create_hierarchy(
    config_dict: Dict[str, Any],
    enable_tracking: bool = True
) -> tuple[Agent, Optional[CallTracker]]:
    """
    从字典配置创建层级团队
    
    Args:
        config_dict: 配置字典
        enable_tracking: 是否启用调用追踪
        
    Returns:
        (Global Supervisor Agent, CallTracker 或 None)
    """
    builder = HierarchyBuilder(enable_tracking=enable_tracking)
    builder.set_global_prompt(config_dict['global_prompt'])
    
    for team in config_dict['teams']:
        builder.add_team(
            name=team['name'],
            supervisor_prompt=team['supervisor_prompt'],
            workers=team['workers'],
            model=team.get('model'),
            prevent_duplicate=team.get('prevent_duplicate', True)
        )
    
    return builder.build()


# ============================================================================
# 注意：演示代码已移至 test/test_quantum_research_full.py
# ============================================================================
