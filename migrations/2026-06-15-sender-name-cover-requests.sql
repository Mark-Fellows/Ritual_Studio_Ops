-- Migration: 2026-06-15-sender-name-cover-requests.sql
-- Purpose : Add sender_name to cover_requests so the dashboard can display
--           the original WhatsApp poster even when the teacher field is later
--           edited.
-- Shared DB risk: rfjygyqijwgkmxboddup is shared by all four Ritual apps.
--                 This migration adds a nullable TEXT column only — no NOT NULL,
--                 no default, no FK — so existing rows are unaffected and the
--                 other apps are not impacted.
-- Apply   : via Supabase MCP apply_migration AFTER Mark reviews and approves.
-- Verify  : SELECT COUNT(*) FROM cover_requests WHERE sender_name IS NOT NULL;

-- ── 1. Add the column ─────────────────────────────────────────────────────────
ALTER TABLE cover_requests
    ADD COLUMN IF NOT EXISTS sender_name TEXT;

-- ── 2. Backfill from whatsapp_messages ───────────────────────────────────────
-- Pass A: exact match on (channel_id, message_timestamp) — most reliable.
-- Pass B: fallback match on raw text — covers the ~33 pre-2026-05-17 rows
--         whose whatsapp_messages.message_timestamp is NULL.
-- Only WhatsApp-sourced rows are updated (source = 'whatsapp').
-- Manual entries (source IS NULL or source != 'whatsapp') are left NULL.

UPDATE cover_requests cr
SET sender_name = (
    SELECT wm.teacher_sender_name
    FROM   whatsapp_messages wm
    WHERE  (
               -- Pass A: channel + timestamp exact match
               (wm.channel_id = cr.whatsapp_channel_id
                AND cr.message_timestamp IS NOT NULL
                AND wm.message_timestamp IS NOT NULL
                AND wm.message_timestamp = cr.message_timestamp)
           OR
               -- Pass B: raw-text fallback (only when Pass A cannot apply)
               (wm.raw_whatsapp_text = cr.raw_message
                AND cr.raw_message IS NOT NULL
                AND cr.raw_message <> '')
           )
    ORDER BY
        -- Prefer Pass A over Pass B when both would match
        CASE
            WHEN wm.channel_id = cr.whatsapp_channel_id
                 AND cr.message_timestamp IS NOT NULL
                 AND wm.message_timestamp IS NOT NULL
                 AND wm.message_timestamp = cr.message_timestamp
            THEN 0
            ELSE 1
        END
    LIMIT 1
)
WHERE cr.source = 'whatsapp'
  AND cr.sender_name IS NULL;

-- ── 3. Spot-check — run this after applying to confirm backfill coverage ─────
-- SELECT
--     COUNT(*)                                            AS total_whatsapp,
--     COUNT(*) FILTER (WHERE sender_name IS NOT NULL)    AS backfilled,
--     COUNT(*) FILTER (WHERE sender_name IS NULL)        AS still_null
-- FROM cover_requests
-- WHERE source = 'whatsapp';
