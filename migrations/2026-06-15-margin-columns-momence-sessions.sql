-- Migration: 2026-06-15 — Margin columns for momence_sessions + teacher cost
--
-- Adds est_revenue, teacher_cost, margin, margin_calculated_at to momence_sessions.
-- Adds cost_per_class to teachers.
-- Creates index on margin_calculated_at for efficient incremental sync.
--
-- Applied: 2026-06-15 via Supabase MCP (apply_migration).
-- Safe to re-run (IF NOT EXISTS / IF NOT EXISTS guards).

-- momence_sessions new columns
ALTER TABLE momence_sessions
  ADD COLUMN IF NOT EXISTS est_revenue           NUMERIC,
  ADD COLUMN IF NOT EXISTS teacher_cost          NUMERIC,
  ADD COLUMN IF NOT EXISTS margin                NUMERIC,
  ADD COLUMN IF NOT EXISTS margin_calculated_at  TIMESTAMPTZ;

-- teachers new column
ALTER TABLE teachers
  ADD COLUMN IF NOT EXISTS cost_per_class  NUMERIC;

-- Index to quickly find stale/uncomputed rows
CREATE INDEX IF NOT EXISTS idx_momence_sessions_margin_calculated_at
  ON momence_sessions (margin_calculated_at);

COMMENT ON COLUMN momence_sessions.est_revenue IS
  'Estimated class revenue. Requires per-booking FP/non-FP split to compute accurately.';
COMMENT ON COLUMN momence_sessions.teacher_cost IS
  'Teacher cost for the session, sourced from teachers.cost_per_class. Uses substitute cost when applicable.';
COMMENT ON COLUMN momence_sessions.margin IS
  'margin = est_revenue - teacher_cost. Negative when revenue not yet populated (cost-only).';
COMMENT ON COLUMN momence_sessions.margin_calculated_at IS
  'Timestamp (UTC) when margin was last computed by margin_sync.py.';
COMMENT ON COLUMN teachers.cost_per_class IS
  'Standard cost paid to the teacher per class taught. Used by margin_sync.py.';
