-- =============================================================================
-- Cover Management System — Stage 1 Schema Migration
-- Project:  rfjygyqijwgkmxboddup.supabase.co
-- Version:  1.0
-- Date:     2026-04-08
-- Run in:   Supabase SQL Editor (or psql)
-- =============================================================================
-- Idempotent: all statements use IF NOT EXISTS / ON CONFLICT DO NOTHING.
-- Safe to re-run after partial execution.
-- =============================================================================


-- ─────────────────────────────────────────────────────────────────────────────
-- 1.  Extend the existing teachers table
-- ─────────────────────────────────────────────────────────────────────────────

ALTER TABLE public.teachers
  ADD COLUMN IF NOT EXISTS whatsapp_phone     text,
  ADD COLUMN IF NOT EXISTS contact_preference text
    DEFAULT 'whatsapp_channel'
    CHECK (contact_preference IN (
      'whatsapp_channel',   -- post to monitored channel only
      'whatsapp_direct',    -- DM via whatsapp_phone
      'email',              -- email only
      'all'                 -- all available channels
    ));

COMMENT ON COLUMN public.teachers.whatsapp_phone IS
  'Teacher WhatsApp number in E.164 format, e.g. +61412345678. '
  'Used for direct cover-opportunity messages.';
COMMENT ON COLUMN public.teachers.contact_preference IS
  'Preferred channel(s) for cover notifications.';


-- ─────────────────────────────────────────────────────────────────────────────
-- 2.  System configuration (key-value store)
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.system_config (
  system_config_id  uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  config_key        text        NOT NULL UNIQUE,
  config_value      text        NOT NULL,
  description       text,
  updated_at        timestamptz DEFAULT now(),
  updated_by        text
);

COMMENT ON TABLE public.system_config IS
  'Configurable thresholds and defaults for the Cover Management System.';

INSERT INTO public.system_config (config_key, config_value, description) VALUES
  ('nlp_confidence_threshold',     '0.70',
   'Min NLP confidence to skip admin review (0.0-1.0). Below threshold sets auto_review_required=true.'),
  ('min_cover_notice_hours',       '2',
   'Minimum hours before class start for a cover request to be processed.'),
  ('whatsapp_poll_interval_hours', '4',
   'Target hours between WhatsApp monitoring runs.'),
  ('initial_teacher_grade',        '10',
   'Grade assigned when syncing a teacher from Momence with grade=0 for that discipline.'),
  ('cover_opportunity_ttl_hours',  '24',
   'Hours after which an unanswered cover opportunity is marked expired.'),
  ('max_candidates_per_request',   '10',
   'Maximum number of teachers to contact for a single cover request.')
ON CONFLICT (config_key) DO NOTHING;


-- ─────────────────────────────────────────────────────────────────────────────
-- 3.  WhatsApp channel configuration
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.whatsapp_channels (
  whatsapp_channel_id  uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  community_name       text        NOT NULL,
  channel_name         text        NOT NULL,
  is_active            boolean     NOT NULL DEFAULT true,
  monitor_order        int         NOT NULL DEFAULT 0,
  notes                text,
  created_at           timestamptz DEFAULT now(),
  updated_at           timestamptz DEFAULT now(),
  UNIQUE (community_name, channel_name)
);

COMMENT ON TABLE public.whatsapp_channels IS
  'WhatsApp community channels to monitor for cover requests. '
  'Stored here (not hardcoded) so names can be updated without code changes.';

INSERT INTO public.whatsapp_channels
  (community_name, channel_name, monitor_order, notes) VALUES
  ('RITUAL TEACHERS', 'RITUAL DIARY',         1, 'Primary diary/schedule announcements'),
  ('RITUAL TEACHERS', 'RITUAL TEACHERS',       2, 'General teacher communications'),
  ('RITUAL TEACHERS', 'RITUAL REFORMER TEAM',  3, 'Reformer Pilates cover requests'),
  ('RITUAL TEACHERS', 'Ritual Yin',            4, 'Yin Yoga cover requests')
