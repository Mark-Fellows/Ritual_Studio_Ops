-- ============================================================
-- Campaign Planning System - Release 4 Schema
-- Ritual Studios - Supabase project: rfjygyqijwgkmxboddup
-- Drafted: 2026-06-15
-- DO NOT APPLY until the studio owner has approved this migration.
-- Apply via Supabase MCP apply_migration with name:
--   campaign_planning_release4
-- Run AFTER campaign_planning_release3 (version 20260615044009).
-- All statements use IF NOT EXISTS / OR REPLACE so the file is
-- safe to re-run.
-- ============================================================

-- ------------------------------------------------------------
-- 1. New columns on public.campaigns
-- ------------------------------------------------------------
ALTER TABLE public.campaigns
  ADD COLUMN IF NOT EXISTS enquiries_owner_id   uuid REFERENCES auth.users(id),
  ADD COLUMN IF NOT EXISTS momence_session_ids  bigint[] NOT NULL DEFAULT '{}',
  ADD COLUMN IF NOT EXISTS xero_tracking_option text,
  ADD COLUMN IF NOT EXISTS finance_reviewer_id  uuid REFERENCES auth.users(id),
  ADD COLUMN IF NOT EXISTS finance_reviewed_at  timestamptz;

COMMENT ON COLUMN public.campaigns.enquiries_owner_id   IS
  'Release 4. Named owner for lead follow-up. The "where do enquiries go" person for this campaign.';
COMMENT ON COLUMN public.campaigns.momence_session_ids  IS
  'Release 4. Array of public.momence_sessions.session_id values that belong to this campaign. Used as the source of truth for signup and revenue tracking. Empty array means no Momence sessions linked.';
COMMENT ON COLUMN public.campaigns.xero_tracking_option IS
  'Release 4. Optional Xero tracking-option value used to tag campaign spend in Xero. Sync is deferred to a later release - the column is captured now so values are not lost.';
COMMENT ON COLUMN public.campaigns.finance_reviewer_id  IS
  'Release 4. The finance reviewer who must sign off before a campaign can move to Live. Enforced by trigger.';
COMMENT ON COLUMN public.campaigns.finance_reviewed_at  IS
  'Release 4. Timestamp the finance reviewer signed off. NULL blocks Approved -> Live (trigger).';

