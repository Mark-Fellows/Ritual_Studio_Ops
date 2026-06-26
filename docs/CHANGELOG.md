# Ritual Studio Ops — Master Changelog

All significant changes to schema, code, configuration, and documentation across all four Ritual technology projects, in reverse chronological order.

Individual project changelogs are NOT the authoritative record from Phase 0 onwards — this file is. Add a one-line entry here first, then write detail in the project-level file if needed.

Format: `YYYY-MM-DD | Project | Summary | Files changed`

2026-06-26 | Cover Management | WhatsApp monitor: add dismiss_wa_error_dialog() — detects WhatsApp Web internal error modal ("We encountered a problem...") that blocks all pointer events while browser_manager reports healthy; auto-reloads page and re-waits for #pane-side. Called in wait_for_wa_loaded() and at top of navigate_to_channel(). Root cause of today's feed blackout (12+ runs collected 0 messages). | stage2/whatsapp_monitor.py

2026-06-22 | Cover Management (legacy) | cover_dashboard.html polish (v1.3.36 -> v1.3.37): (1) Cancelled box number now matches the other boxes — removed a leftover `.stat-card.neutral .stat-value { font-size:13px !important; line-height:1.3 }` rule from the old Last-Message box, so it renders at 28px on the same baseline (muted grey). (2)+(3) Moved "Show duplicates" out of the filter grid onto the actions row (left), sharing one tight row with "Clear All Filters" (right) directly under the grid — removes the orphan row/gap. (4) "New Request" restyled to match "Export to Excel" (same .export-xl-btn shape + dark-green colour); Collapse All already shares the shape (outline). | Ritual_Cover_Management/public/cover_dashboard.html


2026-06-22 | Cover Management (legacy) | cover_dashboard.html layout tweaks (v1.3.35 -> v1.3.36): filter bar now vertically centred with uniform 13px text; Collapse-All + New Request pushed to the right (margin-left:auto), last-message stays left. Advanced Filters: Day of Week moved to sit beside Time of Day and no longer spans full width (grid-column: span 2), Cover Type moved after it — packs the panel into fewer rows. | Ritual_Cover_Management/public/cover_dashboard.html

2026-06-22 | Cover Management (legacy) | cover_dashboard.html UI pass (v1.3.34 -> v1.3.35): (1) Future-only checkbox now PERSISTS across loads via localStorage (cd_futureOnly) and is restored on open — fixes it reverting to checked. (2) Stat boxes now show "(Prior nn)" (count not in the future) beside the big number, for Needs Review / Approved / Cancelled. (3) 5th box "Last Message Retrieved" replaced by a clickable "Cancelled" box; the last-message readout moved into the filter bar. (4) Removed redundant filter tabs (Needs Review/Approved/Covered/Cancelled) since the boxes already filter; kept All + No Cover Needed. (5) Moved "Show duplicates" into Advanced Filters. (6) Removed the read-only RSO banner. (7) "Copy for WhatsApp" recoloured to match "Export to Excel" (#1d6f42). (8) Added small icons to each box (clipboard / tick / green-check / hourglass / no-entry). | Ritual_Cover_Management/public/cover_dashboard.html

