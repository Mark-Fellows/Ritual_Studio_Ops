-- ============================================================
-- Campaign Planning System - Release 5 Schema
-- AI assist, human-in-the-loop
-- Ritual Studios - Supabase project: rfjygyqijwgkmxboddup
-- Applied: 2026-06-15
-- ============================================================
-- Apply AFTER 05_campaign_planning_release4.sql.
-- Safe to re-run.
-- ============================================================

CREATE TABLE IF NOT EXISTS public.campaign_ai_log (
  id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  campaign_id     uuid        REFERENCES public.campaigns(id) ON DELETE CASCADE,
  section_id      uuid        REFERENCES public.campaign_sections(id) ON DELETE SET NULL,
  lead_id         uuid        REFERENCES public.campaign_leads(id) ON DELETE SET NULL,
  action          text        NOT NULL CHECK (action = ANY(ARRAY[
                                'generate_section_copy','draft_reply','consistency_check'
                              ])),
  user_prompt     text,
  result_text     text,
  model           text,
  tokens_input    integer,
  tokens_output   integer,
  invoked_by      uuid        REFERENCES auth.users(id),
  invoked_email   text,
  status          text        NOT NULL DEFAULT 'ok' CHECK (status = ANY(ARRAY['ok','error'])),
  error_message   text,
  created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_campaign_ai_log_campaign ON public.campaign_ai_log(campaign_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_campaign_ai_log_user     ON public.campaign_ai_log(invoked_by, created_at DESC);

COMMENT ON TABLE public.campaign_ai_log IS
  'Release 5. Append-only audit trail for the campaign-ai Edge Function. Every AI generation, reply draft and consistency check writes one row including token usage so cost is visible.';

ALTER TABLE public.campaign_ai_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY "ai_log_sel" ON public.campaign_ai_log
  FOR SELECT TO authenticated USING (true);
CREATE POLICY "ai_log_ins" ON public.campaign_ai_log
  FOR INSERT TO authenticated WITH CHECK (auth.uid() IS NOT NULL);

-- Rollback (commented):
-- DROP TABLE IF EXISTS public.campaign_ai_log;