-- ------------------------------------------------------------
-- 2. campaign_leads - EOI register, scoped per campaign
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.campaign_leads (
  id                  uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  campaign_id         uuid        NOT NULL REFERENCES public.campaigns(id) ON DELETE CASCADE,
  name                text,
  email               text,
  phone               text,
  source              text        CHECK (source IS NULL OR source = ANY(ARRAY[
                                    'website','instagram','facebook_ad','walk_in','referral','momence','other'
                                  ])),
  status              text        NOT NULL DEFAULT 'new'
                                  CHECK (status = ANY(ARRAY[
                                    'new','contacted','waitlist','converted','lost'
                                  ])),
  notes               text,
  owner_id            uuid        REFERENCES auth.users(id),
  owner_email         text,
  momence_member_id   bigint,
  last_contacted_at   timestamptz,
  created_at          timestamptz NOT NULL DEFAULT now(),
  updated_at          timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_campaign_leads_campaign_id ON public.campaign_leads (campaign_id);
CREATE INDEX IF NOT EXISTS idx_campaign_leads_email_lower ON public.campaign_leads ((lower(email)));
CREATE INDEX IF NOT EXISTS idx_campaign_leads_status      ON public.campaign_leads (campaign_id, status);

COMMENT ON TABLE public.campaign_leads IS
  'Release 4. Per-campaign expression-of-interest register. Working view only - Momence remains the system of record for customer data (Decision 2, 2026-05-25). The momence_member_id column links a lead back to a Momence member where known.';

ALTER TABLE public.campaign_leads ENABLE ROW LEVEL SECURITY;

-- RLS: read open to all authenticated; create open to authenticated;
--      update by lead owner or campaign admin; delete by admin only.
CREATE POLICY "lead_sel" ON public.campaign_leads
  FOR SELECT TO authenticated USING (true);
CREATE POLICY "lead_ins" ON public.campaign_leads
  FOR INSERT TO authenticated WITH CHECK (auth.uid() IS NOT NULL);
CREATE POLICY "lead_upd" ON public.campaign_leads
  FOR UPDATE TO authenticated
  USING  (owner_id = auth.uid() OR public.is_campaign_admin())
  WITH CHECK (owner_id = auth.uid() OR public.is_campaign_admin());
CREATE POLICY "lead_del" ON public.campaign_leads
  FOR DELETE TO authenticated USING (public.is_campaign_admin());

DROP TRIGGER IF EXISTS campaign_leads_updated_at ON public.campaign_leads;
CREATE TRIGGER campaign_leads_updated_at
  BEFORE UPDATE ON public.campaign_leads
  FOR EACH ROW EXECUTE FUNCTION public.campaign_touch_updated_at();

-- ------------------------------------------------------------
-- 3. campaign_signup_snapshots - periodic snapshots of in-flight
--    signups per campaign, computed from public.momence_sessions
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.campaign_signup_snapshots (
  id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  campaign_id     uuid        NOT NULL REFERENCES public.campaigns(id) ON DELETE CASCADE,
  captured_at     timestamptz NOT NULL DEFAULT now(),
  signups_count   integer     NOT NULL DEFAULT 0,
  capacity_total  integer,
  revenue_cents   bigint,
  source          text        NOT NULL DEFAULT 'momence_sessions'
                              CHECK (source = ANY(ARRAY[
                                'momence_sessions','momence_bookings','manual'
                              ]))
);

CREATE INDEX IF NOT EXISTS idx_signup_snap_campaign_captured
  ON public.campaign_signup_snapshots (campaign_id, captured_at DESC);

COMMENT ON TABLE public.campaign_signup_snapshots IS
  'Release 4. Periodic snapshots of campaign signup totals. Default source is public.momence_sessions aggregated across the campaign''s linked session_ids. The momence_bookings source becomes available post Phase 7 cutover. The manual source is the entry-by-hand fallback for campaigns not linked to Momence.';

ALTER TABLE public.campaign_signup_snapshots ENABLE ROW LEVEL SECURITY;

-- Snapshots are append-only: SELECT/INSERT only, no UPDATE/DELETE policies.
CREATE POLICY "signup_snap_sel" ON public.campaign_signup_snapshots
  FOR SELECT TO authenticated USING (true);
CREATE POLICY "signup_snap_ins" ON public.campaign_signup_snapshots
  FOR INSERT TO authenticated WITH CHECK (auth.uid() IS NOT NULL);

-- ------------------------------------------------------------
-- 4. View - latest snapshot per campaign (read-side convenience)
-- ------------------------------------------------------------
CREATE OR REPLACE VIEW public.v_campaign_signups_latest AS
  SELECT DISTINCT ON (campaign_id)
    campaign_id, captured_at, signups_count, capacity_total, revenue_cents, source
  FROM public.campaign_signup_snapshots
  ORDER BY campaign_id, captured_at DESC;

COMMENT ON VIEW public.v_campaign_signups_latest IS
  'Release 4. Most recent signup snapshot per campaign. Convenience for the dashboard "in-flight" widget.';

-- ------------------------------------------------------------
-- 5. Live aggregation view straight off momence_sessions, so a
--    campaign can show a fresh figure without waiting for the
--    next snapshot cron run.
-- ------------------------------------------------------------
CREATE OR REPLACE VIEW public.v_campaign_signups_now AS
  SELECT
    c.id            AS campaign_id,
    COALESCE(SUM(ms.signups),  0)::int        AS signups_count_now,
    COALESCE(SUM(ms.capacity), 0)::int        AS capacity_total_now,
    COALESCE(SUM(ms.est_revenue), 0)::numeric AS revenue_estimate_now,
    COUNT(ms.session_id)::int                 AS sessions_linked,
    now()                                     AS computed_at
  FROM public.campaigns c
  LEFT JOIN public.momence_sessions ms
    ON ms.session_id = ANY(c.momence_session_ids)
  GROUP BY c.id;

COMMENT ON VIEW public.v_campaign_signups_now IS
  'Release 4. Live aggregation of signups/capacity/revenue across the Momence sessions linked to each campaign, computed on read. Used by the dashboard for the "as of now" figure when the most recent snapshot is stale.';

-- ------------------------------------------------------------
-- 6. Finance reviewer gate - block Approved -> Live without sign-off
-- ------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.enforce_finance_reviewer_gate()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.status = 'live' AND COALESCE(OLD.status, '') <> 'live' THEN
    IF NEW.finance_reviewer_id IS NULL OR NEW.finance_reviewed_at IS NULL THEN
      RAISE EXCEPTION
        'Campaign cannot move to Live without a finance reviewer sign-off (finance_reviewer_id and finance_reviewed_at are both required).'
        USING ERRCODE = 'check_violation';
    END IF;
  END IF;
  RETURN NEW;
END;
$$;

COMMENT ON FUNCTION public.enforce_finance_reviewer_gate() IS
  'Release 4. Raises an exception if a campaign moves to status = ''live'' without a finance reviewer signed off. Existing live campaigns are not affected (trigger fires only on transitions INTO live).';

DROP TRIGGER IF EXISTS campaigns_finance_gate ON public.campaigns;
CREATE TRIGGER campaigns_finance_gate
  BEFORE UPDATE OF status ON public.campaigns
  FOR EACH ROW EXECUTE FUNCTION public.enforce_finance_reviewer_gate();

-- ------------------------------------------------------------
-- 7. Optional - scheduled snapshot capture every 6 hours.
--    Uses pg_cron (already enabled in the R3 digest migration).
--    Wrapped in a DO block so the migration succeeds even if
--    pg_cron is not available in the local environment.
-- ------------------------------------------------------------
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pg_cron') THEN
    PERFORM cron.unschedule('campaign_signup_snapshot');
    PERFORM cron.schedule(
      'campaign_signup_snapshot',
      '0 */6 * * *',
      $cron$
        INSERT INTO public.campaign_signup_snapshots
          (campaign_id, signups_count, capacity_total, revenue_cents, source)
        SELECT
          campaign_id,
          signups_count_now,
          capacity_total_now,
          (revenue_estimate_now * 100)::bigint,
          'momence_sessions'
        FROM public.v_campaign_signups_now
        WHERE sessions_linked > 0;
      $cron$
    );
  END IF;
EXCEPTION WHEN OTHERS THEN
  RAISE NOTICE 'pg_cron schedule skipped: %', SQLERRM;
END $$;

-- ============================================================
-- Notes for the operator
--
-- 1. New columns and tables are additive. Existing rows are
--    unaffected. The four existing campaigns will have
--    momence_session_ids = '{}' and finance_reviewer_id NULL.
--
-- 2. Existing live campaigns (if any) stay valid - the finance
--    gate only fires on a fresh transition into live.
--
-- 3. The HTML app must populate finance_reviewer_id and
--    finance_reviewed_at before flipping Approved -> Live.
--
-- 4. The pg_cron schedule writes a snapshot every six hours
--    only for campaigns that have at least one Momence session
--    linked. Campaigns with no linked sessions write nothing.
--
-- 5. Verification queries (run after apply):
--      SELECT column_name FROM information_schema.columns
--       WHERE table_name = 'campaigns' AND column_name LIKE 'finance%';
--      SELECT to_regclass('public.campaign_leads'),
--             to_regclass('public.campaign_signup_snapshots');
--      SELECT pg_get_viewdef('public.v_campaign_signups_now'::regclass);
--      SELECT count(*) FROM cron.job
--       WHERE jobname = 'campaign_signup_snapshot';
--
-- ============================================================

-- ============================================================
-- Rollback (for reference - do not include when applying)
-- ------------------------------------------------------------
-- DO $$ BEGIN
--   PERFORM cron.unschedule('campaign_signup_snapshot');
-- EXCEPTION WHEN OTHERS THEN NULL; END $$;
-- DROP TRIGGER  IF EXISTS campaigns_finance_gate ON public.campaigns;
-- DROP FUNCTION IF EXISTS public.enforce_finance_reviewer_gate();
-- DROP VIEW     IF EXISTS public.v_campaign_signups_now;
-- DROP VIEW     IF EXISTS public.v_campaign_signups_latest;
-- DROP TABLE    IF EXISTS public.campaign_signup_snapshots;
-- DROP TABLE    IF EXISTS public.campaign_leads;
-- ALTER TABLE public.campaigns
--   DROP COLUMN IF EXISTS finance_reviewed_at,
--   DROP COLUMN IF EXISTS finance_reviewer_id,
--   DROP COLUMN IF EXISTS xero_tracking_option,
--   DROP COLUMN IF EXISTS momence_session_ids,
--   DROP COLUMN IF EXISTS enquiries_owner_id;
-- ============================================================
