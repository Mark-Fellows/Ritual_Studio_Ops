# ⚡ Quick Start Guide - Momence Automation

## What Changed?
Your script was trying to automate form submission (which froze). Now it uses **saved cookies** like the working `Momence_bookings_update.py` script does.

## One-Time Setup (First Run Only)

### Option A: Easy Setup (Recommended)
```bash
python momence_first_login_setup.py
```
This script will:
1. Open Chrome with login page
2. Wait for you to manually log in
3. Save cookies automatically
4. Done! ✅

### Option B: Manual Setup
See `MOMENCE_FIRST_RUN_SETUP.md` for detailed instructions.

## Run the Automation (Every Run After Setup)

```bash
python Momence_no_card_customers.py
```

That's it! The script will:
- Load saved cookies ✅
- Run completely unattended ✅
- Update your master files ✅
- Log all results ✅

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "No cookie pickle found" | Run setup script first (see above) |
| Script stops working | Cookies expired - run setup script again |
| Chrome window doesn't appear | Check taskbar, it may be in background |

## Files You Need to Know About

| File | Purpose |
|------|---------|
| `momence_first_login_setup.py` | **Run this first!** One-time setup |
| `Momence_no_card_customers.py` | Main automation (run daily/weekly) |
| `momence_cookies.pickle` | Auto-created. Your session cookies |
| `MOMENCE_FIRST_RUN_SETUP.md` | Detailed setup guide |

## Why This Works Better

✅ No form submission automation (no freezing)
✅ Uses proven cookie-based authentication
✅ Same pattern as working scripts
✅ Handles 2FA/authenticator automatically
✅ Works with Windows Task Scheduler
✅ Zero manual interaction after setup

## Need Help?

- **Setup Issues**: See `MOMENCE_FIRST_RUN_SETUP.md`
- **Automation Issues**: Check `FIX_SUMMARY.md` for technical details
- **Working Example**: Look at `Momence_bookings_update.py`

---

**TL;DR**:
1. Run `python momence_first_login_setup.py` once
2. Then run `python Momence_no_card_customers.py` whenever you want
3. Everything else is automatic! 🎉
