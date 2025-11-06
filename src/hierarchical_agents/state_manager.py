"""
State management for hierarchical multi-agent system.

This module provides state persistence and querying capabilities using Redis
for caching and ensuring data consistency across concurrent operations.
"""

import json
import logging
import time
import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from contextlib import asynccontextmanager

from pydantic import BaseModel

from .data_models import (
    ExecutionStatus,
    ExecutionEvent,
    TeamState,
    ExecutionContext,
    ExecutionSummary,
    TeamResult,
    StandardizedOutput,
    ErrorInfo,
    ExecutionMetrics
)


class StateManagerConfig(BaseModel):
    """Configuration for StateManager."""
    key_prefix: str = "hierarchical_agents"
    default_ttl: int = 3600  # 1 hour
    max_retries: int = 3
    retry_delay: float = 0.1
    cleanup_interval: int = 3600  # 1 hour


class ExecutionState(BaseModel):
    """Complete execution state."""
    execution_id: str
    team_id: str
    status: ExecutionStatus
    context: ExecutionContext
    events: List[ExecutionEvent]
    team_states: Dict[str, TeamState]
    results: Dict[str, TeamResult]
    summary: Optional[ExecutionSummary] = None
    errors: List[ErrorInfo] = []
    metrics: ExecutionMetrics = ExecutionMetrics()
    created_at: datetime
    updated_at: datetime


