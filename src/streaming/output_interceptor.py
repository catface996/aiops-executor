"""
Output Interceptor - 输出拦截器

拦截 stdout 并转换为结构化事件
"""

import sys
import re
import threading
from typing import Callable, Optional, Dict, Any, Union
from contextlib import contextmanager
from io import StringIO


class OutputInterceptor:
    """
    输出拦截器 - 拦截 stdout 并转换为结构化事件
    """

    # 输出模式匹配（基于 output_formatter.py 的格式）
    PATTERNS = {
        'worker_start': re.compile(r'={50,}.*?(\S+?).*?开始工作', re.DOTALL),
        'worker_thinking': re.compile(r'思考过程|分析中'),
        'worker_complete': re.compile(r'✅.*?(\S+?).*?完成'),
        'team_start': re.compile(r'#{50,}.*?(\S+?)主管.*?开始协调', re.DOTALL),
        'team_thinking': re.compile(r'主管的协调过程'),
        'team_complete': re.compile(r'✅.*?(\S+?)主管.*?完成'),
        'team_duplicate': re.compile(r'⚠️.*?已在之前执行过'),
        'global_start': re.compile(r'\*{50,}.*?首席科学家.*?开始', re.DOTALL),
        'global_complete': re.compile(r'✅.*?首席科学家.*?完成'),
        'error': re.compile(r'❌|错误|Error|Exception', re.IGNORECASE),
        'warning': re.compile(r'⚠️|警告|Warning', re.IGNORECASE),
    }

    # 标签解析模式（用于从输出中提取 team_name 和 worker_name）
    # 格式: [Team: 团队名 | Worker: 成员名] 或 [Team: 团队名 | Supervisor] 或 [Global Supervisor]
    LABEL_PATTERN = re.compile(r'\[(?:Team:\s*([^|\]]+?)\s*\|)?\s*(?:Worker:\s*([^\]]+?)|Supervisor|Global Supervisor)\s*\]')

    def __init__(self, event_callback: Callable[[str, Dict[str, Any]], None]):
        """
        Args:
            event_callback: 事件回调函数 (event_type, data) -> None
        """
        self.event_callback = event_callback
        self.original_stdout = None
        self.buffer = StringIO()
        self.current_context: Dict[str, Any] = {}
        self._lock = threading.Lock()

    def start_interception(self):
        """开始拦截 stdout"""
        with self._lock:
            if self.original_stdout is None:
                self.original_stdout = sys.stdout
                sys.stdout = self

    def stop_interception(self):
        """停止拦截，恢复 stdout"""
        with self._lock:
            if self.original_stdout is not None:
                sys.stdout = self.original_stdout
                self.original_stdout = None

    def write(self, text: str):
        """拦截 write 调用"""
        # 同时写入原始 stdout（用于调试和日志）
        if self.original_stdout:
            self.original_stdout.write(text)

        # 解析文本并发射事件
        self._parse_and_emit(text)

    def flush(self):
        """实现 flush 方法"""
        if self.original_stdout:
            self.original_stdout.flush()

    def set_context(self, **kwargs):
        """设置当前上下文"""
        self.current_context.update(kwargs)

    def clear_context(self):
        """清除当前上下文"""
        self.current_context.clear()

    def _extract_label_info(self, text: str) -> Dict[str, Optional[str]]:
        """
        从输出文本中提取标签信息（team_name 和 worker_name）

        标签格式:
        - [Team: 团队名 | Worker: 成员名]
        - [Team: 团队名 | Supervisor]
        - [Global Supervisor]
        - [Worker: 成员名]
        """
        result = {'team_name': None, 'worker_name': None}

        match = self.LABEL_PATTERN.search(text)
        if match:
            team_name = match.group(1)
            worker_name = match.group(2)
            if team_name:
                result['team_name'] = team_name.strip()
            if worker_name:
                result['worker_name'] = worker_name.strip()

        return result

    def _parse_and_emit(self, text: str):
        """解析文本并发射对应事件"""
        if not text or not text.strip():
            return

        text_stripped = text.strip()

        # 提取标签信息（team_name 和 worker_name）
        label_info = self._extract_label_info(text_stripped)

        # 按优先级匹配模式
        for event_type, pattern in self.PATTERNS.items():
            match = pattern.search(text_stripped)
            if match:
                data = {
                    'raw_text': text_stripped[:500],  # 限制长度
                    'context': self.current_context.copy(),
                    'team_name': label_info['team_name'],
                    'worker_name': label_info['worker_name']
                }

                # 提取匹配的名称
                if match.groups():
                    data['name'] = match.group(1)

                self.event_callback(event_type, data)
                return

        # 非模式匹配的内容作为 output 事件
        if len(text_stripped) > 10:  # 忽略太短的输出
            self.event_callback('output', {
                'content': text_stripped[:1000],  # 限制长度
                'context': self.current_context.copy(),
                'team_name': label_info['team_name'],
                'worker_name': label_info['worker_name']
            })


@contextmanager
def intercept_output(event_callback: Callable[[str, Dict[str, Any]], None]):
    """
    上下文管理器 - 拦截输出

    Usage:
        def my_callback(event_type, data):
            print(f"Event: {event_type}, Data: {data}")

        with intercept_output(my_callback):
            # 执行任务，所有 print 输出会被拦截
            execute_hierarchy(config)
    """
    interceptor = OutputInterceptor(event_callback)
    interceptor.start_interception()
    try:
        yield interceptor
    finally:
        interceptor.stop_interception()


class EventEmitter:
    """
    事件发射器 - 直接发射结构化事件（不依赖 stdout 拦截）
    """

    def __init__(self, callback: Callable[[str, Dict[str, Any]], None]):
        self.callback = callback

    def emit(self, event_type: str, **data):
        """发射事件"""
        self.callback(event_type, data)

    def execution_started(self, task: str):
        """执行开始"""
        self.emit('execution_started', task=task)

    def execution_completed(self, result: str, statistics: dict = None):
        """执行完成"""
        self.emit('execution_completed', result=result, statistics=statistics)

    def execution_failed(self, error: str):
        """执行失败"""
        self.emit('execution_failed', error=error)

    def execution_cancelled(self):
        """执行取消"""
        self.emit('execution_cancelled')

    def team_started(self, team_name: str):
        """团队开始"""
        self.emit('team_started', team_name=team_name)

    def team_completed(self, team_name: str, result: str = None):
        """团队完成"""
        self.emit('team_completed', team_name=team_name, result=result)

    def worker_started(self, worker_name: str, team_name: str = None):
        """Worker 开始"""
        self.emit('worker_started', worker_name=worker_name, team_name=team_name)

    def worker_output(self, worker_name: str, content: str):
        """Worker 输出"""
        self.emit('worker_output', worker_name=worker_name, content=content)

    def worker_completed(self, worker_name: str, result: str = None):
        """Worker 完成"""
        self.emit('worker_completed', worker_name=worker_name, result=result)

    def topology_created(self, topology: dict):
        """拓扑创建"""
        self.emit('topology_created', topology=topology)
