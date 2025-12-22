"""
Core - 层级多智能体系统核心模块

包含：
- api_models: API 数据模型
- config: 配置管理
- hierarchy_system: 层级系统核心逻辑 (需要 strands)
- hierarchy_executor: 执行器 (需要 strands)
- output_formatter: 输出格式化
"""

# 不依赖 strands 的模块可以直接导入
from .api_models import (
    ExecutionMode,
    EventType,
    WorkerConfigRequest,
    TeamConfigRequest,
    HierarchyConfigRequest,
    StreamEvent,
    ExecutionResponse,
    TopologyInfo,
    ErrorResponse
)

from .config import Config, setup_config, get_config

from .output_formatter import (
    OutputFormatter,
    print_worker_start,
    print_worker_thinking,
    print_worker_complete,
    print_worker_warning,
    print_worker_error,
    print_team_start,
    print_team_thinking,
    print_team_complete,
    print_team_summary,
    print_team_warning,
    print_team_error,
    print_team_duplicate_warning,
    print_global_start,
    print_global_thinking,
    print_global_dispatch,
    print_global_summary,
    print_global_complete,
    set_current_team
)

# 依赖 strands 的模块使用延迟导入
# 这些导出只在被访问时才实际导入
_lazy_imports = {
    'HierarchyBuilder': '.hierarchy_system',
    'GlobalSupervisorFactory': '.hierarchy_system',
    'ExecutionTracker': '.hierarchy_system',
    'CallTracker': '.hierarchy_system',
    'execute_hierarchy': '.hierarchy_executor',
}


def __getattr__(name):
    """延迟导入依赖 strands 的模块"""
    if name in _lazy_imports:
        import importlib
        module = importlib.import_module(_lazy_imports[name], package=__name__)
        return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    # api_models
    'ExecutionMode',
    'EventType',
    'WorkerConfigRequest',
    'TeamConfigRequest',
    'HierarchyConfigRequest',
    'StreamEvent',
    'ExecutionResponse',
    'TopologyInfo',
    'ErrorResponse',
    # config
    'Config',
    'setup_config',
    'get_config',
    # output_formatter
    'OutputFormatter',
    'print_worker_start',
    'print_worker_thinking',
    'print_worker_complete',
    'print_worker_warning',
    'print_worker_error',
    'print_team_start',
    'print_team_thinking',
    'print_team_complete',
    'print_team_summary',
    'print_team_warning',
    'print_team_error',
    'print_team_duplicate_warning',
    'print_global_start',
    'print_global_thinking',
    'print_global_dispatch',
    'print_global_summary',
    'print_global_complete',
    'set_current_team',
    # hierarchy_system (lazy)
    'HierarchyBuilder',
    'GlobalSupervisorFactory',
    'ExecutionTracker',
    'CallTracker',
    # hierarchy_executor (lazy)
    'execute_hierarchy',
]
