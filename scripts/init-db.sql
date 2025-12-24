-- Hierarchical Agents Database Initialization Script
-- This script creates all necessary tables for the hierarchical multi-agent system

SET NAMES utf8mb4;
SET CHARACTER SET utf8mb4;

-- AI Models Table
CREATE TABLE IF NOT EXISTS ai_models (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE COMMENT 'Model display name',
    model_id VARCHAR(200) NOT NULL COMMENT 'AWS Bedrock model ID',
    region VARCHAR(50) DEFAULT 'us-east-1' COMMENT 'AWS region',
    temperature FLOAT DEFAULT 0.7 COMMENT 'Temperature parameter',
    max_tokens INT DEFAULT 2048 COMMENT 'Max tokens',
    top_p FLOAT DEFAULT 0.9 COMMENT 'Top-P parameter',
    description TEXT COMMENT 'Model description',
    is_active TINYINT(1) DEFAULT 1 COMMENT 'Is active',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Hierarchy Teams Table (Main table)
CREATE TABLE IF NOT EXISTS hierarchy_teams (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE COMMENT 'Hierarchy team name',
    description TEXT COMMENT 'Description',
    global_prompt TEXT NOT NULL COMMENT 'Global supervisor prompt',
    execution_mode VARCHAR(20) DEFAULT 'sequential' COMMENT 'Execution mode: sequential/parallel',
    enable_context_sharing TINYINT(1) DEFAULT 0 COMMENT 'Enable context sharing',
    -- Global Supervisor LLM Config
    global_model_id VARCHAR(36) COMMENT 'Global Supervisor model ID',
    global_temperature FLOAT DEFAULT 0.7 COMMENT 'Global Supervisor temperature',
    global_max_tokens INT DEFAULT 2048 COMMENT 'Global Supervisor max tokens',
    global_top_p FLOAT DEFAULT 0.9 COMMENT 'Global Supervisor Top-P',
    is_active TINYINT(1) DEFAULT 1,
    version INT DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (global_model_id) REFERENCES ai_models(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Teams Table
CREATE TABLE IF NOT EXISTS teams (
    id VARCHAR(36) PRIMARY KEY,
    hierarchy_id VARCHAR(36) NOT NULL COMMENT 'Parent hierarchy ID',
    name VARCHAR(100) NOT NULL COMMENT 'Team name',
    supervisor_prompt TEXT NOT NULL COMMENT 'Team supervisor prompt',
    prevent_duplicate TINYINT(1) DEFAULT 1 COMMENT 'Prevent duplicate calls',
    share_context TINYINT(1) DEFAULT 0 COMMENT 'Share context',
    order_index INT DEFAULT 0 COMMENT 'Team order',
    -- Team Supervisor LLM Config
    model_id VARCHAR(36) COMMENT 'Team Supervisor model ID',
    temperature FLOAT DEFAULT 0.7 COMMENT 'Team Supervisor temperature',
    max_tokens INT DEFAULT 2048 COMMENT 'Team Supervisor max tokens',
    top_p FLOAT DEFAULT 0.9 COMMENT 'Team Supervisor Top-P',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (hierarchy_id) REFERENCES hierarchy_teams(id) ON DELETE CASCADE,
    FOREIGN KEY (model_id) REFERENCES ai_models(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Workers Table
CREATE TABLE IF NOT EXISTS workers (
    id VARCHAR(36) PRIMARY KEY,
    team_id VARCHAR(36) NOT NULL COMMENT 'Parent team ID',
    name VARCHAR(100) NOT NULL COMMENT 'Worker name',
    role VARCHAR(200) NOT NULL COMMENT 'Role description',
    system_prompt TEXT NOT NULL COMMENT 'System prompt',
    tools JSON COMMENT 'Tools list',
    order_index INT DEFAULT 0 COMMENT 'Worker order',
    -- Worker LLM Config
    model_id VARCHAR(36) COMMENT 'Worker model ID',
    temperature FLOAT DEFAULT 0.7 COMMENT 'Worker temperature',
    max_tokens INT DEFAULT 2048 COMMENT 'Worker max tokens',
    top_p FLOAT DEFAULT 0.9 COMMENT 'Worker Top-P',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE,
    FOREIGN KEY (model_id) REFERENCES ai_models(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Execution Runs Table
CREATE TABLE IF NOT EXISTS execution_runs (
    id VARCHAR(36) PRIMARY KEY,
    hierarchy_id VARCHAR(36) NOT NULL COMMENT 'Hierarchy team ID',
    task TEXT NOT NULL COMMENT 'Task description',
    status VARCHAR(20) DEFAULT 'pending' COMMENT 'Run status: pending/running/completed/failed/cancelled',
    result TEXT COMMENT 'Execution result',
    error TEXT COMMENT 'Error message',
    statistics JSON COMMENT 'Execution statistics',
    topology_snapshot JSON COMMENT 'Topology snapshot',
    started_at DATETIME,
    completed_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (hierarchy_id) REFERENCES hierarchy_teams(id) ON DELETE CASCADE,
    INDEX idx_hierarchy_id (hierarchy_id),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Execution Events Table
CREATE TABLE IF NOT EXISTS execution_events (
    id VARCHAR(36) PRIMARY KEY,
    run_id VARCHAR(36) NOT NULL COMMENT 'Execution run ID',
    event_type VARCHAR(50) NOT NULL COMMENT 'Event type',
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    sequence BIGINT NOT NULL DEFAULT 0 COMMENT 'Sequence number for ordering events within same second',
    data JSON COMMENT 'Event data',
    -- 来源标识
    is_global_supervisor TINYINT(1) DEFAULT 0 COMMENT 'Is from Global Supervisor',
    team_name VARCHAR(100) COMMENT 'Team name',
    is_team_supervisor TINYINT(1) DEFAULT 0 COMMENT 'Is from Team Supervisor',
    worker_name VARCHAR(100) COMMENT 'Worker name',
    FOREIGN KEY (run_id) REFERENCES execution_runs(id) ON DELETE CASCADE,
    INDEX idx_run_id (run_id),
    INDEX idx_event_type (event_type),
    INDEX idx_timestamp_sequence (timestamp, sequence)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Insert default AI model (Claude Sonnet)
INSERT INTO ai_models (id, name, model_id, region, temperature, max_tokens, top_p, description, is_active)
VALUES (
    UUID(),
    'Claude Sonnet 4',
    'us.anthropic.claude-sonnet-4-20250514-v1:0',
    'us-east-1',
    0.7,
    4096,
    0.9,
    'Anthropic Claude Sonnet 4 - Balanced performance and cost',
    1
) ON DUPLICATE KEY UPDATE name=name;

-- Insert Claude Opus model
INSERT INTO ai_models (id, name, model_id, region, temperature, max_tokens, top_p, description, is_active)
VALUES (
    UUID(),
    'Claude Opus 4',
    'us.anthropic.claude-opus-4-20250514-v1:0',
    'us-east-1',
    0.7,
    4096,
    0.9,
    'Anthropic Claude Opus 4 - Highest capability',
    1
) ON DUPLICATE KEY UPDATE name=name;

-- Insert Claude Haiku model
INSERT INTO ai_models (id, name, model_id, region, temperature, max_tokens, top_p, description, is_active)
VALUES (
    UUID(),
    'Claude Haiku 3.5',
    'us.anthropic.claude-3-5-haiku-20241022-v1:0',
    'us-east-1',
    0.7,
    4096,
    0.9,
    'Anthropic Claude Haiku 3.5 - Fast and economical',
    1
) ON DUPLICATE KEY UPDATE name=name;
