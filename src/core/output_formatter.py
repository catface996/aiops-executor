"""
输出格式化模块 - 统一管理所有输出格式

提供一致的输出格式和样式，便于维护和修改。
输出标签格式:
- [Global Supervisor] - 全局协调者输出
- [Team: 团队名 | Supervisor] - 团队主管输出
- [Team: 团队名 | Worker: 成员名] - 团队成员输出
"""

from typing import List, Optional


class OutputFormatter:
    """输出格式化器 - 统一管理所有输出样式"""

    # 分隔符长度
    SEPARATOR_LENGTH = 70

    # 分隔符样式
    SEPARATOR_WORKER = "="
    SEPARATOR_TEAM = "#"
    SEPARATOR_GLOBAL = "*"
    SEPARATOR_SECTION = "-"

    # 当前上下文（用于标注输出来源）
    _current_team_name: Optional[str] = None

    @classmethod
    def set_current_team(cls, team_name: Optional[str]):
        """设置当前团队上下文"""
        cls._current_team_name = team_name

    @classmethod
    def get_current_team(cls) -> Optional[str]:
        """获取当前团队上下文"""
        return cls._current_team_name

    @staticmethod
    def format_source_label(source_type: str, name: str = None, team_name: str = None) -> str:
        """
        格式化来源标签

        Args:
            source_type: 'global', 'team_supervisor', 'worker'
            name: 名称（worker名称或team名称）
            team_name: 团队名称（仅用于worker）

        Returns:
            格式化的标签字符串
        """
        if source_type == 'global':
            return "[Global Supervisor]"
        elif source_type == 'team_supervisor':
            return f"[Team: {name} | Supervisor]"
        elif source_type == 'worker':
            if team_name:
                return f"[Team: {team_name} | Worker: {name}]"
            elif OutputFormatter._current_team_name:
                return f"[Team: {OutputFormatter._current_team_name} | Worker: {name}]"
            else:
                return f"[Worker: {name}]"
        return ""
    
    # ========================================================================
    # 消息生成器
    # ========================================================================
    
    @staticmethod
    def format_executed_message(name: str) -> str:
        """生成"已执行过"的返回消息"""
        return f"[{name}] 已在之前执行过，结果已在上文中，请直接引用"
    
    @staticmethod
    def format_duplicate_task_message(name: str) -> str:
        """生成"重复任务"的返回消息"""
        return f"[{name}] 已处理过相同任务，结果已在上文中，请直接引用"
    
    @staticmethod
    def format_result_message(name: str, response: str) -> str:
        """生成结果消息"""
        return f"[{name}] {response}"
    
    @staticmethod
    def _print_separator(char: str, length: int = SEPARATOR_LENGTH):
        """打印分隔符"""
        print(char * length)
    
    @staticmethod
    def _truncate_text(text: str, max_length: int = 100) -> str:
        """截断文本"""
        if len(text) > max_length:
            return f"{text[:max_length]}..."
        return text
    
    # ========================================================================
    # Worker Agent 输出
    # ========================================================================

    @staticmethod
    def print_worker_start(name: str, task: str, team_name: str = None):
        """打印 Worker 开始工作"""
        label = OutputFormatter.format_source_label('worker', name, team_name)
        print(f"\n{OutputFormatter.SEPARATOR_WORKER * OutputFormatter.SEPARATOR_LENGTH}")
        print(f"{label} 🔬 开始工作")
        print(OutputFormatter.SEPARATOR_WORKER * OutputFormatter.SEPARATOR_LENGTH)
        print(f"📋 任务: {OutputFormatter._truncate_text(task)}")
        print(f"{OutputFormatter.SEPARATOR_WORKER * OutputFormatter.SEPARATOR_LENGTH}\n")

    @staticmethod
    def print_worker_thinking(name: str, team_name: str = None):
        """打印 Worker 思考过程标题"""
        label = OutputFormatter.format_source_label('worker', name, team_name)
        print(f"{label} 💭 思考中...\n")
        print(OutputFormatter.SEPARATOR_SECTION * OutputFormatter.SEPARATOR_LENGTH + "\n")

    @staticmethod
    def print_worker_complete(name: str, team_name: str = None):
        """打印 Worker 完成工作"""
        label = OutputFormatter.format_source_label('worker', name, team_name)
        print("\n" + OutputFormatter.SEPARATOR_SECTION * OutputFormatter.SEPARATOR_LENGTH)
        print(f"\n{label} ✅ 完成工作\n")

    @staticmethod
    def print_worker_warning(message: str):
        """打印 Worker 警告信息"""
        print(f"\n{OutputFormatter.SEPARATOR_WORKER * OutputFormatter.SEPARATOR_LENGTH}")
        print(message)
        print(f"{OutputFormatter.SEPARATOR_WORKER * OutputFormatter.SEPARATOR_LENGTH}\n")

    @staticmethod
    def print_worker_duplicate_task_warning(name: str, team_name: str = None):
        """打印 Worker 重复任务警告（简化版）"""
        label = OutputFormatter.format_source_label('worker', name, team_name)
        print(f"\n⚠️ {label} 该专家已经处理过此任务，请直接使用之前的结果\n")

    @staticmethod
    def print_worker_error(message: str):
        """打印 Worker 错误信息"""
        print(f"\n❌ {message}\n")
    
    # ========================================================================
    # Team Supervisor 输出
    # ========================================================================

    @staticmethod
    def print_team_start(name: str, call_id: str, task: str, workers: List[str]):
        """打印 Team Supervisor 开始协调"""
        label = OutputFormatter.format_source_label('team_supervisor', name)
        # 设置当前团队上下文
        OutputFormatter.set_current_team(name)
        print(f"\n{OutputFormatter.SEPARATOR_TEAM * OutputFormatter.SEPARATOR_LENGTH}")
        print(f"{label} 👔 开始协调")
        print(OutputFormatter.SEPARATOR_TEAM * OutputFormatter.SEPARATOR_LENGTH)
        print(f"📌 调用ID: {call_id}")
        print(f"📋 任务: {OutputFormatter._truncate_text(task)}")
        print(f"👥 团队成员: {', '.join(workers)}")
        print(f"{OutputFormatter.SEPARATOR_TEAM * OutputFormatter.SEPARATOR_LENGTH}\n")

    @staticmethod
    def print_team_thinking(name: str):
        """打印 Team Supervisor 思考过程标题"""
        label = OutputFormatter.format_source_label('team_supervisor', name)
        print(f"{label} 💭 思考中...\n")
        print(OutputFormatter.SEPARATOR_SECTION * OutputFormatter.SEPARATOR_LENGTH + "\n")

    @staticmethod
    def print_team_complete(name: str):
        """打印 Team Supervisor 完成协调"""
        label = OutputFormatter.format_source_label('team_supervisor', name)
        print("\n" + OutputFormatter.SEPARATOR_SECTION * OutputFormatter.SEPARATOR_LENGTH)
        print(f"\n{label} ✅ 完成协调\n")
        # 清除团队上下文
        OutputFormatter.set_current_team(None)

    @staticmethod
    def print_team_summary(name: str):
        """打印 Team Supervisor 总结"""
        label = OutputFormatter.format_source_label('team_supervisor', name)
        print(f"\n{label} 📝 总结:\n")

    @staticmethod
    def print_team_warning(message: str):
        """打印 Team Supervisor 警告信息"""
        print(f"\n{OutputFormatter.SEPARATOR_TEAM * OutputFormatter.SEPARATOR_LENGTH}")
        print(message)
        print(f"{OutputFormatter.SEPARATOR_TEAM * OutputFormatter.SEPARATOR_LENGTH}\n")

    @staticmethod
    def print_team_error(message: str):
        """打印 Team Supervisor 错误信息"""
        print(f"\n❌ {message}\n")

    @staticmethod
    def print_team_duplicate_warning(message: str):
        """打印 Team Supervisor 重复调用警告"""
        print(f"\n⚠️  {message}\n")

    @staticmethod
    def print_team_dispatch(team_name: str, worker_name: str):
        """打印 Team Supervisor 调度 Worker"""
        label = OutputFormatter.format_source_label('team_supervisor', team_name)
        print(f"\n{label} 📤 DISPATCH: 调度 [{worker_name}]")
        print("")

    # ========================================================================
    # Global Supervisor 输出
    # ========================================================================

    @staticmethod
    def print_global_start(task: str):
        """打印 Global Supervisor 开始分析"""
        label = OutputFormatter.format_source_label('global')
        print(f"\n{OutputFormatter.SEPARATOR_GLOBAL * OutputFormatter.SEPARATOR_LENGTH}")
        print(f"{label} 🎯 开始分析任务")
        print(OutputFormatter.SEPARATOR_GLOBAL * OutputFormatter.SEPARATOR_LENGTH)
        print(f"📋 任务:\n{task}")
        print(f"{OutputFormatter.SEPARATOR_GLOBAL * OutputFormatter.SEPARATOR_LENGTH}\n")

    @staticmethod
    def print_global_thinking():
        """打印 Global Supervisor 思考过程标题"""
        label = OutputFormatter.format_source_label('global')
        print(f"{label} 💭 思考中...\n")
        print(OutputFormatter.SEPARATOR_SECTION * OutputFormatter.SEPARATOR_LENGTH + "\n")

    @staticmethod
    def print_global_dispatch(team_name: str, reason: str = ""):
        """打印 Global Supervisor 调度团队"""
        label = OutputFormatter.format_source_label('global')
        print(f"\n{label} 📤 DISPATCH: 调度 [{team_name}]")
        if reason:
            print(f"   理由: {reason}")
        print("")

    @staticmethod
    def print_global_summary():
        """打印 Global Supervisor 总结"""
        label = OutputFormatter.format_source_label('global')
        print(f"\n{label} 📝 SYNTHESIS: 总结所有团队结果...\n")

    @staticmethod
    def print_global_complete():
        """打印 Global Supervisor 完成分析"""
        label = OutputFormatter.format_source_label('global')
        print("\n" + OutputFormatter.SEPARATOR_GLOBAL * OutputFormatter.SEPARATOR_LENGTH)
        print(f"\n{label} ✅ 完成任务\n")


