# Quick Start - Run Now! 🚀

## Your Setup is Complete

✅ Script updated to load credentials from `.env`
✅ `.env` file has your Momence credentials
✅ python-dotenv is installed
✅ Script syntax is valid

---

## Run the Script Now

### Option 1: Quick Test Run
```powershell
cd "C:\Users\markj\OneDrive - MFPL\Documents\Customer Projects\Ritual\Momence_data"
python Momence_no_card_customers.py
```

### Option 2: With Output Logging
```powershell
cd "C:\Users\markj\OneDrive - MFPL\Documents\Customer Projects\Ritual\Momence_data"
python Momence_no_card_customers.py | Tee-Object -FilePath run_output.log
```

### Option 3: Debug Mode (show all output)
```powershell
cd "C:\Users\markj\OneDrive - MFPL\Documents\Customer Projects\Ritual\Momence_data"
python -u Momence_no_card_customers.py
```

---

## What to Expect

### Initial Startup (30-60 seconds)
```
[INFO] Loaded credentials from .env file
[INFO] Checking if we need to log in...
[INFO] Not logged in - attempting automatic login...
[INFO] Attempting to log in to Momence...
[DEBUG] Navigated to login page
[DEBUG] Waiting for email/username input field...
[DEBUG] Entering username...
[DEBUG] Entering password...
[DEBUG] Clicking login button...
[INFO] Login successful - redirected from login page
[INFO] Cookies saved to pickle.
```

### Report Processing (2-5 minutes per report)
```
============================================================
[INFO] Starting No Card Customers Report Download
============================================================
[INFO] Opening CRM report URL...
[INFO] Waiting for CSV to be fully downloaded...
[DEBUG] Elapsed: 45s | New CSVs detected: 1 | Temp files: 0
[INFO] New CSV detected: C:\...\momence_no_card_customers_...
[INFO] Reading new CSV: ...
[INFO] Added Customer Number column (245 mapped)
[INFO] Rows before de-duplication: 127
[INFO] Rows after de-duplication: 123
[INFO] Removed 4 duplicate rows.
[INFO] Master CSV updated: ...
[INFO] CSV moved to archive: ...
[INFO] 8 records added to No Card Customers
```

### Completion
```
[INFO] All processing complete.
============================================================
```

---

## After Running

### Check Results

1. **Review Log File**
   ```powershell
   Get-Content Momence_batch_log.txt -Tail 50
   ```
   Look for: `X records added to [Report Name]`

2. **Verify CSV Files Updated**
   ```powershell
   ls master_*.csv | Select-Object Name, LastWriteTime, Length
   ```

3. **Check Archive**
   ```powershell
   ls momence_downloads/Archive/
   ```

---

## Troubleshooting

### If Login Fails
1. Check `.env` file has correct username/password
2. Look for `debug_login_page.html` for HTML structure issues
3. Check `Momence_batch_log.txt` for error details
4. Verify internet connection

### If No Reports Download
1. Check `Momence_batch_log.txt` for errors
2. Verify Momence is accessible in your browser
3. Check if page selectors changed (menu button, export option)
4. Look for `debug_page_source*.html` files for structure changes

### If Script Hangs
- Press `Ctrl+C` to stop
- Browser window may still be open - close it manually
- Check logs for where it stopped
- Try running again with fewer reports if needed

---

## Success Indicators

✅ Script completes without errors
✅ `[INFO] X records added to` messages appear
✅ Master CSV files are updated (check timestamp)
✅ Momence_batch_log.txt shows "records added" entries
✅ momence_downloads/Archive/ has new files

---

## Schedule for Automated Runs

Once verified working, schedule in Windows Task Scheduler:

1. Open Task Scheduler
2. Create Basic Task
3. **General Tab**:
   - Name: "Momence Data Export"
   - Description: "Downloads reports from Momence"
   - Run with highest privileges: ✓

4. **Triggers Tab**:
   - Daily at specific time (e.g., 2:00 AM)

5. **Actions Tab**:
   - Program: `python`
   - Arguments: `"C:\Users\markj\OneDrive - MFPL\Documents\Customer Projects\Ritual\Momence_data\Momence_no_card_customers.py"`
   - Start in: `C:\Users\markj\OneDrive - MFPL\Documents\Customer Projects\Ritual\Momence_data`

6. Click OK to save

---

## Files to Monitor

After each run, check these files:

| File | What It Contains |
|------|-----------------|
| `Momence_batch_log.txt` | Detailed execution log |
| `master_no_card_customers.csv` | No Card customer records |
| `master_failed_penalties.csv` | Penalty charge records |
| `master_late_cancellations.csv` | Late cancellation records |
| `master_no_shows.csv` | No show records |
| `momence_cookies.pkl` | Saved authentication session |

---

## Need Help?

### Common Issues

**"Loaded credentials from .env file" but still login error**
- Verify username/password in `.env` are correct
- Test manually logging into Momence.com
- Check if 2FA is enabled (would cause login to fail)

**"Could not find email/username input field"**
- Momence UI may have changed
- Check `debug_login_page.html` to see actual HTML
- Selectors may need updating

**CSV not downloading**
- Menu button selector may have changed
- Export button selector may have changed
- Check `debug_page_source.html` for current structure
- Momence may have redesigned the report interface

---

## Ready to Go! 🎉

Your script is fully configured with:
- ✅ Automatic .env credential loading
- ✅ Automatic Momence login
- ✅ 4 reports to download
- ✅ Deduplication and archiving
- ✅ Comprehensive logging
- ✅ Resource cleanup

**Run it now:**
```powershell
python Momence_no_card_customers.py
```

Good luck! 🚀
