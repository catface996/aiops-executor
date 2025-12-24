-- Migration: Add sequence column to execution_events table
-- Run this script to upgrade existing databases

-- Add sequence column
ALTER TABLE execution_events
ADD COLUMN IF NOT EXISTS sequence BIGINT NOT NULL DEFAULT 0 COMMENT 'Sequence number for ordering events within same second';

-- Drop old index and create new composite index
DROP INDEX IF EXISTS idx_timestamp ON execution_events;
CREATE INDEX idx_timestamp_sequence ON execution_events (timestamp, sequence);

-- Verify column exists
SELECT COLUMN_NAME, COLUMN_TYPE, COLUMN_COMMENT
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_NAME = 'execution_events'
AND COLUMN_NAME = 'sequence';