# ============================================================================
# 便捷函数（向后兼容）
# ============================================================================

# Worker 输出
def print_worker_start(name: str, task: str, team_name: str = None):
    """打印 Worker 开始工作"""
    OutputFormatter.print_worker_start(name, task, team_name)


def print_worker_thinking(name: str, team_name: str = None):
    """打印 Worker 思考过程标题"""
    OutputFormatter.print_worker_thinking(name, team_name)


def print_worker_complete(name: str, team_name: str = None):
    """打印 Worker 完成工作"""
    OutputFormatter.print_worker_complete(name, team_name)


def print_worker_warning(message: str):
    """打印 Worker 警告信息"""
    OutputFormatter.print_worker_warning(message)


def print_worker_error(message: str):
    """打印 Worker 错误信息"""
    OutputFormatter.print_worker_error(message)


# Team 输出
def print_team_start(name: str, call_id: str, task: str, workers: List[str]):
    """打印 Team Supervisor 开始协调"""
    OutputFormatter.print_team_start(name, call_id, task, workers)


def print_team_thinking(name: str):
    """打印 Team Supervisor 思考过程标题"""
    OutputFormatter.print_team_thinking(name)


def print_team_complete(name: str):
    """打印 Team Supervisor 完成协调"""
    OutputFormatter.print_team_complete(name)


