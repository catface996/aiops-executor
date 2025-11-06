"""
Teams API endpoints for hierarchical multi-agent system.

This module provides HTTP endpoints for creating and managing hierarchical teams.
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse

from ..config_manager import ConfigManager, ConfigValidationError
from ..hierarchical_manager import HierarchicalManager, HierarchicalManagerError
from ..data_models import (
    HierarchicalTeam,
    TeamCreationResponse,
    APIResponse
)

logger = logging.getLogger(__name__)

# Create router for teams endpoints
router = APIRouter(prefix="/api/v1", tags=["teams"])

# Global instances (will be properly initialized in main app)
config_manager = ConfigManager()
hierarchical_manager = HierarchicalManager()


@router.post(
    "/hierarchical-teams",
    response_model=TeamCreationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Hierarchical Team",
    description="Create a new hierarchical team structure from configuration",
    responses={
        201: {
            "description": "Team created successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "code": "TEAM_CREATED",
                        "message": "分层团队创建成功",
                        "data": {
                            "team_id": "ht_123456789",
                            "team_name": "research_analysis_team",
                            "status": "created",
                            "created_at": "2024-01-15T10:30:00Z",
                            "sub_teams_count": 2,
                            "total_agents": 3,
                            "execution_order": ["team_a7b9c2d4e5f6", "team_x8y9z1a2b3c4"]
                        }
                    }
                }
            }
        },
        400: {
            "description": "Invalid request data",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "code": "VALIDATION_ERROR",
                        "message": "配置验证失败",
                        "detail": "Missing required fields: ['team_name']"
                    }
                }
            }
        },
        422: {
            "description": "Validation error",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "code": "VALIDATION_ERROR", 
                        "message": "请求数据格式错误",
                        "detail": "Invalid JSON structure"
                    }
                }
            }
        },
        500: {
            "description": "Internal server error",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "code": "INTERNAL_ERROR",
                        "message": "服务器内部错误",
                        "detail": "Failed to create team"
                    }
                }
            }
        }
    }
)
async def create_hierarchical_team(team_config: Dict[str, Any]) -> TeamCreationResponse:
    """
    Create a new hierarchical team structure.
    
    This endpoint accepts a hierarchical team configuration and creates
    the corresponding team structure with all supervisors and agents.
    
    Args:
        team_config: Dictionary containing the complete team configuration
        
    Returns:
        TeamCreationResponse: Response containing team creation details
        
    Raises:
        HTTPException: If validation fails or team creation fails
    """
    try:
        logger.info(f"Received team creation request for: {team_config.get('team_name', 'unnamed')}")
        
        # Validate the configuration structure and business logic
        try:
            validated_team = config_manager.validate_config_dict(team_config)
        except ConfigValidationError as e:
            logger.warning(f"Configuration validation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "success": False,
                    "code": "VALIDATION_ERROR",
                    "message": "配置验证失败",
                    "detail": str(e)
                }
            )
        except Exception as e:
            logger.error(f"Unexpected validation error: {e}")
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "success": False,
                    "code": "VALIDATION_ERROR",
                    "message": "请求数据格式错误",
                    "detail": str(e)
                }
            )
        
        # Build the hierarchical team structure
        try:
            built_team = hierarchical_manager.build_hierarchy(team_config)
        except HierarchicalManagerError as e:
            logger.error(f"Team building failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "success": False,
                    "code": "TEAM_BUILD_ERROR",
                    "message": "团队构建失败",
                    "detail": str(e)
                }
            )
        except Exception as e:
            logger.error(f"Unexpected team building error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "success": False,
                    "code": "INTERNAL_ERROR",
                    "message": "服务器内部错误",
                    "detail": "Failed to build team structure"
                }
            )
        
        # Generate unique team ID
        team_id = f"ht_{uuid.uuid4().hex[:9]}"
        
        # Store team configuration in memory for later execution
        from .executions import _store_team_config_in_memory
        _store_team_config_in_memory(team_id, team_config)
        
        # Calculate execution order
        try:
            execution_order = config_manager.get_execution_order(validated_team)
        except ConfigValidationError as e:
            logger.error(f"Failed to calculate execution order: {e}")
            execution_order = [team.id for team in validated_team.sub_teams]
        
        # Count total agents
        total_agents = sum(len(sub_team.agent_configs) for sub_team in validated_team.sub_teams)
        
        # Create response data
        response_data = {
            "team_id": team_id,
            "team_name": validated_team.team_name,
            "status": "created",
            "created_at": datetime.now().isoformat() + "Z",
            "sub_teams_count": len(validated_team.sub_teams),
            "total_agents": total_agents,
            "execution_order": execution_order
        }
        
        logger.info(f"Successfully created team '{validated_team.team_name}' with ID: {team_id}")
        
        return TeamCreationResponse(
            success=True,
            code="TEAM_CREATED",
            message="分层团队创建成功",
            data=response_data
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        # Handle any unexpected errors
        logger.error(f"Unexpected error in create_hierarchical_team: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "code": "INTERNAL_ERROR",
                "message": "服务器内部错误",
                "detail": "An unexpected error occurred"
            }
        )


@router.get(
    "/hierarchical-teams/{team_id}",
    response_model=Dict[str, Any],
    summary="Get Team Information",
    description="Retrieve information about a specific hierarchical team",
    responses={
        200: {
            "description": "Team information retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "code": "TEAM_FOUND",
                        "message": "团队信息获取成功",
                        "data": {
                            "team_id": "ht_123456789",
                            "team_name": "research_analysis_team",
                            "status": "created",
                            "sub_teams_count": 2,
                            "total_agents": 3
                        }
                    }
                }
            }
        },
        404: {
            "description": "Team not found",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "code": "TEAM_NOT_FOUND",
                        "message": "团队未找到",
                        "detail": "Team with ID 'ht_123456789' not found"
                    }
                }
            }
        }
    }
)
async def get_team_info(team_id: str) -> Dict[str, Any]:
    """
    Get information about a specific hierarchical team.
    
    Args:
        team_id: The unique team identifier
        
    Returns:
        Dict containing team information
        
    Raises:
        HTTPException: If team is not found
    """
    try:
        logger.info(f"Retrieving team information for ID: {team_id}")
        
        # For now, return a placeholder response since we don't have persistent storage
        # In a real implementation, this would query a database or cache
        
        # Validate team_id format
        if not team_id.startswith("ht_") or len(team_id) != 12:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "success": False,
                    "code": "TEAM_NOT_FOUND",
                    "message": "团队未找到",
                    "detail": f"Invalid team ID format: {team_id}"
                }
            )
        
        # Placeholder response - in real implementation, fetch from storage
        response_data = {
            "team_id": team_id,
            "team_name": "placeholder_team",
            "status": "created",
            "created_at": datetime.now().isoformat() + "Z",
            "sub_teams_count": 0,
            "total_agents": 0,
            "execution_order": []
        }
        
        return {
            "success": True,
            "code": "TEAM_FOUND",
            "message": "团队信息获取成功",
            "data": response_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in get_team_info: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "code": "INTERNAL_ERROR",
                "message": "服务器内部错误",
                "detail": "Failed to retrieve team information"
            }
        )


@router.delete(
    "/hierarchical-teams/{team_id}",
    response_model=APIResponse,
    summary="Delete Team",
    description="Delete a hierarchical team",
    responses={
        200: {
            "description": "Team deleted successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "code": "TEAM_DELETED",
                        "message": "团队删除成功"
                    }
                }
            }
        },
        404: {
            "description": "Team not found",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "code": "TEAM_NOT_FOUND",
                        "message": "团队未找到"
                    }
                }
            }
        }
    }
)
async def delete_team(team_id: str) -> APIResponse:
    """
    Delete a hierarchical team.
    
    Args:
        team_id: The unique team identifier
        
    Returns:
        APIResponse: Confirmation of deletion
        
    Raises:
        HTTPException: If team is not found
    """
    try:
        logger.info(f"Deleting team with ID: {team_id}")
        
        # Validate team_id format
        if not team_id.startswith("ht_") or len(team_id) != 12:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "success": False,
                    "code": "TEAM_NOT_FOUND",
                    "message": "团队未找到",
                    "detail": f"Invalid team ID format: {team_id}"
                }
            )
        
        # In a real implementation, this would delete from storage
        logger.info(f"Successfully deleted team: {team_id}")
        
        return APIResponse(
            success=True,
            code="TEAM_DELETED",
            message="团队删除成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in delete_team: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "code": "INTERNAL_ERROR",
                "message": "服务器内部错误",
                "detail": "Failed to delete team"
            }
        )


@router.get(
    "/hierarchical-teams",
    response_model=Dict[str, Any],
    summary="List Teams",
    description="List all hierarchical teams",
    responses={
        200: {
            "description": "Teams listed successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "code": "TEAMS_LISTED",
                        "message": "团队列表获取成功",
                        "data": {
                            "teams": [],
                            "total_count": 0,
                            "page": 1,
                            "page_size": 10
                        }
                    }
                }
            }
        }
    }
)
async def list_teams(page: int = 1, page_size: int = 10) -> Dict[str, Any]:
    """
    List all hierarchical teams with pagination.
    
    Args:
        page: Page number (default: 1)
        page_size: Number of teams per page (default: 10)
        
    Returns:
        Dict containing list of teams and pagination info
    """
    try:
        logger.info(f"Listing teams - page: {page}, page_size: {page_size}")
        
        # Validate pagination parameters
        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:
            page_size = 10
        
        # In a real implementation, this would query from storage
        response_data = {
            "teams": [],  # Placeholder - would contain actual team data
            "total_count": 0,
            "page": page,
            "page_size": page_size
        }
        
        return {
            "success": True,
            "code": "TEAMS_LISTED",
            "message": "团队列表获取成功",
            "data": response_data
        }
        
    except Exception as e:
        logger.error(f"Unexpected error in list_teams: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "code": "INTERNAL_ERROR",
                "message": "服务器内部错误",
                "detail": "Failed to list teams"
            }
        )


# Health check endpoint for the teams API
@router.get(
    "/teams/health",
    response_model=Dict[str, Any],
    summary="Teams API Health Check",
    description="Check the health status of the teams API",
    responses={
        200: {
            "description": "API is healthy",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "code": "HEALTHY",
                        "message": "Teams API is healthy",
                        "data": {
                            "status": "healthy",
                            "timestamp": "2024-01-15T10:30:00Z",
                            "version": "1.0.0"
                        }
                    }
                }
            }
        }
    }
)
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint for the teams API.
    
    Returns:
        Dict containing health status information
    """
    return {
        "success": True,
        "code": "HEALTHY",
        "message": "Teams API is healthy",
        "data": {
            "status": "healthy",
            "timestamp": datetime.now().isoformat() + "Z",
            "version": "1.0.0",
            "components": {
                "config_manager": "initialized",
                "hierarchical_manager": "initialized"
            }
        }
    }