ON CONFLICT (community_name, channel_name) DO NOTHING;


-- ─────────────────────────────────────────────────────────────────────────────
-- 4.  Discipline mappings
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.discipline_mappings (
  discipline_mapping_id  uuid     PRIMARY KEY DEFAULT gen_random_uuid(),
  momence_pattern        text     NOT NULL,
  pattern_type           text     NOT NULL DEFAULT 'contains'
    CHECK (pattern_type IN ('contains', 'regex', 'exact')),
  discipline_code        text     NOT NULL,
  priority               int      NOT NULL DEFAULT 0,
  is_active              boolean  NOT NULL DEFAULT true,
  notes                  text,
  created_at             timestamptz DEFAULT now(),
  UNIQUE (momence_pattern, discipline_code)
);

INSERT INTO public.discipline_mappings
  (momence_pattern, pattern_type, discipline_code, priority, notes) VALUES
  ('reformer',    'contains', 'reformer',    10, 'Reformer Pilates'),
  ('mat pilates', 'contains', 'mat_pilates', 10, 'Mat Pilates (space variant)'),
  ('mat_pilates', 'contains', 'mat_pilates',  9, 'Mat Pilates (underscore variant)'),
  ('yin',         'contains', 'yin',         10, 'Yin Yoga'),
  ('barre',       'contains', 'barre',       10, 'Barre'),
  ('yoga',        'contains', 'yoga',         5, 'Generic yoga - low priority')
ON CONFLICT (momence_pattern, discipline_code) DO NOTHING;


-- ─────────────────────────────────────────────────────────────────────────────
-- 5.  Cover requests
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.cover_requests (
  cover_request_id           uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  whatsapp_channel_id        uuid        REFERENCES public.whatsapp_channels(whatsapp_channel_id),
  raw_message                text        NOT NULL,
  message_timestamp          timestamptz,
  requesting_teacher_id      uuid        REFERENCES public.teachers(id),
  requesting_teacher_name_raw text,
  momence_session_id         bigint,
  class_date                 date,
  class_time                 time,
  class_end_time             time,
  studio                     text        CHECK (studio IN ('Robina', 'Palm Beach')),
  discipline_code            text,
  class_name_raw             text,
  confidence_score           numeric(4,3) NOT NULL DEFAULT 0
    CHECK (confidence_score >= 0 AND confidence_score <= 1),
  auto_review_required       boolean     NOT NULL DEFAULT true,
  parse_notes                text,
  status                     text        NOT NULL DEFAULT 'pending_review'
    CHECK (status IN (
      'pending_review', 'approved', 'covered',
      'cancelled', 'no_cover_needed', 'expired'
    )),
  admin_notes                text,
  reviewed_by                text,
  reviewed_at                timestamptz,
  created_at                 timestamptz DEFAULT now(),
  updated_at                 timestamptz DEFAULT now()
);


-- ─────────────────────────────────────────────────────────────────────────────
-- 6.  Cover candidates  (teachers contacted per request)
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.cover_candidates (
  cover_candidate_id   uuid     PRIMARY KEY DEFAULT gen_random_uuid(),
  cover_request_id     uuid     NOT NULL
    REFERENCES public.cover_requests(cover_request_id) ON DELETE CASCADE,
  teacher_id           uuid     NOT NULL REFERENCES public.teachers(id),
  match_score          int      NOT NULL DEFAULT 0,
  matched_grade        int,
  matched_discipline   text,
  contact_channels     text[]   NOT NULL DEFAULT '{}',
  contacted_at         timestamptz,
  response             text CHECK (response IN ('accepted', 'declined', 'no_response', NULL)),
  responded_at         timestamptz,
  is_confirmed         boolean  NOT NULL DEFAULT false,
  created_at           timestamptz DEFAULT now(),
  UNIQUE (cover_request_id, teacher_id)
);


