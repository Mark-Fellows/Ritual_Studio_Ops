-- Migration: teacher_absences table -- absence tracking
-- Applied: 2026-05-27
-- Phase: Teacher absence tracking (Phase 5 addition)
-- Additive only; parallel-run safe.
-- Database is shared by all Ritual apps -- this change is
-- immediately live for Teacher Management, Cover Management,
-- Momence_data, and the Dashboard once applied.

-- TABLE
CREATE TABLE IF NOT EXISTS teacher_absences (
  id                   UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
  teacher_id           UUID        NOT NULL REFERENCES teachers(id) ON DELETE CASCADE,
  start_date           DATE        NOT NULL,
  end_date             DATE        NOT NULL,
  end_date_approximate BOOLEAN     NOT NULL DEFAULT false,
  reason               TEXT        NOT NULL CHECK (reason IN ('holiday','sick','personal','training','other')),
  note                 TEXT,
  created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
  created_by           UUID        REFERENCES auth.users(id) ON DELETE SET NULL,
  deleted_at           TIMESTAMPTZ,
  deleted_by           UUID        REFERENCES auth.users(id) ON DELETE SET NULL,
  CONSTRAINT chk_end_gte_start CHECK (end_date >= start_date)
);

-- UPDATED_AT TRIGGER
CREATE OR REPLACE FUNCTION set_teacher_absences_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_teacher_absences_updated_at ON teacher_absences;
CREATE TRIGGER trg_teacher_absences_updated_at
  BEFORE UPDATE ON teacher_absences
  FOR EACH ROW EXECUTE FUNCTION set_teacher_absences_updated_at();

-- INDEXES
-- NOTE: CURRENT_DATE is STABLE (not IMMUTABLE) and cannot appear
-- in partial index predicates (L-MG-09). Date filtering happens
-- at query time only.
CREATE INDEX IF NOT EXISTS idx_teacher_absences_teacher
  ON teacher_absences (teacher_id)
  WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_teacher_absences_range
  ON teacher_absences (teacher_id, start_date, end_date)
  WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_teacher_absences_upcoming
  ON teacher_absences (teacher_id, end_date)
  WHERE deleted_at IS NULL;

-- RLS
ALTER TABLE teacher_absences ENABLE ROW LEVEL SECURITY;

-- Developers and administrators: full access
CREATE POLICY "Admins manage all absences"
  ON teacher_absences
  FOR ALL
  USING (
    (SELECT role FROM user_profiles WHERE user_id = auth.uid() LIMIT 1)
    IN ('developer','administrator')
  )
  WITH CHECK (
    (SELECT role FROM user_profiles WHERE user_id = auth.uid() LIMIT 1)
    IN ('developer','administrator')
  );

-- Adjudicators: read all active rows
CREATE POLICY "Adjudicators read absences"
  ON teacher_absences
  FOR SELECT
  USING (
    deleted_at IS NULL AND
    (SELECT role FROM user_profiles WHERE user_id = auth.uid() LIMIT 1)
    = 'adjudicator'
  );

-- Teachers: read their own active rows
CREATE POLICY "Teachers read own absences"
  ON teacher_absences
  FOR SELECT
  USING (
    deleted_at IS NULL AND
    teacher_id = (
      SELECT teacher_id FROM user_profiles
      WHERE user_id = auth.uid()
      LIMIT 1
    )
  );

-- Teachers: insert their own absence rows
CREATE POLICY "Teachers insert own absences"
  ON teacher_absences
  FOR INSERT
  WITH CHECK (
    teacher_id = (
      SELECT teacher_id FROM user_profiles
      WHERE user_id = auth.uid()
      LIMIT 1
    )
  );

-- Teachers: update their own active absence rows
CREATE POLICY "Teachers update own absences"
  ON teacher_absences
  FOR UPDATE
  USING (
    deleted_at IS NULL AND
    teacher_id = (
      SELECT teacher_id FROM user_profiles
      WHERE user_id = auth.uid()
      LIMIT 1
    )
  );
