"""
Hierarchical execution coordinator for multi-agent system.

This module implements the core hierarchical execution logic that coordinates
the three-layer execution flow: top-level supervisor → sub-team supervisors → agents.
It handles dependency resolution, execution order, state synchronization, and error propagation.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple
from contextlib import asynccontextmanager

from .data_models import (
    HierarchicalTeam, SubTeam, AgentConfig, SupervisorConfig,
    ExecutionEvent, ExecutionStatus, TeamState, TeamResult,
    ExecutionContext, ExecutionConfig, ErrorInfo, AgentResult
)
from .agents import SupervisorAgent, WorkerAgent
from .state_manager import StateManager
from .event_manager import EventManager
from .error_handler import ErrorHandler, ErrorContext, ErrorCategory


class HierarchicalExecutionError(Exception):
    """Raised when hierarchical execution fails."""
    pass


class TeamExecutionContext:
    """Context for team execution within hierarchical structure."""
    
    def __init__(
        self,
        team_id: str,
        team_name: str,
        execution_id: str,
        parent_context: ExecutionContext,
        dependencies: List[str],
        supervisor: SupervisorAgent,
        agents: Dict[str, WorkerAgent]
    ):
        """Initialize team execution context."""
        self.team_id = team_id
        self.team_name = team_name
        self.execution_id = execution_id
        self.parent_context = parent_context
        self.dependencies = dependencies
        self.supervisor = supervisor
        self.agents = agents
        
        # Execution state
        self.status = ExecutionStatus.PENDING
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.current_agent: Optional[str] = None
        self.agent_results: Dict[str, AgentResult] = {}
        self.errors: List[ErrorInfo] = []
        
        # Dependency tracking
        self.dependencies_met = len(dependencies) == 0
        self.waiting_for_dependencies: Set[str] = set(dependencies)
    
    def mark_dependency_completed(self, dependency_id: str) -> None:
        """Mark a dependency as completed."""
        self.waiting_for_dependencies.discard(dependency_id)
        self.dependencies_met = len(self.waiting_for_dependencies) == 0
    
    def is_ready_to_execute(self) -> bool:
        """Check if team is ready to execute (all dependencies met)."""
        return self.dependencies_met and self.status == ExecutionStatus.PENDING
    
    def get_available_agents(self) -> List[Dict[str, Any]]:
        """Get list of available agents for supervisor routing."""
        available_agents = []
        
        for agent_id, agent in self.agents.items():
            if hasattr(agent, 'config') and agent.config:
                available_agents.append({
                    "name": agent.config.agent_name,
                    "id": agent.config.agent_id,
                    "description": agent.config.system_prompt[:200] + "...",
                    "capabilities": agent.config.tools,
                    "tools": agent.config.tools
                })
        
        return available_agents


class HierarchicalExecutor:
    """
    Hierarchical execution coordinator for multi-agent system.
    
    This class implements the core hierarchical execution logic that:
    - Coordinates three-layer execution flow (top supervisor → team supervisors → agents)
    - Handles dependency resolution and execution order
    - Manages state synchronization across all layers
    - Provides error propagation and recovery mechanisms
    """
    
    def __init__(
        self,
        state_manager: StateManager,
        event_manager: EventManager,
        error_handler: Optional[ErrorHandler] = None
    ):
        """
        Initialize hierarchical executor.
        
        Args:
            state_manager: State manager for execution state
            event_manager: Event manager for streaming events
            error_handler: Error handler for managing failures
        """
        self.state_manager = state_manager
        self.event_manager = event_manager
        self.error_handler = error_handler or ErrorHandler()
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        
        # Execution state
        self._active_executions: Dict[str, Dict[str, TeamExecutionContext]] = {}
        self._execution_lock = asyncio.Lock()
    
    async def execute_hierarchical_team(
        self,
        team: HierarchicalTeam,
        execution_context: ExecutionContext
    ) -> Dict[str, TeamResult]:
        """
        Execute hierarchical team with full coordination.
        
        Args:
            team: Hierarchical team to execute
            execution_context: Execution context
            
        Returns:
            Dict[str, TeamResult]: Results from all team executions
            
        Raises:
            HierarchicalExecutionError: If execution fails
        """
        execution_id = execution_context.execution_id
        
        try:
            self.logger.info(f"Starting hierarchical execution for team: {team.team_name}")
            
            # Initialize execution context
            await self._initialize_execution_context(team, execution_context)
            
            # Execute teams according to dependency order
            results = await self._execute_teams_in_order(team, execution_context)
            
            self.logger.info(f"Completed hierarchical execution for team: {team.team_name}")
            return results
            
        except Exception as e:
            self.logger.error(f"Hierarchical execution failed for {team.team_name}: {e}")
            
            # Handle execution error
            error_context = ErrorContext(
                execution_id=execution_id,
                team_id=team.team_name,
                operation="hierarchical_execution",
                metadata={"team_name": team.team_name, "error": str(e)}
            )
            
            await self.error_handler.handle_error_async(e, error_context)
            raise HierarchicalExecutionError(f"Hierarchical execution failed: {e}")
        
        finally:
            # Cleanup execution context
            async with self._execution_lock:
                self._active_executions.pop(execution_id, None)
    
    async def _initialize_execution_context(
        self,
        team: HierarchicalTeam,
        execution_context: ExecutionContext
    ) -> None:
        """Initialize execution context for hierarchical team."""
        execution_id = execution_context.execution_id
        
        async with self._execution_lock:
            team_contexts = {}
            
            # Create team execution contexts
            for sub_team in team.sub_teams:
                # Get agents from built team
                agents = {}
                if team.teams and sub_team.id in team.teams:
                    team_data = team.teams[sub_team.id]
                    agents = team_data.get("agents", {})
                
                # Get supervisor from built team
                supervisor = None
                if team.teams and sub_team.id in team.teams:
                    team_data = team.teams[sub_team.id]
                    supervisor = team_data.get("supervisor")
                
                if not supervisor:
                    raise HierarchicalExecutionError(f"No supervisor found for team {sub_team.id}")
                
                # Get dependencies for this team
                dependencies = team.dependencies.get(sub_team.id, [])
                
                team_context = TeamExecutionContext(
                    team_id=sub_team.id,
                    team_name=sub_team.name,
                    execution_id=execution_id,
                    parent_context=execution_context,
                    dependencies=dependencies,
                    supervisor=supervisor,
                    agents=agents
                )
                
                # If no dependencies, mark as ready immediately
                if not dependencies:
                    team_context.dependencies_met = True
                    team_context.waiting_for_dependencies = set()
                
                team_contexts[sub_team.id] = team_context
            
            self._active_executions[execution_id] = team_contexts
            
            # Initialize team states in state manager
            for team_id, context in team_contexts.items():
                team_state = TeamState(
                    next="pending",
                    team_id=team_id,
                    dependencies_met=context.dependencies_met,
                    execution_status=ExecutionStatus.PENDING
                )
                await self.state_manager.update_team_state(execution_id, team_id, team_state)
    
    async def _execute_teams_in_order(
        self,
        team: HierarchicalTeam,
        execution_context: ExecutionContext
    ) -> Dict[str, TeamResult]:
        """Execute teams according to dependency order."""
        execution_id = execution_context.execution_id
        results = {}
        
        if not team.execution_order:
            raise HierarchicalExecutionError("No execution order defined for hierarchical team")
        
        # Execute teams in dependency order
        for team_id in team.execution_order:
            try:
                self.logger.info(f"Executing team: {team_id}")
                
                # Wait for dependencies to be met
                await self._wait_for_dependencies(execution_id, team_id)
                
                # Execute team with top-level supervisor coordination
                result = await self._execute_single_team(team, team_id, execution_context)
                results[team_id] = result
                
                # Mark team as completed for dependent teams
                await self._mark_team_completed(execution_id, team_id)
                
                self.logger.info(f"Completed team: {team_id}")
                
            except Exception as e:
                self.logger.error(f"Team execution failed for {team_id}: {e}")
                
                # Handle team execution error
                error_context = ErrorContext(
                    execution_id=execution_id,
                    team_id=team_id,
                    operation="team_execution",
                    metadata={"team_id": team_id, "error": str(e)}
                )
                
                # Try to recover or continue with other teams
                recovery_result = await self.error_handler.handle_error_async(e, error_context)
                
                # Always mark as failed when there's an exception
                results[team_id] = TeamResult(
                    status="failed",
                    duration=0,
                    output=f"Team execution failed: {str(e)}",
                    agents={}
                )
                
                # Still mark as completed to unblock dependent teams
                await self._mark_team_completed(execution_id, team_id)
        
        return results
    
    async def _wait_for_dependencies(self, execution_id: str, team_id: str) -> None:
        """Wait for team dependencies to be completed."""
        async with self._execution_lock:
            team_contexts = self._active_executions.get(execution_id, {})
            team_context = team_contexts.get(team_id)
            
            if not team_context:
                raise HierarchicalExecutionError(f"Team context not found: {team_id}")
        
        # Wait for dependencies with timeout
        max_wait_time = 30   # 30 seconds for tests
        wait_interval = 0.1  # 100ms
        waited_time = 0
        
        while not team_context.is_ready_to_execute() and waited_time < max_wait_time:
            await asyncio.sleep(wait_interval)
            waited_time += wait_interval
            
            # Check if dependencies are met
            async with self._execution_lock:
                team_contexts = self._active_executions.get(execution_id, {})
                team_context = team_contexts.get(team_id)
                if team_context and team_context.is_ready_to_execute():
                    break
        
        if not team_context.is_ready_to_execute():
            raise HierarchicalExecutionError(
                f"Dependencies not met for team {team_id} after {max_wait_time} seconds. "
                f"Waiting for: {team_context.waiting_for_dependencies}"
            )
    
    async def _execute_single_team(
        self,
        hierarchical_team: HierarchicalTeam,
        team_id: str,
        execution_context: ExecutionContext
    ) -> TeamResult:
        """Execute a single team with supervisor coordination."""
        execution_id = execution_context.execution_id
        
        # Get team context
        async with self._execution_lock:
            team_contexts = self._active_executions.get(execution_id, {})
            team_context = team_contexts.get(team_id)
            
            if not team_context:
                raise HierarchicalExecutionError(f"Team context not found: {team_id}")
        
        start_time = datetime.now()
        team_context.status = ExecutionStatus.RUNNING
        team_context.started_at = start_time
        
        try:
            # Update team state
            team_state = TeamState(
                next="running",
                team_id=team_id,
                dependencies_met=True,
                execution_status=ExecutionStatus.RUNNING
            )
            await self.state_manager.update_team_state(execution_id, team_id, team_state)
            
            # Step 1: Top-level supervisor selects this team (already done by execution order)
            await self._emit_team_selection_event(execution_id, hierarchical_team, team_id)
            
            # Step 2: Execute team with internal supervisor coordination
            agent_results = await self._execute_team_with_supervisor(team_context)
            
            # Step 3: Collect and format results
            end_time = datetime.now()
            duration = int((end_time - start_time).total_seconds())
            
            team_context.status = ExecutionStatus.COMPLETED
            team_context.completed_at = end_time
            team_context.agent_results = agent_results
            
            # Create team result
            result = TeamResult(
                status="completed",
                duration=duration,
                agents=agent_results,
                output=self._format_team_output(agent_results)
            )
            
            # Update state manager
            await self.state_manager.update_team_result(execution_id, team_id, result)
            
            # Update team state
            team_state.execution_status = ExecutionStatus.COMPLETED
            team_state.next = "completed"
            await self.state_manager.update_team_state(execution_id, team_id, team_state)
            
            return result
            
        except Exception as e:
            # Handle team execution error
            end_time = datetime.now()
            duration = int((end_time - start_time).total_seconds())
            
            team_context.status = ExecutionStatus.FAILED
            team_context.completed_at = end_time
            
            error_info = ErrorInfo(
                error_code="TEAM_EXECUTION_FAILED",
                message=str(e),
                timestamp=datetime.now(),
                context={"team_id": team_id, "execution_id": execution_id}
            )
            team_context.errors.append(error_info)
            
            # Update state manager
            await self.state_manager.add_error(execution_id, error_info)
            
            team_state = TeamState(
                next="failed",
                team_id=team_id,
                dependencies_met=True,
                execution_status=ExecutionStatus.FAILED
            )
            await self.state_manager.update_team_state(execution_id, team_id, team_state)
            
            # Create failed result instead of raising exception
            result = TeamResult(
                status="failed",
                duration=duration,
                agents={},
                output=f"Team execution failed: {str(e)}"
            )
            
            # Update state manager with failed result
            await self.state_manager.update_team_result(execution_id, team_id, result)
            
            return result
    
    async def _emit_team_selection_event(
        self,
        execution_id: str,
        hierarchical_team: HierarchicalTeam,
        selected_team_id: str
    ) -> None:
        """Emit event for top-level supervisor team selection."""
        # Find the selected team name
        selected_team_name = None
        for sub_team in hierarchical_team.sub_teams:
            if sub_team.id == selected_team_id:
                selected_team_name = sub_team.name
                break
        
        await self.event_manager.emit_supervisor_routing(
            execution_id=execution_id,
            supervisor_id="top_supervisor",
            supervisor_name="顶级监督者",
            team_id=hierarchical_team.team_name,
            content=f"Top-level supervisor selected team: {selected_team_name or selected_team_id}",
            selected_team=selected_team_id
        )
    
    async def _execute_team_with_supervisor(
        self,
        team_context: TeamExecutionContext
    ) -> Dict[str, AgentResult]:
        """Execute team with internal supervisor coordination."""
        if not team_context.agents:
            self.logger.warning(f"No agents found for team {team_context.team_id}")
            return {}
        
        agent_results = {}
        
        try:
            # Get available agents for supervisor routing
            available_agents = team_context.get_available_agents()
            
            if not available_agents:
                self.logger.warning(f"No available agents for team {team_context.team_id}")
                return {}
            
            # Team supervisor makes routing decision
            selected_agent_name = await self._supervisor_route_to_agent(
                team_context, available_agents
            )
            
            # Find the selected agent
            selected_agent = None
            selected_agent_id = None
            
            for agent_id, agent in team_context.agents.items():
                if hasattr(agent, 'config') and agent.config.agent_name == selected_agent_name:
                    selected_agent = agent
                    selected_agent_id = agent_id
                    break
            
            if not selected_agent:
                # Fallback: use first available agent
                selected_agent_id = list(team_context.agents.keys())[0]
                selected_agent = team_context.agents[selected_agent_id]
                self.logger.warning(
                    f"Selected agent '{selected_agent_name}' not found, using fallback: {selected_agent_id}"
                )
            
            # Execute selected agent
            team_context.current_agent = selected_agent_id
            
            # Emit agent start event
            await self.event_manager.emit_agent_started(
                execution_id=team_context.execution_id,
                team_id=team_context.team_id,
                agent_id=selected_agent_id,
                agent_name=selected_agent.config.agent_name if hasattr(selected_agent, 'config') else selected_agent_id,
                content=f"Starting execution of {selected_agent.config.agent_name if hasattr(selected_agent, 'config') else selected_agent_id}"
            )
            
            # Execute agent
            agent_result = await self._execute_agent(selected_agent, team_context)
            agent_results[selected_agent_id] = agent_result
            
            # Emit agent completion event with full content
            full_result = str(agent_result.get("output", ""))
            await self.event_manager.emit_agent_completed(
                execution_id=team_context.execution_id,
                team_id=team_context.team_id,
                agent_id=selected_agent_id,
                agent_name=selected_agent.config.agent_name if hasattr(selected_agent, 'config') else selected_agent_id,
                result=full_result  # Send complete result without truncation
            )
            
            return agent_results
            
        except Exception as e:
            self.logger.error(f"Team supervisor execution failed for {team_context.team_id}: {e}")
            raise
    
    async def _supervisor_route_to_agent(
        self,
        team_context: TeamExecutionContext,
        available_agents: List[Dict[str, Any]]
    ) -> str:
        """Have team supervisor route task to appropriate agent."""
        try:
            # Create task description for routing
            task_description = f"Execute team task for {team_context.team_name}"
            
            # Use supervisor's intelligent routing
            selected_agent = team_context.supervisor.route_task_intelligently(
                task=task_description,
                available_agents=available_agents,
                execution_id=team_context.execution_id
            )
            
            # Emit supervisor routing event
            await self.event_manager.emit_supervisor_routing(
                execution_id=team_context.execution_id,
                supervisor_id=f"supervisor_{team_context.team_id}",
                supervisor_name=f"{team_context.team_name}监督者",
                team_id=team_context.team_id,
                content=f"Team supervisor selected agent: {selected_agent}",
                selected_agent=selected_agent
            )
            
            return selected_agent
            
        except Exception as e:
            self.logger.error(f"Supervisor routing failed for team {team_context.team_id}: {e}")
            # Fallback to first available agent
            if available_agents:
                fallback_agent = available_agents[0]["name"]
                self.logger.warning(f"Using fallback agent: {fallback_agent}")
                return fallback_agent
            else:
                raise HierarchicalExecutionError(f"No agents available for routing in team {team_context.team_id}")
    
    async def _execute_agent(
        self,
        agent: WorkerAgent,
        team_context: TeamExecutionContext
    ) -> AgentResult:
        """Execute a single agent within team context."""
        try:
            # Create execution context for agent
            agent_context = {
                "team_id": team_context.team_id,
                "team_name": team_context.team_name,
                "execution_id": team_context.execution_id
            }
            
            # Execute agent (this will handle tool integration automatically)
            result = agent.execute(
                execution_id=team_context.execution_id,
                context=agent_context
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Agent execution failed: {e}")
            
            # Create error result and re-raise to propagate error up
            error_result = {
                "agent_id": getattr(agent.config, 'agent_id', 'unknown') if hasattr(agent, 'config') else 'unknown',
                "agent_name": getattr(agent.config, 'agent_name', 'unknown') if hasattr(agent, 'config') else 'unknown',
                "status": "failed",
                "output": f"Agent execution failed: {str(e)}",
                "execution_time": 0,
                "tools_used": [],
                "error": str(e),
                "metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "team_id": team_context.team_id
                }
            }
            
            # Store the error result in team context
            team_context.agent_results[getattr(agent.config, 'agent_id', 'unknown') if hasattr(agent, 'config') else 'unknown'] = error_result
            
            # Re-raise the exception to propagate error up the chain
            raise
    
    def _format_team_output(self, agent_results: Dict[str, AgentResult]) -> str:
        """Format team output from agent results."""
        if not agent_results:
            return "No agent results available"
        
        output_parts = []
        for agent_id, result in agent_results.items():
            agent_name = result.get("agent_name", agent_id)
            agent_output = result.get("output", "No output")
            status = result.get("status", "unknown")
            
            output_parts.append(f"Agent {agent_name} ({status}): {agent_output}")
        
        return "\n\n".join(output_parts)
    
    async def _mark_team_completed(self, execution_id: str, team_id: str) -> None:
        """Mark team as completed and update dependent teams."""
        async with self._execution_lock:
            team_contexts = self._active_executions.get(execution_id, {})
            
            # Update all teams that depend on this team
            for context in team_contexts.values():
                if team_id in context.waiting_for_dependencies:
                    context.mark_dependency_completed(team_id)
                    
                    # Update team state if dependencies are now met
                    if context.dependencies_met and context.status == ExecutionStatus.PENDING:
                        team_state = TeamState(
                            next="ready",
                            team_id=context.team_id,
                            dependencies_met=True,
                            execution_status=ExecutionStatus.PENDING
                        )
                        await self.state_manager.update_team_state(execution_id, context.team_id, team_state)
    
    async def get_execution_progress(self, execution_id: str) -> Dict[str, Any]:
        """Get current execution progress."""
        async with self._execution_lock:
            team_contexts = self._active_executions.get(execution_id, {})
            
            if not team_contexts:
                return {"error": "Execution not found"}
            
            progress = {
                "execution_id": execution_id,
                "total_teams": len(team_contexts),
                "teams": {}
            }
            
            completed_count = 0
            for team_id, context in team_contexts.items():
                team_progress = {
                    "team_id": team_id,
                    "team_name": context.team_name,
                    "status": context.status.value,
                    "dependencies_met": context.dependencies_met,
                    "waiting_for": list(context.waiting_for_dependencies),
                    "current_agent": context.current_agent,
                    "started_at": context.started_at.isoformat() if context.started_at else None,
                    "completed_at": context.completed_at.isoformat() if context.completed_at else None
                }
                
                if context.status in [ExecutionStatus.COMPLETED, ExecutionStatus.FAILED]:
                    completed_count += 1
                
                progress["teams"][team_id] = team_progress
            
            progress["completed_teams"] = completed_count
            progress["overall_progress"] = int((completed_count / len(team_contexts)) * 100)
            
            return progress
    
    async def stop_execution(self, execution_id: str, graceful: bool = True) -> bool:
        """Stop hierarchical execution."""
        async with self._execution_lock:
            team_contexts = self._active_executions.get(execution_id, {})
            
            if not team_contexts:
                return False
            
            # Mark all running teams as stopped
            for context in team_contexts.values():
                if context.status == ExecutionStatus.RUNNING:
                    context.status = ExecutionStatus.FAILED
                    context.completed_at = datetime.now()
                    
                    # Update state manager
                    team_state = TeamState(
                        next="stopped",
                        team_id=context.team_id,
                        dependencies_met=context.dependencies_met,
                        execution_status=ExecutionStatus.FAILED
                    )
                    await self.state_manager.update_team_state(execution_id, context.team_id, team_state)
            
            # Remove from active executions
            del self._active_executions[execution_id]
            
            return True
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get hierarchical executor statistics."""
        async with self._execution_lock:
            active_count = len(self._active_executions)
            total_teams = sum(len(contexts) for contexts in self._active_executions.values())
            
            status_counts = {"pending": 0, "running": 0, "completed": 0, "failed": 0}
            for contexts in self._active_executions.values():
                for context in contexts.values():
                    status_counts[context.status.value] = status_counts.get(context.status.value, 0) + 1
            
            return {
                "active_executions": active_count,
                "total_teams": total_teams,
                "team_status_distribution": status_counts,
                "average_teams_per_execution": total_teams / active_count if active_count > 0 else 0
            }


# Utility functions for common operations
async def create_hierarchical_executor(
    state_manager: StateManager,
    event_manager: EventManager,
    error_handler: Optional[ErrorHandler] = None
) -> HierarchicalExecutor:
    """Create a HierarchicalExecutor instance."""
    return HierarchicalExecutor(state_manager, event_manager, error_handler)


@asynccontextmanager
async def hierarchical_executor_context(
    state_manager: StateManager,
    event_manager: EventManager,
    error_handler: Optional[ErrorHandler] = None
):
    """Context manager for HierarchicalExecutor operations."""
    executor = HierarchicalExecutor(state_manager, event_manager, error_handler)
    try:
        yield executor
    finally:
        # Cleanup any active executions
        pass