-- ─────────────────────────────────────────────────────────────────────────────
-- 7.  Cover notifications log
-- ─────────────────────────────────────────────────────────────────────────────

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'cover_notification_type') THEN
    CREATE TYPE cover_notification_type AS ENUM (
      'cover_opportunity',
      'cover_confirmed',
      'cover_no_longer_needed',
      'cover_reminder',
      'cancellation',
      'class_transfer'
    );
  END IF;
END
$$;

CREATE TABLE IF NOT EXISTS public.cover_notifications (
  cover_notification_id   uuid                    PRIMARY KEY DEFAULT gen_random_uuid(),
  cover_request_id        uuid                    NOT NULL
    REFERENCES public.cover_requests(cover_request_id) ON DELETE CASCADE,
  cover_candidate_id      uuid
    REFERENCES public.cover_candidates(cover_candidate_id),
  notification_type       cover_notification_type NOT NULL,
  channel                 text                    NOT NULL
    CHECK (channel IN ('whatsapp_channel', 'whatsapp_direct', 'email')),
  recipient_type          text                    NOT NULL
    CHECK (recipient_type IN ('teacher', 'admin', 'client')),
  recipient_identifier    text,
  message_body            text    NOT NULL,
  sent_at                 timestamptz,
  delivered               boolean,
  delivery_notes          text,
  created_at              timestamptz DEFAULT now()
);


-- ─────────────────────────────────────────────────────────────────────────────
-- 8.  WhatsApp monitoring run log
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.whatsapp_monitor_runs (
  monitor_run_id    uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  started_at        timestamptz NOT NULL DEFAULT now(),
  completed_at      timestamptz,
  channels_checked  text[],
  messages_read     int         NOT NULL DEFAULT 0,
  requests_found    int         NOT NULL DEFAULT 0,
  run_status        text        NOT NULL DEFAULT 'running'
    CHECK (run_status IN ('running', 'completed', 'failed', 'partial')),
  error_message     text,
  run_notes         text
);


-- ─────────────────────────────────────────────────────────────────────────────
-- 9.  Indexes
-- ─────────────────────────────────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_cover_requests_status   ON public.cover_requests(status);
CREATE INDEX IF NOT EXISTS idx_cover_requests_date     ON public.cover_requests(class_date);
CREATE INDEX IF NOT EXISTS idx_cover_requests_created  ON public.cover_requests(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_cover_requests_channel  ON public.cover_requests(whatsapp_channel_id);
CREATE INDEX IF NOT EXISTS idx_cover_candidates_req    ON public.cover_candidates(cover_request_id);
CREATE INDEX IF NOT EXISTS idx_cover_candidates_teach  ON public.cover_candidates(teacher_id);
CREATE INDEX IF NOT EXISTS idx_cover_candidates_conf   ON public.cover_candidates(is_confirmed) WHERE is_confirmed = true;
CREATE INDEX IF NOT EXISTS idx_cover_notif_request     ON public.cover_notifications(cover_request_id);
CREATE INDEX IF NOT EXISTS idx_teachers_whatsapp       ON public.teachers(whatsapp_phone);
CREATE INDEX IF NOT EXISTS idx_teachers_momence_ref    ON public.teachers(momence_ref);


-- ─────────────────────────────────────────────────────────────────────────────
-- 10. updated_at trigger
-- ─────────────────────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = now(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS cover_requests_updated_at ON public.cover_requests;
CREATE TRIGGER cover_requests_updated_at
  BEFORE UPDATE ON public.cover_requests
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS whatsapp_channels_updated_at ON public.whatsapp_channels;
CREATE TRIGGER whatsapp_channels_updated_at
  BEFORE UPDATE ON public.whatsapp_channels
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- =============================================================================
-- Migration complete.
-- New tables:  whatsapp_channels, discipline_mappings, system_config,
--              cover_requests, cover_candidates, cover_notifications,
--              whatsapp_monitor_runs
-- Modified:    teachers (+ whatsapp_phone, + contact_preference)
-- New type:    cover_notification_type
-- =============================================================================
