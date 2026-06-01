# Ritual Cost Tracking - Design Plan (separate workstream)

Date: 2026-06-01
Status: DRAFT - planning only. Standalone from the Teacher Applications feature.
Owner: TBC

This is a separate thread from the Teacher Applications change. It is recorded here
because the cost ledger is cross-cutting across all four Ritual apps and sits closest
to the existing finance-cashflow.html work, not inside Teacher Management. Execute it
under its own change cycle (SOURCE_OF_TRUTH check, migration approval, changelog).

---

## 1. Purpose

A single place to record and track ongoing costs across all Ritual technology:
API fees (Anthropic, Gemini, etc.), SaaS licences and subscriptions (Supabase,
Cloudflare, Momence, WhatsApp/Meta, email), per-use fees, and one-off charges. Enables
a monthly/annual view of run-rate, feeds the cashflow forecast, and attributes spend to
the app or service that incurs it.

---

## 2. Why separate from Teacher Applications

- Different domain (financial ledger vs intake workflow); no dependency between them.
- Cross-cutting: must capture spend from all four apps plus new feature costs.
- Cleaner change control and rollback when the two are not mixed.

The Teacher Applications feature will, once live, contribute two cost rows here:
Supabase email/auth usage and WhatsApp messaging (Meta Cloud API, when adopted).

---

## 3. Target system

Merged app (Ritual Studio Ops), per SOURCE_OF_TRUTH. Likely a new same-origin page
`Ritual_Studio_Ops/app/cost-tracker.html` (or a section added to finance-cashflow.html).
Confirm placement before build. Shared Supabase project rfjygyqijwgkmxboddup.

---

## 4. Proposed schema (additive)

Migration file (when greenlit): Ritual_Studio_Ops/migrations/YYYY-MM-DD-cost-tracking.sql

Table `cost_items`:
- id            uuid PK default gen_random_uuid()
- app           text   -- which Ritual app/project (teacher_mgmt, cover, dashboard, momence, shared)
- vendor        text   -- Anthropic, Supabase, Cloudflare, Meta, Momence, etc.
- category      text   -- api | licence | subscription | usage | one_off
- description   text
- amount        numeric(12,2)
- currency      text default 'AUD'
- recurrence    text   -- monthly | annual | one_off | usage
- billing_start date
- billing_end   date   -- null for open-ended subscriptions
- status        text default 'active'  -- active | cancelled | trial
- notes         text
- created_at    timestamptz default now()
- updated_at    timestamptz default now()

Optional `cost_actuals` (if tracking real invoiced amounts over time, distinct from the
planned/standing amount): id, cost_item_id FK, period (date), amount, currency, source,
created_at. Lets usage-based costs (API spend) be logged per month against a standing
item. Decide whether this is needed in v1 or deferred.

RLS: authenticated read for finance-capable roles; restrict writes to developer/
administrator. Follow the SECURITY DEFINER role-check pattern; never reference the
protected table inside its own policy (L-TM-04).

---

## 5. UI

- A table of cost items with filters by app, vendor, category, recurrence, status.
- Summary KPIs: monthly run-rate (normalise annual/12, monthly x1), annualised total,
  spend by app and by vendor.
- Add/Edit modal for a cost item. Optional monthly actuals entry if cost_actuals is in.
- Same Ritual design tokens; direct-REST + cachedSession conventions; sbClient naming.
- Feed the figures into finance-cashflow.html opex assumptions where useful.

---

## 6. Seed data to gather

Anthropic API, Gemini API, Supabase plan, Cloudflare Pages/Workers, Momence
subscription, Meta/WhatsApp messaging, email/SMTP, any domains, Twilio (if used),
Power BI/Microsoft 365, and any other licences. Amounts, currency, recurrence, and
billing dates for each.

---

## 7. Build sequence (when started)

1. Confirm placement (new page vs finance-cashflow section) and whether cost_actuals
   is in v1.
2. Write migration -> review -> apply -> verify.
3. Build the page/section; wire CRUD and summaries.
4. Seed current known costs.
5. Local review -> deploy -> commit -> docs (CHANGELOG, DOCS_INDEX, LESSONS_LEARNED).

---

## 8. Open items

1. Page placement: standalone cost-tracker.html or a section of finance-cashflow.html?
2. Track invoiced actuals per period (cost_actuals), or standing amounts only in v1?
3. Which roles may view and edit cost data?
4. Multi-currency: keep AUD only, or store native currency + an FX note?
