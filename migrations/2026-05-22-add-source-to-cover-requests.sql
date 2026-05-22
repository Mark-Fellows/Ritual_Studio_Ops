-- Migration: add source column to cover_requests
-- Applied: 2026-05-22
-- Phase: Manual cover request entry (post-Phase 5)
-- Additive only; parallel-run safe.

ALTER TABLE cover_requests ADD COLUMN IF NOT EXISTS source TEXT DEFAULT 'whatsapp';

-- Values:
--   'whatsapp'  (default) — created by the CM WhatsApp pipeline (stages 1-2)
--   'manual'              — created manually via the RSO New Manual Request modal