def print_team_summary(name: str):
    """打印 Team Supervisor 总结"""
    OutputFormatter.print_team_summary(name)


def print_team_warning(message: str):
    """打印 Team Supervisor 警告信息"""
    OutputFormatter.print_team_warning(message)


def print_team_error(message: str):
    """打印 Team Supervisor 错误信息"""
    OutputFormatter.print_team_error(message)


def print_team_duplicate_warning(message: str):
    """打印 Team Supervisor 重复调用警告"""
    OutputFormatter.print_team_duplicate_warning(message)


def print_team_dispatch(team_name: str, worker_name: str):
    """打印 Team Supervisor 调度 Worker"""
    OutputFormatter.print_team_dispatch(team_name, worker_name)


# Global 输出
def print_global_start(task: str):
    """打印 Global Supervisor 开始分析"""
    OutputFormatter.print_global_start(task)


def print_global_thinking():
    """打印 Global Supervisor 思考过程标题"""
    OutputFormatter.print_global_thinking()


def print_global_dispatch(team_name: str, reason: str = ""):
    """打印 Global Supervisor 调度团队"""
    OutputFormatter.print_global_dispatch(team_name, reason)


def print_global_summary():
    """打印 Global Supervisor 总结"""
    OutputFormatter.print_global_summary()


def print_global_complete():
    """打印 Global Supervisor 完成分析"""
    OutputFormatter.print_global_complete()


# 上下文管理
def set_current_team(team_name: str = None):
    """设置当前团队上下文"""
    OutputFormatter.set_current_team(team_name)


# 消息生成函数
def format_executed_message(name: str) -> str:
    """生成"已执行过"的返回消息"""
    return OutputFormatter.format_executed_message(name)


def format_duplicate_task_message(name: str) -> str:
    """生成"重复任务"的返回消息"""
    return OutputFormatter.format_duplicate_task_message(name)


def format_result_message(name: str, response: str) -> str:
    """生成结果消息"""
    return OutputFormatter.format_result_message(name, response)
