-- T4 migration: add result_json column to agent_runs table
ALTER TABLE agent_runs ADD COLUMN IF NOT EXISTS result_json JSONB DEFAULT NULL;
