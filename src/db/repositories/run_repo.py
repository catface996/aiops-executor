"""
Run Repository - 运行记录数据访问层
"""

import time
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from ..models import ExecutionRun, ExecutionEvent, RunStatus


class RunRepository:
    """运行记录仓库"""

    def __init__(self, session: Session):
        self.session = session

    def create(self, data: dict) -> ExecutionRun:
        """创建运行记录"""
        run = ExecutionRun(**data)
        self.session.add(run)
        self.session.commit()
        self.session.refresh(run)
        return run

    def get_by_id(self, run_id: str, include_events: bool = False) -> Optional[ExecutionRun]:
        """根据 ID 获取运行记录"""
        query = self.session.query(ExecutionRun)

        if include_events:
            query = query.options(joinedload(ExecutionRun.events))

        return query.filter(ExecutionRun.id == run_id).first()

    def list(
        self,
        page: int = 1,
        size: int = 20,
        hierarchy_id: Optional[str] = None,
        status: Optional[str] = None
    ) -> tuple[List[ExecutionRun], int]:
        """
        获取运行记录列表

        Returns:
            (运行列表, 总数)
        """
        query = self.session.query(ExecutionRun)

        if hierarchy_id:
            query = query.filter(ExecutionRun.hierarchy_id == hierarchy_id)
        if status:
            query = query.filter(ExecutionRun.status == status)

        total = query.count()
        runs = query.order_by(ExecutionRun.created_at.desc()) \
                   .offset((page - 1) * size) \
                   .limit(size) \
                   .all()

        return runs, total

    def update_status(self, run_id: str, status: str) -> bool:
        """更新运行状态"""
        run = self.get_by_id(run_id)
        if not run:
            return False

        run.status = status

        if status == RunStatus.RUNNING.value:
            run.started_at = datetime.utcnow()
        elif status in (RunStatus.COMPLETED.value, RunStatus.FAILED.value, RunStatus.CANCELLED.value):
            run.completed_at = datetime.utcnow()

        self.session.commit()
        return True

    def update_result(
        self,
        run_id: str,
        status: str,
        result: str = None,
        error: str = None,
        statistics: dict = None
    ) -> bool:
        """更新运行结果"""
        run = self.get_by_id(run_id)
        if not run:
            return False

        run.status = status
        run.completed_at = datetime.utcnow()

        if result is not None:
            run.result = result
        if error is not None:
            run.error = error
        if statistics is not None:
            run.statistics = statistics

        self.session.commit()
        return True

    def add_event(
        self,
        run_id: str,
        event_type: str,
        data: dict = None,
        is_global_supervisor: bool = False,
        team_name: str = None,
        is_team_supervisor: bool = False,
        worker_name: str = None
    ) -> ExecutionEvent:
        """添加执行事件"""
        # 使用微秒时间戳作为序列号，保证顺序
        sequence = int(time.time() * 1000000)

        event = ExecutionEvent(
            run_id=run_id,
            event_type=event_type,
            data=data,
            sequence=sequence,
            is_global_supervisor=is_global_supervisor,
            team_name=team_name,
            is_team_supervisor=is_team_supervisor,
            worker_name=worker_name,
            timestamp=datetime.utcnow()
        )
        self.session.add(event)
        self.session.commit()
        self.session.refresh(event)
        return event

    def get_events(self, run_id: str) -> List[ExecutionEvent]:
        """获取运行的所有事件"""
        return self.session.query(ExecutionEvent) \
            .filter(ExecutionEvent.run_id == run_id) \
            .order_by(ExecutionEvent.timestamp, ExecutionEvent.sequence) \
            .all()

    def set_topology_snapshot(self, run_id: str, topology: dict) -> bool:
        """设置拓扑快照"""
        run = self.get_by_id(run_id)
        if not run:
            return False

        run.topology_snapshot = topology
        self.session.commit()
        return True

    def delete(self, run_id: str) -> bool:
        """删除运行记录（级联删除事件）"""
        run = self.get_by_id(run_id)
        if not run:
            return False

        self.session.delete(run)
        self.session.commit()
        return True