class StateManager:
    """
    State manager for hierarchical multi-agent system.
    
    Provides state persistence, querying, and caching using Redis.
    Ensures data consistency and high performance for concurrent operations.
    """
    
    def __init__(self, config: Optional[StateManagerConfig] = None):
        """Initialize StateManager with configuration."""
        self.config = config or StateManagerConfig()
        self._memory_store: Dict[str, Dict[str, Any]] = {
            'executions': {},
            'teams': {},
            'agents': {},
            'events': {}
        }
        self._lock_timeout = 10  # seconds
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        self._initialized = False
        
    async def initialize(self) -> None:
        """Initialize in-memory storage."""
        if self._initialized:
            return
            
        self.logger.info("Initializing StateManager with in-memory storage")
        
        # Start cleanup task
        asyncio.create_task(self._cleanup_expired_data())
        
        self._initialized = True
        self.logger.info("StateManager initialized successfully")
    
    async def close(self) -> None:
        """Close StateManager and cleanup resources."""
        self._initialized = False
        self._memory_store.clear()
        self.logger.info("StateManager closed")
    
    def _get_key(self, key_type: str, identifier: str) -> str:
        """Generate storage key with prefix."""
        return f"{self.config.key_prefix}:{key_type}:{identifier}"
    
    def _get_lock_key(self, identifier: str) -> str:
        """Generate lock key for memory locking."""
        return f"{self.config.key_prefix}:lock:{identifier}"
    
    @asynccontextmanager
    async def _distributed_lock(self, identifier: str):
        """Simple memory lock for ensuring data consistency."""
        if not self._initialized:
            raise RuntimeError("StateManager not initialized")
        
        # For in-memory storage, we don't need complex locking
        # Just yield immediately since we're single-threaded
        yield
    
    async def create_execution(
        self, 
        execution_id: str, 
        team_id: str, 
        context: ExecutionContext
    ) -> None:
        """Create a new execution state."""
        if not self._initialized:
            raise RuntimeError("StateManager not initialized")
        
        async with self._distributed_lock(execution_id):
            # Check if execution already exists
            if execution_id in self._memory_store['executions']:
                raise ValueError(f"Execution {execution_id} already exists")
            
            # Create initial state
            now = datetime.now()
            state = ExecutionState(
                execution_id=execution_id,
                team_id=team_id,
                status=ExecutionStatus.PENDING,
                context=context,
                events=[],
                team_states={},
                results={},
                created_at=now,
                updated_at=now
            )
            
            # Store in memory with expiration timestamp
            self._memory_store['executions'][execution_id] = {
                'data': state.model_dump(),
                'expires_at': now.timestamp() + self.config.default_ttl
            }
    
    async def update_execution_status(
        self, 
        execution_id: str, 
        status: ExecutionStatus
    ) -> None:
        """Update execution status."""
        if not self._initialized:
            raise RuntimeError("StateManager not initialized")
        
        async with self._distributed_lock(execution_id):
            if execution_id not in self._memory_store['executions']:
                raise ValueError(f"Execution {execution_id} not found")
            
            # Get current state
            stored_data = self._memory_store['executions'][execution_id]
            state_dict = stored_data['data']
            state_dict['status'] = status.value
            state_dict['updated_at'] = datetime.now().isoformat()
            
            # Update expiration
            stored_data['expires_at'] = datetime.now().timestamp() + self.config.default_ttl
    
    async def add_event(self, execution_id: str, event: ExecutionEvent) -> None:
        """Add an event to execution state."""
        if not self._initialized:
            raise RuntimeError("StateManager not initialized")
        
        async with self._distributed_lock(execution_id):
            if execution_id not in self._memory_store['executions']:
                raise ValueError(f"Execution {execution_id} not found")
            
            # Get current state
            stored_data = self._memory_store['executions'][execution_id]
            state_dict = stored_data['data']
            
            # Add event
            if 'events' not in state_dict:
                state_dict['events'] = []
            state_dict['events'].append(event.model_dump())
            state_dict['updated_at'] = datetime.now().isoformat()
            
            # Update expiration
            stored_data['expires_at'] = datetime.now().timestamp() + self.config.default_ttl
    
    async def update_team_state(
        self, 
        execution_id: str, 
        team_id: str, 
        team_state: TeamState
    ) -> None:
        """Update team state within execution."""
        if not self._initialized:
            raise RuntimeError("StateManager not initialized")
        
        async with self._distributed_lock(execution_id):
            if execution_id not in self._memory_store['executions']:
                raise ValueError(f"Execution {execution_id} not found")
            
            # Get current state
            stored_data = self._memory_store['executions'][execution_id]
            state_dict = stored_data['data']
            
            # Update team state
            if 'team_states' not in state_dict:
                state_dict['team_states'] = {}
            state_dict['team_states'][team_id] = team_state.model_dump()
            state_dict['updated_at'] = datetime.now().isoformat()
            
            # Update expiration
            stored_data['expires_at'] = datetime.now().timestamp() + self.config.default_ttl
    
    async def update_team_result(
        self, 
        execution_id: str, 
        team_id: str, 
        result: TeamResult
    ) -> None:
        """Update team result within execution."""
        if not self._initialized:
            raise RuntimeError("StateManager not initialized")
        
        async with self._distributed_lock(execution_id):
            if execution_id not in self._memory_store['executions']:
                raise ValueError(f"Execution {execution_id} not found")
            
            # Get current state
            stored_data = self._memory_store['executions'][execution_id]
            state_dict = stored_data['data']
            
            # Update team result
            if 'results' not in state_dict:
                state_dict['results'] = {}
            state_dict['results'][team_id] = result.model_dump()
            state_dict['updated_at'] = datetime.now().isoformat()
            
            # Update expiration
            stored_data['expires_at'] = datetime.now().timestamp() + self.config.default_ttl
    
    async def update_execution_summary(
        self, 
        execution_id: str, 
        summary: ExecutionSummary
    ) -> None:
        """Update execution summary."""
        if not self._initialized:
            raise RuntimeError("StateManager not initialized")
        
        async with self._distributed_lock(execution_id):
            if execution_id not in self._memory_store['executions']:
                raise ValueError(f"Execution {execution_id} not found")
            
            # Get current state
            stored_data = self._memory_store['executions'][execution_id]
            state_dict = stored_data['data']
            
            # Update summary
            state_dict['summary'] = summary.model_dump()
            state_dict['updated_at'] = datetime.now().isoformat()
            
            # Update expiration
            stored_data['expires_at'] = datetime.now().timestamp() + self.config.default_ttl
    
    async def add_error(self, execution_id: str, error: ErrorInfo) -> None:
        """Add error to execution state."""
        if not self._initialized:
            raise RuntimeError("StateManager not initialized")
        
        async with self._distributed_lock(execution_id):
            if execution_id not in self._memory_store['executions']:
                raise ValueError(f"Execution {execution_id} not found")
            
            # Get current state
            stored_data = self._memory_store['executions'][execution_id]
            state_dict = stored_data['data']
            
            # Add error
            if 'errors' not in state_dict:
                state_dict['errors'] = []
            state_dict['errors'].append(error.model_dump())
            state_dict['updated_at'] = datetime.now().isoformat()
            
            # Update expiration
            stored_data['expires_at'] = datetime.now().timestamp() + self.config.default_ttl
    
    async def update_metrics(
        self, 
        execution_id: str, 
        metrics: ExecutionMetrics
    ) -> None:
        """Update execution metrics."""
        if not self._redis:
            raise RuntimeError("StateManager not initialized")
        
        async with self._distributed_lock(execution_id):
            state = await self.get_execution_state(execution_id)
            if not state:
                raise ValueError(f"Execution {execution_id} not found")
            
            state.metrics = metrics
            state.updated_at = datetime.now()
            
            key = self._get_key("execution", execution_id)
            await self._redis.setex(
                key,
                self.config.default_ttl,
                state.model_dump_json()
            )
    
    async def get_execution_state(self, execution_id: str) -> Optional[ExecutionState]:
        """Get complete execution state."""
        if not self._initialized:
            return None
            
        start_time = time.time()
        
        # Check if execution exists and is not expired
        if execution_id not in self._memory_store['executions']:
            return None
            
        stored_data = self._memory_store['executions'][execution_id]
        
        # Check expiration
        if stored_data['expires_at'] < datetime.now().timestamp():
            # Remove expired data
            del self._memory_store['executions'][execution_id]
            return None
        
        query_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        
        try:
            state_dict = stored_data['data']
            return ExecutionState.model_validate(state_dict)
        except Exception as e:
            self.logger.error(f"Failed to deserialize execution state: {e}")
            return None
    
    async def get_execution_status(self, execution_id: str) -> Optional[ExecutionStatus]:
        """Get execution status quickly."""
        state = await self.get_execution_state(execution_id)
        return state.status if state else None
    
    async def get_execution_events(
        self, 
        execution_id: str, 
        limit: Optional[int] = None
    ) -> List[ExecutionEvent]:
        """Get execution events."""
        state = await self.get_execution_state(execution_id)
        if not state:
            return []
        
        events = state.events
        if limit:
            events = events[-limit:]  # Get most recent events
        
        return events
    
    async def get_team_state(
        self, 
        execution_id: str, 
        team_id: str
    ) -> Optional[TeamState]:
        """Get specific team state."""
        state = await self.get_execution_state(execution_id)
        if not state:
            return None
        
        return state.team_states.get(team_id)
    
    async def get_team_result(
        self, 
        execution_id: str, 
        team_id: str
    ) -> Optional[TeamResult]:
        """Get specific team result."""
        state = await self.get_execution_state(execution_id)
        if not state:
            return None
        
        return state.results.get(team_id)
    
    async def get_standardized_output(
        self, 
        execution_id: str
    ) -> Optional[StandardizedOutput]:
        """Get standardized output format."""
        state = await self.get_execution_state(execution_id)
        if not state or not state.summary:
            return None
        
        return StandardizedOutput(
            execution_id=execution_id,
            execution_summary=state.summary,
            team_results=state.results,
            errors=state.errors,
            metrics=state.metrics
        )
    
    async def list_executions(
        self, 
        team_id: Optional[str] = None,
        status: Optional[ExecutionStatus] = None,
        limit: int = 100
    ) -> List[str]:
        """List execution IDs with optional filtering."""
        if not self._initialized:
            return []
        
        execution_ids = []
        current_time = datetime.now().timestamp()
        
        # Clean up expired entries and collect valid ones
        expired_keys = []
        for execution_id, stored_data in self._memory_store['executions'].items():
            # Check expiration
            if stored_data['expires_at'] < current_time:
                expired_keys.append(execution_id)
                continue
                
            # Apply filters if specified
            if team_id or status:
                try:
                    state_dict = stored_data['data']
                    if team_id and state_dict.get('team_id') != team_id:
                        continue
                    if status and state_dict.get('status') != status.value:
                        continue
                except Exception:
                    continue
            
            execution_ids.append(execution_id)
            
            # Respect limit
            if len(execution_ids) >= limit:
                break
        
        # Clean up expired entries
        for key in expired_keys:
            del self._memory_store['executions'][key]
        
        return execution_ids
    
    async def _cleanup_expired_data(self) -> None:
        """Periodically clean up expired data."""
        while self._initialized:
            try:
                current_time = datetime.now().timestamp()
                expired_keys = []
                
                # Check executions
                for execution_id, stored_data in self._memory_store['executions'].items():
                    if stored_data['expires_at'] < current_time:
                        expired_keys.append(execution_id)
                
                # Remove expired entries
                for key in expired_keys:
                    del self._memory_store['executions'][key]
                
                if expired_keys:
                    self.logger.info(f"Cleaned up {len(expired_keys)} expired executions")
                
                # Wait for next cleanup cycle
                await asyncio.sleep(self.config.cleanup_interval)
                
            except Exception as e:
                self.logger.error(f"Error during cleanup: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying
    
    async def delete_execution(self, execution_id: str) -> bool:
        """Delete execution state."""
        if not self._initialized:
            raise RuntimeError("StateManager not initialized")
        
        async with self._distributed_lock(execution_id):
            if execution_id in self._memory_store['executions']:
                del self._memory_store['executions'][execution_id]
                return True
            return False
    
    async def cleanup_expired_executions(self) -> int:
        """Clean up expired executions (manual cleanup for debugging)."""
        if not self._initialized:
            raise RuntimeError("StateManager not initialized")
        
        current_time = datetime.now().timestamp()
        expired_keys = []
        
        for execution_id, stored_data in self._memory_store['executions'].items():
            if stored_data['expires_at'] < current_time:
                expired_keys.append(execution_id)
        
        # Remove expired entries
        for key in expired_keys:
            del self._memory_store['executions'][key]
        
        return len(expired_keys)
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get StateManager statistics."""
        if not self._initialized:
            raise RuntimeError("StateManager not initialized")
        
        current_time = datetime.now().timestamp()
        active_executions = 0
        expired_executions = 0
        
        for stored_data in self._memory_store['executions'].values():
            if stored_data['expires_at'] >= current_time:
                active_executions += 1
            else:
                expired_executions += 1
        
        stats = {
            "total_executions": len(self._memory_store['executions']),
            "active_executions": active_executions,
            "expired_executions": expired_executions,
            "memory_usage": {
                "executions_count": len(self._memory_store['executions']),
                "teams_count": len(self._memory_store['teams']),
                "agents_count": len(self._memory_store['agents']),
                "events_count": len(self._memory_store['events'])
            },
            "config": self.config.model_dump()
        }
        
        # Count by status
        status_counts = {}
        for execution_id in list(self._memory_store['executions'].keys())[:50]:  # Limit to prevent performance issues
            state = await self.get_execution_state(execution_id)
            if state:
                status = state.status.value
                status_counts[status] = status_counts.get(status, 0) + 1
        
        stats["status_distribution"] = status_counts
        
        return stats


# Utility functions for common operations
async def create_state_manager() -> StateManager:
    """Create and initialize a StateManager instance."""
    config = StateManagerConfig()
    manager = StateManager(config)
    await manager.initialize()
    return manager


async def with_state_manager(func):
    """Context manager for StateManager operations."""
    manager = await create_state_manager()
    try:
        return await func(manager)
    finally:
        await manager.close()